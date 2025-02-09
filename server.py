import socket
import threading
from modules import TCPProtocolHandler,UDPProtocolHandler,CryptoHandler
import time
import datetime
import secrets
import base64

# 扱うデータ
# rooms_info {
#    room_name: {
#       "members": {token: address},
#       "password": password
#    }
# }

# tokens_info {
#    token: {
#       "room_name": room_name,
#       "last_access": datetime,
#       "is_host": bool
#    }
# }

# ★クラス毎の役割と連携イメージ
# 【役割】
# TCPProtocolHandler:TCPデータの作成、パース
# UDPProtocolHandler:UDPデータの作成、パース
# ChatServer:全てのルームやクライアント情報の管理
# TCPServer:TCP通信でのデータの送受信
# UDPServer:UDP通信でのデータの送受信
# 【連携】
# TCP/UDPServerでデータ受信→TCP/UDPProtocolHandlerでデータ解析→解析結果を基にChatServerでデータ処理→処理結果を基にTCP/UDPProtocolHandlerでデータ作成→TCP/UDPServerでデータ送信

# TCP通信でのデータの送受信
class TCPServer:
   def __init__(self, server_ip, tcp_port, chat_server):
      self.server_address = (server_ip, tcp_port)
      self.chat_server = chat_server

   # 役割：クライアントからの接続の受信
   # 戻り値：無し
   def run(self):
      try:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(self.server_address)
        self.sock.settimeout(3)
        self.sock.listen(5)
        print(f"TCPサーバー起動: {self.server_address}")

        while not is_system_active.is_set():
            try:
               connection, client_address = self.sock.accept()
               print(f"TCP接続受信: {client_address}")
            except socket.timeout as e:
               continue

            handle_request = threading.Thread(target=self.handle_request, args=(connection, client_address), daemon=True)
            handle_request.start()

      except KeyboardInterrupt as e:
         print(e)
      finally:
          self.sock.close()
          print("TCP 接続を閉じました。")

   # 役割：クライアントからのリクエストの処理
   # 戻り値：無し
   def handle_request(self, connection, client_address):
      try:
         while True:
            # リクエストの取得
            request = self.recieve_request(connection)
   
            if not request:
               print(f"{client_address}とのTCP接続を終了します。")
               break

            # リクエストの解析
            parsed_request = TCPProtocolHandler.parse_data(request)
            # リクエストのバリデーション。エラーが無ければ空文字が返ってくる
            error_message = self.chat_server.validate_request(parsed_request)
            if error_message:
               print(error_message)
            else:
               print("バリデーションに成功しました。")
            # バリデートレスポンスの作成
            response = TCPProtocolHandler.make_validate_response(error_message)
            # バリデートレスポンスの送信
            connection.send(response)

            # バリデートに失敗している場合は処理を終える
            if error_message:
               return
            
            # リクエストの処理
            operation = parsed_request["operation"]
            operation_payload = parsed_request["operation_payload"]
            type = operation_payload["type"]

            if operation == 1:
               # ルームの作成。成功すればトークンが返ってくる。
               token, error_message = self.chat_server.create_room(parsed_request, client_address)
               # レスポンスの作成
               response = TCPProtocolHandler.make_token_response(token, error_message)
               if error_message:
                  print(error_message)
               else:
                  print("ルームの作成に成功しました。")
            elif operation == 2 and type == "GET":
               # ルーム一覧の作成。成功すれば一覧がリストで返ってくる。
               room_list, error_message = self.chat_server.get_room_list()
               # レスポンスの作成
               response = TCPProtocolHandler.make_room_list_response(room_list, error_message)
               if error_message:
                  print(error_message)
               else:
                  print("ルーム一覧の取得に成功しました。")
            elif operation == 2 and type == "JOIN":
               # ルームへ追加。成功すればトークンが返ってくる。
               token, error_message = self.chat_server.join_room(parsed_request, client_address)
               # レスポンスの作成
               response = TCPProtocolHandler.make_token_response(token, error_message)
               if error_message:
                  print(error_message)
               else:
                  print("ルームの参加に成功しました。")
            # レスポンスの送信(共通のため最後処理する)
            connection.sendall(response)
            print("レスポンスを送信しました。")
      except OSError as e:
         print(e)
      except KeyboardInterrupt as e:
         print(e)
      finally:
         connection.close()

   # 役割：クライアントからのリクエストデータの取得
   # 戻り値：リクエストデータ
   def recieve_request(self, connection):
      try:
         recieved_header_data = b""
         while len(recieved_header_data) < 32:
            chunk = connection.recv(32 - len(recieved_header_data))
            if not chunk:
               return ""
            recieved_header_data += chunk

         room_name_size = recieved_header_data[0]
         operation_payload_size = int.from_bytes(recieved_header_data[3:], "big")
         total_body_size = room_name_size + operation_payload_size
         
         recieved_body_data = b""
         while len(recieved_body_data) < total_body_size:
            chunk = connection.recv(total_body_size - len(recieved_body_data))
            recieved_body_data += chunk
         
         request = recieved_header_data + recieved_body_data
         return request
      except socket.timeout as e:
         print(e)
      except socket.error as e:
         print(e)


# UDP通信でのデータの送受信
class UDPServer:
   def __init__(self, server_ip, udp_port, chat_server):
      self.server_address = (server_ip, udp_port)
      self.chat_server = chat_server
   
   # 役割：クライアントからのメッセージの受信
   # 戻り値：無し
   def run(self):
      try:
          self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          self.sock.bind(self.server_address)
          self.sock.settimeout(3)
          threading.Thread(target=self.handle_unactive_client, daemon=True).start()

          print(f"UDPサーバー起動: {self.server_address}")

          while not is_system_active.is_set():
            try:
               message, client_address = self.sock.recvfrom(4096)
               self.handle_message(message, client_address)
            except socket.timeout as e:
               continue

      except KeyboardInterrupt as e:
         print(e)
      except Exception as e:
          print(e)
      finally:
          self.sock.close()
          print("UDP 接続を閉じました。")

   # 役割：メッセージの処理
   # 戻り値：無し
   def handle_message(self, message, client_address):
      try:
         parsed_message = UDPProtocolHandler.parse_message(message)
         content = parsed_message["content"]
         print(f"{content['user_name']}から{content['type']}:{content['chat_data']}を受信しました。")
         
         # 通常のチャット時
         if content["type"] == "CHAT":
            # 最終接続時刻の更新
            self.chat_server.update_last_access(parsed_message)
            # メッセージのバリデーション
            is_valid = self.chat_server.validate_message(parsed_message, client_address)
            if not is_valid:
               return
            # メッセージの作成
            message = UDPProtocolHandler.make_relay_message(content["user_name"], content["chat_data"])
            # アドレスリストの取得
            members_list = self.chat_server.get_members_list(parsed_message["room_name"])
            if members_list is None:
               return
            # メッセージのリレー
            for _, address in members_list:
               if address != client_address:
                  self.sock.sendto(message, address)
                  # print(f"{message}を{address}に送信しました。")
         
         # チャット退出時
         elif content["type"] == "LEAVE":
            # メッセージのバリデーション
            is_valid = self.chat_server.validate_message(parsed_message, client_address)
            if not is_valid:
               return
            # print(f"{client_address}が退出しました。")
            # ホストかどうか確認
            is_host = self.chat_server.is_host(parsed_message["token"])
            if is_host:
               # ルームメンバー(ゲスト全員)の情報の取得
               members_list = self.chat_server.get_members_list(parsed_message["room_name"])
               # ルームメンバーへクローズメッセージの送信
               # ルームメンバー情報の削除
               message = UDPProtocolHandler.make_close_message()
               for token, address in members_list:
                  self.chat_server.delete_client(token)
                  self.sock.sendto(message, address)
            else:
               # 退出者情報のみ削除
               self.chat_server.delete_client(parsed_message["token"])
            
         # チャット開始時
         elif content["type"] == "INITIAL":
            self.chat_server.initial(parsed_message, client_address)
      except Exception as e:
         print(e)

   # 役割：非アクティブクライアントの削除
   # 戻り値：無し
   def handle_unactive_client(self):
      while True:
         time.sleep(5)

         # 非アクティブクライアントのリストを取得。(token, address)のリスト。
         unactive_members_list = self.chat_server.detect_unactive_address_list()
         # タイムアウトメッセージの作成
         time_out_message = UDPProtocolHandler.make_timeout_message()
         # 非アクティブクライアントがホストだった場合に取得するゲストリストの変数
         guests_members_list = []

         for token, address in unactive_members_list:
            is_host = self.chat_server.is_host(token)
            if is_host:
               # ホストだったらゲスト情報を取得。(token, address)のリスト
               room_name = self.chat_server.get_client_room_name(token)
               guests_members_list.extend(self.chat_server.get_members_list(room_name))
            # 非アクティブクライアントを削除しメッセージを送信
            self.chat_server.delete_client(token)
            self.sock.sendto(time_out_message, address)

         # アクティブなゲストリスト情報を取得。
         active_members_list = list(set(guests_members_list) - set(unactive_members_list))
         # クローズメッセージの作成
         close_message = UDPProtocolHandler.make_close_message()
         # アクティブなゲストを削除しメッセージを送信
         for token, address in active_members_list:
            self.chat_server.delete_client(token)
            self.sock.sendto(close_message, address)

# 全てのルームやクライアント情報の管理
class ChatServer:
   def __init__(self):
      self.rooms_info = {}
      self.tokens_info = {}
      self.TIMEOUT = 15 # 最終接続からTIMEOUT秒経つとクライアントは自動的に削除される。

   # 役割：リクエストのバリデーション。現在はルーム参加時のみ行っているが今後変更する可能性あり。
   # 戻り値：成功=None、失敗=エラーメッセージ
   def validate_request(self, parsed_request):
      operation = parsed_request["operation"]
      type = parsed_request["operation_payload"]["type"]
      room_name = parsed_request["room_name"]
      password = parsed_request["operation_payload"]["password"]

      if operation == 2 and type == "JOIN":
         is_valid = CryptoHandler.verify_password(password, self.rooms_info[room_name]["password"])
         if not is_valid:
            return "パスワードに誤りがあります。"
      
      return None

   # 役割：ルームの作成
   # 戻り値：成功=(トークン,None)、失敗=(None、エラーメッセージ)
   def create_room(self, parsed_request, client_address):
      room_name = parsed_request["room_name"]

      with lock:
         if room_name in self.rooms_info:
            return None, "ルームは既に存在します。"
         else:
            token = self.generate_token()
            self.rooms_info[room_name] = {
               "members": {token: client_address},
               "password": parsed_request["operation_payload"]["password"]
            }
            self.tokens_info[token] = {
               "room_name": room_name,
               "last_access": datetime.datetime.now(),
               "is_host": True
            }
         return token, None
      
   # 役割：ルームにクライアントを追加（ルームへの参加）
   # 戻り値：成功=(トークン、None), 失敗=(None、エラーメッセージ)
   def join_room(self, parsed_request, client_address):
      room_name = parsed_request["room_name"]
      with lock:
         if room_name not in self.rooms_info:
            return None, "ルームが存在しません。"
         else:
            token = self.generate_token()
            self.rooms_info[room_name]["members"][token] = client_address
            self.tokens_info[token] = {
               "room_name": room_name,
               "last_access": datetime.datetime.now(),
               "is_host": False
            }
      return token, None

   # 役割：ルーム一覧の取得
   # 戻り値：成功=(ルーム一覧リスト,None), 失敗=(None,エラーメッセージ)
   def get_room_list(self):
      if not self.rooms_info:
         return None, "現在ルームが存在しません。"
      else:
         return list(self.rooms_info.keys()), None

   # 役割：トークンの生成
   # 戻り値：トークン
   def generate_token(self):
       # トークンの生成
        token_bytes = secrets.token_bytes(UDPProtocolHandler.TOKEN_MAX_BYTE_SIZE // 2)
        # Base64エンコードして文字列として返す
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8")
        # トークンサイズを超えないようにトリミング
        return token[:UDPProtocolHandler.TOKEN_MAX_BYTE_SIZE]

   # 役割：アドレスの更新(TCP接続とUDP接続でポートが異なるためチャット開始時に更新)
   # 戻り値：無し
   def initial(self, parsed_message, client_address):
      with lock:
         room_name = parsed_message["room_name"]
         token = parsed_message["token"]
         self.rooms_info[room_name]["members"][token] = client_address
         
   # 役割：メッセージのバリデーション(トークンとアドレスが一致するかどうか)
   # 戻り値：真偽値
   def validate_message(self, parsed_message, client_address):
      if not self.rooms_info:
         return False
      
      if self.rooms_info[parsed_message["room_name"]]["members"][parsed_message["token"]] != client_address:
         return False
      
      return True

   # 役割：ルーム名からルームメンバー情報を取得
   # 戻り値：ルームメンバーのトークンとアドレスのタプルのリスト
   def get_members_list(self, room_name):
      members_list = []

      for token, address in self.rooms_info[room_name]["members"].items():
         members_list.append((token, address))
      
      return members_list
   
   # 役割：トークンからアドレスを取得
   # 戻り値：アドレス
   def get_client_room_name(self, token):
      return self.tokens_info[token]["room_name"]
   
   # 役割：クライアント全員のアドレスを取得
   # 戻り値：クライアント全員のアドレス
   def get_all_addresses(self):
      all_addresses = []

      for room_name, room_info in self.rooms_info.items():
         for token, address in room_info["members"].items():
            all_addresses.append(address)
      
      return all_addresses

   # 役割：ホストかどうか確認
   # 戻り値：真偽値
   def is_host(self, token):
      if self.tokens_info[token]["is_host"]:
         return True
      else:
         return False

   # 役割：非アクティブクライアント情報の取得
   # 戻り値：非アクティブユーザーのトークンとアドレスのタプルのリスト
   def detect_unactive_address_list(self):
      timeout = datetime.timedelta(seconds=self.TIMEOUT)
      now = datetime.datetime.now()

      members_list = []
      for token, members_info in self.tokens_info.items():
         last_access = members_info["last_access"]

         if now - last_access > timeout:
            room_name = members_info["room_name"]
            address = self.rooms_info[room_name]["members"][token]
            members_list.append((token, address))

      return members_list
   
   # 役割：最終接続時刻の更新
   # 戻り値：無し
   def update_last_access(self, parsed_message):
      token = parsed_message["token"]
      with lock:
         self.tokens_info[token]["last_access"] = datetime.datetime.now()

   # 役割：ユーザーの削除
   # 戻り値：無し
   def delete_client(self, token):
      room_name = self.tokens_info[token]["room_name"]
      with lock:
         del self.tokens_info[token]
         del self.rooms_info[room_name]["members"][token]

         if not self.rooms_info[room_name]["members"]:
            del self.rooms_info[room_name]



if __name__ == "__main__":
   lock = threading.Lock()
   is_system_active = threading.Event()

   server_ip = "0.0.0.0"
   tcp_port = 6058
   udp_port = 7018
  
   try:
      chat_server = ChatServer()

      tcp_server = TCPServer(server_ip=server_ip, tcp_port=tcp_port, chat_server=chat_server)
      tcp_server_thread = threading.Thread(target=tcp_server.run)
      tcp_server_thread.start()

      udp_server = UDPServer(server_ip=server_ip, udp_port=udp_port, chat_server=chat_server)
      udp_server_thread = threading.Thread(target=udp_server.run)
      udp_server_thread.start()

      tcp_server_thread.join()
      udp_server_thread.join()
   except KeyboardInterrupt as e:
      print(e)
   except Exception as e:
      print(e)
   finally:
      is_system_active.set()

      message = UDPProtocolHandler.make_system_stop_message()
      all_addresses = chat_server.get_all_addresses()
      for address in all_addresses:
         udp_server.sock.sendto(message, address)