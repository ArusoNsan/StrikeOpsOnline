# STRIKE OPS Online

CS2仕様準拠のブラウザFPS(爆破モード 5v5、人間+Botで常時フル編成)。
単一HTMLクライアント + Python製リレーサーバーによる**ホスト権威型**オンライン対戦。

## 構成

| ファイル | 役割 |
|---|---|
| `strike_ops_online.html` | ゲーム本体 (Three.js/WebAudio、オフラインモード同居) |
| `strike_ops_server.py` | リレーサーバー (ルーム管理+中継のみ、ゲームロジックなし) |
| `dual_test.html` | 2クライアント並列のローカル検証ハーネス |
| `requirements.txt` | サーバー依存 (`websockets`) |

## 遊び方 (ローカル)

```bash
pip install -r requirements.txt
python strike_ops_server.py          # リレー起動 (port 8732)
# strike_ops_online.html をHTTPサーバー経由で開く (例: python -m http.server 8731)
# → タイトル「オンライン対戦」→ サーバー ws://localhost:8732 / 同じルームコードで入室
```

2画面テスト: `dual_test.html` を開くとホスト(CT)とゲスト(T)が自動対戦を開始します。

## インターネット公開 (Render無料枠)

1. このリポジトリをRenderの **Web Service** として接続
2. Start Command: `python strike_ops_server.py` (PORT環境変数は自動で読みます)
3. クライアントのサーバー欄に `wss://<アプリ名>.onrender.com` を入力し、友達とルームコードを共有

招待リンク形式: `strike_ops_online.html?ws=wss://xxx.onrender.com&room=ABCD&name=名前&team=auto&auto=1`

## アーキテクチャ概要

- **ホスト** (ルーム作成者のブラウザ) が全シミュレーションを実行。人間はBot枠を置き換え
- **ゲスト** は入力を30Hzで送信し、世界スナップショットを20Hzで受信。
  自機はローカル予測 (乖離>1.5uで権威補正)、他ユニットは追従補間
- ヒット判定・経済・爆弾・ラウンド進行はすべてホスト権威
