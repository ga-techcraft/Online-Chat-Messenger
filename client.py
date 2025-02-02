import sys
import select
import socket
import threading
import json
from modules import TCPProtocolHandler,UDPProtocolHandler

# ヘッダー(32バイト) : RoomNameSize(1バイト) | 0peration(1バイト) | State(1バイト) | OperationPayloadSize(29バイト)
# ボディ : 最初のRoomNameSizeバイトがルーム名で、その後にOperationPayloadSizeバイトが続く。
class TCPClient:
  # 役割：サーバーアドレスの設定とTCPソケットの作成
  # 戻り値：無し
   def __init__(self, server_ip, server_port):
      self.server_address = (server_ip, server_port)
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   
   # 役割：サーバーへの接続
   # 戻り値：真偽値(接続できたかどうか)
   def connect(self):
      try:
         self.sock.connect(self.server_address)
      except socket.error as e:
         print(f"TCP 接続エラー:{e}")
         return False
      print("TCPサーバーに接続しました。")
      return True
   
   # 役割：リクエストデータの送信、レスポンスデータの受信(2種類)
   # 戻り値：レスポンスデータ
   def send_request(self, request_data): 
    try:
      if request_data is None:
         print("不正なデータです。送信をスキップします。")
         return None

      # リクエストデータの送信
      # *1つのリクエストに対して最初は認証のレスポンスが返ってきて、認証に成功したら取得したいデータが受信できる。
      self.sock.send(request_data)

      print(f"{request_data}を送信しました。")

      print("データの送信")


      # ①レスポンスデータ(認証)の受信と解析
      auth_response_data = self.sock.recv(4096)
      print(f"auth_response{auth_response_data}を受信しました。")
      auth_response_data_parsed = TCPProtocolHandler.parse_data(auth_response_data)["operation_payload"]

      print("データの受信")
      
      # 認証に失敗した場合、ここで処理を終える。
      if not auth_response_data_parsed["auth_status"]:
        return auth_response_data_parsed
      
      print("認証成功")
      
      # ②レスポンスデータ(トークン、またはルーム一覧)の受信と解析
      processed_response_data = self.sock.recv(4096)
      processed_response_data_parsed = TCPProtocolHandler.parse_data(processed_response_data)["operation_payload"]

      print("データの作成完了")

      print("hello")
      return processed_response_data_parsed

    except socket.error as e:
      print(f"TCP 通信エラー:{e}")
      return None
    except Exception as e:
       print(f"予期しないエラーが発生しました:{e}")
       return None
  
   # 役割：TCPソケットの解放
   # 戻り値：無し
   def close(self):
      self.sock.close()
      print("TCP 接続を閉じました。")
   

# UDPプロトコルに基づいてサーバーとデータを送受信する
# ヘッダー: RoomNameSize（1 バイト）| TokenSize（1 バイト）
# ボディ: 最初の RoomNameSizeバイトはルーム名、次のTokenSizeバイトはトークン文字列、そしてその残りが実際のメッセージです。
class UDPClient:
   # 役割：サーバーアドレス、ソケット、ストップフラグの設定
   # 戻り値：無し
   def __init__(self, server_ip, server_port):
      self.server_address = (server_ip, server_port)
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.stop_event = threading.Event() # チャットを開始すると送信はメインスレッド、受信はワーカーズスレッドで行う。チャットの終了時にスレッド間でどちらも終了させるためにフラグを使う。
      self.sock.settimeout(1) # チャットの受信の常時ブロッキングを防ぐため
   
   # 役割：メッセージの送信
   # 戻り値：無し
   def send_message(self, message):
      # データの送信
      try:
        self.sock.sendto(message, self.server_address)
        print("メッセージを送信しました。")
      except socket.error as e:
        print(f"UDP 通信エラー:{e}")
      
   # 役割：メッセージの受信、メッセージの種類に応じた処理
   # 戻り値：無し
   def receive_messages(self):
      # フラグが立っていれば、受信を終了。
      while not self.stop_event.is_set():
        try:
          # データの受信
          chat_data, _ = self.sock.recvfrom(4096)

          print(f"{chat_data}を受信しました。")

          # データの解析
          parsed_message = UDPProtocolHandler.parse_message(chat_data)
          if parsed_message is None:
             continue
          parsed_message_content = parsed_message["content"]
          status = parsed_message_content["status"]
          user_name = parsed_message_content["user_name"]
          chat_data = parsed_message_content["chat_data"]

          # state=CLOSE:部屋が閉じられた時、state=TIMEPUT:タイムアウト時
          # stop_eventフラグを立てて受信を終了。
          if status == "CLOSE" or status == "TIMEOUT":
            print(chat_data)
            self.stop_event.set()
            break
          # state=CHAT:他のユーザーのメッセージを表示
          else:
            print(user_name + ":" + chat_data)
        except socket.timeout:
           continue
        except Exception as e:
           print(f"受信処理中に予期しないエラーが発生しました:{e}")
        
   # 役割：UDPソケットの解放
   # 戻り値：無し
   def close(self):
     self.sock.close()
     print("UDP 接続を閉じました。")
  

class ChatClient:
   # 役割：初期化
   # 戻り値：無し
   def __init__(self, tcp_client, udp_client):
      self.tcp_client = tcp_client
      self.udp_client = udp_client
      self.user_name = None
      self.room_token = () # (room, token)

   # 役割：ユーザーからデータの取得、データに応じた処理
   # 戻り値：無し
   def start(self):
      if not self.tcp_client.connect():
        print("TCPサーバーに接続できませんでした。終了します。")
        return
      
      self.user_name = input("ユーザー名を入力してください: ")

      try:
        while True:
          print("1: ルームを作成")
          print("2: ルームに参加")

          choice = input("選択してください: ")
          if choice == "1":
              room_name = input("ルーム名を入力してください。")
              self.create_room(room_name)
          elif choice == "2":
              self.join_room()
      except KeyboardInterrupt as e:
         print(e)
      except Exception as e:
         print(e)
      finally:
         self.close
   
   # 役割：リクエストデータの作成、ルームの作成依頼、ルームとトークンの保存、チャットの開始
   # 戻り値：無し
   def create_room(self, room_name):
      # リクエストデータの作成
      request_data = TCPProtocolHandler.make_create_room_request(room_name=room_name, user_name=self.user_name)

      # ルームの作成依頼
      operation_payload = self.tcp_client.send_request(request_data)

      # 例外が発生した場合
      if operation_payload is None:
         return

      # 認証の失敗や同名のルームが存在した場合
      if operation_payload["token"] is None:
        print(operation_payload["error_message"])
        return
      
      # ルームとトークンの保存
      self.room_token = (room_name, operation_payload["token"])

      # チャットの開始
      self.start_chat()
   
   # 役割：リクエストデータの作成、ルーム一覧の取得依頼、ルーム参加依頼、ルームとトークンの保存、チャットの開始
   # 戻り値：無し
   def join_room(self):
      # リクエストデータの作成
      request_data = TCPProtocolHandler.make_get_room_list_request(user_name=self.user_name)

      # ルーム一覧の取得依頼
      operation_payload = self.tcp_client.send_request(request_data)

      # 認証の失敗や通信エラーが発生した場合
      if operation_payload is None:
        return
      
      try:
        room_list = operation_payload["room_list"]
      except json.JSONDecodeError as e:
         print(f"ルーム一覧のデコードに失敗しました。")
         return

      # ルーム一覧の表示
      for room_name in room_list:
        print(room_name)

      selected_room_name = input("参加したいルームを選択してください。")

      print("まえ")

      # リクエストデータの作成
      request_data = TCPProtocolHandler.make_join_room_request(room_name=selected_room_name, user_name=self.user_name)

      print(request_data)

      print("なか")

      # ルームの参加依頼とトークンの取得
      operation_payload = self.tcp_client.send_request(request_data)


      if operation_payload is  None:
        return
      
      print("あと")
      
      # ルームとトークンの保存
      self.room_token = (selected_room_name, operation_payload["token"])

      # チャットの開始
      self.start_chat()

   # 役割：ルームの退出メッセージの作成と送信
   # 戻り値：無し
   def leave_room(self):
      print("ルームを退出します。")

      # 退出したことをサーバーに通知
      message = UDPProtocolHandler.make_leave_message(self.room_token[0], self.room_token[1])
      print(message)
      self.udp_client.send_message(message)

      self.room_token = ()
   
   # 役割：メッセージの受信を別スレッドで処理、ユーザーからメッセージデータの取得、メッセージデータの作成と送信
   # 戻り値：無し
   def start_chat(self):
    print("チャットを開始します。")
    # フラグを下ろしてチャットを開始
    self.udp_client.stop_event.clear()

    # メッセージの受信はワーカーズスレッドで処理
    recerve_thread = threading.Thread(target=self.udp_client.receive_messages, daemon=False)
    recerve_thread.start()

    # メッセージの入力と送信
    try:
      # フラグが立っていたら送信を終了
      while not self.udp_client.stop_event.is_set():
        # sys.stdinに入力データがある場合、readableリストにsys.stdinが格納され次の処理に進む。
        # 1秒間の間に何も入力がない場合も、次の処理に進む。
        # selectを使うことで、定期的にstop_eventフラグを確認しつつメッセージの入力が可能。
        # ちなみにinputを使うとユーザーが何も入力しない限りプログラムがブロックされてしまい、フラグの状態を確認できない。
        readable, _, _ = select.select([sys.stdin], [], [], 1)

        # 入力がある場合のみデータを取得。
        if readable:
          chat_data = sys.stdin.readline().strip() 

          # メッセージの作成
          message = UDPProtocolHandler.make_chat_message(self.room_token[0], self.room_token[1], self.user_name, chat_data)

          # メッセージの送信
          self.udp_client.send_message(message)

    except KeyboardInterrupt as e:
       print(e)
    finally:
       # チャット終了時はフラグを立てて、メッセージの入力も受信も終了させる。
       self.udp_client.stop_event.set()
       # ワーカーズスレッドの解放
       recerve_thread.join()
       # サーバーに退出したことを通知
       self.leave_room()
       print("チャットが閉じれました。")
   
   # 役割：TCPとUDPソケットのクローズ
   # 戻り値：無し
   def close(self):
      self.tcp_client.close()
      self.udp_client.close()

if __name__ == "__main__":
   server_ip = "127.0.0.1"
   tcp_port = 9022
   udp_port = 9014

   tcp_client = TCPClient(server_ip, tcp_port)
   udp_client = UDPClient(server_ip, udp_port)

   chat_client = ChatClient(tcp_client, udp_client)
   
   chat_client.start()



# chat開始時にサーバー側でアドレスの更新が必要だから、最初になにかしらの情報を入力させる。名前にしてもいいかも。つまり、名前はチャット参加時に都度決めれる。
# join_roomの処理はそれぞれ別の関数にして、ユーザーの入力は全てstartで行うようにする
# 名前でクライアントを区別して、更にチャット開始時に自動的にudpサーバー二メッセージを送信するようにしてポートを更新するのはどう？