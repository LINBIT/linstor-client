# -*- coding: utf-8 -*-

import linstor.sharedconsts as apiconsts


def get_toggle_disk_state_str(rsc):
    """
    Returns a display string for an in-progress toggle-disk operation on the resource.

    Toggle-disk converts a resource between diskless and diskful. The controller and
    satellite track the progress with these resource flags:
      DISK_ADD_REQUESTED / DISK_ADDING       - a disk is being added (diskless -> diskful)
      DISK_REMOVE_REQUESTED / DISK_REMOVING  - a disk is being removed (diskful -> diskless)

    The "*_REQUESTED" flags are set while the operation is still queued on the controller,
    the "DISK_ADDING"/"DISK_REMOVING" flags while the satellite is actively working on it.

    :param rsc: resource of type (responses.) Resource
    :return: a state string prefixed with ", " or an empty string if no toggle-disk is in progress
    """
    flags = rsc.flags
    if apiconsts.FLAG_DISK_ADDING in flags:
        return ", Adding Disk"
    if apiconsts.FLAG_DISK_ADD_REQUESTED in flags:
        return ", Adding Disk (pending)"
    if apiconsts.FLAG_DISK_REMOVING in flags:
        return ", Removing Disk"
    if apiconsts.FLAG_DISK_REMOVE_REQUESTED in flags:
        return ", Removing Disk (pending)"
    return ""
