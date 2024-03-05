import collections
import getpass
import socket
import sys
import json

import linstor.responses
import linstor.sharedconsts as apiconsts
import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor import SizeCalc, LogLevelEnum
from linstor_client.commands import Commands
from linstor_client.consts import Color, ExitCode
from linstor_client.tree import TreeNode
from linstor_client.utils import (LinstorClientError, ip_completer,
                                  rangecheck)
from datetime import datetime


class NodeCommands(Commands):
    DISKLESS_STORAGE_POOL = 'DfltDisklessStorPool'
    DISKLESS_RESOURCE_NAME = 'diskless resource'

    _node_headers = [
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("NodeType"),
        linstor_client.TableHeader("Addresses"),
        linstor_client.TableHeader("State", color=Color.DARKGREEN)
    ]

    _info_headers_provs = [
        linstor_client.TableHeader("Node"),
        [
            linstor_client.TableHeader("Diskless"),
            linstor_client.TableHeader("LVM"),
            linstor_client.TableHeader("LVMThin"),
            linstor_client.TableHeader("ZFS/Thin"),
            linstor_client.TableHeader("File/Thin"),
            linstor_client.TableHeader("SPDK"),
            linstor_client.TableHeader("EXOS"),
            linstor_client.TableHeader("Remote_SPDK"),
            linstor_client.TableHeader("Storage_Spaces"),
            linstor_client.TableHeader("Storage_Spaces/Thin")
        ]
    ]

    _info_headers_lrs = [
        linstor_client.TableHeader("Node"),
        [
            linstor_client.TableHeader("DRBD"),
            linstor_client.TableHeader("LUKS"),
            linstor_client.TableHeader("NVMe"),
            linstor_client.TableHeader("Cache"),
            linstor_client.TableHeader("BCache"),
            linstor_client.TableHeader("WriteCache"),
            linstor_client.TableHeader("Storage"),
        ]
    ]

    class CreateRemoteSpdkTarget:
        LONG = "create-remote-spdk-target"
        SHORT = "crspdkt"

    class CreateEbsTarget:
        LONG = "create-ebs-target"
        SHORT = "cebst"

    class Reconnect:
        LONG = "reconnect"
        SHORT = "rc"

    def __init__(self):
        super(NodeCommands, self).__init__()

    def setup_commands(self, parser):
        # Node subcommands
        subcmds = [
            Commands.Subcommands.Create,
            NodeCommands.CreateRemoteSpdkTarget,
            NodeCommands.CreateEbsTarget,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Lost,
            Commands.Subcommands.Describe,
            Commands.Subcommands.Interface,
            Commands.Subcommands.Info,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.Modify,
            NodeCommands.Reconnect,
            Commands.Subcommands.Restore,
            Commands.Subcommands.Evacuate
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
            description='Creates a node entry for a node that participates in the LINSTOR cluster.'
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
        p_new_node.add_argument('--node-type', choices=[x.lower() for x in node_types],
                                default=apiconsts.VAL_NODE_TYPE_STLT,
                                type=str.lower,
                                help='Node type (default: %s)' % ntype_def.lower())
        ctype_def = apiconsts.VAL_NETCOM_TYPE_PLAIN
        p_new_node.add_argument('--communication-type',
                                choices=(apiconsts.VAL_NETCOM_TYPE_PLAIN.lower(),
                                         apiconsts.VAL_NETCOM_TYPE_SSL.lower()),
                                default=ctype_def,
                                type=str.lower,
                                help='Communication type (default: %s)' % ctype_def.lower())
        itype_def = apiconsts.VAL_NETIF_TYPE_IP
        p_new_node.add_argument('--interface-type', choices=(apiconsts.VAL_NETIF_TYPE_IP.lower(),),
                                type=str.lower,
                                default=itype_def,
                                help='Interface type (default: %s)' % itype_def.lower())
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

        # remote spdk create
        p_create_remote_spdk_target = node_subp.add_parser(
            NodeCommands.CreateRemoteSpdkTarget.LONG,
            aliases=[NodeCommands.CreateRemoteSpdkTarget.SHORT],
            description='Creates a virtual remote SPDK target node on the LINSTOR controller.'
        )
        p_create_remote_spdk_target.add_argument(
            'node_name',
            help='Name of the new remote SPDK target node',
            type=str
        )
        p_create_remote_spdk_target.add_argument('api_host', help='Remote SPDK storage device API host')
        p_create_remote_spdk_target.add_argument('--api-port', help='Remote SPDK storage device API port')
        p_create_remote_spdk_target.add_argument('--api-user', help='Remote SPDK storage device API user name')
        p_create_remote_spdk_target.add_argument(
            '--api-user-env',
            help='Environment variable containing remote SPDK storage device API user name'
        )
        p_create_remote_spdk_target.add_argument(
            '--api-pw',
            type=str,
            nargs='?',
            help='Remote SPDK storage device API password',
            action='store',
            const=''
        )
        p_create_remote_spdk_target.add_argument(
            '--api-pw-env',
            help='Environment variable containing remote SPDK storage device API password'
        )
        p_create_remote_spdk_target.set_defaults(func=self.create_remote_spdk_target)

        # ebs create
        p_create_ebs_target = node_subp.add_parser(
            NodeCommands.CreateEbsTarget.LONG,
            aliases=[NodeCommands.CreateEbsTarget.SHORT],
            description='Creates a virtual EBS target node on the LINSTOR controller.'
        )
        p_create_ebs_target.add_argument(
            'node_name',
            help='Name of the new EBS target node',
            type=str
        )
        p_create_ebs_target.add_argument('ebs_remote_name', help='EBS Remote name')
        p_create_ebs_target.set_defaults(func=self.create_ebs_target)

        # modify node
        p_modify_node = node_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modify node type for a specified node.'
        )
        p_modify_node.add_argument(
            '--node-type', '-t',
            choices=[x.lower() for x in node_types],
            type=str.lower,
            default=apiconsts.VAL_NODE_TYPE_STLT,
            help='Node type (default: %s)' % ntype_def.lower()
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
            description='Shows a tree view of storage pools, resources, and volumes, in that order, on a specified '
            'node (or all nodes if none specified).')
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
            description='Removes a node from the LINSTOR cluster. '
            'All LINSTOR resources that are still deployed on the specified '
            'node are marked for undeployment, and the node entry is marked for '
            "removal from LINSTOR's data tables. The specified node is "
            'expected to undeploy all resources. As soon as all resources have been '
            'undeployed from the node, the node entry is removed from '
            "LINSTOR's data tables.")
        p_rm_node.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_rm_node.add_argument('name',
                               help='Name of the node to remove').completer = self.node_completer
        p_rm_node.set_defaults(func=self.delete)

        # lost-node
        p_lost_node = node_subp.add_parser(
            Commands.Subcommands.Lost.LONG,
            aliases=[Commands.Subcommands.Lost.SHORT],
            description='Removes an unrecoverable node from the LINSTOR cluster. '
            'All LINSTOR resources attached to this node will be deleted from the database.'
        )
        p_lost_node.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_lost_node.add_argument(
            'name',
            help='Name of the node to delete.').completer = self.node_completer
        p_lost_node.set_defaults(func=self.lost)

        # reconnect node(s)
        p_recon_node = node_subp.add_parser(
            NodeCommands.Reconnect.LONG,
            aliases=[NodeCommands.Reconnect.SHORT],
            description='Reconnect a node to the LINSTOR controller, reinitializing the node\'s state.'
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
            description='Creates and adds a new network interface to a given node. '
                        'If a port is specified this network interface is used as satellite port.'
        )
        p_create_netinterface.add_argument(
            '-p', '--port',
            type=rangecheck(1, 65535),
            help='Port to use for satellite connections'
        )
        p_create_netinterface.add_argument(
            '--communication-type',
            choices=(apiconsts.VAL_NETCOM_TYPE_PLAIN.lower(), apiconsts.VAL_NETCOM_TYPE_SSL.lower()),
            type=str.lower,
            default=ctype_def,
            help='Communication type (default: %s)' % ctype_def.lower()
        )
        p_create_netinterface.add_argument(
            '--active',
            action='store_true',
            help='Create this net interface as the active satellite connection'
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
            description='Modify the network interface of a specified node: port number, communication type, active '
            'satellite connection state, IP address listening on.'
        )
        p_mod_netif.add_argument(
            '-p', '--port', type=rangecheck(1, 65535),
            help='Port to use for satellite connections'
        )
        p_mod_netif.add_argument(
            '--communication-type',
            choices=(apiconsts.VAL_NETCOM_TYPE_PLAIN.lower(), apiconsts.VAL_NETCOM_TYPE_SSL.lower()),
            type=str.lower,
            default=ctype_def,
            help='Communication type (default: %s)' % ctype_def.lower()
        )
        p_mod_netif.add_argument(
            '--active',
            action='store_true',
            help='Set this net interface as the active satellite connection'
        )
        p_mod_netif.add_argument('--ip', help='New IP address for the network interface')
        p_mod_netif.add_argument("node_name", help="Name of the node").completer = self.node_completer
        p_mod_netif.add_argument("interface_name", help="Interface to change").completer = self.netif_completer
        p_mod_netif.set_defaults(func=self.modify_netif)

        # delete net interface
        p_delete_netinterface = interface_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Delete a network interface from a node.'
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
        node_groupby = [x.name.lower() for x in self._node_headers]
        node_group_completer = Commands.show_group_completer(node_groupby, "groupby")

        p_lnodes = node_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all cluster nodes known to LINSTOR. '
            'By default, the list is printed as a human readable table.')
        p_lnodes.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnodes.add_argument('-g', '--groupby', nargs='+', type=str.lower,
                              choices=node_groupby).completer = node_group_completer
        p_lnodes.add_argument('-n', '--nodes', nargs='+', type=str,
                              help='Filter by list of nodes').completer = self.node_completer
        p_lnodes.add_argument('--show-aux-props', action="store_true", help='Show aux properties for nodes')
        p_lnodes.add_argument('--props', nargs='+', type=str, help='Filter list by object properties')
        p_lnodes.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lnodes.add_argument(
            '--from-file',
            type=argparse.FileType('r'),
            help="Read data to display from the given json file",
        )
        p_lnodes.set_defaults(func=self.list)

        # list info
        p_info_node = node_subp.add_parser(
            Commands.Subcommands.Info.LONG,
            aliases=[Commands.Subcommands.Info.SHORT],
            description='Prints detailed information about supported storage technologies for all cluster nodes '
            'known to LINSTOR. By default, the list is printed as a human readable table.'
        )
        p_info_node.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_info_node.add_argument('-f', '--full', action="store_true", help="Also shows provider/layer errors")
        p_info_node.add_argument(
            '-n', '--nodes', nargs='+', type=str, help='Filter by list of nodes'
        ).completer = self.node_completer
        p_info_node.set_defaults(func=self.info)

        # list netinterface
        p_lnetif = interface_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of network interfaces for a specified node.'
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
            formatter_class=argparse.RawTextHelpFormatter,
            description="Set a property on the given node."
        )
        p_setp.add_argument(
            'node_name',
            help="Node for which to set the property"
        ).completer = self.node_completer
        Commands.add_parser_keyvalue(p_setp, "node")
        p_setp.set_defaults(func=self.set_props)

        # restore evicted node
        p_restore_node = node_subp.add_parser(
            Commands.Subcommands.Restore.LONG,
            aliases=[Commands.Subcommands.Restore.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Restore an evicted node."
        )
        p_restore_node.add_argument(
            'node_name',
            help="Evicted node to restore"
        ).completer = self.node_completer
        p_restore_node.add_argument(
            '--delete-resources',
            action='store_true',
            help="Delete the resources before reconnecting the node"
        ).completer = self.node_completer
        p_restore_node.add_argument(
            '--delete-snapshots',
            action='store_true',
            help="Delete the snapshots before reconnecting the node"
        ).completer = self.node_completer
        p_restore_node.set_defaults(func=self.restore_node)

        # node evacuate
        p_evacuate_node = node_subp.add_parser(
            Commands.Subcommands.Evacuate.LONG,
            aliases=[Commands.Subcommands.Evacuate.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Evacuate a node."
        )
        p_evacuate_node.add_argument(
            'node_name',
            help="Node to evacuate"
        ).completer = self.node_completer
        p_evacuate_node.set_defaults(func=self.evacuate_node)

        self.check_subcommands(interface_subp, netif_subcmds)
        self.check_subcommands(node_subp, subcmds)

        # node set-log-level
        p_set_log_level = node_subp.add_parser(
            Commands.Subcommands.LogLevel.LONG,
            aliases=[Commands.Subcommands.LogLevel.SHORT],
            description="Sets the log level")
        p_set_log_level.add_argument(
            'node_name',
            help="Node to set the log level"
        ).completer = self.node_completer
        p_set_log_level.add_argument('level',
                                     type=LogLevelEnum.check,
                                     choices=list(LogLevelEnum))
        p_set_log_level.add_argument('--library', '--lib',
                                     action='store_true',
                                     help='Modify the log level of external libraries instead of LINSTOR itself')
        p_set_log_level.set_defaults(func=self.set_log_level)

    @classmethod
    def _resolve_remote_ip(cls, hostname):
        """
        Tries to resolve a non local ip address of the given hostname
        :param str hostname: hostname to resolve
        :return: ip address as string or None if it couldn't be resolved
        :rtype: str
        :raise: LinstorClientError if unable to determine an address
        """
        try:
            addrinfo = socket.getaddrinfo(hostname, None)

            non_local = [y for y in addrinfo if y[0] == 2 and not y[4][0].startswith('127.')]
            if non_local:
                return non_local[0][4][0]
            raise LinstorClientError(
                "Unable determine a valid ip address '" + hostname + "'", ExitCode.ARGPARSE_ERROR)

        except socket.gaierror as err:
            raise LinstorClientError(
                "Unable to resolve ip address for '" + hostname + "': " + str(err), ExitCode.ARGPARSE_ERROR)

    def create(self, args):
        ip_addr = args.ip
        if args.ip is None:
            ip_addr = self._resolve_remote_ip(args.name)

        replies = self._linstor.node_create(
            args.name,
            args.node_type,
            ip_addr,
            args.communication_type,
            args.port,
            args.interface_name
        )

        return self.handle_replies(args, replies)

    def create_remote_spdk_target(self, args):
        props = {
            apiconsts.NAMESPC_STORAGE_DRIVER + '/' + apiconsts.KEY_STOR_POOL_REMOTE_SPDK_API_HOST: args.api_host,
        }

        tmp_dict = {
            apiconsts.KEY_STOR_POOL_REMOTE_SPDK_API_PORT: args.api_port,
            apiconsts.KEY_STOR_POOL_REMOTE_SPDK_API_USER_NAME: args.api_user,
            apiconsts.KEY_STOR_POOL_REMOTE_SPDK_API_USER_NAME_ENV: args.api_user_env,
            apiconsts.KEY_STOR_POOL_REMOTE_SPDK_API_USER_PW: self._get_password(args),
            apiconsts.KEY_STOR_POOL_REMOTE_SPDK_API_USER_PW_ENV: args.api_pw_env
        }

        for key, val in tmp_dict.items():
            if val:
                props[apiconsts.NAMESPC_STORAGE_DRIVER + '/' + key] = val

        replies = self.get_linstorapi().node_create(
            args.node_name,
            apiconsts.VAL_NODE_TYPE_REMOTE_SPDK,
            "127.0.0.1",
            property_dict=props
        )
        return self.handle_replies(args, replies)

    def create_ebs_target(self, args):
        replies = self.get_linstorapi().node_create_ebs(
            args.node_name,
            args.ebs_remote_name
        )
        return self.handle_replies(args, replies)

    @staticmethod
    def _get_password(args):
        if args.api_pw is None:
            return None
        elif args.api_pw:
            return args.api_pw
        else:
            return getpass.getpass("Password: ")

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

        node_hdr = list(cls._node_headers)
        if args.show_aux_props:
            node_hdr.insert(-1, linstor_client.TableHeader("AuxProps"))

        for hdr in node_hdr:
            tbl.add_header(hdr)

        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        conn_stat_dict = {
            apiconsts.ConnectionStatus.OFFLINE.name: ("OFFLINE", Color.RED),
            apiconsts.ConnectionStatus.CONNECTED.name: ("Connected", Color.YELLOW),
            apiconsts.ConnectionStatus.ONLINE.name: ("Online", Color.GREEN),
            apiconsts.ConnectionStatus.VERSION_MISMATCH.name: ("OFFLINE(VERSION MISMATCH)", Color.RED),
            apiconsts.ConnectionStatus.FULL_SYNC_FAILED.name: ("OFFLINE(FULL SYNC FAILED)", Color.RED),
            apiconsts.ConnectionStatus.MISSING_EXT_TOOLS.name: ("OFFLINE(MISSING EXTERNAL TOOLS)", Color.RED),
            apiconsts.ConnectionStatus.AUTHENTICATION_ERROR.name: ("OFFLINE(AUTHENTICATION ERROR)", Color.RED),
            apiconsts.ConnectionStatus.UNKNOWN.name: ("Unknown", Color.YELLOW),
            apiconsts.ConnectionStatus.HOSTNAME_MISMATCH.name: ("OFFLINE(HOSTNAME MISMATCH)", Color.RED),
            apiconsts.ConnectionStatus.OTHER_CONTROLLER.name: ("OFFLINE(OTHER_CONTROLLER)", Color.RED),
            apiconsts.ConnectionStatus.NO_STLT_CONN.name: ("OFFLINE(NO CONNECTION TO SATELLITE)", Color.RED)
        }

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])

        show_eviction_info = False
        for node in lstmsg.nodes:
            node_is_offline = conn_stat_dict.get(node.connection_status)[0] == apiconsts.ConnectionStatus.OFFLINE.name
            node_is_evicted = apiconsts.FLAG_EVICTED in node.flags
            if node.eviction_timestamp and node_is_offline and not node_is_evicted:
                show_eviction_info = True
                break

        for node in lstmsg.nodes:
            # concat a ip list with satellite connection indicator
            active_ip = ""
            for net_if in node.net_interfaces:
                if net_if.is_active and net_if.stlt_port:
                    active_ip = net_if.address + ":" + str(net_if.stlt_port) + " (" + net_if.stlt_encryption_type + ")"

            aux_props = ["{k}={v}".format(k=k, v=v)
                         for k, v in node.properties.items() if k.startswith(apiconsts.NAMESPC_AUXILIARY + '/')]

            if apiconsts.FLAG_EVICTED in node.flags:
                conn_stat = (apiconsts.FLAG_EVICTED, Color.RED)
            elif apiconsts.FLAG_DELETE in node.flags:
                conn_stat = (apiconsts.FLAG_DELETE, Color.RED)
            elif apiconsts.FLAG_EVACUATE in node.flags:
                conn_stat = (apiconsts.FLAG_EVACUATE, Color.YELLOW)
            else:
                conn_stat = conn_stat_dict.get(node.connection_status)

            row = [node.name, node.type, active_ip]
            if args.show_aux_props:
                row.append("\n".join(aux_props))

            state_text = conn_stat[0]
            node_is_offline = conn_stat_dict.get(node.connection_status)[0] == apiconsts.ConnectionStatus.OFFLINE.name
            node_is_evicted = apiconsts.FLAG_EVICTED in node.flags
            if show_eviction_info and node_is_offline and not node_is_evicted:
                if node.eviction_timestamp:
                    eviction = datetime.fromtimestamp(int(node.eviction_timestamp / 1000))
                else:
                    eviction = "Disabled"
                state_text += " (Auto-eviction: {eviction})".format(eviction=eviction)

            row += [tbl.color_cell(state_text, conn_stat[1])]
            for sprop in show_props:
                row.append(node.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()

        if show_eviction_info:
            print("To cancel automatic eviction please consider the corresponding "
                  "DrbdOptions/AutoEvict* properties on controller and / or node level")
            print("See 'linstor controller set-property --help' or 'linstor node set-property --help' for more details")

    def list(self, args):
        args = self.merge_config_args('node.list', args)
        if args.from_file:
            lstmsg = [linstor.responses.NodeListResponse(json.load(args.from_file))]
        else:
            lstmsg = self._linstor.node_list(args.nodes, args.props)
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
        node = lstnodes.node(args.node_name)
        if node:
            tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column(node.name, color=Color.GREEN)
            tbl.add_column("NetInterface")
            tbl.add_column("IP")
            tbl.add_column("Port")
            tbl.add_column("EncryptionType")
            # warning: system test depends on alphabetical ordering
            for net_if in node.net_interfaces:
                tbl.add_row([
                    "+ StltCon" if net_if.is_active else "+",
                    net_if.name,
                    net_if.address,
                    net_if.stlt_port if net_if.stlt_port else "",
                    net_if.stlt_encryption_type if net_if.stlt_encryption_type else ""
                ])
            tbl.show()
        else:
            raise LinstorClientError("Node '{n}' not found on controller.".format(n=args.node_name),
                                     ExitCode.OBJECT_NOT_FOUND)

    def list_netinterfaces(self, args):
        return self.output_list(args, self._linstor.node_list([args.node_name]), self.show_netinterfaces)

    @classmethod
    def show_info(cls, args, lstmsg):
        tbl_provs = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl_lrs = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        tbl_provs.add_header(cls._info_headers_provs[0])
        tbl_lrs.add_header(cls._info_headers_lrs[0])

        stor_prov_hdrs = cls._info_headers_provs[1]
        rsc_layer_hdrs = cls._info_headers_lrs[1]

        for stor_prov_hdr in stor_prov_hdrs:
            tbl_provs.add_header(stor_prov_hdr)
        for rsc_layer_hdr in rsc_layer_hdrs:
            tbl_lrs.add_header(rsc_layer_hdr)

        unsp_provs_msgs = {}
        unsp_lrs_msgs = {}

        # only satellite nodes got useful info
        for node in [x for x in lstmsg.nodes if x.type.lower() in [apiconsts.VAL_NODE_TYPE_STLT.lower(),
                                                                   apiconsts.VAL_NODE_TYPE_CMBD.lower()]]:
            if node.connection_status != "ONLINE":
                node_offline_msg = "NODE IS OFFLINE!"
                unsp_provs_msgs.update({node.name: node_offline_msg})
                unsp_lrs_msgs.update({node.name: node_offline_msg})
            else:
                if node.unsupported_providers:
                    unsp_provs_msgs.update({node.name: node.unsupported_providers})
                if node.unsupported_layers:
                    unsp_lrs_msgs.update({node.name: node.unsupported_layers})

            row_provs = [node.name]
            row_lrs = [node.name]

            # fill table for supported storage providers
            stor_provs = [x.replace("_", "") for x in node.storage_providers]
            for stor_prov_hdr in stor_prov_hdrs:
                stor_prov_hdr_name = stor_prov_hdr.name.replace("_", "").upper()
                if "/" in stor_prov_hdr_name:
                    stor_prov_hdr_name = stor_prov_hdr_name.replace("/", "").upper()
                if stor_prov_hdr_name in stor_provs:
                    row_provs.append(tbl_provs.color_cell("+", Color.GREEN))
                else:
                    row_provs.append(tbl_provs.color_cell("-", Color.RED))
            tbl_provs.add_row(row_provs)

            # fill table for supported resource layers
            rsc_layers = [x.replace("_", "") for x in node.resource_layers]
            for rsc_layer_hdr in rsc_layer_hdrs:
                if rsc_layer_hdr.name.upper() in rsc_layers:
                    row_lrs.append(tbl_provs.color_cell("+", Color.GREEN))
                else:
                    row_lrs.append(tbl_provs.color_cell("-", Color.RED))
            tbl_lrs.add_row(row_lrs)

        # print storage providers
        tbl_provs.show()
        if args.full and unsp_provs_msgs:
            print("Unsupported storage providers:")
            for node_name, unsp_provs_msg in unsp_provs_msgs.items():
                is_node_online = isinstance(unsp_provs_msg, dict)
                print(" " + node_name + ": " + (unsp_provs_msg if not is_node_online else ""))
                if is_node_online:
                    for prov_name, reasons in unsp_provs_msg.items():
                        for reason in reasons:
                            print("  " + prov_name + ": " + reason)

        # print resource layers
        print("")
        tbl_lrs.show()
        if args.full and unsp_lrs_msgs:
            print("Unsupported resource layers:")
            for node_name, unsp_lrs_msg in unsp_lrs_msgs.items():
                is_node_online = isinstance(unsp_lrs_msg, dict)
                print(" " + node_name + ": " + (unsp_lrs_msg if not is_node_online else ""))
                if is_node_online:
                    for lr_name, reasons in unsp_lrs_msg.items():
                        for reason in reasons:
                            print("  " + lr_name + ": " + reason)

    def info(self, args):
        return self.output_list(args, self._linstor.node_list(args.nodes), self.show_info)

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
        lstmsg = self._linstor.node_list([args.node_name])
        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self.get_linstorapi().node_modify(
            args.node_name,
            property_dict=mod_prop_dict['pairs'],
            delete_props=mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def restore_node(self, args):
        replies = self.get_linstorapi().node_restore(
            node_name=args.node_name,
            delete_resources=args.delete_resources,
            delete_snapshots=args.delete_snapshots
        )
        return self.handle_replies(args, replies)

    def evacuate_node(self, args):
        replies = self.get_linstorapi().node_evacuate(
            node_name=args.node_name
        )
        return self.handle_replies(args, replies)

    def create_netif(self, args):
        replies = self._linstor.netinterface_create(
            args.node_name,
            args.interface_name,
            args.ip,
            args.port,
            args.communication_type,
            args.active
        )

        return self.handle_replies(args, replies)

    def modify_netif(self, args):
        replies = self._linstor.netinterface_modify(
            args.node_name,
            args.interface_name,
            args.ip,
            args.port,
            args.communication_type,
            args.active
        )

        return self.handle_replies(args, replies)

    def delete_netif(self, args):
        # execute delete netinterfaces and flatten result list
        replies = [x for subx in args.interface_name for x in self._linstor.netinterface_delete(args.node_name, subx)]
        return self.handle_replies(args, replies)

    def set_log_level(self, args):
        replies = self._linstor.node_set_log_level(
            args.node_name,
            args.level,
            args.library if args.library else False)

        return self.handle_replies(args, replies)
