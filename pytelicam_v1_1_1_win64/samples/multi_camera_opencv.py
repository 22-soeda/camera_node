#
# multi_camera_opencv.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import numpy as np
import cv2
import pytelicam


if __name__ == "__main__":
    # It is recommended to set the interfaces be used.
    #  (U3v / Gev / GenTL)
    cam_system = pytelicam.get_camera_system( \
        int(pytelicam.CameraType.U3v) | \
        int(pytelicam.CameraType.Gev))

    try:
        cam_num = cam_system.get_num_of_cameras()
        if cam_num == 0:
            print("Camera not found.")
            sys.exit()

        print(f"{cam_num} camera(s) found.")

        cam_device = []
        receive_signal = []

        for i in range(cam_num):
            cam_device.append(cam_system.create_device_object(i))
            receive_signal.append(cam_system.create_signal())

        for i in range(cam_num):
            cam_device[i].open()

            # Set TriggerMode false.
            res = cam_device[i].cam_control.set_trigger_mode(False)
            if res != pytelicam.CamApiStatus.Success:
                raise Exception("Can't set TriggerMode.")

            cam_device[i].cam_stream.open(receive_signal[i])
            cam_device[i].cam_stream.start()

        print("Press \'ESC\' Key on the OpenCV window to exit\n")

        while True:
            for i in range(cam_num):
                res = cam_system.wait_for_signal(receive_signal[i], 0)
                if res == pytelicam.CamApiStatus.Success:
                    # If you don't use 'with' statement, image_data.release() must be called after using image_data.
                    with cam_device[i].cam_stream.get_current_buffered_image() as image_data:
                        if image_data.status != pytelicam.CamApiStatus.Success:
                            print(f"Grab error! status = {image_data.status}")
                            break
                        else:
                            np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)
                            np_arr = cv2.resize(np_arr, dsize=(320, 240))
                            cv2.imshow('image %d' %i, np_arr)

            k = cv2.waitKey(1)
            if k == ord('q') or k == 27 :       # 'q' or ESC key
                break

    except pytelicam.PytelicamError as teli_exception:
        print("An error occurred!")
        print(f"  message : {teli_exception.message}")
        print(f"  status  : {teli_exception.status}")
    except Exception as exception:
        print(exception)

    finally:
        for i in range(cam_num):
            if cam_device[i] is not None:
                if cam_device[i].cam_stream.is_open:
                    cam_device[i].cam_stream.stop()
                    cam_device[i].cam_stream.close()

                if cam_device[i].is_open:
                    cam_device[i].close()

            if receive_signal[i] is not None:
                cam_system.close_signal(receive_signal[i])

        cam_system.terminate()

        cv2.destroyAllWindows()

        print("Finished.")
