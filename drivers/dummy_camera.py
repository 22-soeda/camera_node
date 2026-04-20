import time
import cv2
import random
import numpy as np
from pathlib import Path
from typing import Optional
from .abstract_camera import ICamera

class DummyCamera(ICamera):
    def __init__(self):
        self.is_connected = False
        self.is_continuous = True
        
        # 画像ディレクトリの指定 (dummy_images フォルダから読み込む)
        self.image_dir = Path(__file__).parent.parent / "dummy_images"
        self.image_files = list(self.image_dir.glob("*.png")) + list(self.image_dir.glob("*.jpg"))
        
        self.images = []
        if not self.image_files:
            print(f"⚠️ 警告: {self.image_dir} に画像が見つかりません。テスト用の黒画像を生成します。")
            self.images = [np.zeros((480, 640, 3), dtype=np.uint8)]
        else:
            for img_path in self.image_files:
                img = cv2.imread(str(img_path))
                if img is not None:
                    self.images.append(img)
            print(f"✅ ダミー画像を {len(self.images)} 枚読み込みました。")

        self.current_image = random.choice(self.images)
        self.last_update_time = time.time()
        self.refresh_time = 10.0  # 画像の切り替え間隔（秒）

        # カメラの初期パラメータ
        self.exposure = 10000.0
        self.gain = 1.0
        self.fps = 30.0
        self.frame_interval = 1.0 / self.fps
        self.last_frame_time = 0
        self.trigger_flag = False

    def connect(self, port_or_id: str = "0") -> bool:
        print(f"[DummyCamera] Connected to port {port_or_id}")
        self.is_connected = True
        return True

    def disconnect(self):
        print("[DummyCamera] Disconnected")
        self.is_connected = False

    def get_frame(self) -> Optional[np.ndarray]:
        if not self.is_connected:
            return None

        current_time = time.time()
        
        # トリガーモード時の処理
        if not self.is_continuous:
            if not self.trigger_flag:
                return None
            self.trigger_flag = False # トリガー消費

        # フレームレート制御 (連続モード時)
        elif current_time - self.last_frame_time < self.frame_interval:
            return None 

        self.last_frame_time = current_time

        # 指定時間ごとに画像をランダムに切り替え
        if current_time - self.last_update_time > self.refresh_time:
            self.current_image = random.choice(self.images)
            self.last_update_time = current_time

        # OpenCVで読み込んだ画像をそのまま返す
        return self.current_image.copy()

    def set_exposure(self, value_us: float):
        self.exposure = value_us
        print(f"[DummyCamera] Exposure set to {value_us} us")

    def get_exposure(self) -> Optional[float]:
        return float(self.exposure)

    def set_gain(self, value: float):
        self.gain = value
        print(f"[DummyCamera] Gain set to {value}")

    def set_gamma(self, value: float):
        print(f"[DummyCamera] Gamma set to {value}")

    def set_framerate(self, fps: float):
        self.fps = fps
        self.frame_interval = 1.0 / fps
        print(f"[DummyCamera] Framerate set to {fps} fps")

    def set_continuous_mode(self, is_continuous: bool):
        self.is_continuous = is_continuous
        mode = "Continuous" if is_continuous else "Trigger"
        print(f"[DummyCamera] Mode set to {mode}")

    def execute_software_trigger(self):
        if not self.is_continuous:
            self.trigger_flag = True
            print("[DummyCamera] Software trigger executed")