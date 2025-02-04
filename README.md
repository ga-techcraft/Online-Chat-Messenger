# 📡 **通信データ仕様**

---

## 🔆 **JSONサンプル**

```json
{
  "tcp_data": {
    "operation": 1,
    "state": 0,
    "room_name": "roomA",
    "operation_payload": {
      "type": "GET",
      "user_name": "taro",
      "token": "abc123",
      "is_valid": true,
      "error_message": "error"
    }
  },
  "udp_data": {
    "room_name": "roomA",
    "token": "abc123",
    "content": {
      "type": "CHAT",
      "user_name": "taro",
      "chat_data": "Hello,World!"
    }
  }
}
```

---

## 🔆 **TCPデータ (`tcp_data`)**

### 🔹 **フィールド説明**
| フィールド名          | 説明                       |
|-----------------|----------------------------|
| `operation`     | 操作を示す数値（例: 1, 2） |
| `state`         | 状態を示す数値（例: 0, 1, 2） |
| `room_name`     | 対象のルーム名               |
| `operation_payload` | 操作に関連する詳細情報     |

### 🔹 **`operation_payload` の詳細**
| フィールド名      | 説明                      |
|----------------|---------------------------|
| `type`         | 操作の種類                  |
| `user_name`    | ユーザー名                  |
| `token`        | 認証用トークン              |
| `is_valid`     | パスワード認証状態          |
| `error_message`| エラーメッセージ（エラー時） |

#### **`type` の詳細**
| 値       | 説明            |
|----------|-----------------|
| `"GET"`  | ルーム一覧取得   |
| `"JOIN"` | ルーム参加       |

#### **`is_valid` の詳細**
| 値       | 説明            |
|----------|-----------------|
| `true`   | パスワード認証成功 |
| `false`  | パスワード認証失敗 |

---

## 🔆 **UDPデータ (`udp_data`)**

### 🔹 **フィールド説明**
| フィールド名      | 説明                         |
|----------------|------------------------------|
| `room_name`    | ルーム名                      |
| `token`        | 認証用トークン                |
| `content`      | チャット内容を含むオブジェクト  |

### 🔹 **`content` の詳細**
| フィールド名   | 説明                      |
|---------------|---------------------------|
| `type`        | チャットの種類              |
| `user_name`   | メッセージ送信者の名前      |
| `chat_data`   | 実際のチャットメッセージ     |

#### **`type` の詳細**
| 値         | 説明                                      |
|------------|-------------------------------------------|
| `"CHAT"`   | 通常のチャット（クライアント ↔ サーバー） |
| `"LEAVE"`  | 退出時（クライアント → サーバー）         |
| `"CLOSE"`  | ルームクローズ（サーバー → クライアント） |
