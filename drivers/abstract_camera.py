from abc import ABC, abstractmethod
import numpy as np
from typing import Optional

class ICamera(ABC):
    @abstractmethod
    def connect(self, port_or_id: str = "0") -> bool:
        """カメラに接続する"""
        pass

    @abstractmethod
    def disconnect(self):
        """カメラから切断する"""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[np.ndarray]:
        """最新のフレームを取得する"""
        pass

    # --- パラメータ設定 ---
    @abstractmethod
    def set_exposure(self, value_us: float):
        """露光時間を設定する（マイクロ秒）"""
        pass

    @abstractmethod
    def set_gain(self, value: float):
        """ゲインを設定する"""
        pass

    @abstractmethod
    def set_gamma(self, value: float):
        """ガンマ補正を設定する"""
        pass

    @abstractmethod
    def set_framerate(self, fps: float):
        """フレームレートを設定する"""
        pass

    # --- 動作モード ---
    @abstractmethod
    def set_continuous_mode(self, is_continuous: bool):
        """映像取り込み(連続)か、画像取り込み(トリガー)かを切り替える"""
        pass

    @abstractmethod
    def execute_software_trigger(self):
        """ソフトウェアトリガーを発行し、1枚撮影する"""
        pass