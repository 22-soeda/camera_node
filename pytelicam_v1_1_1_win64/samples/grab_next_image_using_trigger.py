#
# grab_next_image_using_trigger.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
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

        # Set TriggerMode true.
        res = cam_device.cam_control.set_trigger_mode(True)
        if res != pytelicam.CamApiStatus.Success:
            raise Exception("Can't set TriggerMode.")

        # Set TriggerSource software.
        # The set_trigger_source can be set both a "SoftwareTrigger" and a "HardwareTrigger".
        #   "SoftwareTrigger" : Software
        #   "HardwareTrigger" : Line0, Line1, Line2
        # note1:When configuring a "HardwareTrigger", check the camera specifications to determine which Lines (Line0, Line1, or Line2) to use.
        # note2:When configuring a "HardwareTrigger", need to set an appropriate timeout duration using the wait_for_signal.
        res = cam_device.cam_control.set_trigger_source(pytelicam.pytelicam.CameraTriggerSource.Software)
        if res != pytelicam.CamApiStatus.Success:
            raise Exception("Can't set TriggerSource.")

        # Set TriggerSequence Sequence0.
        cam_device.cam_control.set_trigger_sequence(pytelicam.pytelicam.CameraTriggerSequence.Sequence0)
        # Please use the following comments, if you use cameras with a cpu.
        '''
        res = cam_device.cam_control.set_trigger_sequence(pytelicam.pytelicam.CameraTriggerSequence.Sequence0)
        if res != pytelicam.CamApiStatus.Success:
            raise Exception("Can't set TriggerSequence.")
        '''

        cam_device.cam_stream.open()
        cam_device.cam_stream.start()

        np.set_printoptions(threshold=0)

        print("---------------------------------------------------------------------")
        print("Press \'0\' + \'Enter\' key to issue \"Software Trigger\" and grab a frame.")
        print("Press \'9\' + \'Enter\' key to quit application.")
        print("---------------------------------------------------------------------")


        while True:
            key = input()

            if key == '0':
                res = cam_device.genapi.execute_command('TriggerSoftware')
                if res != pytelicam.CamApiStatus.Success:
                    raise Exception("Can't execute TriggerSoftware.")
                else:
                    # If you don't use 'with' statement, image_data.release() must be called after using image_data.
                    with cam_device.cam_stream.get_next_image() as image_data:
                        if image_data.status != pytelicam.CamApiStatus.Success:
                            print(f"Grab error! status = {image_data.status}")
                        else:
                            if image_data.pixel_format == pytelicam.CameraPixelFormat.Mono8:
                                np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Raw)
                            else:
                                np_arr = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)

                            print(f"shape      : {np_arr.shape}")
                            print(f"image data :\n {np_arr[0,]}")
                            print(f"average    : {np.average(np_arr)}\n")

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
