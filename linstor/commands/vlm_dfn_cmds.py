from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from proto.MsgCrtVlmDfn_pb2 import MsgCrtVlmDfn
from proto.VlmDfn_pb2 import VlmDfn
#from proto.MsgDelVlmDfn_pb2 import MsgDelVlmDfn
from proto.MsgLstRscDfn_pb2 import MsgLstRscDfn
from linstor.sharedconsts import API_CRT_VLM_DFN, API_DEL_VLM_DFN, API_LST_RSC_DFN
from linstor.commcontroller import need_communication, CommController
from linstor.commands import Commands


class VolumeDefinitionCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtVlmDfn()
        p.rsc_name = args.name

        vlmdf = p.vlm_dfns.add()
        vlmdf.vlm_size = int(args.size)

        return Commands._create(cc, API_CRT_VLM_DFN, p)

    def delete(self):
        pass

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_RSC_DFN, MsgLstRscDfn())
        if isinstance(lstmsg, MsgApiCallResponse):
            return lstmsg

        prntfrm = "{uuid:<40s} {vlmnr:<5s} {vlmminor:<10s} {vlmsize:<20s}"
        print(prntfrm.format(uuid="UUID", vlmnr="VlmNr", vlmminor="VlmMinor", vlmsize="Size"))
        prntfrm = "{uuid:<40s} {vlmnr:<5d} {vlmminor:<10d} {vlmsize:<20d}"
        for rscdfn in lstmsg.rsc_dfns:
            for vlmdfn in rscdfn.vlm_dfns:
                print(prntfrm.format(uuid=vlmdfn.vlm_dfn_uuid.decode("utf8"), vlmnr=vlmdfn.vlm_nr, vlmminor=vlmdfn.vlm_minor, vlmsize=vlmdfn.vlm_size))

            # for prop in n.node_props:
            #     print('    {key:<30s} {val:<20s}'.format(key=prop.key, val=prop.value))

        return None
