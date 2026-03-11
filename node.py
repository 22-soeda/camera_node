import time
import zmq
import json
import queue

# coreパッケージから設定を読み込む
from core import network_config
from core import message_config

from .camera_controller import CameraController
from .terminal_handler import TerminalHandler

class CameraNode:
    """ZMQ通信とノードのメインループを管理するクラス"""
    def __init__(self):
        self.context = zmq.Context()
        
        # 画像配信ソケット (network_configを使用)
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(network_config.ZMQ_URL_CAMERA_PUB)

        # コマンド受信ソケット (network_configを使用)
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.bind(network_config.ZMQ_URL_CAMERA_SUB)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "") 

        # 内部コンポーネントの初期化
        self.cmd_queue = queue.Queue()
        self.camera_ctrl = CameraController()
        self.terminal = TerminalHandler(self.cmd_queue)

    def run(self):
        print(f"Camera Node Started.")
        print(f"  Listening for commands on: {network_config.ZMQ_URL_CAMERA_SUB}")
        print(f"  Publishing frames on:      {network_config.ZMQ_URL_CAMERA_PUB}")
        print(f"  Publishing topic:          {message_config.TOPIC_CAMERA_FRAME}")
        
        # ターミナル入力の待ち受けスレッドを開始
        self.terminal.start()
        
        try:
            while True:
                # 1. ターミナル入力からのコマンド処理
                while not self.cmd_queue.empty():
                    cmd = self.cmd_queue.get_nowait()
                    self.camera_ctrl.handle_command(cmd)

                # 2. ZMQネットワークからのコマンド処理 (ノンブロッキング)
                try:
                    cmd_json = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                    cmd = json.loads(cmd_json)
                    self.camera_ctrl.handle_command(cmd)
                except zmq.Again:
                    pass

                # 3. 画像の取得と配信
                frame = self.camera_ctrl.get_frame()
                if frame is not None:
                    # トピック名は message_config を使用
                    self.pub_socket.send(message_config.TOPIC_CAMERA_FRAME, zmq.SNDMORE)
                    self.pub_socket.send_pyobj(frame)

                time.sleep(0.005)

        except KeyboardInterrupt:
            print("\nShutting down Camera Node...")
        finally:
            self.camera_ctrl.cleanup()
            self.pub_socket.close()
            self.sub_socket.close()
            self.context.term()