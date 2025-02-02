import socket
import threading
import secrets
import base64
import datetime
from modules import TCPProtocolHandler, UDPProtocolHandler
import queue

class ChatServer:
    def __init__(self):
        self.rooms = {}
        # {room_name: {"members": {(ip, port): {"user_name": user_name, "token": token}}, "last_access": {(ip, port): datetime}}}
        self.lock = threading.Lock()
        UDPProtocolHandler.TOKEN_MAX_BYTE_SIZE
    
    # 役割：リクエストデータのバリデーション、レスポンスデータの作成
    # 戻り値：真偽値
    def validate_request(self, parsed_request_data):
        auth_response = TCPProtocolHandler.make_auth_response(auth_status=True)
        return True, auth_response

    # 役割：トークンの発行、チャットルームの作成、レスポンスデータの作成
    # 戻り値：レスポンスデータ
    def handle_create_room_request(self, room_name, user_name, client_address):
        with self.lock:
            if room_name in self.rooms:
                processed_response = TCPProtocolHandler.make_token_response(error_message="ルームは既に存在します。")
            else:
                # トークンの発行
                token = self.generate_token()

                # 新規ルームの作成
                self.rooms[room_name] = {
                    "members": {client_address: {"user_name": user_name, "token": token}},
                    "last_access": {client_address: datetime.datetime.now()}
                }

                # レスポンスデータの作成
                processed_response = TCPProtocolHandler.make_token_response(token=token)

            return processed_response

    # 役割：トークンの発行、チャットルームへのゲストの追加、レスポンスデータの作成
    # 戻り値：レスポンスデータ
    def handle_join_room_request(self, room_name, user_name, client_address):
        with self.lock:
            if room_name not in self.rooms:
                processed_response = TCPProtocolHandler.make_token_response(error_message="指定されたルームが存在しません。")
            else:
                # トークンの発行
                token = self.generate_token()
                # ルームにゲストデータを追加
                self.rooms[room_name]["members"][client_address] = {"user_name": user_name, "token": token}
                self.rooms[room_name]["last_access"][client_address] = datetime.datetime.now()
                processed_response = TCPProtocolHandler.make_token_response(token=token)

            return processed_response

    # 役割：チャットルームリストの取得、レスポンスデータの作成
    # 戻り値：レスポンスデータ
    def handle_get_room_list_request(self):
        with self.lock:
            if not self.rooms:
                processed_response = TCPProtocolHandler.make_room_list_response(error_message="ルームが存在しません。")
            else:
                processed_response = TCPProtocolHandler.make_room_list_response(room_list=list(self.rooms.keys()))

            return processed_response

    # 役割：トークンの発行
    # 戻り値：トークン
    def generate_token(self):
        # トークンの生成
        token_bytes = secrets.token_bytes(UDPProtocolHandler.TOKEN_MAX_BYTE_SIZE // 2)
        # Base64エンコードして文字列として返す
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8")
        # トークンサイズを超えないようにトリミング
        return token[:UDPProtocolHandler.TOKEN_MAX_BYTE_SIZE]

    # 役割：メッセージのバリデーション
    # 戻り値：真偽値
    def validate_message(self, parsed_message_data, client_address):
        room_name = parsed_message_data["room_name"]
        token = parsed_message_data["token"]



        # TCPとUDPでサーバーが異なるポートでクライアントを認識するため、TCP接続時のipアドレスがUDP接続時のipアドレスと一致したら、rooms情報のポートはUDPのポートに更新する。
        for (ip, port) in list(self.rooms[room_name]["members"].keys()):
            if ip == client_address[0]:
                # ポート番号だけを更新
                new_address = (ip, client_address[1])

                # トークン情報など既存データを保持しつつ、新しいアドレスで登録
                self.rooms[room_name]["members"][new_address] = self.rooms[room_name]["members"].pop((ip, port))
                self.rooms[room_name]["last_access"][new_address] = self.rooms[room_name]["last_access"].pop((ip, port))
                break

        # トークンとアドレスが一致するかどうか
        if self.rooms[room_name]["members"][client_address]["token"] == token:
            return True
        else:
            return False

    # 役割：リレーメッセージの作成、リレー先のアドレスリストの作成
    # 戻り値：リレーメッセージ、リレー先のアドレスリスト
    def handle_chat_message(self, parsed_message_data):
        print("handle_chat_message関数の処理")
        # リレー先アドレスの作成
        address_list = list(self.rooms[parsed_message_data["room_name"]]["members"].keys())

        print(address_list)

        content = parsed_message_data["content"]
        user_name = content["user_name"]
        chat_data = content["chat_data"]

        return UDPProtocolHandler.make_relay_message(user_name, chat_data), address_list

    # 役割：退出するユーザー情報の削除(ホストの場合はルームの削除、ゲストのアドレスリストの取得、ゲストへのクローズメッセージの作成)
    # 戻り値：ホストの場合のみ ゲストのアドレスリスト、ゲストへのクローズメッセージ
    def handle_leave_message(self, room_name, client_address):
        with self.lock:

            if room_name not in self.rooms:
                return None, None
            
            # ルーム情報を取得
            room = self.rooms[room_name]

            # ルームの最初のアドレスと一致すればホスト。
            is_host = list(room["members"].keys())[0] == client_address

            # クライアント情報を削除
            if client_address in room["members"]:
                del room["members"][client_address]
                del room["last_access"][client_address]
                print(f"クライアント{client_address}がルーム'{room_name}'から退出しました。")


            
            # ホストが退出する場合、ルームを削除
            if is_host:
                del self.rooms[room_name]
                print(f"ルーム'{room_name}'がホストの退出により削除されました。")

                message = UDPProtocolHandler.make_close_message()

                # ゲストのアドレスリストを返す
                return message, list(room["members"].keys())

    # 役割：非アクティブユーザー情報の削除(ホストであればゲスト情報も削除)
    # 戻り値：非アクティブユーザーのアドレスリスト、非アクティブユーザーへのクローズメッセージ
    def detect_inactive_users(self, timeout_seconds=300):
        inactive_address_list = []
        message = UDPProtocolHandler.make_timeout_message()

        with self.lock:
            now = datetime.datetime.now()
            for room_name, room_data in list(self.rooms.items()):
                for client_address, last_access_time in list(room_data["last_access"].items()):
                    if (now - last_access_time).total_seconds() > timeout_seconds:
                        inactive_address_list.append(client_address)

                        guest_address_list = self.handle_leave_message(room_name, client_address)
                        if guest_address_list is not None:
                            inactive_address_list.extend(guest_address_list)

        return message, inactive_address_list


class TCPServer:
    # 役割：サーバーアドレスの設定とTCPソケットの作成
    # 戻り値：無し
    def __init__(self, server_ip, server_port, chat_server):
        self.server_address = (server_ip, server_port)
        self.chat_server = chat_server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # サーバーのバインドと接続の受付
    # 戻り値：無し
    def run(self):
        try:
            self.sock.bind(self.server_address)
            self.sock.listen(5)
            print(f"TCPサーバー起動: {self.server_address}")

            while True:
                connection, client_address = self.sock.accept()
                print(f"TCP接続受信: {client_address}")

                threading.Thread(target=self.handle_request, args=(connection, client_address)).start()

        except Exception as e:
            print(e)
        finally:
            self.sock.close()
            print("TCP 接続を閉じました。")

    # 役割：リクエストの受信と認証、リクエストの種類に応じた処理、レスポンスの送信
    # 戻り値：無し
    def handle_request(self, connection, client_address):
        try:
            while True:
                # リクエストデータの取得
                request_data = connection.recv(4096)
                print(f"tcpリクエストデータ{request_data}")

                if not request_data:
                    break

                # リクエストデータの解析
                parsed_request_data = TCPProtocolHandler.parse_data(request_data)
                room_name = parsed_request_data["room_name"]
                operation = parsed_request_data["operation"]
                operation_payload = parsed_request_data["operation_payload"]
                user_name = operation_payload["user_name"]

                # 現在は全てのリクエストに対して認証の成功を返している。
                # 今後バリデーションを加えて、認証の失敗も返していく。
                # 例えばルームの参加の場合はパスワードを入力させるとか。ルームの作成は管理者idを持つ人のみが作成できるなど。
                is_valid_request, auth_response = self.chat_server.validate_request(parsed_request_data)


                # 認証レスポンスの送信
                connection.send(auth_response)
                print(f"認証レスポンス：{auth_response}を送信しました。")

                if not is_valid_request:
                    raise 

                # ルームの作成リクエストの場合
                if operation == 1:
                    processed_response = self.chat_server.handle_create_room_request(room_name, user_name, client_address) 

                # ルーム参加リクエストの場合
                elif operation == 2 and operation_payload["operation_mode"] == "JOIN":
                    processed_response = self.chat_server.handle_join_room_request(room_name, user_name,client_address)
                
                # ルーム一覧の取得リクエストの場合
                elif operation == 2 and operation_payload["operation_mode"] == "GET":
                    processed_response = self.chat_server.handle_get_room_list_request()
                
                # 次のレスポンスの送信
                connection.send(processed_response)

        except Exception as e:
            print(f"TCPハンドリングエラー: {e}")

        finally:
            connection.close()


class UDPServer:
    # 役割：サーバーアドレスの設定とUDPソケットの作成
    # 戻り値：無し
    def __init__(self, server_ip, server_port, chat_server):
        self.server_address = (server_ip, server_port)
        self.chat_server = chat_server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message_queue = queue.Queue()

    # 役割：サーバーのバインドとメッセージの受信
    # 戻り値：無し
    def run(self):
        try:
            self.sock.bind(self.server_address)
            print(f"UDPサーバー起動: {self.server_address}")

            threading.Thread(target=self.handle_message).start()

            while True:
                message_data, client_address = self.sock.recvfrom(4096)
                print(f"{message_data}をrun関数で受信しました")
                self.message_queue.put((message_data, client_address))

        except Exception as e:
            print(e)
        finally:
            self.sock.close()
            print("UDP 接続を閉じました。")

    # 役割：メッセージのバリデーション、メッセージの種類に応じた処理、メッセージのリレー
    # 戻り値：無し
    def handle_message(self):
        while True:
            message_data, client_address = self.message_queue.get()
            parsed_message_data = UDPProtocolHandler.parse_message(message_data)

            # is_valid_message = self.chat_server.validate_message(parsed_message_data, client_address)

            # if not is_valid_message:
            #     return

            room_name = parsed_message_data["room_name"]
            status = parsed_message_data["content"]["status"]

            if status == "CHAT":
                message, address_list = self.chat_server.handle_chat_message(parsed_message_data)

                if message is not None:
                    self.relay_message(message, address_list, client_address)

            elif status == "LEAVE":
                message, guest_addess_list = self.chat_server.handle_leave_message(room_name, client_address)

                if message is not None:
                    self.relay_message(message, guest_addess_list, client_address)

    # 役割：非アクティブユーザー情報の取得、非アクティブユーザーへのクローズメッセージの送信
    # 戻り値：無し
    def monitor_inactive_users(self):
        message, inactive_address_list = self.chat_server.detect_inactive_users()

        if message is not None:
            self.relay_message(message, inactive_address_list)

    # 役割：メッセージのリレー
    # 戻り値：無し
    def relay_message(self, message, othres_address_list, client_address=""):
        print("relay_message関数")
        for other_address in othres_address_list:
            if client_address is not None and other_address != client_address:
                print(f"{client_address}から{other_address}に{message}を送信しました。")
                self.sock.sendto(message, other_address)


if __name__ == "__main__":
    server_ip = "0.0.0.0"
    tcp_port = 9022
    udp_port = 9014

    chat_server = ChatServer()
    tcp_server = TCPServer(server_ip, tcp_port, chat_server)
    udp_server = UDPServer(server_ip, udp_port, chat_server)

    tcp_server_thread = threading.Thread(target=tcp_server.run)
    tcp_server_thread.start()

    udp_server_thread = threading.Thread(target=udp_server.run)
    udp_server_thread.start()

    tcp_server_thread.join()
    udp_server_thread.join()
