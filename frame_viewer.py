import sys
import os
import zmq
import cv2
import numpy as np

# プロジェクトのルートディレクトリ(coreパッケージがある場所)をパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import network_config
from core import message_config

def main():
    print("--- Camera Frame Viewer ---")
    print(f"Connecting to: {network_config.ZMQ_URL_CAMERA_PUB}")
    print(f"Topic:         {message_config.TOPIC_CAMERA_FRAME}")
    print("Waiting for frames... (Press 'q' on the image window to quit)")

    context = zmq.Context()
    
    # 画像受信用ソケット (SUB) の設定
    frame_socket = context.socket(zmq.SUB)
    frame_socket.connect(network_config.ZMQ_URL_CAMERA_PUB)
    frame_socket.setsockopt(zmq.SUBSCRIBE, message_config.TOPIC_CAMERA_FRAME)

    # ウィンドウを作成し、リサイズ可能に設定
    cv2.namedWindow("Camera Frame Viewer", cv2.WINDOW_NORMAL)
    
    is_first_frame = True  # 初回描画判定用のフラグ

    try:
        while True:
            # 1. データの受信 (画像が来るまでここで待機します)
            topic = frame_socket.recv()           # 第1フレーム: トピック名
            frame = frame_socket.recv_pyobj()     # 第2フレーム: 画像データ(NumPy配列)
            
            img_h, img_w = frame.shape[:2]

            # ★ 初回のみ、画像の縦横比を保ちつつ、横幅800pxの使いやすいサイズに設定する
            if is_first_frame:
                target_w = 800
                target_h = int(img_h * (target_w / img_w))
                cv2.resizeWindow("Camera Frame Viewer", target_w, target_h)
                is_first_frame = False

            # 2. 現在のウィンドウの描画領域サイズを取得
            try:
                rect = cv2.getWindowImageRect("Camera Frame Viewer")
                win_w, win_h = rect[2], rect[3]
            except cv2.error:
                # 初回描画時など、ウィンドウサイズが取得できない場合のフォールバック
                win_w, win_h = target_w, target_h

            # 描画領域が有効な場合のみアスペクト比維持の処理を行う
            if win_w > 0 and win_h > 0:
                # ウィンドウサイズと画像サイズの比率から、縮小/拡大スケールを計算
                scale = min(win_w / img_w, win_h / img_h)
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                
                # 画像をアスペクト比を維持したままリサイズ
                resized_frame = cv2.resize(frame, (new_w, new_h))
                
                # ウィンドウサイズと同じ大きさの黒い背景(キャンバス)を作成
                canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
                
                # リサイズした画像をキャンバスの中央に配置
                x_offset = (win_w - new_w) // 2
                y_offset = (win_h - new_h) // 2
                canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_frame
                
                cv2.imshow("Camera Frame Viewer", canvas)
            else:
                cv2.imshow("Camera Frame Viewer", frame)

            # 'q' キーが押されたら終了
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        frame_socket.close()
        context.term()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()