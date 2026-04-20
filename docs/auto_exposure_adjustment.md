# 自動露光量調節の実装

## 概要

本プロジェクトにおける「自動露光調節」は、**カメラ本体のオートエクスポージャ（AE）に任せる**のではなく、`CameraController` が **現在フレームの明るさ** を見て **露光時間をソフトウェアで反復調整**する方式です。  
そのため NOA630B では `set_exposure` 内で `put_AutoExpoEnable(0)` が呼ばれ、**手動露光**に切り替わったうえで値が書き込まれます。

実装の中心は `camera_controller.py` の `_adjust_exposure_once` です。

## 明るさの定義

- `_mean_gray_brightness(frame)`  
  - グレースケール画像なら平均画素値。  
  - カラー（BGR）なら `cv2.cvtColor(..., COLOR_BGR2GRAY)` したうえで **全画素の平均**（0〜255）。

## 目標値

- `target_brightness`（既定 **128.0**）。  
- ターミナル / コマンド経由で `set_target_brightness` により変更可能。

## 調整アルゴリズム（比例制御）

各イテレーションで次を実行します。

1. `get_frame()` で最新フレームを取得。失敗したら終了。
2. `measured = _mean_gray_brightness(frame)` を計算。
3. `abs(measured - target) <= tolerance` なら **収束**として終了。
4. 現在の露光 `current` を取得:
   - `camera.get_exposure()` が使えればその値。
   - なければ `_last_exposure_us`、それもなければ **10000.0 µs** を仮定。
5. 比例更新:
   - `ratio = target / max(measured, _BRIGHTNESS_EPS)`（`_BRIGHTNESS_EPS = 1e-3` でゼロ除算回避）
   - `new_exp = current * ratio`
6. `camera.set_exposure(new_exp)` を呼び、可能なら `_sync_last_exposure_from_camera()` で内部キャッシュを更新。
7. `sleep_s > 0` なら待機（次フレームが新露光で更新される時間を確保）。

物理的な露光は「明るさにほぼ比例」するという単純モデルに基づく **1 ステップの比例補正**です。複数回 `max_iterations` を回すことで徐々に目標に近づけます。

## コマンドパラメータ

`adjust_exposure` アクション（ターミナルでは `adjust_exposure [max_iterations] [tolerance] [sleep_s]`）:

| パラメータ | 既定 | 意味 |
|-----------|------|------|
| `max_iterations` | 1 | 最大ループ回数 |
| `tolerance` | 1.0 | 目標との平均輝度差（これ以下なら打ち切り） |
| `sleep_s` | 0.05 | 各ステップ後の待機秒（連続撮影で次フレームを待つ用） |

## ドライバとの関係

- **NOA630B**: 露光設定時に AE をオフにするため、調整はすべて **手動露光の数値変更**として行われる。
- **他ドライバ**（Dummy / Telicam）: 同じ `CameraController` ロジックが使われるが、`get_exposure` / `set_exposure` の挙動は各 `ICamera` 実装に依存する。

## 関連ファイル

- `camera_controller.py`: `_adjust_exposure_once`, `target_brightness`, `handle_command` の `adjust_exposure` 分岐
- `terminal_handler.py`: CLI 引数のパース
- `drivers/noa630b_camera.py`: `set_exposure` / `get_exposure`（AE 無効化を含む）
