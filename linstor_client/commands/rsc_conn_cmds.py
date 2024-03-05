from __future__ import print_function

import os

import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands, DrbdOptions
from linstor_client import TableHeader, Table
from linstor import consts as apiconsts


class ResourceConnectionCommands(Commands):
    OBJECT_NAME = 'rsc-conn'

    _headers = [
        TableHeader("Source"),
        TableHeader("Target"),
        TableHeader("Properties"),
        TableHeader("Port")
    ]

    class Path(object):
        LONG = "path"
        SHORT = "p"

    def __init__(self):
        super(ResourceConnectionCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdPeerDeviceOptions,
            ResourceConnectionCommands.Path
        ]

        res_conn_parser = parser.add_parser(
            Commands.RESOURCE_CONN,
            aliases=["rc"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resource connection subcommands")
        subp = res_conn_parser.add_subparsers(
            title="resource connection commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        rescon_groubby = [x.name.lower() for x in ResourceConnectionCommands._headers]
        res_group_completer = Commands.show_group_completer(rescon_groubby, "groupby")

        p_lresconn = subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource connections for the given resource. '
                        'By default, the list is printed as a human readable table.'
        )
        p_lresconn.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lresconn.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=rescon_groubby,
            type=str.lower).completer = res_group_completer
        p_lresconn.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lresconn.add_argument(
            'resource_name',
            help="Resource name"
        ).completer = self.resource_completer
        p_lresconn.set_defaults(func=self.list)

        # show properties
        p_sp = subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given resource connection.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_sp.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        p_sp.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given resource connection.')
        p_setprop.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_setprop.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        p_setprop.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource'
        ).completer = self.resource_completer
        Commands.add_parser_keyvalue(p_setprop, "rsc-conn")
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
        p_drbd_peer_opts.add_argument(
            'resource_name',
            type=str,
            help="Resource name"
        ).completer = self.resource_completer

        DrbdOptions.add_arguments(p_drbd_peer_opts, self.OBJECT_NAME)
        p_drbd_peer_opts.set_defaults(func=self.drbd_opts)

        # Path commands
        path_subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete
        ]

        path_parser = subp.add_parser(
            ResourceConnectionCommands.Path.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[ResourceConnectionCommands.Path.SHORT],
            description="%s subcommands" % ResourceConnectionCommands.Path.LONG)

        path_subp = path_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.Interface.LONG,
            metavar="",
            description=Commands.Subcommands.generate_desc(path_subcmds))

        # create path
        path_create = path_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a new resource connection path.'
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
            "resource_name",
            type=str,
            help="Resource name"
        ).completer = self.resource_completer
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
            description='Deletes an existing resource connection path.'
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
            "resource_name",
            type=str,
            help="Resource name"
        ).completer = self.resource_completer
        path_delete.add_argument(
            "path_name",
            help="Name of the created path"
        )
        path_delete.set_defaults(func=self.path_delete)

        # list path
        path_list = path_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='List all existing resource connection paths.'
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
        path_list.add_argument(
            "resource_name",
            type=str,
            help="Resource name"
        ).completer = self.resource_completer
        path_list.set_defaults(func=self.path_list)

        self.check_subcommands(path_subp, path_subcmds)
        self.check_subcommands(subp, subcmds)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_headers(ResourceConnectionCommands._headers)
        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        tbl.set_groupby(args.groupby if args.groupby else [ResourceConnectionCommands._headers[0].name])

        props_str_size = 30

        for rsc_con in [x for x in lstmsg.resource_connections if "DELETED" not in x.flags]:
            opts = [os.path.basename(x) + '=' + rsc_con.properties[x] for x in rsc_con.properties]
            props_str = ",".join(opts)
            row = [
                rsc_con.node_a,
                rsc_con.node_b,
                props_str if len(props_str) < props_str_size else props_str[:props_str_size] + '...',
                rsc_con.port if rsc_con.port else ''
            ]
            for sprop in show_props:
                row.append(rsc_con.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.resource_conn_list(args.resource_name)
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_show(cls, args, lstmsg):
        """

        :param args:
        :param linstor.responses.ResourceConnection lstmsg:
        :return:
        """
        result = []
        if lstmsg:
            result.append(lstmsg.properties)
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_conn_node_list_raise(args.resource_name, args.node_name_a, args.node_name_b)
        return self.output_props_list(args, [lstmsg], self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.resource_conn_modify(
            args.resource_name,
            args.node_name_a,
            args.node_name_b,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']
        del a['node-a']
        del a['node-b']

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = self._linstor.resource_conn_modify(
            args.resource_name,
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
        replies = self.get_linstorapi().resource_conn_modify(
            args.resource_name,
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
            for rsc_con in lstmsg.resource_connections:
                if (rsc_con.node_a == args.node_a and rsc_con.node_b == args.node_b) or \
                        (rsc_con.node_b == args.node_a and rsc_con.node_a == args.node_b):
                    result.append({x: rsc_con.properties[x] for x in rsc_con.properties
                                   if x.startswith(apiconsts.NAMESPC_CONNECTION_PATHS + '/')})
                    break
        return result

    def path_list(self, args):
        lstmsg = self._linstor.resource_conn_list(args.resource_name)
        return self.output_props_list(args, lstmsg, self._path_list)

    def path_delete(self, args):
        prop_ns = "{ns}/{pn}".format(ns=apiconsts.NAMESPC_CONNECTION_PATHS, pn=args.path_name)
        replies = self.get_linstorapi().resource_conn_modify(
            args.resource_name,
            args.node_a,
            args.node_b,
            property_dict={},
            delete_props=["{ns}/{n}".format(ns=prop_ns, n=args.node_a),
                          "{ns}/{n}".format(ns=prop_ns, n=args.node_b)]
        )
        return self.handle_replies(args, replies)
