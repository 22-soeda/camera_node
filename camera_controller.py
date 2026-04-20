import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from core import message_config

from .drivers.dummy_camera import DummyCamera
from .drivers.noa630b_camera import NOA630BCamera
from .drivers.telicam_camera import TelicamCamera


class CameraController:
    """カメラドライバのライフサイクルと操作を管理するクラス"""

    _BRIGHTNESS_EPS = 1e-3

    def __init__(self):
        self.camera = None
        self.target_brightness = 128.0
        self._last_exposure_us = None

    def _create_driver(self, driver_type: str):
        t = (driver_type or "").lower()
        if t == "telicam":
            return TelicamCamera()
        if t == "noa630b":
            return NOA630BCamera()
        return DummyCamera()

    @staticmethod
    def _mean_gray_brightness(frame: np.ndarray) -> float:
        if frame.ndim == 2:
            return float(np.mean(frame))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def _sync_last_exposure_from_camera(self):
        if self.camera is None:
            return
        t = self.camera.get_exposure()
        if t is not None:
            self._last_exposure_us = t

    def _adjust_exposure_once(
        self,
        max_iterations: int,
        tolerance: float,
        sleep_s: float,
    ) -> None:
        target = self.target_brightness
        for _ in range(max(1, int(max_iterations))):
            frame = self.camera.get_frame()
            if frame is None:
                print("[CameraController] adjust_exposure: フレームを取得できませんでした。")
                return
            measured = self._mean_gray_brightness(frame)
            if abs(measured - target) <= tolerance:
                return

            current = self.camera.get_exposure()
            if current is None:
                current = self._last_exposure_us
            if current is None:
                current = 10000.0

            ratio = target / max(measured, self._BRIGHTNESS_EPS)
            new_exp = current * ratio
            self.camera.set_exposure(new_exp)
            self._sync_last_exposure_from_camera()
            if self._last_exposure_us is None:
                self._last_exposure_us = float(new_exp)

            if sleep_s > 0:
                time.sleep(sleep_s)

    def _save_capture_if_requested(self, save_dir: Optional[str]) -> None:
        if not save_dir:
            return
        frame = self.camera.get_frame()
        if frame is None:
            print("[CameraController] capture save skipped: フレームを取得できませんでした。")
            return

        output_dir = Path(save_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        output_path = output_dir / filename

        if cv2.imwrite(str(output_path), frame):
            print(f"[CameraController] Captured image saved: {output_path.resolve()}")
        else:
            print(f"[CameraController] Failed to save captured image: {output_path}")

    def handle_command(self, cmd: dict, source: str = "terminal") -> Optional[dict[str, Any]]:
        """辞書型のコマンドを受け取り、カメラを操作する。

        source が \"zmq\" のとき、get_target_brightness は PUB 用の応答 dict を返す。
        """
        action = cmd.get("action")

        if action == "connect":
            self.cleanup()  # 既存の接続があれば切断
            self.camera = self._create_driver(cmd.get("driver", "dummy"))
            success = self.camera.connect(cmd.get("port", "0"))
            if success:
                self._sync_last_exposure_from_camera()
            print(f"[CameraController] Connected to {cmd.get('driver')} on port {cmd.get('port')}: {success}")

        elif action == "disconnect":
            self.cleanup()
            print("[CameraController] Disconnected.")

        elif action == "set_target_brightness":
            self.target_brightness = float(cmd.get("value", 128.0))

        elif action == "get_target_brightness":
            if source == "terminal":
                print(f"[CameraController] target_brightness: {self.target_brightness}")
                return None
            return {
                "topic": message_config.TOPIC_CAMERA_CMD_REPLY,
                "body": {
                    "action": "get_target_brightness",
                    "value": self.target_brightness,
                },
            }

        # 以下、カメラが接続されている場合のみ有効なコマンド
        elif self.camera is not None:
            if action == "set_exposure":
                v = float(cmd.get("value", 10000.0))
                self.camera.set_exposure(v)
                self._sync_last_exposure_from_camera()
                if self._last_exposure_us is None:
                    self._last_exposure_us = v
            elif action == "set_gain":
                self.camera.set_gain(cmd.get("value", 1.0))
            elif action == "set_fps":
                self.camera.set_framerate(cmd.get("value", 30.0))
            elif action == "set_mode":
                is_continuous = cmd.get("value") == "continuous"
                self.camera.set_continuous_mode(is_continuous)
            elif action == "capture":
                self.camera.execute_software_trigger()
                self._save_capture_if_requested(cmd.get("save_dir"))
            elif action == "adjust_exposure":
                self._adjust_exposure_once(
                    max_iterations=int(cmd.get("max_iterations", 1)),
                    tolerance=float(cmd.get("tolerance", 1.0)),
                    sleep_s=float(cmd.get("sleep_s", 0.05)),
                )
            elif action == "get_exposure" and cmd.get("terminal"):
                t = self.camera.get_exposure()
                if t is not None:
                    print(f"[CameraController] exposure: {t} us")
                else:
                    print("[CameraController] exposure: (取得できません)")
        else:
            if action == "get_exposure" and cmd.get("terminal"):
                print("[CameraController] Camera is not connected.")
            elif action not in [
                "connect",
                "disconnect",
                "set_target_brightness",
                "get_target_brightness",
            ]:
                print(f"[CameraController] Camera is not connected. Ignored command: {action}")

    def get_frame(self):
        """最新のフレームを取得する"""
        if self.camera is not None:
            return self.camera.get_frame()
        return None

    def cleanup(self):
        """終了処理・切断処理"""
        if self.camera is not None:
            self.camera.disconnect()
            self.camera = None
        self._last_exposure_us = None
