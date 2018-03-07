import linstor
from linstor.proto.MsgLstNode_pb2 import MsgLstNode
from linstor.commcontroller import completer_communication
from linstor.commands import Commands
from linstor.utils import Output, rangecheck, namecheck, ip_completer, LinstorError
from linstor.consts import NODE_NAME, Color, ExitCode
from linstor.sharedconsts import (
    DFLT_STLT_PORT_PLAIN,
    DFLT_CTRL_PORT_PLAIN,
    DFLT_CTRL_PORT_SSL,
    VAL_NETCOM_TYPE_PLAIN,
    VAL_NETCOM_TYPE_SSL,
    VAL_NODE_TYPE_STLT,
    VAL_NODE_TYPE_CTRL,
    VAL_NODE_TYPE_AUX,
    VAL_NODE_TYPE_CMBD,
    VAL_NETIF_TYPE_IP,
    API_LST_NODE,
)


class NodeCommands(Commands):
    def __init__(self):
        super(NodeCommands, self).__init__()

    def setup_commands(self, parser):
        # create node
        p_new_node = parser.add_parser(
            Commands.CREATE_NODE,
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
        p_new_node.set_defaults(func=self.create)

        # remove-node
        p_rm_node = parser.add_parser(
            Commands.DELETE_NODE,
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
        p_rm_node.set_defaults(func=self.delete)

        # create net interface
        p_create_netinterface = parser.add_parser(
            Commands.CREATE_NETINTERFACE,
            aliases=['crtnetif'],
            description='Creates and adds a new netinterface to a given node. If port is specified this netinterface '
                        'is used as satellite port'
        )
        p_create_netinterface.add_argument('-p', '--port', type=rangecheck(1, 65535),
                                help='Port to use for satellite connections')
        p_create_netinterface.add_argument('--communication-type', choices=(VAL_NETCOM_TYPE_PLAIN, VAL_NETCOM_TYPE_SSL),
                                default=ctype_def,
                                help='Communication type (default: %s)' % ctype_def)
        p_create_netinterface.add_argument(
            "node_name",
            help="Name of the node to add the net interface"
        ).completer = NodeCommands.completer
        p_create_netinterface.add_argument("interface_name", help="Interface name")
        p_create_netinterface.add_argument('ip', help='New IP address for the network interface')
        p_create_netinterface.set_defaults(func=self.create_netif)

        # modify net interface
        p_mod_netif = parser.add_parser(
            Commands.MODIFY_NETINTERFACE,
            aliases=['mfynetif'],
            description='Change the ip listen address of a netinterface on the given node.'
        )
        p_mod_netif.add_argument('-p', '--port', type=rangecheck(1, 65535),
                                 help='Port to use for satellite connections')
        p_mod_netif.add_argument('--communication-type', choices=(VAL_NETCOM_TYPE_PLAIN, VAL_NETCOM_TYPE_SSL),
                                 default=ctype_def,
                                 help='Communication type (default: %s)' % ctype_def)
        p_mod_netif.add_argument(
            "node_name",
            help="Name of the node"
        ).completer = NodeCommands.completer
        p_mod_netif.add_argument("interface_name", help="Interface name to change")
        p_mod_netif.add_argument('ip', help='New IP address for the network interface')
        p_mod_netif.set_defaults(func=self.modify_netif)

        # delete net interface
        p_delete_netinterface = parser.add_parser(
            Commands.DELETE_NETINTERFACE,
            aliases=['delnetif'],
            description='Delete a netinterface from a node.'
        )
        p_delete_netinterface.add_argument(
            "node_name",
            help="Name of the node to remove the net interface"
        ).completer = NodeCommands.completer
        p_delete_netinterface.add_argument(
            "interface_name",
            nargs='+',
            help="Interface name"
        ).completer = NodeCommands.completer_netif
        p_delete_netinterface.set_defaults(func=self.delete_netif)

        # list nodes
        nodesverbose = ('Family', 'IP', 'Site')
        nodesgroupby = ('Name', 'Pool_Size', 'Pool_Free', 'Family', 'IP', 'State')

        nodes_verbose_completer = Commands.show_group_completer(nodesverbose, "show")
        nodes_group_completer = Commands.show_group_completer(nodesgroupby, "groupby")
        p_lnodes = parser.add_parser(
            Commands.LIST_NODE,
            aliases=['dspnode'],
            description='Prints a list of all cluster nodes known to linstor. '
            'By default, the list is printed as a human readable table.')
        p_lnodes.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnodes.add_argument('-s', '--show', nargs='+',
                              choices=nodesverbose).completer = nodes_verbose_completer
        p_lnodes.add_argument('-g', '--groupby', nargs='+',
                              choices=nodesgroupby).completer = nodes_group_completer
        p_lnodes.add_argument('-N', '--nodes', nargs='+', type=namecheck(NODE_NAME),
                              help='Filter by list of nodes').completer = NodeCommands.completer
        p_lnodes.set_defaults(func=self.list)

        # list netinterface
        p_lnetif = parser.add_parser(
            Commands.LIST_NETINTERFACE,
            aliases=['dspnetif'],
            description='Prints a list of netinterfaces from a node.'
        )
        p_lnetif.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnetif.add_argument(
            'node_name',
            help='Node name for which to print the net interfaces'
        ).completer = NodeCommands.completer
        p_lnetif.set_defaults(func=self.list_netinterfaces)

        # show properties
        p_sp = parser.add_parser(
            Commands.GET_NODE_PROPS,
            aliases=['dspnodeprp'],
            description="Prints all properties of the given node.")
        p_sp.add_argument(
            'node_name',
            help="Node for which to print the properties").completer = NodeCommands.completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        # disabled until there are properties
        # p_setp = parser.add_parser(
        #     Commands.SET_NODE_PROP,
        #     aliases=['setnodeprp'],
        #     description="Set a property on the given node."
        # )
        # p_setp.add_argument(
        #     'node_name',
        #     help="Node for which to set the property"
        # ).completer = NodeCommands.completer
        # Commands.add_parser_keyvalue(p_setp, "node")
        # p_setp.set_defaults(func=NodeCommands.set_props)

        # set aux properties
        p_setauxp = parser.add_parser(
            Commands.SET_NODE_AUX_PROP,
            aliases=['setnodeauxprp'],
            description="Set a auxiliary property on the given node."
        )
        p_setauxp.add_argument(
            'node_name',
            help="Node for which to set the property"
        ).completer = NodeCommands.completer
        Commands.add_parser_keyvalue(p_setauxp)
        p_setauxp.set_defaults(func=self.set_prop_aux)

    def create(self, args):
        replies = self._linstor.node_create(
            args.name,
            args.node_type,
            args.ip,
            args.communication_type,
            args.port,
            args.interface_name
        )

        return self.handle_replies(args, replies)

    def delete(self, args):
        replies = self._linstor.node_delete(args.name)

        return self.handle_replies(args, replies)

    def list(self, args):
        lstmsg = self._linstor.node_list()

        if lstmsg:
            if args.machine_readable:
                self._print_machine_readable([lstmsg])
            else:
                tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
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

        return ExitCode.OK

    @staticmethod
    def find_node(proto_node_list, node_name):
        if proto_node_list:
            for n in proto_node_list.nodes:
                if n.name == node_name:
                    return n
        return None

    def list_netinterfaces(self, args):
        lstnodes = self._linstor.node_list()

        if lstnodes:
            if args.machine_readable:
                self._print_machine_readable([lstnodes])
            else:
                node = NodeCommands.find_node(lstnodes, args.node_name)
                if node:
                    tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
                    tbl.add_column(node.name, color=Color.GREEN)
                    tbl.add_column("NetInterface")
                    tbl.add_column("IP")
                    for netif in node.net_interfaces:
                        tbl.add_row([
                            "+",
                            netif.name,
                            netif.address
                        ])
                    tbl.show()
                else:
                    raise LinstorError("Node '{n}' not found on controller.".format(n=args.node_name),
                                       ExitCode.OBJECT_NOT_FOUND)

        return ExitCode.OK

    def print_props(self, args):
        lstmsg = self._linstor.node_list()

        result = []
        node = NodeCommands.find_node(lstmsg, args.node_name)
        if node:
            result.append(node.props)
        else:
            raise LinstorError("Node '{n}' not found on controller.".format(n=args.node_name),
                               ExitCode.OBJECT_NOT_FOUND)

        Commands._print_props(result, machine_readable=args.machine_readable)
        return ExitCode.OK

    def set_props(self, args):
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.node_modify(args.node_name, mod_prop_dict['pairs'], mod_prop_dict['delete'])
        return self.handle_replies(args, replies)

    def create_netif(self, args):
        replies = self._linstor.netinterface_create(
            args.node_name,
            args.interface_name,
            args.ip,
            args.port,
            args.communication_type
        )

        return self.handle_replies(args, replies)

    def modify_netif(self, args):
        replies = self._linstor.netinterface_modify(
            args.node_name,
            args.interface_name,
            args.ip,
            args.port,
            args.communication_type
        )

        return self.handle_replies(args, replies)

    def delete_netif(self, args):
        # execute delete netinterfaces and flatten result list
        replies = [x for subx in args.interface_name for x in self._linstor.netinterface_delete(args.node_name, subx)]
        return self.handle_replies(args, replies)

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

    @staticmethod
    @completer_communication
    def completer_netif(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_NODE, MsgLstNode())

        node = NodeCommands.find_node(lstmsg, kwargs['parsed_args'].node_name)
        if node:
            for netif in node.net_interfaces:
                possible.add(netif.name)

            if prefix:
                return [netif for netif in possible if netif.startswith(prefix)]

        return possible
