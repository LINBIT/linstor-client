from proto.MsgCrtNode_pb2 import MsgCrtNode
from proto.MsgDelNode_pb2 import MsgDelNode
from proto.MsgLstNode_pb2 import MsgLstNode
from proto.LinStorMapEntry_pb2 import LinStorMapEntry
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.utils import Output, Table, rangecheck, namecheck, ip_completer
from linstor.consts import NODE_NAME, Color
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
    VAL_NODE_TYPE_CTRL,
    VAL_NODE_TYPE_AUX,
    VAL_NODE_TYPE_CMBD,
    VAL_NETIF_TYPE_IP,
    API_CRT_NODE,
    API_DEL_NODE,
    API_LST_NODE
)


class NodeCommands(Commands):

    @staticmethod
    def setup_commands(parser):
        # create node
        p_new_node = parser.add_parser(
            'create-node',
            aliases=['crtnode'],
            description='Creates a node entry for a node that participates in the '
            'linstor cluster.')
        p_new_node.add_argument('-p', '--port', type=rangecheck(1, 65535),
                                help='default: Satellite %s for %s; Controller %s for %s; %s for %s' % (
                                    DFLT_STLT_PORT_PLAIN,
                                    VAL_NETCOM_TYPE_PLAIN,
                                    DFLT_CTRL_PORT_PLAIN,
                                    VAL_NETCOM_TYPE_PLAIN,
                                    DFLT_CTRL_PORT_SSL,
                                    VAL_NETCOM_TYPE_SSL))
        ntype_def = VAL_NODE_TYPE_STLT
        p_new_node.add_argument('--node-type', choices=(VAL_NODE_TYPE_CTRL, VAL_NODE_TYPE_AUX,
                                                        VAL_NODE_TYPE_CMBD, VAL_NODE_TYPE_STLT),
                                default=VAL_NODE_TYPE_STLT, help='Node type (default: %s)' % (ntype_def))
        ctype_def = VAL_NETCOM_TYPE_PLAIN
        p_new_node.add_argument('--communication-type', choices=(VAL_NETCOM_TYPE_PLAIN, VAL_NETCOM_TYPE_SSL),
                                default=ctype_def,
                                help='Communication type (default: %s)' % (ctype_def))
        itype_def = VAL_NETIF_TYPE_IP
        p_new_node.add_argument('--interface-type', choices=(VAL_NETIF_TYPE_IP,), default=itype_def,
                                help='Interface type (default: %s)' % (itype_def))
        iname_def = 'default'
        p_new_node.add_argument('--interface-name', default=iname_def,
                                help='Interface name (default: %s)' % (iname_def))
        p_new_node.add_argument(
            'name',
            help='Name of the new node, must match the nodes hostname',
            type=namecheck(NODE_NAME))
        p_new_node.add_argument('ip',
                                help='IP address of the new node').completer = ip_completer("name")
        p_new_node.set_defaults(func=NodeCommands.create)

        # modify-node
        p_mod_node_command = 'modify-node'
        p_mod_node = parser.add_parser(
            p_mod_node_command,
            aliases=['modnode', 'mn'],
            description='Modifies a linstor node.')
        p_mod_node.add_argument('-a', '--address-family', metavar="FAMILY",
                                choices=['ipv4', 'ipv6'],
                                help='FAMILY: "ipv4" (default) or "ipv6"')
        p_mod_node.add_argument('-s', '--storage')
        p_mod_node.add_argument('name', type=namecheck(NODE_NAME),
                                help='Name of the node').completer = NodeCommands.completer
        p_mod_node.add_argument('--address',
                                help='Network address of the node').completer = ip_completer("name")
        p_mod_node.set_defaults(func=Commands.cmd_enoimp)
        p_mod_node.set_defaults(command=NodeCommands.modify)

        # remove-node
        p_rm_node = parser.add_parser(
            'delete-node',
            aliases=['delnode'],
            description='Removes a node from the linstor cluster. '
            'All linstor resources that are still deployed on the specified '
            'node are marked for undeployment, and the node entry is marked for '
            "removal from linstor's data tables. The specified node is "
            'expected to undeploy all resources. As soon as all resources have been '
            'undeployed from the node, the node entry is removed from '
            "linstor's data tables.")
        p_rm_node.add_argument('-q', '--quiet', action="store_true",
                               help='Unless this option is used, linstor will issue a safety question '
                               'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_node.add_argument('name',
                               help='Name of the node to remove').completer = NodeCommands.completer
        p_rm_node.set_defaults(func=NodeCommands.delete)

        # list nodes
        nodesverbose = ('Family', 'IP', 'Site')
        nodesgroupby = ('Name', 'Pool_Size', 'Pool_Free', 'Family', 'IP', 'State')

        nodes_verbose_completer = Commands.show_group_completer(nodesverbose, "show")
        nodes_group_completer = Commands.show_group_completer(nodesgroupby, "groupby")
        p_lnodes = parser.add_parser(
            'list-nodes',
            aliases=['list-node', 'ls-nodes', 'display-nodes'],
            description='Prints a list of all cluster nodes known to linstor. '
            'By default, the list is printed as a human readable table.')
        p_lnodes.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnodes.add_argument('-s', '--show', nargs='+',
                              choices=nodesverbose).completer = nodes_verbose_completer
        p_lnodes.add_argument('-g', '--groupby', nargs='+',
                              choices=nodesgroupby).completer = nodes_group_completer
        p_lnodes.add_argument('-N', '--nodes', nargs='+', type=namecheck(NODE_NAME),
                              help='Filter by list of nodes').completer = NodeCommands.completer
        p_lnodes.add_argument('--separators', action="store_true")
        p_lnodes.set_defaults(func=NodeCommands.list)

        # show properties
        p_sp = parser.add_parser(
            'get-node-properties',
            aliases=['get-node-props'],
            description="Prints all properties of the given node.")
        p_sp.add_argument(
            'node_name',
            help="Node for which to print the properties").completer = NodeCommands.completer
        p_sp.set_defaults(func=NodeCommands.print_props)

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
                Output.err("Communication type %s has no default port" % (args.communication_type), args.no_color)
        gen_nif(KEY_PORT_NR, str(port))

        satcon = p.satellite_connections.add()
        satcon.net_interface_name = args.interface_name
        satcon.port = port
        satcon.encryption_type = args.communication_type

        return Commands._create(cc, API_CRT_NODE, p, args)

    @staticmethod
    @need_communication
    def modify(cc, args):
        pass

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        p = MsgDelNode()
        p.node_name = args.name

        del_msgs.append(p)

        return Commands._delete_and_output(cc, args, API_DEL_NODE, del_msgs)

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_NODE, MsgLstNode(), args)

        if lstmsg:
            tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column("Node")
            tbl.add_column("NodeType")
            tbl.add_column("IPs")
            tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color))
            for n in lstmsg.nodes:
                ips = [if_.address for if_ in n.net_interfaces]
                tbl.add_row([
                    n.name,
                    n.type,
                    ",".join(ips),
                    tbl.color_cell("ok", Color.DARKGREEN) if n.connected else tbl.color_cell("OFFLINE", Color.RED)
                ])
            tbl.show()

            # prntfrm = "{node:<20s} {type:<10s} {uuid:<40s}"
            # print(prntfrm.format(node="Node", type="NodeType", uuid="UUID"))

            # netiffrm = " +   {name:<20s} {address:>20s}"
            # for n in lstmsg.nodes:
            #     print(prntfrm.format(node=n.name, type=n.type, uuid=n.uuid))

            #     for interface in n.net_interfaces:
            #         print(netiffrm.format(
            #             name=interface.name,
            #             address=interface.address))

        return None

    @staticmethod
    @need_communication
    def print_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_NODE, MsgLstNode())

        if lstmsg:
            for n in lstmsg.nodes:
                if n.name == args.node_name:
                    Commands._print_props(n.props)
                    break

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
