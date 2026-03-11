import numpy as np
from typing import Optional
from .abstract_camera import ICamera

class TelicamCamera(ICamera):
    def __init__(self):
        self.system = None
        self.cam = None
        self.is_continuous = True

    def connect(self, port_or_id: str = "0") -> bool:
        try:
            import pytelicam
            self.system = pytelicam.get_camera_system()
            # ID(インデックス)でカメラオブジェクトを作成
            self.cam = self.system.create_device_object(int(port_or_id))
            self.cam.open()
            print(f"[TelicamCamera] Successfully connected to camera {port_or_id}")
            return True
        except Exception as e:
            print(f"[TelicamCamera] Connection failed: {e}")
            return False

    def disconnect(self):
        if self.cam is not None:
            self.cam.close()
            self.system.terminate()
            print("[TelicamCamera] Disconnected")

    def get_frame(self) -> Optional[np.ndarray]:
        if self.cam is None:
            return None
        try:
            # トリガーモードでトリガーがかかっていない時のタイムアウトエラー等を回避
            image_data = self.cam.get_image(timeout=100) 
            if image_data.status == 0: # 成功
                return image_data.get_ndarray()
        except Exception:
            pass # タイムアウト時はNoneを返す
        return None

    def set_exposure(self, value_us: float):
        if self.cam:
            self.cam.genapi.set_float_value("ExposureTime", value_us)

    def set_gain(self, value: float):
        if self.cam:
            self.cam.genapi.set_float_value("Gain", value)

    def set_gamma(self, value: float):
        if self.cam:
            self.cam.genapi.set_float_value("Gamma", value)

    def set_framerate(self, fps: float):
        if self.cam:
            self.cam.genapi.set_boolean_value("AcquisitionFrameRateEnable", True)
            self.cam.genapi.set_float_value("AcquisitionFrameRate", fps)

    def set_continuous_mode(self, is_continuous: bool):
        self.is_continuous = is_continuous
        if self.cam:
            mode = "Off" if is_continuous else "On"
            self.cam.genapi.set_enum_str_value("TriggerMode", mode)
            if not is_continuous:
                self.cam.genapi.set_enum_str_value("TriggerSource", "Software")

    def execute_software_trigger(self):
        if self.cam and not self.is_continuous:
            self.cam.genapi.execute_command("TriggerSoftware")