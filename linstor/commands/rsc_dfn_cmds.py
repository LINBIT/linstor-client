from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgCrtRscDfn_pb2 import MsgCrtRscDfn
from proto.MsgDelRscDfn_pb2 import MsgDelRscDfn
from proto.MsgLstRscDfn_pb2 import MsgLstRscDfn
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.commcontroller import need_communication, CommController
from linstor.commands import Commands
from linstor.utils import Output
from linstor.sharedconsts import (
    API_CRT_RSC_DFN,
    API_DEL_RSC_DFN,
    API_LST_RSC_DFN
)


class ResourceDefinitionCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtRscDfn()
        p.rsc_name = args.name
        if args.port:
            p.rsc_port = args.port
        if args.secret:
            p.secret = args.secret

        return Commands._create(cc, API_CRT_RSC_DFN, p)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for rsc_name in args.name:
            p = MsgDelRscDfn()
            p.rsc_name = rsc_name

            del_msgs.append(p)

        Commands._delete(cc, args, API_DEL_RSC_DFN, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_RSC_DFN, MsgLstRscDfn(), args)

        if lstmsg:
            prntfrm = "{rsc:<20s} {port:<10s} {uuid:<40s}"
            print(prntfrm.format(rsc="Resource-name", port="Port", uuid="UUID"))
            for rsc_dfn in lstmsg.rsc_dfns:
                print(prntfrm.format(rsc=rsc_dfn.rsc_name, port=str(rsc_dfn.rsc_port), uuid=rsc_dfn.uuid))

                # for prop in n.node_props:
                #     print('    {key:<30s} {val:<20s}'.format(key=prop.key, val=prop.value))

        return None
