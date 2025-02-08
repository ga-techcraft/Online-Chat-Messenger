import socket
import threading
from modules import TCPProtocolHandler,UDPProtocolHandler

# ★クラス毎の役割と連携
# 【役割】
# TCPProtocolHandler:TCPデータの作成、パース
# UDPProtocolHandler:UDPデータの作成、パース
# ChatClient:ユーザーインターフェースを提供し、ルームの作成、参加、チャット開始などの操作を処理
# TCPClient:TCP通信でのデータの送受信
# UDPClient:UDP通信でのデータの送受信
# 【連携】
# ChatClientでユーザーの要求を受信→TCP/UDPProtocolHandlerで送信データの作成→TCP/UDPClientでデータの送信と受信→TCP/UDPProtocolHandlerで受信データの解析→ChatClientでユーザーにデータ表示

# TCP通信でのデータの送受信
class TCPClient:
  def __init__(self, server_ip, tcp_port):
    self.server_address = (server_ip, tcp_port)
    self.sock = None

  # 役割：サーバーへの接続
  # 戻り値：真偽値（既に接続されている場合、または接続が成功した場合にTrueを返す。接続に失敗したらFalseを返す。）
  def connect(self):
    if self.sock:
      return True
    
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      self.sock.connect(self.server_address)
      return True
    except socket.error as e:
      return False
    
  # 役割：サーバーへリクエストを送信
  # 戻り値：レスポンスデータ
  def send_request(self, request):
    try:
      self.sock.send(request)

      response = self.sock.recv(4096)
      parsed_response = TCPProtocolHandler.parse_data(response)["operation_payload"]

      if parsed_response["error_message"]:
        return parsed_response
      
      response = self.sock.recv(4096)
      parsed_response = TCPProtocolHandler.parse_data(response)["operation_payload"]
      return parsed_response
    
    except socket.error as e:
      print(f"TCP通信エラー:{e}")
      return None
    except Exception as e:
      print(f"予期しないエラーが発生しました{e}")
      return None

  # 役割：サーバーとの接続を解除する
  # 戻り値：無し
  def disconnect(self):
    if not self.sock:
      return
    self.sock.close()
    self.sock = None
    print("TCP接続を終了しました。")

# UDP通信でのデータの送受信
class UDPClient:
  def __init__(self, server_ip, udp_port):
    self.server_address = (server_ip, udp_port)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.settimeout(1)

  # 役割：データの送信
  # 戻り値：無し
  def send_message(self, message):
      try:
        self.sock.sendto(message, self.server_address)
        # print("メッセージを送信しました。")
      except socket.error as e:
        print(f"UDP 通信エラー:{e}")

  # 役割：メッセージ受信
  # 戻り値：無し
  def recieve_message(self):
    while not is_chat_active.is_set():
      try:
        data, _ = self.sock.recvfrom(4096)
        parsed_data = UDPProtocolHandler.parse_message(data)["content"]
        # print(f"{parsed_data}を受信しました")

        # 通常のチャット時
        if parsed_data["type"] == "CHAT":
          print(f"{parsed_data['user_name']}: {parsed_data['chat_data']}")
        
        # チャットルームのクローズ時
        elif parsed_data["type"] == "CLOSE":
          is_chat_active.set()
          print(f"{parsed_data['chat_data']}")

        # クライアントのタイムアウト時
        elif parsed_data["type"] == "TIMEOUT":
          is_chat_active.set()
          print(f"{parsed_data['chat_data']}")

        # システム終了時(未実装)
        # elif parsed_data["type"] == "STOP":
        #   is_chat_active.set()
        #   print(f"{parsed_data['chat_data']}")
      except socket.timeout:
        continue

  # 役割：UDPソケットの解放
  # 戻り値：無し
  def close(self):
    self.sock.close()

# ユーザーインターフェースを提供し、ルームの作成、参加、チャット開始などの操作を処理。
class ChatClient:
  def __init__(self, tcp_client, udp_client):
    self.tcp_client = tcp_client
    self.udp_client = udp_client
    self.user_name = None
    self.room_token = () # (room, token)

  # 役割：ユーザーインターフェース
  # 戻り値：無し
  def play(self):

    try:
      while True:
        self.user_name = input("名前を入力してください。").strip()
        if not self.user_name:
          print("名前が入力されていません。")
          continue
        else:
          break

      while True:
        print("1: ルームを作成")
        print("2: ルームに参加")

        while True:
          choice = input("選択してください: ").strip()
          if not choice or (choice != "1" and choice != "2"):
            print("1または2を選択してください。")
          else:
            break

        if not self.tcp_client.connect():
          return
        
        if choice == "1":
            while True:
              room_name = input("ルーム名を入力してください。").strip()
              if not room_name:
                print("ルーム名が入力されていません。")
                continue
              else:
                break
            while True:
              password = input("パスワードを設定してください").strip()
              if not password:
                print("パスワードが入力されていません。")
                continue
              else:
                break
            # ルーム作成依頼
            token, error_messaage = self.create_room_request(room_name, password)
            if error_messaage:
              self.tcp_client.sock = None
              print(error_messaage)
              continue

        elif choice == "2":
            # ルーム一覧取得依頼
            room_list, error_messaage = self.get_room_list_request()
            if error_messaage:
              self.tcp_client.sock = None
              print(error_messaage)
              continue
            for room_name in room_list:
              print(room_name)
            while True:
              selected_room_name = input("参加したいルームを選択してください。").strip()
              if not selected_room_name:
                print("ルーム名を入力してください。")
                continue
              if selected_room_name not in room_list:
                print("入力されたルームは存在しません。")
                continue
              else:
                break
            while True:
              password = input("パスワードを入力してください。").strip()
              if not password:
                print("パスワードが入力されていません。")
                continue
              else:
                break

            # ルーム参加依頼
            token, error_messaage = self.join_room_request(selected_room_name, password)
            if error_messaage:
              self.tcp_client.sock = None
              print(error_messaage)
              continue

        if token:
          # チャットの開始
          self.tcp_client.disconnect()
          self.start_chat()

    except KeyboardInterrupt as e:
      print(e)
    except Exception as e:
      print(e)
    finally:
      self.udp_client.close()
      self.tcp_client.disconnect()
      print("システムを終了します。")

  # 役割：ルーム作成
  # 戻り値：成功=(トークン,None), 失敗=(None,エラーメッセージ)
  def create_room_request(self, room_name, password):
    # リクエストの作成
    request = TCPProtocolHandler.make_create_room_request(room_name, password)
    if not request:
      return None, "ルーム名サイズの上限を超えています。"
    
    # サーバーにルーム作成依頼
    response = self.tcp_client.send_request(request)
    if not response:
      return None, "エラーが発生しました。"
    if response["error_message"]:
      return None, response["error_message"]
    else:
      self.room_token = (room_name, response["token"])
      return response["token"], None

  # 役割：ルーム一覧取得
  # 戻り値：成功=(ルーム一覧,None), 失敗=(None,エラーメッセージ)
  def get_room_list_request(self):
    # リクエストの作成
    request = TCPProtocolHandler.make_get_room_list_request()
    
    # サーバーにルーム一覧取得依頼
    response = self.tcp_client.send_request(request)
    if response is None:
      return None, "エラーが発生しました。"
    if response["error_message"]:
      return None, response["error_message"]
    else:
      return response["room_list"], None

  # 役割：ルーム参加
  # 戻り値：成功=(トークン,None)、失敗=(None,エラーメッセージ)
  def join_room_request(self, room_name, password):
    # リクエストの作成
    request = TCPProtocolHandler.make_join_room_request(room_name, password)

    # サーバーにルーム参加依頼
    response = self.tcp_client.send_request(request)
    if response is None:
      return None, "エラーが発生しました。"
    if response["error_message"]:
      return None, response["error_message"]
    else:
      self.room_token = (room_name, response["token"])
      return response["token"], None

  # 役割：チャットインターフェース
  # 戻り値：無し
  def start_chat(self):
    is_chat_active.clear()
    print("チャットを開始します")

    # メッセージの受信はワーカーズスレッドで処理
    recieve_message_thread = threading.Thread(target=self.udp_client.recieve_message)
    recieve_message_thread.start()

    # tcpとudpでクライアントのポートが異なるためチャット開始時に自動的にudpメッセージをサーバーに送りアドレスを更新する
    message = UDPProtocolHandler.make_initial_message(room_name=self.room_token[0], token=self.room_token[1], user_name=self.user_name)
    self.udp_client.send_message(message)

    try:
      while not is_chat_active.is_set():
        # メッセージの入力
        data = input("")
        if not data:
          continue
        # メッセージの作成
        message = UDPProtocolHandler.make_chat_message(self.room_token[0], self.room_token[1], self.user_name, data)
        # メッセージの送信
        self.udp_client.send_message(message)
    except KeyboardInterrupt as e:
      print(e)
    finally:
      # 退出時には退出メッセージを送信
      message = UDPProtocolHandler.make_leave_message(room_name=self.room_token[0], token=self.room_token[1])
      self.udp_client.send_message(message)
      is_chat_active.set()
      recieve_message_thread.join()

if __name__ == "__main__":
  is_chat_active = threading.Event()

  server_ip = "127.0.0.1"
  tcp_port = 6051
  udp_port = 7011
  tcp_client = TCPClient(server_ip, tcp_port)
  upd_client = UDPClient(server_ip, udp_port)

  chat_client = ChatClient(tcp_client, upd_client)
  chat_client.play()
