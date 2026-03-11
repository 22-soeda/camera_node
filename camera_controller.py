from .drivers.dummy_camera import DummyCamera
from .drivers.telicam_camera import TelicamCamera

class CameraController:
    """カメラドライバのライフサイクルと操作を管理するクラス"""
    def __init__(self):
        self.camera = None

    def _create_driver(self, driver_type: str):
        if driver_type.lower() == "telicam":
            return TelicamCamera()
        return DummyCamera()

    def handle_command(self, cmd: dict):
        """辞書型のコマンドを受け取り、カメラを操作する"""
        action = cmd.get("action")
        
        if action == "connect":
            self.cleanup() # 既存の接続があれば切断
            self.camera = self._create_driver(cmd.get("driver", "dummy"))
            success = self.camera.connect(cmd.get("port", "0"))
            print(f"[CameraController] Connected to {cmd.get('driver')} on port {cmd.get('port')}: {success}")

        elif action == "disconnect":
            self.cleanup()
            print("[CameraController] Disconnected.")

        # 以下、カメラが接続されている場合のみ有効なコマンド
        elif self.camera is not None:
            if action == "set_exposure":
                self.camera.set_exposure(cmd.get("value", 10000.0))
            elif action == "set_gain":
                self.camera.set_gain(cmd.get("value", 1.0))
            elif action == "set_fps":
                self.camera.set_framerate(cmd.get("value", 30.0))
            elif action == "set_mode":
                is_continuous = (cmd.get("value") == "continuous")
                self.camera.set_continuous_mode(is_continuous)
            elif action == "capture":
                self.camera.execute_software_trigger()
        else:
            if action not in ["connect", "disconnect"]:
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