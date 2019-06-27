import linstor_client.argparse.argparse as argparse
import collections
import sys
import socket

import linstor_client
from linstor_client.commands import Commands
from linstor_client.tree import TreeNode
from linstor_client.consts import Color, ExitCode
from linstor_client.utils import (LinstorClientError, ip_completer,
                                  rangecheck)
import linstor.sharedconsts as apiconsts
from linstor import SizeCalc


class NodeCommands(Commands):
    DISKLESS_STORAGE_POOL = 'DfltDisklessStorPool'
    DISKLESS_RESOURCE_NAME = 'diskless resource'

    _node_headers = [
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("NodeType"),
        linstor_client.TableHeader("Addresses"),
        linstor_client.TableHeader("State", color=Color.DARKGREEN)
    ]

    class CreateSwordfishTarget:
        LONG = "create-swordfish-target"
        SHORT = "cswt"

    class Reconnect:
        LONG = "reconnect"
        SHORT = "rc"

    def __init__(self):
        super(NodeCommands, self).__init__()

    def setup_commands(self, parser):
        # Node subcommands
        subcmds = [
            Commands.Subcommands.Create,
            NodeCommands.CreateSwordfishTarget,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Lost,
            Commands.Subcommands.Describe,
            Commands.Subcommands.Interface,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.Modify,
            NodeCommands.Reconnect
        ]

        node_parser = parser.add_parser(
            Commands.NODE,
            aliases=["n"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Node subcommands"
        )

        node_subp = node_parser.add_subparsers(
            title="Node commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        node_types = [
            apiconsts.VAL_NODE_TYPE_CTRL,
            apiconsts.VAL_NODE_TYPE_AUX,
            apiconsts.VAL_NODE_TYPE_CMBD,
            apiconsts.VAL_NODE_TYPE_STLT
        ]

        # create node
        p_new_node = node_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a node entry for a node that participates in the linstor cluster.'
        )
        p_new_node.add_argument('-p', '--port', type=rangecheck(1, 65535),
                                help='default: Satellite %s for %s; Controller %s for %s; %s for %s' % (
                                    apiconsts.DFLT_STLT_PORT_PLAIN,
                                    apiconsts.VAL_NETCOM_TYPE_PLAIN,
                                    apiconsts.DFLT_CTRL_PORT_PLAIN,
                                    apiconsts.VAL_NETCOM_TYPE_PLAIN,
                                    apiconsts.DFLT_CTRL_PORT_SSL,
                                    apiconsts.VAL_NETCOM_TYPE_SSL))
        ntype_def = apiconsts.VAL_NODE_TYPE_STLT
        p_new_node.add_argument('--node-type', choices=node_types,
                                default=apiconsts.VAL_NODE_TYPE_STLT, help='Node type (default: %s)' % ntype_def)
        ctype_def = apiconsts.VAL_NETCOM_TYPE_PLAIN
        p_new_node.add_argument('--communication-type',
                                choices=(apiconsts.VAL_NETCOM_TYPE_PLAIN, apiconsts.VAL_NETCOM_TYPE_SSL),
                                default=ctype_def,
                                help='Communication type (default: %s)' % ctype_def)
        itype_def = apiconsts.VAL_NETIF_TYPE_IP
        p_new_node.add_argument('--interface-type', choices=(apiconsts.VAL_NETIF_TYPE_IP,), default=itype_def,
                                help='Interface type (default: %s)' % itype_def)
        iname_def = 'default'
        p_new_node.add_argument('--interface-name', default=iname_def,
                                help='Interface name (default: %s)' % iname_def)
        p_new_node.add_argument(
            'name',
            help='Name of the new node, must match the nodes hostname',
            type=str)
        p_new_node.add_argument(
            'ip',
            nargs='?',
            help='IP address of the new node, if not specified it will be resolved by the name.'
        ).completer = ip_completer("name")
        p_new_node.set_defaults(func=self.create)

        p_create_sw_target = node_subp.add_parser(
            NodeCommands.CreateSwordfishTarget.LONG,
            aliases=[NodeCommands.CreateSwordfishTarget.SHORT],
            description='Creates a virtual on controller swordfish target node.'
        )
        p_create_sw_target.add_argument(
            'node_name',
            help='Name of the new swordfish target node',
            type=str
        )
        p_create_sw_target.add_argument('storage_service', help='Storage service id')
        p_create_sw_target.set_defaults(func=self.create_sw_target)

        # modify node
        p_modify_node = node_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modify a node'
        )
        p_modify_node.add_argument(
            '--node-type', '-t',
            choices=node_types,
            default=apiconsts.VAL_NODE_TYPE_STLT,
            help='Node type (default: %s)' % ntype_def
        )
        p_modify_node.add_argument(
            'node_name',
            help='Name of the node to modify.'
        ).completer = self.node_completer
        p_modify_node.set_defaults(func=self.modify_node)

        # describe-node
        p_desc_node = node_subp.add_parser(
            Commands.Subcommands.Describe.LONG,
            aliases=[Commands.Subcommands.Describe.SHORT],
            description='describe a node (or all nodes), list storage pools, resources and volumes under this node, '
            'in this order')
        p_desc_node.add_argument(
            'name',
            nargs='?',
            help='Name of the node to be described. With no name, all nodes are described'
        ).completer = self.node_completer
        p_desc_node.set_defaults(func=self.describe)

        # remove-node
        p_rm_node = node_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Removes a node from the linstor cluster. '
            'All linstor resources that are still deployed on the specified '
            'node are marked for undeployment, and the node entry is marked for '
            "removal from linstor's data tables. The specified node is "
            'expected to undeploy all resources. As soon as all resources have been '
            'undeployed from the node, the node entry is removed from '
            "linstor's data tables.")
        p_rm_node.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for actual deletion on satellites before returning'
        )
        p_rm_node.add_argument('name',
                               help='Name of the node to remove').completer = self.node_completer
        p_rm_node.set_defaults(func=self.delete)

        # lost-node
        p_lost_node = node_subp.add_parser(
            Commands.Subcommands.Lost.LONG,
            aliases=[Commands.Subcommands.Lost.SHORT],
            description='Removes an unrecoverable node from the linstor cluster. '
            'All linstor resources attached to this node will be deleted from the database.'
        )
        p_lost_node.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for actual deletion on peers before returning'
        )
        p_lost_node.add_argument(
            'name',
            help='Name of the node to delete.').completer = self.node_completer
        p_lost_node.set_defaults(func=self.lost)

        # reconnect node(s)
        p_recon_node = node_subp.add_parser(
            NodeCommands.Reconnect.LONG,
            aliases=[NodeCommands.Reconnect.SHORT],
            description='Reconnect a node reinitializing the nodes state.'
        )
        p_recon_node.add_argument(
            'nodes',
            nargs="+",
            help='List of nodes to reconnect.'
        ).completer = self.node_completer
        p_recon_node.set_defaults(func=self.reconnect)

        # Interface commands
        netif_subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Modify,
            Commands.Subcommands.Delete
        ]

        interface_parser = node_subp.add_parser(
            Commands.Subcommands.Interface.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[Commands.Subcommands.Interface.SHORT],
            description="%s subcommands" % Commands.Subcommands.Interface.LONG)

        interface_subp = interface_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.Interface.LONG,
            metavar="",
            description=Commands.Subcommands.generate_desc(netif_subcmds))

        # create net interface
        p_create_netinterface = interface_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates and adds a new netinterface to a given node. If port is specified this netinterface '
                        'is used as satellite port'
        )
        p_create_netinterface.add_argument(
            '-p', '--port',
            type=rangecheck(1, 65535),
            help='Port to use for satellite connections'
        )
        p_create_netinterface.add_argument(
            '--communication-type',
            choices=(apiconsts.VAL_NETCOM_TYPE_PLAIN, apiconsts.VAL_NETCOM_TYPE_SSL),
            default=ctype_def,
            help='Communication type (default: %s)' % ctype_def
        )
        p_create_netinterface.add_argument(
            "node_name",
            help="Name of the node to add the net interface"
        ).completer = self.node_completer
        p_create_netinterface.add_argument("interface_name", help="Interface name")
        p_create_netinterface.add_argument('ip', help='New IP address for the network interface')
        p_create_netinterface.set_defaults(func=self.create_netif)

        # modify net interface
        p_mod_netif = interface_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Change the ip listen address of a netinterface on the given node.'
        )
        p_mod_netif.add_argument('-p', '--port', type=rangecheck(1, 65535),
                                 help='Port to use for satellite connections')
        p_mod_netif.add_argument('--communication-type',
                                 choices=(apiconsts.VAL_NETCOM_TYPE_PLAIN, apiconsts.VAL_NETCOM_TYPE_SSL),
                                 default=ctype_def,
                                 help='Communication type (default: %s)' % ctype_def)
        p_mod_netif.add_argument('--ip', help='New IP address for the network interface')
        p_mod_netif.add_argument("node_name", help="Name of the node").completer = self.node_completer
        p_mod_netif.add_argument("interface_name", help="Interface to change").completer = self.netif_completer
        p_mod_netif.set_defaults(func=self.modify_netif)

        # delete net interface
        p_delete_netinterface = interface_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
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
        node_groupby = [x.name for x in self._node_headers]
        node_group_completer = Commands.show_group_completer(node_groupby, "groupby")

        p_lnodes = node_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all cluster nodes known to linstor. '
            'By default, the list is printed as a human readable table.')
        p_lnodes.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnodes.add_argument('-g', '--groupby', nargs='+',
                              choices=node_groupby).completer = node_group_completer
        p_lnodes.add_argument('-N', '--nodes', nargs='+', type=str,
                              help='Filter by list of nodes').completer = self.node_completer
        p_lnodes.set_defaults(func=self.list)

        # list netinterface
        p_lnetif = interface_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of netinterfaces from a node.'
        )
        p_lnetif.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnetif.add_argument(
            'node_name',
            help='Node name for which to print the net interfaces'
        ).completer = self.node_completer
        p_lnetif.set_defaults(func=self.list_netinterfaces)

        # show properties
        p_sp = node_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given node.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name',
            help="Node for which to print the properties").completer = self.node_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setp = node_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            description="Set a property on the given node."
        )
        p_setp.add_argument(
            'node_name',
            help="Node for which to set the property"
        ).completer = self.node_completer
        Commands.add_parser_keyvalue(p_setp, "node")
        p_setp.set_defaults(func=self.set_props)

        self.check_subcommands(interface_subp, netif_subcmds)
        self.check_subcommands(node_subp, subcmds)

    def create(self, args):
        ip_addr = args.ip
        if args.ip is None:
            try:
                ip_addr = socket.gethostbyname(args.name)
            except socket.gaierror as err:
                raise LinstorClientError(
                    "Unable to resolve ip address for '" + args.name + "': " + str(err),
                    ExitCode.ARGPARSE_ERROR
                )

        replies = self._linstor.node_create(
            args.name,
            args.node_type,
            ip_addr,
            args.communication_type,
            args.port,
            args.interface_name
        )

        return self.handle_replies(args, replies)

    def create_sw_target(self, args):
        replies = self.get_linstorapi().node_create_swordfish_target(args.node_name, args.storage_service)
        return self.handle_replies(args, replies)

    def modify_node(self, args):
        replies = self.get_linstorapi().node_modify(args.node_name, args.node_type)
        return self.handle_replies(args, replies)

    def delete(self, args):
        async_flag = vars(args)["async"]

        replies = self._linstor.node_delete(args.name, async_flag)

        return self.handle_replies(args, replies)

    def lost(self, args):
        async_flag = vars(args)["async"]

        replies = self._linstor.node_lost(args.name, async_flag)

        return self.handle_replies(args, replies)

    def reconnect(self, args):
        replies = self.get_linstorapi().node_reconnect(args.nodes)

        return self.handle_replies(args, replies)

    @classmethod
    def show_nodes(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._node_headers:
            tbl.add_header(hdr)

        conn_stat_dict = {
            "OFFLINE": ("OFFLINE", Color.RED),
            "CONNECTED": ("Connected", Color.YELLOW),
            "ONLINE": ("Online", Color.GREEN),
            "VERSION_MISMATCH": ("OFFLINE(VERSION MISMATCH)", Color.RED),
            "FULL_SYNC_FAILED": ("OFFLINE(FULL SYNC FAILED)", Color.RED),
            "AUTHENTICATION_ERROR": ("OFFLINE(AUTHENTICATION ERROR)", Color.RED),
            "UNKNOWN": ("Unknown", Color.YELLOW),
            "HOSTNAME_MISMATCH": ("OFFLINE(HOSTNAME MISMATCH)", Color.RED),
            "OTHER_CONTROLLER": ("OFFLINE(OTHER_CONTROLLER)", Color.RED)
        }

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])

        node_list = [x for x in lstmsg.nodes if x.name in args.nodes] if args.nodes else lstmsg.nodes
        for n in node_list:
            # concat a ip list with satellite connection indicator
            ips = [
                if_.address +
                (":" + str(if_.stlt_port) + " (" + if_.stlt_encryption_type + ")" if if_.stlt_port else "")
                for if_ in n.net_interfaces
            ]
            conn_stat = conn_stat_dict[n.connection_status]
            tbl.add_row([
                n.name,
                n.type,
                ",".join(ips),
                tbl.color_cell(conn_stat[0], conn_stat[1])
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

        try:
            node_list_replies = self._linstor.node_list()
            self.check_list_sanity(args, node_list_replies)
            node_map = self.construct_node(node_list_replies[0])

            storage_pool_list_replies = self._linstor.storage_pool_list()
            self.check_list_sanity(args, storage_pool_list_replies)
            self.construct_storpool(node_map, storage_pool_list_replies[0])

            rsc_dfn_list_replies = self._linstor.resource_dfn_list(query_volume_definitions=False)
            self.check_list_sanity(args, rsc_dfn_list_replies)

            rsc_list_replies = self._linstor.resource_list()
            self.check_list_sanity(args, rsc_list_replies)
            self.construct_rsc(node_map, rsc_list_replies[0])

            outputted = False
            machine_data = []
            for node_name_key in sorted(node_map.keys()):
                if outputted:
                    print("")
                if args.name == node_name_key or not args.name:
                    node = node_map[node_name_key]
                    machine_data.append(node.to_data())
                    if not args.machine_readable:
                        node.print_node(args.no_utf8, args.no_color)
                        outputted = True

            if args.machine_readable:
                print(self._to_json(machine_data))
            elif not outputted and args.name:
                sys.stderr.write('%s: no such node\n' % args.name)
                return ExitCode.OBJECT_NOT_FOUND

        except LinstorClientError as lce:
            return lce.exit_code

        return ExitCode.OK

    def check_list_sanity(self, args, replies):
        if replies:
            if self.check_for_api_replies(replies):
                rc = self.handle_replies(args, replies)
                raise LinstorClientError("List reply error", rc)
        return True

    @classmethod
    def get_volume_size(cls, rsc_dfn_list):
        """
        Constructs a map of minor numbers to volume sizes.

        :param rsc_dfn_list: Protobuf definition list
        :return: the created minor number to volume size map.
        :rtype: dict[int, int]
        """
        volume_def_map = {}  # type dict[int, int]
        for rsc_dfn in rsc_dfn_list.resource_definitions:
            for vlmdfn in rsc_dfn.volume_definitions:
                if vlmdfn.drbd_data:
                    minor = vlmdfn.drbd_data.minor
                    volume_def_map[minor] = vlmdfn.size
        return volume_def_map

    @classmethod
    def make_volume_node(cls, vlm):
        """

        :param responses.Volume vlm:
        :return:
        """
        volume_node = TreeNode('volume' + str(vlm.number), '', Color.DARKGREEN)
        volume_node.set_description('minor number: ' + str(vlm.drbd_data.drbd_volume_definition.minor)
                                    if vlm.drbd_data else '')
        volume_node.add_description(
            ', size: ' + str(SizeCalc.approximate_size_string(vlm.allocated_size))
        )
        return volume_node

    def construct_rsc(self, node_map, rsc_list):
        for rsc in rsc_list.resources:
            vlm_by_storpool = collections.defaultdict(list)
            for vlm in rsc.volumes:
                vlm_by_storpool[vlm.storage_pool_name].append(vlm)

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
                    rsc_node.add_child(self.make_volume_node(vlm))

                storpool_node.add_child(rsc_node)

    def construct_storpool(self, node_map, storage_pool_list):
        for storpool in storage_pool_list.storage_pools:
            storpool_node = TreeNode(storpool.name, '', Color.PINK)
            storpool_node.set_description('storage pool')
            node_map[storpool.node_name].add_child(storpool_node)

    @classmethod
    def construct_node(cls, node_list):
        """
        Constructs a dict of node names to TreeNodes

        :param node_list:
        :return:
        :rtype: dict[str, TreeNode]
        """
        node_map = {}
        for n in node_list.nodes:
            root_node = TreeNode(n.name, '', Color.RED)
            root_node.set_description('node')
            node_map[n.name] = root_node
        return node_map

    @classmethod
    def show_netinterfaces(cls, args, lstnodes):
        node = NodeCommands.find_node(lstnodes, args.node_name)
        if node:
            tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
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
        replies = self.get_linstorapi().node_modify(
            args.node_name,
            property_dict=mod_prop_dict['pairs'],
            delete_props=mod_prop_dict['delete']
        )
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
