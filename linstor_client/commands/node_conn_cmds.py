from __future__ import print_function

import os

import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands, DrbdOptions
from linstor_client import TableHeader, Table
from linstor import consts as apiconsts


class NodeConnectionCommands(Commands):
    DRBD_OBJECT_NAME = 'rsc-conn'  # although this is a node-connection, for drbd-options we still want to use
    # resource-connections

    _headers = [
        TableHeader("Node A"),
        TableHeader("Node B"),
        TableHeader("Properties")
    ]

    class Path(object):
        LONG = "path"
        SHORT = "p"

    def __init__(self):
        super(NodeConnectionCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdPeerDeviceOptions,
            NodeConnectionCommands.Path
        ]

        node_conn_parser = parser.add_parser(
            Commands.NODE_CONN,
            aliases=["nc"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Node connection subcommands")
        subp = node_conn_parser.add_subparsers(
            title="node connection commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        node_con_groubby = [x.name.lower() for x in NodeConnectionCommands._headers]
        node_group_completer = Commands.show_group_completer(node_con_groubby, "groupby")

        p_lnodeconn = subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all non-empty node connections. '
                        'By default, the list is printed as a human readable table.'
        )
        p_lnodeconn.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lnodeconn.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=node_con_groubby,
            type=str.lower).completer = node_group_completer
        p_lnodeconn.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lnodeconn.add_argument(
            'node_name_a',
            nargs='?',
            help="Node name"
        ).completer = self.node_completer
        p_lnodeconn.add_argument(
            'node_name_b',
            nargs='?',
            help="Node name"
        ).completer = self.node_completer
        p_lnodeconn.set_defaults(func=self.list)

        # show properties
        p_sp = subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given node connection.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_sp.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given node connection.')
        p_setprop.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_setprop.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        Commands.add_parser_keyvalue(p_setprop, "node-conn")
        p_setprop.set_defaults(func=self.set_props)

        # drbd peer device options
        p_drbd_peer_opts = subp.add_parser(
            Commands.Subcommands.DrbdPeerDeviceOptions.LONG,
            aliases=[
                Commands.Subcommands.DrbdPeerDeviceOptions.SHORT
            ],
            description=DrbdOptions.description("peer-device")
        )
        p_drbd_peer_opts.add_argument(
            'node_a',
            type=str,
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'node_b',
            type=str,
            help="2. Node in the node connection"
        ).completer = self.node_completer

        DrbdOptions.add_arguments(p_drbd_peer_opts, self.DRBD_OBJECT_NAME)
        p_drbd_peer_opts.set_defaults(func=self.drbd_opts)

        # Path commands
        path_subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete
        ]

        path_parser = subp.add_parser(
            NodeConnectionCommands.Path.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[NodeConnectionCommands.Path.SHORT],
            description="%s subcommands" % NodeConnectionCommands.Path.LONG)

        path_subp = path_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.Interface.LONG,
            metavar="",
            description=Commands.Subcommands.generate_desc(path_subcmds))

        # create path
        path_create = path_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a new node connection path.'
        )
        path_create.add_argument(
            "node_a",
            type=str,
            help="1. Node of the connection"
        ).completer = self.node_completer
        path_create.add_argument(
            "node_b",
            type=str,
            help="2. Node of the connection"
        ).completer = self.node_completer
        path_create.add_argument(
            "path_name",
            help="Name of the created path"
        )
        path_create.add_argument(
            "netinterface_a",
            help="Netinterface name to use for 1. node"
        ).completer = self.netif_completer
        path_create.add_argument(
            "netinterface_b",
            help="Netinterface name to use for the 2. node"
        ).completer = self.netif_completer
        path_create.set_defaults(func=self.path_create)

        # delete path
        path_delete = path_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Deletes an existing node connection path.'
        )
        path_delete.add_argument(
            "node_a",
            type=str,
            help="1. Node of the connection"
        ).completer = self.node_completer
        path_delete.add_argument(
            "node_b",
            type=str,
            help="2. Node of the connection"
        ).completer = self.node_completer
        path_delete.add_argument(
            "path_name",
            help="Name of the created path"
        )
        path_delete.set_defaults(func=self.path_delete)

        # list path
        path_list = path_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='List all existing node connection paths.'
        )
        path_list.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        path_list.add_argument(
            "node_a",
            type=str,
            help="1. Node of the connection"
        ).completer = self.node_completer
        path_list.add_argument(
            "node_b",
            type=str,
            help="2. Node of the connection"
        ).completer = self.node_completer
        path_list.set_defaults(func=self.path_list)

        self.check_subcommands(path_subp, path_subcmds)
        self.check_subcommands(subp, subcmds)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_headers(NodeConnectionCommands._headers)
        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        tbl.set_groupby(args.groupby if args.groupby else [NodeConnectionCommands._headers[0].name])

        props_str_size = 30

        for node_con in [x for x in lstmsg.node_connections if "DELETED" not in x.flags]:
            opts = [os.path.basename(x) + '=' + node_con.properties[x] for x in node_con.properties]
            props_str = ",".join(opts)
            row = [
                node_con.node_a,
                node_con.node_b,
                props_str if len(props_str) < props_str_size else props_str[:props_str_size] + '...'
            ]
            for sprop in show_props:
                row.append(node_con.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.node_conn_list(args.node_name_a, args.node_name_b)
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_show(cls, args, lstmsg):
        """

        :param args:
        :param linstor.responses.NodeConnection lstmsg:
        :return:
        """
        result = []
        if lstmsg:
            result.append(lstmsg.properties)
        return result

    def print_props(self, args):
        lstmsg = self._linstor.node_conn_list(args.node_name_a, args.node_name_b)
        node_con = []
        if lstmsg:
            node_con = lstmsg[0].node_connections
        return self.output_props_list(args, node_con, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.node_conn_modify(
            args.node_name_a,
            args.node_name_b,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['node-a']
        del a['node-b']

        mod_props, del_props = DrbdOptions.parse_opts(a, self.DRBD_OBJECT_NAME)

        replies = self._linstor.node_conn_modify(
            args.node_a,
            args.node_b,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)

    def path_create(self, args):
        prop_ns = "{ns}/{pn}".format(ns=apiconsts.NAMESPC_CONNECTION_PATHS, pn=args.path_name)
        props = {
            "{ns}/{n}".format(ns=prop_ns, n=args.node_a): args.netinterface_a,
            "{ns}/{n}".format(ns=prop_ns, n=args.node_b): args.netinterface_b,
        }
        replies = self.get_linstorapi().node_conn_modify(
            args.node_a,
            args.node_b,
            property_dict=props,
            delete_props=[]
        )
        return self.handle_replies(args, replies)

    @classmethod
    def _path_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for node_con in lstmsg.node_connections:
                if (node_con.node_a == args.node_a and node_con.node_b == args.node_b) or \
                        (node_con.node_b == args.node_a and node_con.node_a == args.node_b):
                    result.append({x: node_con.properties[x] for x in node_con.properties
                                   if x.startswith(apiconsts.NAMESPC_CONNECTION_PATHS + '/')})
                    break
        return result

    def path_list(self, args):
        lstmsg = self._linstor.node_conn_list(args.node_a, args.node_b)
        return self.output_props_list(args, lstmsg, self._path_list)

    def path_delete(self, args):
        prop_ns = "{ns}/{pn}".format(ns=apiconsts.NAMESPC_CONNECTION_PATHS, pn=args.path_name)
        replies = self.get_linstorapi().node_conn_modify(
            args.node_a,
            args.node_b,
            property_dict={},
            delete_props=["{ns}/{n}".format(ns=prop_ns, n=args.node_a),
                          "{ns}/{n}".format(ns=prop_ns, n=args.node_b)]
        )
        return self.handle_replies(args, replies)
