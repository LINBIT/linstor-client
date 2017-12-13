from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgCrtNode_pb2 import MsgCrtNode
from proto.MsgDelNode_pb2 import MsgDelNode
from proto.MsgLstNode_pb2 import MsgLstNode
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from proto.LinStorMapEntry_pb2 import LinStorMapEntry
from linstor.commcontroller import need_communication, CommController
from linstor.commands import Commands
from linstor.utils import Output
from linstor.sharedconsts import (
    DFLT_STLT_PORT_PLAIN,
    DFLT_CTRL_PORT_PLAIN,
    DFLT_CTRL_PORT_SSL,
    KEY_IP_ADDR,
    KEY_NETCOM_TYPE,
    KEY_NETIF_TYPE,
    KEY_PORT_NR,
    NAMESPC_NETIF,
    VAL_NETCOM_TYPE_PLAIN,
    VAL_NETCOM_TYPE_SSL,
    VAL_NETIF_TYPE_IP,
    VAL_NODE_TYPE_AUX,
    VAL_NODE_TYPE_CMBD,
    VAL_NODE_TYPE_CTRL,
    VAL_NODE_TYPE_STLT,
    API_CRT_NODE,
    API_DEL_NODE,
    API_LST_NODE
)


class NodeCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtNode()
        def gen_nif(k, v):
            prop = LinStorMapEntry()
            prop.key = "%s/%s/%s" % (NAMESPC_NETIF, args.interface_name, k)
            prop.value = v
            p.node_props.extend([prop])

        p.node_name = args.name
        p.node_type = args.node_type

        # interface
        gen_nif(KEY_NETIF_TYPE, args.interface_type)
        gen_nif(KEY_NETCOM_TYPE, args.communication_type)
        gen_nif(KEY_IP_ADDR, args.ip)

        port = args.port
        if not port:
            if args.communication_type == VAL_NETCOM_TYPE_PLAIN:
                port = DFLT_STLT_PORT_PLAIN if p.node_type == VAL_NODE_TYPE_STLT else DFLT_CTRL_PORT_PLAIN
            elif args.communication_type == VAL_NETCOM_TYPE_SSL:
                port = DFLT_CTRL_PORT_SSL
            else:
                self.err("Communication type %s has no default port" % (args.communication_type))
        gen_nif(KEY_PORT_NR, str(port))

        return Commands._create(cc, API_CRT_NODE, p)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        p = MsgDelNode()
        p.node_name = args.name

        del_msgs.append(p)

        Commands._delete(cc, args, API_DEL_NODE, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_NODE, MsgLstNode())
        if isinstance(lstmsg, MsgApiCallResponse):
            return lstmsg

        if False: # disabled for now
            tbl = Table()
            tbl.add_column("Node")
            tbl.add_column("NodeType")
            tbl.add_column("UUID")
            for n in p.nodes:
                tbl.add_row([n.name, n.type, n.uuid])
            tbl.show()

        prntfrm = "{node:<20s} {type:<10s} {uuid:<40s}"
        print(prntfrm.format(node="Node", type="NodeType", uuid="UUID"))

        netiffrm = " +   {name:<20s} {address:>20s}:{port:<6d} {type:<10s}"
        for n in lstmsg.nodes:
            print(prntfrm.format(node=n.name, type=n.type, uuid=n.uuid))

            for interface in n.net_interfaces:
                print(netiffrm.format(
                    name=interface.name,
                    address=interface.address,
                    port=interface.port,
                    type=interface.type))

            # for prop in n.node_props:
            #     print('    {key:<30s} {val:<20s}'.format(key=prop.key, val=prop.value))

        return None
