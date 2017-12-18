from proto.MsgCrtNode_pb2 import MsgCrtNode
from proto.MsgDelNode_pb2 import MsgDelNode
from proto.MsgLstNode_pb2 import MsgLstNode
from proto.LinStorMapEntry_pb2 import LinStorMapEntry
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.utils import Output, Table
from linstor.sharedconsts import (
    DFLT_STLT_PORT_PLAIN,
    DFLT_CTRL_PORT_PLAIN,
    DFLT_CTRL_PORT_SSL,
    KEY_NETCOM_TYPE,
    KEY_NETIF_TYPE,
    KEY_PORT_NR,
    NAMESPC_NETIF,
    VAL_NETCOM_TYPE_PLAIN,
    VAL_NETCOM_TYPE_SSL,
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
            p.node.props.extend([prop])

        # interface
        gen_nif(KEY_NETIF_TYPE, args.interface_type)
        gen_nif(KEY_NETCOM_TYPE, args.communication_type)

        p.node.name = args.name
        p.node.type = args.node_type

        netif = p.node.net_interfaces.add()
        netif.name = args.interface_name
        netif.address = args.ip

        port = args.port
        if not port:
            if args.communication_type == VAL_NETCOM_TYPE_PLAIN:
                port = DFLT_STLT_PORT_PLAIN if p.node.type == VAL_NODE_TYPE_STLT else DFLT_CTRL_PORT_PLAIN
            elif args.communication_type == VAL_NETCOM_TYPE_SSL:
                port = DFLT_CTRL_PORT_SSL
            else:
                Output.err("Communication type %s has no default port" % (args.communication_type))
        gen_nif(KEY_PORT_NR, str(port))

        satcon = p.satellite_connections.add()
        satcon.net_interface_name = args.interface_name
        satcon.port = port
        satcon.encryption_type = args.communication_type

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
        lstmsg = Commands._get_list_message(cc, API_LST_NODE, MsgLstNode(), args)

        if lstmsg:
            if False:  # disabled for now
                tbl = Table()
                tbl.add_column("Node")
                tbl.add_column("NodeType")
                tbl.add_column("UUID")
                for n in lstmsg.nodes:
                    tbl.add_row([n.name, n.type, n.uuid])
                tbl.show()

            prntfrm = "{node:<20s} {type:<10s} {uuid:<40s}"
            print(prntfrm.format(node="Node", type="NodeType", uuid="UUID"))

            netiffrm = " +   {name:<20s} {address:>20s}"
            for n in lstmsg.nodes:
                print(prntfrm.format(node=n.name, type=n.type, uuid=n.uuid))

                for interface in n.net_interfaces:
                    print(netiffrm.format(
                        name=interface.name,
                        address=interface.address))

                # for prop in n.node_props:
                #     print('    {key:<30s} {val:<20s}'.format(key=prop.key, val=prop.value))

        return None

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_NODE, MsgLstNode())

        if lstmsg:
            for node in lstmsg.nodes:
                possible.add(node.name)

            if prefix:
                return [node for node in possible if node.startswith(prefix)]

        return possible
