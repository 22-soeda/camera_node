#
# get_camera_feature_list.py (for Python 3)
#
# Copyright (c) 2024 Toshiba-Teli Corporation
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#

import sys
import pytelicam

enable_beginner = True
enable_expert = True
enable_guru = False
enable_invisible = False

def list_features(node_name, level):
    global enable_beginner
    global enable_expert
    global enable_guru
    global enable_invisible

    # The get_available_feature_names() can be used by setting only a node name.
    #features = cam_device.genapi.get_available_feature_names(node_name)
    features = cam_device.genapi.get_available_feature_names(node_name, enable_beginner, enable_expert, enable_guru, enable_invisible)

    for feature_name in features:
        status, node_type = cam_device.genapi.get_node_type(feature_name)
        if status != pytelicam.CamApiStatus.Success:
            print("Error!")
            return

        status, access_mode = cam_device.genapi.get_access_mode(feature_name)
        if status != pytelicam.CamApiStatus.Success:
            print("Error!")
            return

        print(f"{''.ljust(level * 2)}{feature_name} : {node_type}, {access_mode}")

        if node_type == pytelicam.NodeType.Category:
            list_features(feature_name, level + 1)

        if node_type == pytelicam.NodeType.Enumeration:
            enum_entries = cam_device.genapi.get_available_enum_entry_names(feature_name)

            for enum_entry_name in enum_entries:
                print(f"{''.ljust(level * 2 + 2)}- {enum_entry_name}")


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

        print(f"{cam_num} camera(s) found.\n")

        # Open a camera that is detected first, in this sample code.
        cam_no = 0
        cam_device = cam_system.create_device_object(cam_no)
        cam_device.open()

        print("Root :")
        list_features('Root', 1)

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

        print("\nFinished.")
