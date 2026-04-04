#
# get_camera_information.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import pytelicam


if __name__ == "__main__":
    # It is recommended that the settings of unused interfaces be removed.
    #  (U3v / Gev / GenTL)
    cam_system = pytelicam.get_camera_system( \
        int(pytelicam.CameraType.U3v) | \
        int(pytelicam.CameraType.Gev) | \
        int(pytelicam.CameraType.GenTL) \
        )

    sys_info = cam_system.get_information()

    print("<System information>")
    print(f"  TeliCamApi version  : {sys_info.dll_version}")

    try:
        cam_num = cam_system.get_num_of_cameras()
        if cam_num == 0:
            print("Camera not found.")
            sys.exit()

        print(f"{cam_num} camera(s) found.")

        for no in range(cam_num):
            cam_info = cam_system.get_camera_information(no)

            print(f"<Camera{no} information>")
            print(f"  Cam type              : {cam_info.cam_type}")
            print(f"  Cam vendor            : {cam_info.cam_vendor}")
            print(f"  Cam model             : {cam_info.cam_model}")
            print(f"  Cam serial number     : {cam_info.cam_serial_number}")
            print(f"  Cam version           : {cam_info.cam_version}")
            print(f"  Cam user defined name : {cam_info.cam_user_defined_name}")
            print(f"  Cam display name      : {cam_info.cam_display_name}")
            print(f"  TL vendor             : {cam_info.tl_vendor}")
            print(f"  TL model              : {cam_info.tl_model}")
            print(f"  TL version            : {cam_info.tl_version}")
            print(f"  TL display name       : {cam_info.tl_display_name}")
            print(f"  TL-IF display name    : {cam_info.tl_if_display_name}\n")

        # Open a camera that is detected first, in this sample code.
        cam_no = 0
        cam_device = cam_system.create_device_object(cam_no)
        cam_device.open()

        # Get sensor width.
        status, sensor_width  = cam_device.cam_control.get_sensor_width()
        if status != pytelicam.CamApiStatus.Success:
            print(f"Failed get_sensor_width, status = {status}\n")
            sys.exit()

        print(f"  The maximum image width  in pixels : {sensor_width:4d}")

        # Get sensor height.
        status, sensor_height = cam_device.cam_control.get_sensor_height()
        if status != pytelicam.CamApiStatus.Success:
            print(f"Failed get_sensor_height, status = {status}\n")
            sys.exit()

        print(f"  The maximum image height in pixels : {sensor_height:4d}")

    except pytelicam.PytelicamError as teli_exception:
        print("An error occurred!")
        print(f"  message : {teli_exception.message}")
        print(f"  status  : {teli_exception.status}")
    except Exception as exception:
        print(exception)

    finally:
        if 'cam_device' in globals():
            if cam_device.is_open:
                cam_device.close()

        cam_system.terminate()

        print('Finished.')
