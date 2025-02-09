# Chat Messenger Messenger

## 概要
このプロジェクトは、**TCP/UDP通信を使用したシンプルなチャットメッセンジャーシステム**です。クライアントはTCP通信でチャットルームの作成や参加を行い、UDP通信を用いてメッセージの送受信を行います。また、一定時間非アクティブなクライアントを自動的に検出し、クリーンアップする機能も備えています。

## システムの全体構成

1. **クライアント**
    - ユーザーがルームの作成、参加、メッセージ送信を行うインターフェース。
    - TCP通信を使用してルーム情報の取得や認証、UDP通信を使用してチャットメッセージを送受信します。

2. **サーバー**
    - **TCPサーバー**: クライアントからのリクエストを受け取り、チャットルームの作成、参加、一覧取得の処理を行います。
    - **UDPサーバー**: チャットメッセージのリレーやクライアントの非アクティブ検出、クリーンアップを行います。

3. **データ構造**
    - **`rooms_info`**: 各チャットルームの情報（メンバーやパスワード）を保持します。
    - **`tokens_info`**: 各トークンのクライアント情報（接続先や最終アクセス時刻）を管理します。

## プロトコルのデータフォーマット

### TCPデータフォーマット
```json
{
  "operation": "1",                              // 1: ルーム作成, 2: ルーム参加
  "state": "0",                                  // 0: サーバの初期化, 1: リクエストの応答, 2: リクエストの完了
  "room_name": "roomA",                          // ルーム名
  "operation_payload": {
    "error_message": "error_message",            // エラーメッセージ（空の場合は正常）
    "type": "GET",                               // "GET": ルーム一覧の取得, "JOIN": ルームの参加
    "token": "token123",                         // クライアント用のトークン
    "password": "password123",                   // ルームのパスワード
    "room_list": "['roomA', 'roomB', 'roomC']"   // ルーム一覧
  }
}
```

### UDPデータフォーマット
```json
{
  "room_name": "roomA",            // ルーム名
  "token": "token123",             // クライアント用のトークン
  "content": {
    "type": "INITIAL",             // "INITIAL": チャット開始, "CHAT": 通常のチャット, "LEAVE": 退出, "CLOSE": ルームのクローズ
    "user_name": "user1",          // ユーザー名
    "chat_data": "error_message"   // チャットメッセージ
  }
}
```

## クラスの構成

### 1. `TCPProtocolHandler`
- TCP通信で使用するデータの作成と解析を行います。
- **主な機能**:
  - データ作成 (`make_tcp_data`): クライアントからサーバーへ送信するTCPデータをバイト形式で作成します。
  - データ解析 (`parse_data`): サーバーから受信したTCPデータをパースし、辞書形式に変換します。

### 2. `UDPProtocolHandler`
- UDP通信で使用するメッセージの作成と解析を行います。
- **主な機能**:
  - メッセージ作成 (`make_udp_data`): クライアントやサーバー間でやり取りするメッセージデータをバイト形式で作成します。
  - メッセージ解析 (`parse_message`): 受信したUDPメッセージを解析し、辞書形式に変換します。

### 3. `TCPClient`
- TCP通信を介してサーバーにリクエストを送信し、レスポンスを受信します。
- **主な機能**:
  - サーバー接続 (`connect`)
  - リクエスト送信 (`send_request`)
  - サーバー接続の解除 (`disconnect`)

### 4. `UDPClient`
- UDP通信を介してメッセージを送受信します。
- **主な機能**:
  - メッセージ送信 (`send_message`)
  - メッセージ受信 (`recieve_message`)
  - ソケットの解放 (`close`)

### 5. `ChatClient`
- ユーザーインターフェースを提供し、ルームの作成、参加、チャット開始などの操作を処理します。
- **主な機能**:
  - ユーザーインターフェース（`play`）
  - ルームの作成処理 (`create_room_request`)
  - ルーム一覧の取得処理 (`get_room_list_request`)
  - ルームへの参加処理 (`join_room_request`)
  - チャットインターフェース (`start_chat`)

### 6. `ChatServer`
- すべてのルームやクライアント情報の管理、リクエストの処理を行います。
- **主な機能**:
  - ルームの作成 (`create_room`)
  - ルーム一覧の取得 (`get_room_list`)
  - ルームへの参加 (`join_room`)
  - 非アクティブクライアントの検出 (`detect_unactive_address_list`)

### 7. `TCPServer`
- TCP通信を介してクライアントからのリクエストを受け取り、適切な処理を実行します。
- **主な機能**:
  - クライアントからの接続受付 (`run`)
  - リクエスト処理 (`handle_request`)

### 8. `UDPServer`
- UDP通信を介してメッセージを受信し、リレーまたは適切な処理を行います。
- **主な機能**:
  - クライアントからのメッセージ受信 (`run`)
  - メッセージの処理 (`handle_message`)
  - 非アクティブクライアントの削除 (`handle_unactive_client`)

## システムの流れ
1. **クライアント側**
- `ChatClient`でユーザーの要求を受信
- `TCP/UDPProtocolHandler`で送信データの作成
- `TCP/UDPClient`でデータの送信と受信
- `TCP/UDPProtocolHandler`で受信データの解析
- `ChatClient`でユーザーにデータ表示

2. **サーバー側**
- `TCP/UDPServer`でデータ受信
- `TCP/UDPProtocolHandler`でデータ解析
- 解析結果を基に`ChatServer`でデータ処理
- 処理結果を基に`TCP/UDPProtocolHandler`でデータ作成
- `TCP/UDPServer`でデータ送信

## タイムアウト、退出、システム終了の詳細
1. **タイムアウト**
- 各クライアントの最終アクセス時刻を監視し、一定時間（デフォルト15秒）を過ぎたら自動的に退出させます。
2. **退出**
- ルーム情報から削除されます。ルームに再度入出する場合は再度パスワードの入力が必要です。
- ホストが退出した場合は、ゲスト全員を自動的に退出させます。
3. **サーバー停止**
- チャットに参加しているクライアント全員を自動的に退出させます。
## 実行方法

### システム要件
- OS: Linux（Ubuntu推奨）
- Python: 3.8異常
- パッケージ管理: apt

### パッケージ、ライブラリのインストール
1. 必要なOSパッケージをインストールします。
    ```bash
    sudo apt update
    sudo apt install python3-venv
2. 仮想環境を生成します。
    ```bash
    python3 -m venv my_env
    source my_env/bin/activate
3. 必要なライブラリをインストールします。
    ```bash
    pip install -r requirements.txt

### サーバーの起動
1. サーバーのスクリプトを実行します。
   ```bash
   python3 server.py
   ```

### クライアントの起動
1. クライアントのスクリプトを実行します。
   ```bash
   python3 client.py
   ```
2. ユーザーインターフェースに従って操作を行います。
