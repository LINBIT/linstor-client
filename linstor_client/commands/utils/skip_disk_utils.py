# -*- coding: utf-8 -*-

from linstor_client.commands.commands import Commands
from linstor_client.consts import Color
from linstor_client.utils import Output


def get_skip_disk_state_str(rsc):
    occurrences = []
    # originally we checked for "if not linstor_api.api_version_smaller('1.20.2')"
    # but this method needs to be called from "r l", "v l" and also from "r lv"
    # "r lv" requires "v l"'s show_volumes to be a classmethod. Such a classmethod
    # however cannot get an instance of linstor_api. That makes the original check
    # hard to achieve.
    # as a workaround we simply check if the effective_properties exist or not...
    if hasattr(rsc, "effective_properties"):
        if "DrbdOptions/SkipDisk" in rsc.effective_properties:
            skip_disk_eff_prop = rsc.effective_properties["DrbdOptions/SkipDisk"]
            if skip_disk_eff_prop.value == "True":
                occurrences = [Commands.EFFECTIVE_PROPS_TYPES[skip_disk_eff_prop.type]]
                if skip_disk_eff_prop.other:
                    occurrences += [Commands.EFFECTIVE_PROPS_TYPES[other.type]
                                    for other in skip_disk_eff_prop.other]
    return ", SkipDisk (" + ', '.join(occurrences) + ")" if occurrences else ""


def print_skip_disk_info(no_color):
    print(Output.color_str("SkipDisk", Color.YELLOW, no_color) + ":")
    print("  At least one resource has 'DrbdOptions/SkipDisk' enabled. This indicates an IO error on the")
    print("  affected resource(s). Remove this property (using "
          "'linstor resource set-property $node $rsc DrbdOptions/SkipDisk') ")
    print("  to instruct LINSTOR and DRBD to adjust (and recreate if necessary) the affected logical volumes "
          "again.")
    print("  For more information please visit: "
          "https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-drbd-skip-disk")
