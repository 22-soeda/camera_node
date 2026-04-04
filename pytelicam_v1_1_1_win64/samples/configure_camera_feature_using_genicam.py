#
# configure_camera_feature_using_genicam.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import pytelicam

multi_disp_exp = 0.001

#############################################
def is_float(value):
    try:
        float(value)
    except ValueError:
        return False
    else:
        return True

#############################################
def set_exposure_time():
    print("\nset_exposure_time() started!")

    # Get ExposureTime (minimum).
    status, exposure_time_min = cam_device.genapi.get_float_min('ExposureTime')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_min, status = {status}\n")
        return False

    # Get ExposureTime (maximum).
    status, exposure_time_max = cam_device.genapi.get_float_max('ExposureTime')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_max, status = {status}\n")
        return False

    exposure_time_value = input(f" exposure_time_min : {round(exposure_time_min * multi_disp_exp, 4):0.4f} , exposure_time_max : {round(exposure_time_max * multi_disp_exp, 4):0.4f} [ms] >>> ")

    # Convert float value.
    while not is_float(exposure_time_value):
        exposure_time_value = input(" Input exposure_time value >>> ")
    exposure_time = float(exposure_time_value)
    exposure_time /= multi_disp_exp

    if exposure_time < exposure_time_min:
        exposure_time = exposure_time_min
    elif exposure_time > exposure_time_max:
        exposure_time = exposure_time_max

    # Set ExposureTime.
    status = cam_device.genapi.set_float_value('ExposureTime', exposure_time)
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed set_exposure_time, status = {status}\n")
        return False

    # Get ExposureTime (current).
    status, exposure_time = cam_device.genapi.get_float_value('ExposureTime')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_value, status = {status}\n")
        return False

    print(f" Current exposure_time : {round(exposure_time * multi_disp_exp, 4):0.4f} [ms]")

    print("set_exposure_time() finished!\n")
    return True

#############################################
def set_gain():
    print("\nset_gain() started!")

    # Get Gain (minimum).
    status, gain_min = cam_device.genapi.get_float_min('Gain')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_min, status = {status}\n")
        return False

    # Get Gain (maximum).
    status, gain_max = cam_device.genapi.get_float_max('Gain')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_max, status = {status}\n")
        return False

    gain_value = input(f" gain_min : {round(gain_min, 4):0.4f} , gain_max : {round(gain_max, 4):0.4f} [db] or [times] >>> ")

    # Convert float value.
    while not is_float(gain_value):
        gain_value = input(" Input gain value >>> ")
    gain = float(gain_value)

    if gain < gain_min:
        gain = gain_min
    elif gain > gain_max:
        gain = gain_max

    # Set Gain.
    status = cam_device.genapi.set_float_value('Gain', gain)
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed set_float_value, status = {status}\n")
        return False

    # Get Gain (current).
    status, gain = cam_device.genapi.get_float_value('Gain')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_value, status = {status}\n")
        return False

    print(f" Current gain : {round(gain, 4):0.4f} [db] or [times]")

    print("set_gain() finished!\n")
    return True

#############################################
def set_frame_rate():
    print("\nset_frame_rate() started!")

    # Get AcquisitionFrameRate (minimum).
    status, frame_rate_min = cam_device.genapi.get_float_min('AcquisitionFrameRate')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_min, status = {status}\n")
        return False

    # Get AcquisitionFrameRate (maximum).
    status, frame_rate_max = cam_device.genapi.get_float_max('AcquisitionFrameRate')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_max, status = {status}\n")
        return False

    frame_rate_value = input(f" frame_rate_min : {round(frame_rate_min, 4):0.4f} , frame_rate_max : {round(frame_rate_max, 4):0.4f} [fps] >>> ")

    # Convert float value.
    while not is_float(frame_rate_value):
        frame_rate_value = input(" Input frame rate value >>> ")
    frame_rate = float(frame_rate_value)

    if frame_rate < frame_rate_min:
        frame_rate = frame_rate_min
    elif frame_rate > frame_rate_max:
        frame_rate = frame_rate_max

    # Set AcquisitionFrameRate.
    status = cam_device.genapi.set_float_value('AcquisitionFrameRate', frame_rate)
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed set_float_value, status = {status}\n")
        return False

    # Get AcquisitionFrameRate (current).
    status, frame_rate = cam_device.genapi.get_float_value('AcquisitionFrameRate')
    if status != pytelicam.CamApiStatus.Success:
        print(f"Failed get_float_value, status = {status}\n")
        return False

    print(f" Current frame_rate : {round(frame_rate, 4):0.4f} [fps]")

    print("set_frame_rate() finished!\n")
    return True

#############################################
if __name__ == "__main__":
    # It is recommended that the settings of unused interfaces be removed.
    #  (U3v / Gev / GenTL)
    cam_system = pytelicam.get_camera_system( \
        int(pytelicam.CameraType.U3v) | \
        int(pytelicam.CameraType.Gev) | \
        int(pytelicam.CameraType.GenTL))

    try:
        cam_num = cam_system.get_num_of_cameras()
        if cam_num == 0:
            print("Camera not found.")
            sys.exit()

        print(f"{cam_num} camera(s) found.\n")

        # Open a camera that is detected first, in this sample code.
        cam_no = 0
        cam_device = cam_system.create_device_object(cam_no)
        cam_device.open()

        # ExposureTime / ExposureMode.
        # Set ExposureTimeControl "Manual", in this sample code.
        status = cam_device.cam_control.set_exposure_time_control(pytelicam.pytelicam.CameraExposureTimeCtrl.Manual)
        if status != pytelicam.CamApiStatus.Success:
            print(f"Failed set_exposure_time_control, status = {status}")
            sys.exit()

        # Check whether the camera support IIDC2 standard.
        is_suport_iidc2 = cam_device.is_support_iidc2

        # AcquisitionFrameRateControl.
        # Set AcquisitionFramerRateControl "Manual".
        if is_suport_iidc2: # BU camera and CPU less BG camera.
            status = cam_device.cam_control.set_acquisition_frame_rate_control(pytelicam.pytelicam.CameraAcqFrameRateCtrl.Manual)
            if status != pytelicam.CamApiStatus.Success:
                print(f"Failed set_acquisition_frame_rate_control, status = {status}")
                sys.exit()

        print("Set Camera Parameters started!\n")
        is_disp = True

        while 1:
            if is_disp:
                print("Camera parameters")

                # Get ExposureTime.
                status, exposure_time = cam_device.genapi.get_float_value('ExposureTime')
                if status != pytelicam.CamApiStatus.Success:
                    print(f"Failed get_float_value, status = {status}")
                    break
                print(f" exposure_time   : {round(exposure_time * multi_disp_exp, 4):0.4f}[ms]")

                # Get Gain.
                status, gain = cam_device.genapi.get_float_value('Gain')
                if status != pytelicam.CamApiStatus.Success:
                    print(f"Failed get_float_value, status = {status}")
                    break
                print(f" gain            : {round(gain, 4):0.4f}[db]")

                # Get AcquisitionFrameRate.
                status, frame_rate = cam_device.genapi.get_float_value('AcquisitionFrameRate')
                if status != pytelicam.CamApiStatus.Success:
                    print(f"Failed get_float_value, status = {status}")
                    break
                print(f" frame_rate      : {round(frame_rate, 4):0.4f}[fps]")

                print("---------------------------------------------------------------------")
                print("Press '1' key to set exposure time.")
                print("Press '2' key to set gain.")
                print("Press '3' key to set frame rate.")
                print("Press '9' key to quit application.")
                print("---------------------------------------------------------------------")

                is_disp = False

            key = input()

            if key == '1':
                # Set ExposureTime.
                status = set_exposure_time()
                if not status:
                    break
                is_disp = True
            elif key == '2':
                # Set Gain.
                status = set_gain()
                if not status:
                    break
                is_disp = True
            elif key == '3':
                # Set FrameRate.
                status = set_frame_rate()
                if not status:
                    break
                is_disp = True
            elif key == '9':
                print("\nSet Camera Parameters finished!")
                break

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

        print("Finished.")