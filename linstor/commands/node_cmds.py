import collections
import linstor
from linstor.commands import Commands
from linstor.utils import Output, rangecheck, SizeCalc, namecheck, ip_completer, LinstorClientError
from linstor.consts import NODE_NAME, Color, ExitCode
from linstor.commands.tree import TreeNode
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
    VAL_NETIF_TYPE_IP
)

import sys


class NodeCommands(Commands):
    DISKLESS_STORAGE_POOL = 'DfltDisklessStorPool'
    DISKLESS_RESOURCE_NAME = 'diskless resource'

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

        #describe-node
        p_desc_node = parser.add_parser(
            Commands.DESCRIBE_NODE,
            aliases=['descnode'],
            description='describe a node (or all nodes), list storage pools, resources and volumes under this node, '
            'in this order')
        p_desc_node.add_argument('name', nargs='?',
                                help='Name of the node to be described. With no name, all nodes are described').completer = self.node_completer
        p_desc_node.set_defaults(func=self.describe)

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
                               help='Name of the node to remove').completer = self.node_completer
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
        ).completer = self.node_completer
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
        ).completer = self.node_completer
        p_mod_netif.add_argument("interface_name", help="Interface name to change").completer = self.netif_completer
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
        ).completer = self.node_completer
        p_delete_netinterface.add_argument(
            "interface_name",
            nargs='+',
            help="Interface name"
        ).completer = self.netif_completer
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
                              help='Filter by list of nodes').completer = self.node_completer
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
        ).completer = self.node_completer
        p_lnetif.set_defaults(func=self.list_netinterfaces)

        # show properties
        p_sp = parser.add_parser(
            Commands.GET_NODE_PROPS,
            aliases=['dspnodeprp'],
            description="Prints all properties of the given node.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name',
            help="Node for which to print the properties").completer = self.node_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setp = parser.add_parser(
            Commands.SET_NODE_PROP,
            aliases=['setnodeprp'],
            description="Set a property on the given node."
        )
        p_setp.add_argument(
            'node_name',
            help="Node for which to set the property"
        ).completer = self.node_completer
        Commands.add_parser_keyvalue(p_setp, "node")
        p_setp.set_defaults(func=self.set_props)

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

    @classmethod
    def show_nodes(cls, args, lstmsg):
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

    def list(self, args):
        lstmsg = self._linstor.node_list()

        return self.output_list(args, lstmsg, self.show_nodes)

    def describe(self, args=None):
        """
        describe the details of a node
        It will construct a 4 level tree and print it.
        The four levels are: node, storage pool, resource, and volume

        :param args:
        :return:
        """

        if args.machine_readable:
            sys.stderr.write('This command does not support machine-readable\n')
            return ExitCode.OPTION_NOT_SUPPORTED

        node_map = dict()
        volume_def_map = dict()

        node_list_replies = self._linstor.node_list()
        exit_code = self.check_list_sanity(args, node_list_replies)
        if exit_code != ExitCode.OK:
            return exit_code

        self.construct_node(node_map, node_list_replies[0].proto_msg)

        storage_pool_list_replies = self._linstor.storage_pool_list()
        exit_code = self.check_list_sanity(args, storage_pool_list_replies)
        if exit_code != ExitCode.OK:
            return exit_code

        self.construct_storpool(node_map, storage_pool_list_replies[0].proto_msg)

        rsc_dfn_list_replies = self._linstor.resource_dfn_list()
        exit_code = self.check_list_sanity(args, rsc_dfn_list_replies)
        if exit_code != ExitCode.OK:
            return exit_code

        self.get_volume_size(rsc_dfn_list_replies[0].proto_msg, volume_def_map)

        rsc_list_replies = self._linstor.resource_list()
        exit_code = self.check_list_sanity(args, rsc_list_replies)
        if exit_code != ExitCode.OK:
            return exit_code

        self.construct_rsc(node_map, rsc_list_replies[0].proto_msg, volume_def_map)

        if args.name:
            if args.name in node_map:
                node = node_map[args.name]
                node.print_node(args.no_utf8, args.no_color)
            else:
                sys.stderr.write('%s: no such node\n' % args.name)
                return ExitCode.OBJECT_NOT_FOUND

        else:
            for index, node_name_key in enumerate(node_map):
                if index:
                    print("")
                node = node_map[node_name_key]
                node.print_node(args.no_utf8, args.no_color)

    def check_list_sanity(self, args, replies):
        if replies:
            if self.check_for_api_replies(replies):
                return self.handle_replies(args, replies)
        return ExitCode.OK

    def get_volume_size(self, rsc_dfn_list, volume_def_map):
        for rsc_dfn in rsc_dfn_list.rsc_dfns:
            for vlmdfn in rsc_dfn.vlm_dfns:
                volume_def_map[vlmdfn.vlm_minor] = vlmdfn.vlm_size

    def make_volume_node(self, vlm, volume_def_map):
        volume_node = TreeNode('volume' + str(vlm.vlm_nr), '', Color.DARKGREEN)
        volume_node.set_description('minor number: ' + str(vlm.vlm_minor_nr))
        volume_node.add_description(
            ', size: ' + str(SizeCalc.approximate_size_string(volume_def_map[vlm.vlm_minor_nr]))
        )
        return volume_node

    def construct_rsc(self, node_map, rsc_list, volume_map):
        for rsc in rsc_list.resources:
            vlm_by_storpool = collections.defaultdict(list)
            for vlm in rsc.vlms:
                vlm_by_storpool[vlm.stor_pool_name].append(vlm)

            for (storpool_name, vlms) in vlm_by_storpool.items():
                rsc_node = TreeNode(rsc.name, '', Color.BLUE)
                rsc_node.set_description('resource')

                if storpool_name == self.DISKLESS_STORAGE_POOL:
                    storpool_node = node_map[rsc.node_name].find_child(self.DISKLESS_RESOURCE_NAME)
                    if not storpool_node:
                        storpool_node = TreeNode(self.DISKLESS_RESOURCE_NAME, '', Color.PINK)
                        storpool_node.set_description('resources may reside on other nodes')
                        node_map[rsc.node_name].add_child(storpool_node)
                else:
                    storpool_node = node_map[rsc.node_name].find_child(storpool_name)

                for vlm in vlms:
                    rsc_node.add_child(self.make_volume_node(vlm, volume_map))

                storpool_node.add_child(rsc_node)

    def construct_storpool(self, node_map, storage_pool_list):
        for storpool in storage_pool_list.stor_pools:
            storpool_node = TreeNode(storpool.stor_pool_name, '', Color.PINK)
            storpool_node.set_description('storage pool')
            node_map[storpool.node_name].add_child(storpool_node)

    def construct_node(self, node_map, node_list):
        for n in node_list.nodes:
            root_node = TreeNode(n.name, '', Color.RED)
            root_node.set_description('node')
            node_map[n.name] = root_node

    @classmethod
    def show_netinterfaces(cls, args, lstnodes):
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
            raise LinstorClientError("Node '{n}' not found on controller.".format(n=args.node_name),
                                     ExitCode.OBJECT_NOT_FOUND)

    def list_netinterfaces(self, args):
        lstnodes = self._linstor.node_list()

        return self.output_list(args, lstnodes, self.show_netinterfaces)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        node = NodeCommands.find_node(lstmsg, args.node_name)
        if node:
            result.append(node.props)
        else:
            raise LinstorClientError("Node '{n}' not found on controller.".format(n=args.node_name),
                                     ExitCode.OBJECT_NOT_FOUND)

        return result

    def print_props(self, args):
        lstmsg = self._linstor.node_list()

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
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
