# NOA630B ドライバ実装（`NOA630BCamera`）

## 概要

`drivers/noa630b_camera.py` は、Wraycam SDK（`lib/wraycam.py` と同梱 DLL）を用いて **NOA630B** 向けに `ICamera` 抽象インターフェースを実装したクラスです。取得方式は **Pull モード** で、画像到達時にコールバックから `PullImageV4` でフレームを取り込みます。

## 依存関係

- `lib/` 配下の `wraycam` モジュール（インポート失敗時は接続不可）
- OpenCV（`cv2`）: RGB→BGR 変換、モノクロ時の GRAY2BGR
- NumPy: バッファの ndarray 化

## デバイス列挙と接続 ID の解決（`_resolve_cam_id`）

1. `wraycam.Wraycam.EnumV2()` でデバイス一覧を取得。
2. 引数 `port_or_id` が `sn:`, `ip:`, `name:`, `mac:` で始まる場合は、その文字列を Wraycam の `Open` にそのまま渡す。
3. 上記以外では、モデル名に **「NOA630B」** を含むデバイスを優先して選択。
4. 数値のみの文字列なら、列挙インデックスとして解釈。
5. それでも決まらなければ先頭デバイスを使い、警告ログを出す。

## 接続フロー（`connect`）

1. 既存ハンドルがあれば `disconnect` 相当で掃除。
2. 列挙結果に GigE / 10GigE が含まれる場合、`Wraycam.GigeEnable` を試行（失敗はデバッグログのみ）。
3. `_resolve_cam_id` で `cam_id` を決定し、`Wraycam.Open(cam_id)` でオープン。
4. 同じ `cam_id` のデバイス情報から `model.flag` を取得し、**モノクロ**（`WRAYCAM_FLAG_MONO`）かどうかを判定。
5. `WRAYCAM_OPTION_BYTEORDER` を `0` に設定（OpenCV 側で RGB→BGR する前提）。
6. `_realloc_buffer` で幅・高さ・ストライド・生バッファを確保。
7. トリガー設定（連続/トリガー）を反映後、`StartPullModeWithCallback` で Pull＋コールバック開始。

## 画像バッファと色形式

- `_realloc_buffer`: `get_Size()` で解像度取得。8bit モノクロなら 8bit、カラーなら 24bit。ストライドは `TDIBWIDTHBYTES` で計算。
- `_buf_to_bgr`: 生バッファを ndarray 化。モノクロは幅列のみ切り出して GRAY2BGR。カラーは RGB としてreshapeし `COLOR_RGB2BGR`。
- 最新フレームは `_latest_bgr` に保持（スレッドロック付き）。

## フレーム取得（`get_frame`）

- **連続モード**（`is_continuous is True`）: コールバックで `_pull_and_store_latest` が更新した `_latest_bgr` のコピーを返す。
- **トリガーモード**: `execute_software_trigger` で `_trigger_pending` を立て、`TriggerSyncV4` で同期取得して BGR を返す。

## パラメータ操作の要点

| メソッド | 内容 |
|---------|------|
| `set_exposure` | `get_ExpTimeRange()` でクランプ後、`put_AutoExpoEnable(0)` で **自動露光オフ**、`put_ExpoTime` |
| `get_exposure` | `get_ExpoTime()` |
| `set_gain` | `get_ExpoAGainRange()` でクランプ、`put_AutoExpoEnable(0)`、`put_ExpoAGain` |
| `set_gamma` | `put_Gamma`（整数に丸め） |
| `set_framerate` | `WRAYCAM_FLAG_PRECISE_FRAMERATE` があれば精密 FPS オプション、なければ `MaxSpeed` と `put_Speed` で近似 |
| `set_continuous_mode` | `Stop` → トリガーオプション → `StartPullModeWithCallback` で再起動 |

## エラー処理

- Wraycam の `HRESULTException` は多くの箇所でログ（debug/warning）に留め、呼び出し側に例外を再送出しない設計です。

## 関連ファイル

- `drivers/abstract_camera.py`: `ICamera` 定義
- `lib/wraycam.py`: SDK ラッパー
