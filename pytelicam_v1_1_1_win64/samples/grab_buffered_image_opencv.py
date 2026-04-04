#
# grab_buffered_image_opencv.py (for Python 3)
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

        # Open a camera that is detected first, in this sample code.
        cam_no = 0
        cam_device = cam_system.create_device_object(cam_no)
        cam_device.open()

        # Set TriggerMode false.
        res = cam_device.cam_control.set_trigger_mode(False)
        if res != pytelicam.CamApiStatus.Success:
            raise Exception("Can't set TriggerMode.")

        receive_signal = cam_system.create_signal()

        cam_device.cam_stream.open(receive_signal)
        cam_device.cam_stream.start()

        print("Press \'ESC\' Key on the OpenCV window to exit.\n")

        while True:
            res = cam_system.wait_for_signal(receive_signal)
            if res != pytelicam.CamApiStatus.Success:
                print(f"Grab error! status = {res}")
                break
            else:
                current_index = cam_device.cam_stream.get_current_buffer_index()
                # Please use the following comments for debugging (check for any missing or skipped the current_index, etc).
                #print(f"current_index = {current_index}")

                # If you don't use 'with' statement, image_data.release() must be called after using image_data.
                with cam_device.cam_stream.get_buffered_image(current_index) as image_data:
                    if image_data.status != pytelicam.CamApiStatus.Success:
                        print(f"Grab error! status = {image_data.status}")
                    else:
                        if image_data.pixel_format == pytelicam.CameraPixelFormat.Mono8:
                            np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
                        else:
                            np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)

                        np_arr = cv2.resize(np_arr, dsize=(320, 240))
                        cv2.imshow('image', np_arr)
                    
                    k = cv2.waitKey(5) & 0xFF
                    if k == ord('q') or k == 27 :       # 'q' or ESC key
                        break


    except pytelicam.PytelicamError as teli_exception:
        print("An error occurred!")
        print(f"  message : {teli_exception.message}")
        print(f"  status  : {teli_exception.status}")
    except Exception as exception:
        print(exception)


    finally:
        if 'cam_device' in globals():
            if cam_device.cam_stream.is_open:
                cam_device.cam_stream.stop()
                cam_device.cam_stream.close()

            if cam_device.is_open:
                cam_device.close()

        if 'receive_signal' in globals():
            cam_system.close_signal(receive_signal)

        cam_system.terminate()

        print("Finished.")
