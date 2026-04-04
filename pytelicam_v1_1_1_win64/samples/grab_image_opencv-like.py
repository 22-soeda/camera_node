#
# grab_image_opencv-like.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import cv2
import numpy as np
import pytelicam


class TeliVideoCapture:
    cam_system = None
    instance_count = 0

    # timeout = 5000ms
    timeout = 5000

    def __init__(self, cam_index):
        self.cam_device = None

        if TeliVideoCapture.cam_system is None:
            # It is recommended that the settings of unused interfaces be removed.
            #  (U3v / Gev / GenTL)
            TeliVideoCapture.cam_system = pytelicam.get_camera_system( \
                                              int(pytelicam.CameraType.U3v) | \
                                              int(pytelicam.CameraType.Gev)
                                              )

        cam_num = TeliVideoCapture.cam_system.get_num_of_cameras()
        print(f"{cam_num} camera(s) found.")
        if cam_index < cam_num:
            self.cam_device = TeliVideoCapture.cam_system.create_device_object(cam_index)
            self.cam_device.open()

            # Set TriggerMode false.
            res = self.cam_device.cam_control.set_trigger_mode(False)
            if res != pytelicam.CamApiStatus.Success:
                raise Exception("Can't set TriggerMode.")

            self.cam_device.cam_stream.open()
            self.cam_device.cam_stream.start()

        TeliVideoCapture.instance_count += 1


    def read(self):
        np_arr = None

        if self.cam_device is None:
            return (False, None)

        with self.cam_device.cam_stream.get_next_image(self.timeout) as image_data:
            if image_data.status != pytelicam.CamApiStatus.Success:
                return (False, None)
            else:
                if image_data.pixel_format == pytelicam.CameraPixelFormat.Mono8:
                    np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
                else:
                    np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)

        return (True, np_arr)


    def release(self):
        if self.cam_device is not None:
            if self.cam_device.cam_stream.is_open:
                self.cam_device.cam_stream.stop()
                self.cam_device.cam_stream.close()

                if self.cam_device.is_open:
                    self.cam_device.close()

            self.cam_device = None

        TeliVideoCapture.instance_count -= 1
        if TeliVideoCapture.instance_count == 0:
            TeliVideoCapture.cam_system.terminate()
            TeliVideoCapture.cam_system = None


if __name__ == "__main__":
    try:
        # Open camera that is detected first, in this sample code.
        cap = TeliVideoCapture(0)
        print("Press \'ESC\' Key on the OpenCV window to exit.\n")

        while(True):
            # Capture frame-by-frame
            res, frame = cap.read()

            frame = cv2.resize(frame, dsize=(320, 240))
            # Display the resulting frame
            cv2.imshow('image', frame)

            k = cv2.waitKey(1)
            if k == ord('q') or k == 27 :       # 'q' or ESC key
                break

        # When everything done, release the capture
        cap.release()
        cv2.destroyAllWindows()

    except pytelicam.PytelicamError as teli_exception:
        print("An error occurred!")
        print(f"  message : {teli_exception.message}")
        print(f"  status  : {teli_exception.status}")

    except Exception as exception:
        print(exception)

    finally:
        print("Finished.")
