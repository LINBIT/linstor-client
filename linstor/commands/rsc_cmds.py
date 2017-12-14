from proto.MsgCrtRsc_pb2 import MsgCrtRsc
from proto.MsgDelRsc_pb2 import MsgDelRsc
from proto.MsgLstRsc_pb2 import MsgLstRsc
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.commcontroller import need_communication
from linstor.commands import Commands
from linstor.sharedconsts import (
    API_CRT_RSC,
    API_DEL_RSC,
    API_LST_RSC
)


class ResourceCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtRsc()
        p.rsc_name = args.name
        p.node_name = args.node_name

        return Commands._create(cc, API_CRT_RSC, p)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for node_name in args.node_name:
            p = MsgDelRsc()
            p.rsc_name = args.name
            p.node_name = node_name

            del_msgs.append(p)

        Commands._delete(cc, args, API_DEL_RSC, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_RSC, MsgLstRsc())
        if isinstance(lstmsg, MsgApiCallResponse):
            return lstmsg

        prntfrm = "{rsc:<20s} {uuid:<40s} {node:<30s}"
        print(prntfrm.format(rsc="Resource-name", uuid="UUID", node="Node"))
        for rsc in lstmsg.resources:
            print(prntfrm.format(
                rsc=rsc.name,
                uuid=rsc.uuid.decode("utf8"),
                node=rsc.node_name))

        return None
