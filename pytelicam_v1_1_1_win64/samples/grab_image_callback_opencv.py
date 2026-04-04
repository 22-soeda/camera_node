#
# grab_image_callback_opencv.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import time
import cv2
import pytelicam


image_stop = False

# image_data.release() doesn't need to be called in the callback function.
def callback_image_acquired(image_data):
    if image_data.status != pytelicam.CamApiStatus.Success:
        print(f"Grab error! status = {image_data.status}")
    else:
        np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)
        np_arr = cv2.resize(np_arr, dsize=(320, 240))
        cv2.imshow('image', np_arr)

        k = cv2.waitKey(1) & 0xFF
        if k == ord('q') or k == 27 :       # 'q' or ESC key
            global image_stop
            image_stop = True


def callback_image_error(status, buffer_index):
    print(f"ImageError Callback! , status = {status}, buffer_index={buffer_index}")

def callback_buffer_busy(buffer_index):
    print(f"BufferBusy Callback! , buffer_index = {buffer_index}")

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

        # It takes a long time when displaying a first image in OpenCV and may cause BufferBusy error.
        # To avoid this error, this sample increases the number of buffers to 32.
        cam_device.cam_stream.open(None, 32)

        cam_device.cam_stream.set_callback_image_acquired(callback_image_acquired)
        cam_device.cam_stream.set_callback_image_error(callback_image_error)
        cam_device.cam_stream.set_callback_buffer_busy(callback_buffer_busy)

        cam_device.cam_stream.start()

        print("Press \'ESC\' key on the OpenCV window to exit.")

        while not image_stop:
            time.sleep(0.1)

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

        cam_system.terminate()

        cv2.destroyAllWindows()

        print("Finished.")
