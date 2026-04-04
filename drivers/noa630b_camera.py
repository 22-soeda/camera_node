"""NOA630B（Wraycam SDK / Pull モード）向け ICamera 実装。"""

from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Optional

import cv2
import numpy as np

from .abstract_camera import ICamera

logger = logging.getLogger(__name__)

_LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

try:
    import wraycam
except ImportError:  # pragma: no cover
    wraycam = None

_MODEL_SUBSTR = "NOA630B"


def _maybe_import_wraycam():
    if wraycam is None:
        raise RuntimeError("wraycam をインポートできません。lib/wraycam.py と wraycam.dll を確認してください。")


def _enum_devices():
    _maybe_import_wraycam()
    return wraycam.Wraycam.EnumV2()


def _any_gige(devices: list) -> bool:
    for d in devices:
        try:
            if d.model and (d.model.flag & wraycam.WRAYCAM_FLAG_GIGE):
                return True
            if d.model and (d.model.flag & wraycam.WRAYCAM_FLAG_10GIGE):
                return True
        except Exception:
            continue
    return False


def _resolve_cam_id(port_or_id: str) -> Optional[str]:
    """port_or_id から Wraycam_Open に渡す camId を決定する。"""
    _maybe_import_wraycam()
    devices = _enum_devices()
    s = (port_or_id or "").strip()

    if s.startswith(("sn:", "ip:", "name:", "mac:")):
        return s

    # 機種名 NOA630B を優先
    needle = _MODEL_SUBSTR.upper()
    for d in devices:
        name = (d.model.name or "") if d.model else ""
        if needle in name.upper():
            return d.id

    if s.isdigit():
        idx = int(s)
        if 0 <= idx < len(devices):
            return devices[idx].id

    if devices:
        logger.warning(
            "NOA630B に一致するカメラが見つかりません。先頭デバイスを開きます: %s",
            devices[0].displayname,
        )
        return devices[0].id

    return None


class NOA630BCamera(ICamera):
    """Wraycam SDK を用いた NOA630B 向け ICamera 実装（Pull + コールバック）。"""

    def __init__(self):
        self._hcam = None
        self._raw_buf: Optional[bytes] = None
        self._width = 0
        self._height = 0
        self._stride = 0
        self._pull_bits = 24
        self._mono = False
        self._model_flags = 0
        self._lock = threading.Lock()
        self._latest_bgr: Optional[np.ndarray] = None
        self.is_continuous = True
        self._trigger_pending = False

    @staticmethod
    def _callback(n_event: int, ctx: "NOA630BCamera"):
        if ctx._hcam is None:
            return
        if n_event == wraycam.WRAYCAM_EVENT_IMAGE and ctx.is_continuous:
            ctx._pull_and_store_latest()
        elif n_event == wraycam.WRAYCAM_EVENT_ERROR:
            logger.warning("Wraycam WRAYCAM_EVENT_ERROR")

    def _realloc_buffer(self):
        assert self._hcam is not None
        w, h = self._hcam.get_Size()
        self._width = int(w)
        self._height = int(h)
        self._pull_bits = 8 if self._mono else 24
        self._stride = wraycam.TDIBWIDTHBYTES(self._width * self._pull_bits)
        self._raw_buf = bytes(self._stride * self._height)

    def _buf_to_bgr(self) -> np.ndarray:
        arr = np.frombuffer(self._raw_buf, dtype=np.uint8, count=self._stride * self._height)
        view = arr.reshape((self._height, self._stride))
        if self._mono:
            gray = view[:, : self._width].copy()
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        rgb = view[:, : self._width * 3].reshape((self._height, self._width, 3))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def _pull_and_store_latest(self):
        if self._hcam is None or self._raw_buf is None:
            return
        try:
            self._hcam.PullImageV4(self._raw_buf, 0, self._pull_bits, 0, None)
            bgr = self._buf_to_bgr()
            with self._lock:
                self._latest_bgr = bgr
        except wraycam.HRESULTException as ex:
            logger.debug("PullImageV4 failed: hr=0x%x", ex.hr & 0xFFFFFFFF)

    def _apply_trigger_option_only(self):
        if self._hcam is None:
            return
        mode = 0 if self.is_continuous else 1
        self._hcam.put_Option(wraycam.WRAYCAM_OPTION_TRIGGER, mode)

    def _restart_pull(self):
        if self._hcam is None:
            return
        self._hcam.Stop()
        self._apply_trigger_option_only()
        self._hcam.StartPullModeWithCallback(NOA630BCamera._callback, self)

    def connect(self, port_or_id: str = "0") -> bool:
        if wraycam is None:
            logger.error("wraycam が利用できません")
            return False

        self.disconnect()

        try:
            devices = _enum_devices()
            if _any_gige(devices):
                try:
                    wraycam.Wraycam.GigeEnable(None, None)
                except Exception as e:
                    logger.debug("GigeEnable をスキップまたは失敗: %s", e)

            cam_id = _resolve_cam_id(port_or_id)
            if not cam_id:
                logger.error("カメラが見つかりません")
                return False

            self._hcam = wraycam.Wraycam.Open(cam_id)
            if not self._hcam:
                logger.error("Wraycam.Open に失敗しました")
                return False

            devs = _enum_devices()
            self._model_flags = 0
            cam_key = str(cam_id)
            for d in devs:
                if str(d.id) == cam_key:
                    self._model_flags = int(d.model.flag) if d.model else 0
                    break

            self._mono = (self._model_flags & wraycam.WRAYCAM_FLAG_MONO) != 0
            # OpenCV 側で RGB→BGR するため RGB バイト順で取得
            self._hcam.put_Option(wraycam.WRAYCAM_OPTION_BYTEORDER, 0)

            self._realloc_buffer()
            self._apply_trigger_option_only()
            self._hcam.StartPullModeWithCallback(NOA630BCamera._callback, self)

            logger.info("NOA630B (Wraycam) に接続しました camId=%s", cam_id)
            return True
        except Exception as e:
            logger.exception("NOA630B 接続失敗: %s", e)
            self._cleanup_resources()
            return False

    def disconnect(self):
        active = self._hcam is not None
        self._cleanup_resources()
        if active:
            logger.info("NOA630B (Wraycam) を切断しました")

    def _cleanup_resources(self):
        if self._hcam is not None:
            try:
                self._hcam.Stop()
            except Exception as e:
                logger.warning("Stop 中にエラー: %s", e)
            try:
                self._hcam.Close()
            except Exception as e:
                logger.warning("Close 中にエラー: %s", e)
            self._hcam = None
        self._raw_buf = None
        self._latest_bgr = None
        self._trigger_pending = False

    def get_frame(self) -> Optional[np.ndarray]:
        if self._hcam is None:
            return None

        if self.is_continuous:
            with self._lock:
                if self._latest_bgr is None:
                    return None
                return self._latest_bgr.copy()

        if not self._trigger_pending:
            return None
        self._trigger_pending = False

        if self._raw_buf is None:
            return None

        try:
            self._hcam.TriggerSyncV4(10000, self._raw_buf, 0, self._pull_bits, 0, None)
            return self._buf_to_bgr()
        except wraycam.HRESULTException as e:
            logger.warning("TriggerSyncV4 失敗: hr=0x%x", e.hr & 0xFFFFFFFF)
            return None

    def set_exposure(self, value_us: float):
        if self._hcam is None:
            return
        try:
            lo, hi, _ = self._hcam.get_ExpTimeRange()
            v = int(max(lo, min(hi, float(value_us))))
            self._hcam.put_AutoExpoEnable(0)
            self._hcam.put_ExpoTime(v)
        except wraycam.HRESULTException as e:
            logger.debug("set_exposure: %s", e)

    def set_gain(self, value: float):
        if self._hcam is None:
            return
        try:
            lo, hi, _ = self._hcam.get_ExpoAGainRange()
            v = int(max(lo, min(hi, float(value))))
            self._hcam.put_AutoExpoEnable(0)
            self._hcam.put_ExpoAGain(v)
        except wraycam.HRESULTException as e:
            logger.debug("set_gain: %s", e)

    def set_gamma(self, value: float):
        if self._hcam is None:
            return
        try:
            self._hcam.put_Gamma(int(round(value)))
        except wraycam.HRESULTException as e:
            logger.debug("set_gamma: %s", e)

    def set_framerate(self, fps: float):
        if self._hcam is None:
            return
        try:
            if self._model_flags & wraycam.WRAYCAM_FLAG_PRECISE_FRAMERATE:
                lo = self._hcam.get_Option(wraycam.WRAYCAM_OPTION_MIN_PRECISE_FRAMERATE)
                hi = self._hcam.get_Option(wraycam.WRAYCAM_OPTION_MAX_PRECISE_FRAMERATE)
                target = int(round(float(fps) * 10))
                target = max(lo, min(hi, target))
                self._hcam.put_Option(wraycam.WRAYCAM_OPTION_PRECISE_FRAMERATE, target)
                return
        except wraycam.HRESULTException:
            pass

        try:
            ms = self._hcam.MaxSpeed()
            if ms <= 0:
                return
            # 簡易マッピング: 1〜60 fps を速度レベルに線形割当
            f = max(1.0, min(60.0, float(fps)))
            sp = int(round((f / 60.0) * ms))
            sp = max(0, min(ms, sp))
            self._hcam.put_Speed(sp)
        except wraycam.HRESULTException as e:
            logger.debug("set_framerate: %s", e)

    def set_continuous_mode(self, is_continuous: bool):
        self.is_continuous = is_continuous
        if self._hcam is None:
            return
        try:
            self._restart_pull()
        except Exception as e:
            logger.exception("撮影モード切替に失敗: %s", e)

    def execute_software_trigger(self):
        if self._hcam is None or self.is_continuous:
            return
        self._trigger_pending = True
