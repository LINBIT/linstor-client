from proto.MsgCrtVlmDfn_pb2 import MsgCrtVlmDfn
# from proto.MsgDelVlmDfn_pb2 import MsgDelVlmDfn
from proto.MsgLstRscDfn_pb2 import MsgLstRscDfn
from linstor.sharedconsts import API_CRT_VLM_DFN, API_LST_RSC_DFN  # API_DEL_VLM_DFN
from linstor.commcontroller import need_communication
from linstor.commands import Commands
from linstor.utils import SizeCalc, approximate_size_string
import re
import sys


class VolumeDefinitionCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtVlmDfn()
        p.rsc_name = args.name

        vlmdf = p.vlm_dfns.add()
        vlmdf.vlm_size = VolumeDefinitionCommands._get_volume_size(args.size)

        return Commands._create(cc, API_CRT_VLM_DFN, p)

    def delete(self):
        raise NotImplementedError("delete has not been implemented yet.")

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_RSC_DFN, MsgLstRscDfn(), args)

        if lstmsg:
            prntfrm = "{res:<15s} {uuid:<40s} {vlmnr:<5s} {vlmminor:<10s} {vlmsize:<10s}"
            print(prntfrm.format(res="Resource", uuid="UUID", vlmnr="VlmNr", vlmminor="VlmMinor", vlmsize="Size"))
            prntfrm = "{res:<15s} {uuid:<40s} {vlmnr:<5d} {vlmminor:<10d} {vlmsize:<20s}"
            for rscdfn in lstmsg.rsc_dfns:
                for vlmdfn in rscdfn.vlm_dfns:
                    print(prntfrm.format(
                        res=rscdfn.rsc_name,
                        uuid=vlmdfn.vlm_dfn_uuid,
                        vlmnr=vlmdfn.vlm_nr,
                        vlmminor=vlmdfn.vlm_minor,
                        vlmsize=approximate_size_string(vlmdfn.vlm_size)))

                # for prop in n.node_props:
                #     print('    {key:<30s} {val:<20s}'.format(key=prop.key, val=prop.value))

        return None

    @classmethod
    def _get_volume_size(cls, size_str):
        m = re.match('(\d+)(\D*)', size_str)

        size = 0
        try:
            size = int(m.group(1))
        except AttributeError:
            sys.stderr.write('Size is not a valid number\n')
            return None

        unit_str = m.group(2)
        if unit_str == "":
            unit_str = "GiB"
        try:
            unit = SizeCalc.UNITS_MAP[unit_str.lower()]
        except KeyError:
            sys.stderr.write('"%s" is not a valid unit!\n' % (unit_str))
            sys.stderr.write('Valid units: %s\n' % (','.join(SizeCalc.UNITS_MAP.keys())))
            return None

        unit = SizeCalc.UNITS_MAP[unit_str.lower()]

        if unit != SizeCalc.UNIT_kiB:
            size = SizeCalc.convert_round_up(size, unit,
                                             SizeCalc.UNIT_kiB)

        return size
