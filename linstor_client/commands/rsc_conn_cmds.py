from __future__ import print_function

import os

import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands, DrbdOptions, ArgumentError
from linstor_client.consts import NODE_NAME, RES_NAME
from linstor_client.utils import Output, namecheck, Color
from linstor_client import TableHeader, Table


class ResourceConnectionCommands(Commands):
    OBJECT_NAME = 'rsc-conn'

    _headers = [
        TableHeader("Source"),
        TableHeader("Target"),
        TableHeader("Properties"),
        TableHeader("Port")
    ]

    def __init__(self):
        super(ResourceConnectionCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions,
            Commands.Subcommands.DrbdPeerDeviceOptions
        ]

        res_conn_parser = parser.add_parser(
            Commands.RESOURCE_CONN,
            aliases=["rc"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resouce subcommands")
        subp = res_conn_parser.add_subparsers(
            title="resource commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        rescon_groubby = [x.name for x in ResourceConnectionCommands._headers]
        res_group_completer = Commands.show_group_completer(rescon_groubby, "groupby")

        p_lresconn = subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource connnections for the given resource.' +
                        'By default, the list is printed as a human readable table.'
        )
        p_lresconn.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lresconn.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=rescon_groubby).completer = res_group_completer
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
            description='Sets properties for the given resource connection.')
        p_setprop.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_setprop.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        p_setprop.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_completer
        Commands.add_parser_keyvalue(p_setprop, "rsc-conn")
        p_setprop.set_defaults(func=self.set_props)

        # drbd peer device options
        p_drbd_peer_opts = subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[
                Commands.Subcommands.DrbdOptions.SHORT,
                Commands.Subcommands.DrbdPeerDeviceOptions.LONG,
                Commands.Subcommands.DrbdPeerDeviceOptions.SHORT
            ],
            description=DrbdOptions.description("peer-device")
        )
        p_drbd_peer_opts.add_argument(
            'node_a',
            type=namecheck(NODE_NAME),
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'node_b',
            type=namecheck(NODE_NAME),
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help="Resource name"
        ).completer = self.resource_completer

        DrbdOptions.add_arguments(p_drbd_peer_opts, self.OBJECT_NAME)
        p_drbd_peer_opts.set_defaults(func=self.drbd_opts)

        self.check_subcommands(subp, subcmds)

    def show(self, args, lstmsg):
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_headers(ResourceConnectionCommands._headers)

        tbl.set_groupby(args.groupby if args.groupby else [ResourceConnectionCommands._headers[0].name])

        props_str_size = 30

        for rsc_con in [x for x in lstmsg.rsc_connections if "DELETED" not in x.rsc_conn_flags]:
            opts = [os.path.basename(x.key) + '=' + x.value for x in rsc_con.rsc_conn_props]
            props_str = ",".join(opts)
            tbl.add_row([
                rsc_con.node_name_1,
                rsc_con.node_name_2,
                props_str if len(props_str) < props_str_size else props_str[:props_str_size] + '...',
                rsc_con.port if rsc_con.HasField('port') else ''
            ])

        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.resource_conn_list(args.resource_name)
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc_con in lstmsg.rsc_connections:
                if (rsc_con.node_name_1 == args.node_name_a and rsc_con.node_name_2 == args.node_name_b) or \
                        (rsc_con.node_name_2 == args.node_name_a and rsc_con.node_name_1 == args.node_name_b):
                    result.append(rsc_con.rsc_conn_props)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_conn_list(args.resource_name)

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
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
