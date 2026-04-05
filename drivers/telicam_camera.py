import logging
import time
from typing import Optional

import cv2
import numpy as np

from .abstract_camera import ICamera

logger = logging.getLogger(__name__)

try:
    import pytelicam
except ImportError:  # pragma: no cover
    pytelicam = None


def _camera_system_flags() -> int:
    assert pytelicam is not None
    return int(pytelicam.CameraType.U3v) | int(pytelicam.CameraType.Gev)


def _image_data_to_bgr(image_data) -> np.ndarray:
    """ImageData を OpenCV 表示向け BGR uint8 に変換する。"""
    assert pytelicam is not None
    pf = image_data.pixel_format

    if pf == pytelicam.CameraPixelFormat.Mono8:
        raw = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
        return cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)

    if pf == pytelicam.CameraPixelFormat.RGB8:
        raw = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
        return cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)

    if pf == pytelicam.CameraPixelFormat.BGR8:
        return image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)

    try:
        return image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)
    except pytelicam.PytelicamError:
        raw = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
        if raw.ndim == 2:
            return cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
        if raw.ndim == 3 and raw.shape[2] == 3:
            return cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
        raise


class TelicamCamera(ICamera):
    """Teli pytelicam を用いた ICamera 実装（公式サンプルのストリーム取得に準拠）。"""

    # grab_image_opencv-like.py に合わせた get_next_image の待ち時間 (ms)
    _GET_NEXT_IMAGE_TIMEOUT_MS = 5000
    # 自動再接続の連打を防ぐ（秒）
    _AUTO_RECONNECT_COOLDOWN_SEC = 3.0

    def __init__(self):
        self._system = None
        self._cam = None
        self.is_continuous = True
        self._trigger_pending = False
        self._port_or_id: Optional[str] = None
        self._last_auto_reconnect_time = 0.0

    def connect(self, port_or_id: str = "0") -> bool:
        if pytelicam is None:
            logger.error("pytelicam がインポートできません")
            return False

        self.disconnect()

        try:
            self._system = pytelicam.get_camera_system(_camera_system_flags())
            cam_index = int(port_or_id)
            self._cam = self._system.create_device_object(cam_index)
            self._cam.open()

            self._apply_trigger_mode()
            self._start_stream()

            self._port_or_id = str(port_or_id)
            logger.info("TeliCam に接続しました (index=%s)", cam_index)
            return True
        except Exception as e:
            logger.exception("TeliCam 接続失敗: %s", e)
            self._cleanup_resources()
            self._port_or_id = None
            return False

    def disconnect(self):
        active = self._cam is not None or self._system is not None
        self._cleanup_resources()
        self._port_or_id = None
        if active:
            logger.info("TeliCam を切断しました")

    def _cleanup_resources(self):
        self._stop_stream()
        if self._cam is not None:
            try:
                if self._cam.is_open:
                    self._cam.close()
            except Exception as e:
                logger.warning("カメラ close 中にエラー: %s", e)
            self._cam = None
        if self._system is not None:
            try:
                self._system.terminate()
            except Exception as e:
                logger.warning("camera_system terminate 中にエラー: %s", e)
            self._system = None
        self._trigger_pending = False

    @staticmethod
    def _is_stream_timeout_status(status) -> bool:
        if pytelicam is None:
            return False
        return status in (
            pytelicam.CamApiStatus.RequestTimeout,
            pytelicam.CamApiStatus.Timeout,
            pytelicam.CamApiStatus.ResendTimeout,
            pytelicam.CamApiStatus.ResponseTimeout,
        )

    def reconnect_after_stream_timeout(self) -> bool:
        """ストリーム取得がタイムアウトしたとき、切断して同じデバイス index で再接続する。"""
        if pytelicam is None:
            return False
        port = self._port_or_id
        if port is None:
            return False
        now = time.monotonic()
        if now - self._last_auto_reconnect_time < self._AUTO_RECONNECT_COOLDOWN_SEC:
            logger.debug(
                "TeliCam 自動再接続はクールダウン中 (あと %.1fs)",
                self._AUTO_RECONNECT_COOLDOWN_SEC - (now - self._last_auto_reconnect_time),
            )
            return False
        self._last_auto_reconnect_time = now
        logger.warning("TeliCam ストリームタイムアウトのため切断→再接続します (index=%s)", port)
        return self.connect(port)

    def _apply_trigger_mode(self):
        cc = self._cam.cam_control
        if self.is_continuous:
            if cc.set_trigger_mode(False) != pytelicam.CamApiStatus.Success:
                raise RuntimeError("TriggerMode を Off にできません")
            return

        if cc.set_trigger_mode(True) != pytelicam.CamApiStatus.Success:
            raise RuntimeError("TriggerMode を On にできません")
        if cc.set_trigger_source(pytelicam.CameraTriggerSource.Software) != pytelicam.CamApiStatus.Success:
            raise RuntimeError("TriggerSource を Software にできません")
        if cc.set_trigger_sequence(pytelicam.CameraTriggerSequence.Sequence0) != pytelicam.CamApiStatus.Success:
            raise RuntimeError("TriggerSequence を設定できません")

    def _start_stream(self):
        if self._cam.cam_stream.is_open:
            return
        self._cam.cam_stream.open()
        self._cam.cam_stream.start()

    def _stop_stream(self):
        if self._cam is None:
            return
        try:
            if self._cam.cam_stream.is_open:
                self._cam.cam_stream.stop()
                self._cam.cam_stream.close()
        except Exception as e:
            logger.warning("ストリーム停止中にエラー: %s", e)

    def get_frame(self) -> Optional[np.ndarray]:
        if self._cam is None or not self._cam.cam_stream.is_open:
            return None

        if not self.is_continuous:
            if not self._trigger_pending:
                return None
            self._trigger_pending = False

        # get_next_image の with が ImageData::Release するまで切断しない（InvalidStreamHandle 防止）
        reconnect_after = False
        img: Optional[np.ndarray] = None

        try:
            if not self.is_continuous:
                st = self._cam.cam_control.execute_software_trigger()
                if st != pytelicam.CamApiStatus.Success:
                    logger.warning("execute_software_trigger が失敗: %s", st)
                    return None

            with self._cam.cam_stream.get_next_image(self._GET_NEXT_IMAGE_TIMEOUT_MS) as image_data:
                if image_data.status != pytelicam.CamApiStatus.Success:
                    if self._is_stream_timeout_status(image_data.status):
                        logger.warning(
                            "フレーム取得失敗: %s → with 終了後に自動再接続します",
                            image_data.status,
                        )
                        reconnect_after = True
                    else:
                        logger.warning("フレーム取得失敗: %s", image_data.status)
                else:
                    img = _image_data_to_bgr(image_data)
        except pytelicam.PytelicamError as e:
            st = getattr(e, "status", None)
            if st is not None and self._is_stream_timeout_status(st):
                logger.warning("pytelicam エラー (タイムアウト): %s → 自動再接続を試行", e)
                reconnect_after = True
            else:
                logger.warning("pytelicam エラー: %s", e)

        if reconnect_after:
            self.reconnect_after_stream_timeout()
        return img

    def set_exposure(self, value_us: float):
        if self._cam is None:
            return
        cc = self._cam.cam_control
        st, lo, hi = cc.get_exposure_time_min_max()
        if st != pytelicam.CamApiStatus.Success:
            return
        v = max(lo, min(hi, float(value_us)))
        cc.set_exposure_time(v)

    def set_gain(self, value: float):
        if self._cam is None:
            return
        cc = self._cam.cam_control
        st, lo, hi = cc.get_gain_min_max()
        if st != pytelicam.CamApiStatus.Success:
            return
        v = max(lo, min(hi, float(value)))
        cc.set_gain(v)

    def set_gamma(self, value: float):
        if self._cam is None:
            return
        cc = self._cam.cam_control
        st, lo, hi = cc.get_gamma_min_max()
        if st != pytelicam.CamApiStatus.Success:
            return
        v = max(lo, min(hi, float(value)))
        cc.set_gamma(v)

    def set_framerate(self, fps: float):
        if self._cam is None:
            return
        cc = self._cam.cam_control
        if cc.set_acquisition_frame_rate_control(pytelicam.CameraAcqFrameRateCtrl.Manual) != pytelicam.CamApiStatus.Success:
            return
        st, lo, hi = cc.get_acquisition_frame_rate_min_max()
        if st != pytelicam.CamApiStatus.Success:
            return
        v = max(lo, min(hi, float(fps)))
        cc.set_acquisition_frame_rate(v)

    def set_continuous_mode(self, is_continuous: bool):
        self.is_continuous = is_continuous
        if self._cam is None:
            return
        self._stop_stream()
        try:
            self._apply_trigger_mode()
            self._start_stream()
        except Exception as e:
            logger.exception("撮影モード切替に失敗: %s", e)

    def execute_software_trigger(self):
        if self._cam is None or self.is_continuous:
            return
        self._trigger_pending = True
