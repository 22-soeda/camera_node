import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import zmq

# project root (for core import)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import network_config

_ZMQ_PORTS_FILE = Path(__file__).resolve().parent / "zmq_ports.json"


def _camera_cmd_connect_url() -> str:
    port = network_config.CAMERA_CMD_PORT
    if _ZMQ_PORTS_FILE.exists():
        try:
            loaded = json.loads(_ZMQ_PORTS_FILE.read_text(encoding="utf-8"))
            port = int(loaded.get("cmd_port", port))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return network_config.pub_addr(port)


def _default_filename(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{ts}.png"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="camera_node に capture コマンドを手動タイミングで送信する"
    )
    parser.add_argument(
        "--save-dir",
        required=True,
        help="保存先ディレクトリ（camera_node 側で作成される）",
    )
    parser.add_argument(
        "--prefix",
        default="capture_manual",
        help="空Enter時に使うファイル名プレフィックス",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="起動直後に1回だけ送信して終了する",
    )
    args = parser.parse_args()

    context = zmq.Context()
    sock = context.socket(zmq.PUB)
    sock.setsockopt(zmq.LINGER, 0)
    connect_url = _camera_cmd_connect_url()
    sock.connect(connect_url)

    try:
        print("--- Capture Sender ---")
        print(f"camera command endpoint: {connect_url}")
        print(f"save_dir: {args.save_dir}")
        print("Enter: capture送信 / 入力文字: ファイル名 / q: 終了")

        # PUB/SUB の初回ロスを避けるため短いウォームアップ
        import time

        time.sleep(0.1)

        def send_capture(filename: str) -> None:
            cmd = {
                "action": "capture",
                "save_dir": args.save_dir,
                "filename": filename,
            }
            sock.send_string(json.dumps(cmd, ensure_ascii=False))
            print(f"sent: {filename}")

        if args.once:
            send_capture(_default_filename(args.prefix))
            return

        while True:
            line = input("> ").strip()
            if line.lower() in {"q", "quit", "exit"}:
                break
            if line == "":
                filename = _default_filename(args.prefix)
            else:
                filename = line if "." in line else f"{line}.png"
            send_capture(filename)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        context.term()


if __name__ == "__main__":
    main()
