#
# grab_image_callback.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import time
import numpy as np
import pytelicam


# image_data.release() doesn't need to be called in the callback function.
def callback_image_acquired(image_data):
    if image_data.status != pytelicam.CamApiStatus.Success:
        print(f"Grab error! status = {image_data.status}")
    else:
        if image_data.pixel_format == pytelicam.CameraPixelFormat.Mono8:
            np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
        else:
            np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)

        np.set_printoptions(threshold=0)
        print(f"shape      : {np_arr.shape}")
        print(f"image data :\n {np_arr[0,]}")
        print(f"average    : {np.average(np_arr)}\n")

def callback_image_error(status, buffer_index):
    print(f"ImageError Callback! , status={status}, buffer_index = {buffer_index}")

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

        cam_device.cam_stream.open()

        cam_device.cam_stream.set_callback_image_acquired(callback_image_acquired)
        cam_device.cam_stream.set_callback_image_error(callback_image_error)
        cam_device.cam_stream.set_callback_buffer_busy(callback_buffer_busy)

        while True:

            print("---------------------------------------------------------------------")
            print("Press \'0\' + \'Enter\' key to grab frames.")
            print("Press \'9\' + \'Enter\' key to quit application.")
            print("---------------------------------------------------------------------")
            
            key = input()

            if key == '0':
                cam_device.cam_stream.start()
                time.sleep(1)
                cam_device.cam_stream.stop()
                time.sleep(1)
            elif key == '9':
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

        cam_system.terminate()

        print('Finished.')
