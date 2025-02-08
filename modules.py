import json

# TCPデータ
# {
#   "operation": operation, 1:ルーム作成 2:ルーム参加
#   "state": state, 0:サーバの初期化 1:リクエストの応答 2:リクエストの完了
#   "room_name": room_name, 
#   "operation_payload": {
#     "error_message": error_message, 
#     "type": type, "GET"=ルーム一覧の取得、"JOIN"=ルームの参加
#     "token": token,
#     "password": password,
#     "room_list": room_list
#   }
# }
# TCPデータの作成、パース
class TCPProtocolHandler:
  ROOM_NAME_MAX_BYTE_SIZE = 2**8 # room_nameの最大バイト数
  OPERATION_PAYLOAD_MAX_BYTE_SIZE = 2**29 # operation_payloadの最大バイト数

  # データの作成。（ベースとなるメソッド）
  @staticmethod
  def make_tcp_data(room_name, operation, state, error_message="", type="", token="", password="", room_list=None):
    # オペレーションペイロードの作成
    operation_payload = {
        "error_message": error_message,
        "type": type,
        "token": token,
        "password": password,
        "room_list": room_list if room_list is not None else []
    }

    # データのエンコード
    room_name_bytes = room_name.encode("utf-8")
    operation_payload_bytes = json.dumps(operation_payload).encode("utf-8")

    # データサイズのチェック
    if len(room_name_bytes) > TCPProtocolHandler.ROOM_NAME_MAX_BYTE_SIZE:
      return None
    
    if len(operation_payload_bytes) > TCPProtocolHandler.OPERATION_PAYLOAD_MAX_BYTE_SIZE:
      return None
    
    # データの作成
    header = (
      len(room_name_bytes).to_bytes(1, "big") +
      operation.to_bytes(1, "big") +
      state.to_bytes(1, "big") + 
      len(operation_payload_bytes).to_bytes(29, "big")
    )

    return header + room_name_bytes + operation_payload_bytes

  # 認証レスポンスの作成
  @staticmethod
  def make_validate_response(error_message=""):
    return TCPProtocolHandler.make_tcp_data(room_name="", operation=10, state=1, error_message=error_message)

  # トークンレスポンスの作成
  @staticmethod
  def make_token_response(token="", error_message=""):
    return TCPProtocolHandler.make_tcp_data(room_name="", operation=10, state=2, token=token, error_message=error_message)

  # ルーム一覧レスポンスの作成
  @staticmethod
  def make_room_list_response(room_list, error_message=""):
    return TCPProtocolHandler.make_tcp_data(room_name="", operation=10, state=2, room_list=room_list, error_message=error_message)

  # ルーム作成依頼リクエストの作成
  @staticmethod
  def make_create_room_request(room_name, password):
    return TCPProtocolHandler.make_tcp_data(room_name=room_name, password=password, operation=1, state=0)

  # ルーム一覧取得依頼リクエストの作成
  @staticmethod
  def make_get_room_list_request():
    return TCPProtocolHandler.make_tcp_data(room_name="", operation=2, state=0, type="GET")

  # ルーム参加依頼リクエストの作成
  @staticmethod
  def make_join_room_request(room_name, password):
    return TCPProtocolHandler.make_tcp_data(room_name=room_name, password=password, operation=2, state=0, type="JOIN")

  # レスポンスデータの解析。戻り値はレスポンスデータ(dict)。
  @staticmethod
  def parse_data(response_data):
    header = response_data[:32]
    room_name_size = header[0]
    operation = header[1]
    state = header[2]
    operation_payload_size = int.from_bytes(header[3:32], "big")

    body = response_data[32:]
    room_name = body[:room_name_size].decode("utf-8")
    operation_payload = body[room_name_size:room_name_size+operation_payload_size].decode("utf-8")

    # dictに変換
    return {
      "operation": operation,
      "state": state,
      "room_name": room_name,
      "operation_payload": json.loads(operation_payload)
    }


# UDPデータ
# {
#   "room_name": room_name,
#   "token": token,
#   "content": {
#     "type": type,
#     "user_name": user_name,
#     "chat_data": chat_data
#   }
# }
# UDPデータの作成、パース
class UDPProtocolHandler:
  ROOM_NAME_MAX_BYTE_SIZE = 2**8 # room_nameの最大バイト数
  TOKEN_MAX_BYTE_SIZE = 2**8 # tokenの最大バイト数

  # メッセージの作成（ベースとなるメソッド）
  @staticmethod
  def make_udp_data(type, room_name="", token="", user_name="", chat_data=""):
    # データのエンコード
    room_name_bytes = room_name.encode("utf-8")
    token_bytes = token.encode("utf-8")
    content_bytes = json.dumps({
      "type": type,
      "user_name": user_name,
      "chat_data": chat_data
    }).encode("utf-8")
    
    # データサイズのチェック
    if len(room_name_bytes) > UDPProtocolHandler.ROOM_NAME_MAX_BYTE_SIZE:
      print("ルーム名が最大バイトサイズを超えています。")
      return None
    if len(token_bytes) > UDPProtocolHandler.TOKEN_MAX_BYTE_SIZE:
      print("トークンが最大バイトサイズを超えています。")
      return None

    # データの作成
    header = (
      len(room_name_bytes).to_bytes(1, "big") +
      len(token_bytes).to_bytes(1, "big") 
    )
    return header + room_name_bytes + token_bytes + content_bytes
  
  @staticmethod
  # チャット開始時に自動的にサーバーに送信されるメッセージの作成(クライアント用)
  def make_initial_message(room_name, token, user_name):
    return UDPProtocolHandler.make_udp_data(room_name=room_name, type="INITIAL", token=token, user_name=user_name)

  # チャットメッセージの作成(クライアント用)
  @staticmethod
  def make_chat_message(room_name, token, user_name, chat_data):
    return UDPProtocolHandler.make_udp_data(room_name=room_name, type="CHAT", token=token, user_name=user_name, chat_data=chat_data)
  
  # 退出メッセージの作成(クライアント用)
  @staticmethod
  def make_leave_message(room_name, token):
    return UDPProtocolHandler.make_udp_data(type="LEAVE", room_name=room_name, token=token)
  
  # リレーするチャットメッセージの作成(クライアント用)
  @staticmethod
  def make_relay_message(user_name, chat_data):
    return UDPProtocolHandler.make_udp_data(user_name=user_name, chat_data=chat_data, type="CHAT")

  # クローズメッセージの作成(サーバー用)
  @staticmethod
  def make_close_message():
    return UDPProtocolHandler.make_udp_data(type="CLOSE", chat_data="ルームがクローズしました。")
  
  # タイムアウトメッセージの作成(サーバー用)
  @staticmethod
  def make_timeout_message():
    return UDPProtocolHandler.make_udp_data(type="TIMEOUT", chat_data="タイムアウトが発生しました。")
  
  # システム停止メッセージの作成(サーバー用)
  @staticmethod
  def make_system_stop_message():
    return UDPProtocolHandler.make_udp_data(type="STOP", chat_data="システムメンテナンス中です。")
    
  # メッセージの解析 
  @staticmethod
  def parse_message(message_data):
    try:
      header = message_data[:2]
      room_name_size = header[0]
      token_size = header[1]

      body = message_data[2:]
      room_name = body[:room_name_size].decode("utf-8")
      token = body[room_name_size:room_name_size+token_size].decode("utf-8")

      try:
        content = json.loads(body[room_name_size+token_size:].decode("utf-8"))
      except json.JSONDecodeError as e:
          print(f"JSONデコードエラー:{e}")
          return None

      return {
        "room_name": room_name,
        "token": token,
        "content": content
      }

    except IndexError as e:
      print(f"パケット解析中にエラーが発生しました。:{e}")
      return None
