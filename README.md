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
├── lib/                   # SDK 同梱物（例: pytelicam の .whl、Wraycam の wraycam.py / wraycam.dll）
└── drivers/               # 各種カメラドライバの実装
    ├── abstract_camera.py # カメラの抽象基底クラス
    ├── dummy_camera.py    # テスト用ダミーカメラ
    ├── telicam_camera.py  # Toshiba Teli製カメラ用ドライバ
    └── noa630b_camera.py  # NOA630B（Wraycam SDK）用ドライバ
```

## 依存関係

実行には以下のPythonライブラリが必要です。

-   `pyzmq`
-   `numpy`
-   `opencv-python` (ダミーカメラおよびテストクライアントでの画像表示用)
-   `pytelicam` (Teli カメラを使用する場合。lib ディレクトリの `.whl` からインストールしてください)
-   **NOA630B（Wraycam）** を使用する場合は PyPI パッケージは不要です。WRAYCAM SDK に含まれる `wraycam.py` と `wraycam.dll`（Windows の場合）を `lib/` に配置し、`wraycam.py` と同じディレクトリに DLL があることを確認してください（公式マニュアル同様）。

GigE 接続のカメラのみを使う場合は、SDK ドキュメントに従い GigE 用ドライバの導入や `Wraycam_GigeEnable` の利用が必要になることがあります。NOA630B が USB の場合は通常そのままで動作します。

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

# NOA630B（Wraycam）— ドライバ名は NOA630B（大文字小文字は区別されず接続可能）
# 第2引数 port: デバイス番号(0,1,...)、または sn:xxxx / ip:xxx など Wraycam_Open 形式
connect NOA630B 0

# 露光時間を 20000us に設定
set_exposure 20000

# トリガーモード（単発撮影）に切り替え
set_mode trigger

# ソフトウェアトリガーを発行して1枚撮影
capture

# カメラから切断
disconnect
```

#### NOA630B（Wraycam）と `capture` の挙動

- **連続モード（既定）**では、`execute_software_trigger()` は **何もしません**（Wraycam のトリガ設定が連続ストリームのため）。`capture <保存ディレクトリ>` は **直近のストリーム画像を保存**する動きになります。
- 接続直後は、SDK コールバックで最初の `PullImageV4` が成功するまでバッファが空のことがあります。保存処理では **最大約 2 秒**、同期 `Pull` と短いポーリングで初回フレームを待ちます（プレビュー用の `get_frame()` はブロックしません）。
- **単発撮影（ソフトトリガで毎回 1 枚取得）**にしたい場合は、`set_mode trigger` のあと `capture <dir>` を使います（このとき `execute_software_trigger()` が有効になり、`get_frame()` が `TriggerSyncV4` で 1 枚取得します）。
- フレームが得られない場合は `PullImageV4` / `TriggerSyncV4` の失敗が **最大 5 秒間隔**で WARNING ログに出ます。保存に失敗したときはターミナルに `continuous_mode` などの付加情報が表示されます。

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

### 3. 手動タイミングで `capture` 送信（`capture_sender.py`）

任意のタイミングで `capture` コマンドを送りたい場合は、次を使ってください。

```bash
python camera_node/capture_sender.py --save-dir ./tmp_captures
```

- Enter: `capture` を1回送信（自動ファイル名）
- 文字入力 + Enter: その名前で送信（拡張子省略時は `.png`）
- `q` / `quit` / `exit`: 終了

1回だけ送って終了する場合:

```bash
python camera_node/capture_sender.py --save-dir ./tmp_captures --once
```

## ネットワーク通信仕様 (ZMQ)

ネットワークの設定やトピック名は `core/network_config.py` および `core/message_config.py` で一元管理されています。

### コマンド受信 (SUB)

-   Endpoint: `tcp://127.0.0.1:5550` (`ZMQ_URL_CAMERA_SUB`)
-   Format: JSON形式。`{"action": "コマンド名", "value": 設定値}` など。
-   接続例: `{"action": "connect", "driver": "NOA630B", "port": "0"}`（`port` は上記と同様の指定が可能）

### 画像配信 (PUB)

-   Endpoint: `tcp://127.0.0.1:5555` (`ZMQ_URL_CAMERA_PUB`)
-   Topic: `camera/frame` (`TOPIC_CAMERA_FRAME`)
-   Format: ZMQのマルチパート通信。第1フレームにトピック名、第2フレームに `pyobj` 形式でNumPy配列（画像データ）を送信。