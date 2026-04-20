import time
import zmq
import json
import queue
from pathlib import Path

# coreパッケージから設定を読み込む
from core import network_config
from core import message_config

from .camera_controller import CameraController
from .terminal_handler import TerminalHandler

_ZMQ_PORTS_FILE = Path(__file__).resolve().parent / "zmq_ports.json"


class CameraNode:
    """ZMQ通信とノードのメインループを管理するクラス"""
    def __init__(self):
        self.context = zmq.Context()
        self._setup_zmq_sockets()

        # 内部コンポーネントの初期化
        self.cmd_queue = queue.Queue()
        self.camera_ctrl = CameraController()
        self.terminal = TerminalHandler(self.cmd_queue)

    def _setup_zmq_sockets(self) -> None:
        """既定ポートが使用中のとき、2 ずつずらしたペアで bind を再試行する。"""
        base_pub = network_config.CAMERA_PUB_PORT
        base_cmd = network_config.CAMERA_CMD_PORT

        for attempt in range(32):
            pub_p = base_pub + 2 * attempt
            cmd_p = base_cmd + 2 * attempt
            pub_sock = self.context.socket(zmq.PUB)
            sub_sock = self.context.socket(zmq.SUB)
            pub_sock.setsockopt(zmq.LINGER, 0)
            sub_sock.setsockopt(zmq.LINGER, 0)
            try:
                pub_sock.bind(network_config.bind_addr(pub_p))
                sub_sock.bind(network_config.bind_addr(cmd_p))
            except zmq.ZMQError:
                pub_sock.close()
                sub_sock.close()
                continue

            self.pub_socket = pub_sock
            self.sub_socket = sub_sock
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            network_config.set_camera_bind_ports(pub_p, cmd_p)
            _ZMQ_PORTS_FILE.write_text(
                json.dumps({"pub_port": pub_p, "cmd_port": cmd_p}, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            if attempt > 0:
                print(
                    f"[camera_node] ポート競合のため画像 PUB={pub_p}, コマンド SUB={cmd_p} に切り替えました。"
                )
            return

        raise RuntimeError(
            "カメラ用 ZMQ ポートが取得できませんでした。別の camera_node を終了するか、"
            "環境変数 MEASUREMENT_CAMERA_PUB_PORT / MEASUREMENT_CAMERA_CMD_PORT で空き番号を指定してください。"
        )

    def run(self):
        print(f"Camera Node Started.")
        print(f"  Listening for commands on: {network_config.ZMQ_URL_CAMERA_SUB}")
        print(f"  Publishing frames on:      {network_config.ZMQ_URL_CAMERA_PUB}")
        print(f"  Viewer connect (SUB):      {network_config.camera_pub_connect_url()}")
        print(f"  Publishing topic:          {message_config.TOPIC_CAMERA_FRAME}")
        
        # ターミナル入力の待ち受けスレッドを開始
        self.terminal.start()
        
        try:
            while True:
                # 1. ターミナル入力からのコマンド処理
                while not self.cmd_queue.empty():
                    cmd = self.cmd_queue.get_nowait()
                    self.camera_ctrl.handle_command(cmd, source="terminal")

                # 2. ZMQネットワークからのコマンド処理 (ノンブロッキング)
                try:
                    cmd_json = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                    cmd = json.loads(cmd_json)
                    reply = self.camera_ctrl.handle_command(cmd, source="zmq")
                    if reply is not None:
                        self.pub_socket.send(reply["topic"], zmq.SNDMORE)
                        self.pub_socket.send(
                            json.dumps(reply["body"], ensure_ascii=False).encode("utf-8")
                        )
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
            try:
                _ZMQ_PORTS_FILE.unlink()
            except OSError:
                pass