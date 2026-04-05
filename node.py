import json
import logging
import queue
import threading
import time

import zmq

# coreパッケージから設定を読み込む
from core import network_config
from core import message_config

from .camera_controller import CameraController
from .terminal_handler import TerminalHandler

logger = logging.getLogger(__name__)

# 遅いサブスクライバではキューが満ちた時点でフレームが落ちる（撮影スレッドはブロックしない）
_PUB_SND_HWM = 5


def _put_latest_frame(q: queue.Queue, frame) -> None:
    """maxsize=1 相当: 常に最新1枚だけ残す。満杯なら古いフレームを捨てる。"""
    try:
        q.put_nowait(frame)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(frame)
        except queue.Full:
            pass


class CameraNode:
    """ZMQ通信とノードのメインループを管理するクラス"""

    def __init__(self):
        self.context = zmq.Context()

        # 画像配信ソケット (network_configを使用)
        self.pub_socket = self.context.socket(zmq.PUB)
        # 送信キュー肥大を抑える（内部キューが膨らみ続けるのを防ぐ）
        self.pub_socket.setsockopt(zmq.SNDHWM, _PUB_SND_HWM)
        self.pub_socket.bind(network_config.ZMQ_URL_CAMERA_PUB)

        # コマンド受信ソケット (network_configを使用)
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.bind(network_config.ZMQ_URL_CAMERA_SUB)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        self.cmd_queue: queue.Queue = queue.Queue()
        # カメラスレッド -> メイン: 最新フレームのみ（遅い PUB で取得が詰まらない）
        self._frame_queue: queue.Queue = queue.Queue(maxsize=1)

        self.camera_ctrl = CameraController()
        self.terminal = TerminalHandler(self.cmd_queue)

        self._stop = threading.Event()
        self._camera_thread = threading.Thread(
            target=self._camera_worker,
            name="CameraWorker",
            daemon=False,
        )

    def _camera_worker(self):
        """CameraController / get_frame はこのスレッドのみが触る。"""
        try:
            while not self._stop.is_set():
                while True:
                    try:
                        cmd = self.cmd_queue.get_nowait()
                    except queue.Empty:
                        break
                    self.camera_ctrl.handle_command(cmd)

                frame = self.camera_ctrl.get_frame()
                if frame is not None:
                    _put_latest_frame(self._frame_queue, frame)
                else:
                    time.sleep(0.001)
        finally:
            self.camera_ctrl.cleanup()

    def run(self):
        print(f"Camera Node Started.")
        print(f"  Listening for commands on: {network_config.ZMQ_URL_CAMERA_SUB}")
        print(f"  Publishing frames on:      {network_config.ZMQ_URL_CAMERA_PUB}")
        print(f"  Publishing topic:          {message_config.TOPIC_CAMERA_FRAME}")

        self.terminal.start()
        self._camera_thread.start()

        try:
            while True:
                try:
                    cmd_json = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                    cmd = json.loads(cmd_json)
                    self.cmd_queue.put(cmd)
                except zmq.Again:
                    pass
                except json.JSONDecodeError as e:
                    logger.warning("ZMQ コマンドの JSON 解析に失敗: %s", e)

                try:
                    frame = self._frame_queue.get_nowait()
                except queue.Empty:
                    frame = None

                if frame is not None:
                    # NOBLOCK: 送信キューが詰まったフレームは捨て、撮影側の詰まりを防ぐ
                    try:
                        self.pub_socket.send(
                            message_config.TOPIC_CAMERA_FRAME,
                            zmq.SNDMORE | zmq.NOBLOCK,
                        )
                        self.pub_socket.send_pyobj(frame, zmq.NOBLOCK)
                    except zmq.Again:
                        pass

                time.sleep(0.001)

        except KeyboardInterrupt:
            print("\nShutting down Camera Node...")
        finally:
            self._stop.set()
            self._camera_thread.join(timeout=15.0)
            if self._camera_thread.is_alive():
                logger.warning(
                    "カメラスレッドが %s 秒以内に終了しませんでした",
                    15,
                )

            self.pub_socket.setsockopt(zmq.LINGER, 0)
            self.pub_socket.close()
            self.sub_socket.close()
            self.context.term()

