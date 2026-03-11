# Camera Node

ZeroMQを利用した疎結合アーキテクチャにおける、カメラ制御および画像配信を行うノードです。

## 概要

本ノードは、外部からのJSONコマンドをZMQのSUBソケットで受信してカメラ（実機またはダミー）を制御し、取得した画像フレームをZMQのPUBソケットで配信します。
また、開発およびデバッグの効率化のため、ノード単体で起動してターミナルから直接コマンドを入力することでも操作可能です。

## ディレクトリ構成

```text
camera_node/
├── main.py                # エントリーポイント（起動用スクリプト）
├── node.py                # ZMQ通信とメインループの管理
├── camera_controller.py   # カメラドライバのライフサイクル・状態管理
├── terminal_handler.py    # ターミナル入力の待ち受けとパース処理
├── test_client.py         # GUIモック用のテストクライアント
└── drivers/               # 各種カメラドライバの実装
    ├── abstract_camera.py # カメラの抽象基底クラス
    ├── dummy_camera.py    # テスト用ダミーカメラ
    └── telicam_camera.py  # Toshiba Teli製カメラ用ドライバ
```

## 依存関係

実行には以下のPythonライブラリが必要です。

-   `pyzmq`
-   `numpy`
-   `opencv-python` (ダミーカメラおよびテストクライアントでの画像表示用)
-   `pytelicam` (実機カメラを使用する場合。libディレクトリの `.whl` からインストールしてください)

## 起動方法

本ノードは core パッケージの設定ファイル (`network_config.py`, `massage_config.py`) に依存しています。プロジェクトのルートディレクトリ（`camera_node` と `core` が存在するディレクトリ）から起動するか、適切に `PYTHONPATH` を通して実行してください。

### Bash

```bash
# プロジェクトルートから実行する場合の例
python -m camera_node.main
```

実行すると、ZMQのポートが開放され、同時にターミナル上でコマンド入力の待ち受けが開始されます。

## テスト・デバッグ方法

本ノードは、用途に合わせて2種類のテスト方法をサポートしています。

### 1. ターミナルからの単体アクティブテスト

`main.py` を起動したターミナルに直接コマンドを打ち込むことで、外部ノードを使わずにカメラの動作確認が可能です。

#### コマンド例:

```bash
# ダミーカメラ(ポート0)に接続
connect dummy 0

# Teliカメラ(ポート0)に接続
connect telicam 0

# 露光時間を 20000us に設定
set_exposure 20000

# トリガーモード（単発撮影）に切り替え
set_mode trigger

# ソフトウェアトリガーを発行して1枚撮影
capture

# カメラから切断
disconnect
```

### 2. テストクライアント (`test_client.py`) による通信テスト

外部からのZMQメッセージ通信と、配信された画像の受信テストを行うためのモックスクリプトです。OpenCVのウィンドウが開き、取得したフレームをリアルタイムで確認できます。

別のターミナルを開き、以下のコマンドを実行します。

### Bash

```bash
python camera_node/test_client.py --driver dummy --port 0 --exposure 15000
```

#### テストクライアント起動中の操作:

-   `[q]`: クライアントを終了
-   `[t]`: ソフトウェアトリガーの発行 (`trigger` モード時のみ有効)
-   `[e]`: 露光時間を動的に増加 (パラメータ変更の通信テスト)

## ネットワーク通信仕様 (ZMQ)

ネットワークの設定やトピック名は `core/network_config.py` および `core/message_config.py` で一元管理されています。

### コマンド受信 (SUB)

-   Endpoint: `tcp://127.0.0.1:5550` (`ZMQ_URL_CAMERA_SUB`)
-   Format: JSON形式。`{"action": "コマンド名", "value": 設定値}` など。

### 画像配信 (PUB)

-   Endpoint: `tcp://127.0.0.1:5555` (`ZMQ_URL_CAMERA_PUB`)
-   Topic: `camera/frame` (`TOPIC_CAMERA_FRAME`)
-   Format: ZMQのマルチパート通信。第1フレームにトピック名、第2フレームに `pyobj` 形式でNumPy配列（画像データ）を送信。