import sys
import os
import json
import time
import zmq
import cv2
import numpy as np
from pathlib import Path

# プロジェクトのルートディレクトリ(coreパッケージがある場所)をパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import network_config
from core import message_config

_ZMQ_PORTS_FILE = Path(__file__).resolve().parent / "zmq_ports.json"


def _viewer_pub_url() -> str:
    """camera_node が書いた zmq_ports.json があれば、その PUB 番号で接続する。"""
    port = network_config.CAMERA_PUB_PORT
    if _ZMQ_PORTS_FILE.exists():
        try:
            data = json.loads(_ZMQ_PORTS_FILE.read_text(encoding="utf-8"))
            port = int(data["pub_port"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError, TypeError):
            pass
    return network_config.pub_addr(port)


def main():
    pub_url = _viewer_pub_url()
    print("--- Camera Frame Viewer ---")
    print(f"Connecting to: {pub_url}")
    print(f"Topic:         {message_config.TOPIC_CAMERA_FRAME}")
    print("Waiting for frames... (Press 'q' on the image window, or Ctrl+C here to quit)")

    context = zmq.Context()
    
    # 画像受信用ソケット (SUB) の設定
    frame_socket = context.socket(zmq.SUB)
    frame_socket.connect(pub_url)
    frame_socket.setsockopt(zmq.SUBSCRIBE, message_config.TOPIC_CAMERA_FRAME)
    # 無限 recv だとメインスレッドがブロックし Ctrl+C が効きにくいため、短いタイムアウトで抜ける
    frame_socket.setsockopt(zmq.RCVTIMEO, 250)

    # ウィンドウを作成し、リサイズ可能に設定
    cv2.namedWindow("Camera Frame Viewer", cv2.WINDOW_NORMAL)
    
    is_first_frame = True  # 初回描画判定用のフラグ
    window_name = "Camera Frame Viewer"
    target_w, target_h = 800, 600

    # 低遅延優先: 受信は連続で行い、描画は上限fpsで間引く
    display_fps_cap = 30.0
    min_display_interval_s = 1.0 / display_fps_cap
    next_display_at = time.monotonic()

    # getWindowImageRect は高コストなので一定周期だけ更新する
    rect_refresh_interval_s = 0.25
    next_rect_refresh_at = 0.0
    win_w, win_h = target_w, target_h

    # 描画キャッシュ
    cached_geom_key = None
    cached_new_size: tuple[int, int] | None = None
    cached_offset: tuple[int, int] | None = None
    canvas: np.ndarray | None = None

    latest_frame = None

    try:
        while True:
            # 1. データ受信（最初は待ち、その後はキューを掃き出して最新1枚を残す）
            try:
                frame_socket.recv()  # 第1フレーム: トピック名
                latest_frame = frame_socket.recv_pyobj()  # 第2フレーム: 画像データ(NumPy配列)
            except zmq.Again:
                cv2.waitKey(1)
                continue

            while True:
                try:
                    frame_socket.recv(flags=zmq.NOBLOCK)
                    latest_frame = frame_socket.recv_pyobj(flags=zmq.NOBLOCK)
                except zmq.Again:
                    break

            now = time.monotonic()
            if now < next_display_at:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            frame = latest_frame
            if frame is None:
                continue
            img_h, img_w = frame.shape[:2]

            # ★ 初回のみ、画像の縦横比を保ちつつ、横幅800pxの使いやすいサイズに設定する
            if is_first_frame:
                target_h = int(img_h * (target_w / img_w))
                cv2.resizeWindow(window_name, target_w, target_h)
                win_w, win_h = target_w, target_h
                canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
                is_first_frame = False

            # 2. 現在のウィンドウ描画領域サイズを周期的に取得
            if now >= next_rect_refresh_at:
                try:
                    rect = cv2.getWindowImageRect(window_name)
                    win_w, win_h = rect[2], rect[3]
                except cv2.error:
                    win_w, win_h = target_w, target_h
                next_rect_refresh_at = now + rect_refresh_interval_s

            # 描画領域が有効な場合のみアスペクト比維持の処理を行う
            if win_w > 0 and win_h > 0:
                geom_key = (win_w, win_h, img_w, img_h)
                if geom_key != cached_geom_key:
                    scale = min(win_w / img_w, win_h / img_h)
                    new_w, new_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))
                    x_offset = (win_w - new_w) // 2
                    y_offset = (win_h - new_h) // 2
                    cached_new_size = (new_w, new_h)
                    cached_offset = (x_offset, y_offset)
                    cached_geom_key = geom_key

                if canvas is None or canvas.shape[0] != win_h or canvas.shape[1] != win_w:
                    canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
                else:
                    canvas.fill(0)

                assert cached_new_size is not None and cached_offset is not None
                resized_frame = cv2.resize(frame, cached_new_size)
                x_offset, y_offset = cached_offset
                new_w, new_h = cached_new_size
                canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_frame
                cv2.imshow(window_name, canvas)
            else:
                cv2.imshow(window_name, frame)

            # 'q' キーが押されたら終了
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            next_display_at = now + min_display_interval_s

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl+C)")
    finally:
        frame_socket.close()
        context.term()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()