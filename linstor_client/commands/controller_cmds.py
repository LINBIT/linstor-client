import json

import linstor
import linstor_client.argparse.argparse as argparse
import linstor_client
from linstor import SizeCalc
from linstor_client.commands import Commands, DrbdOptions
from linstor.sharedconsts import KEY_STOR_POOL_DFN_MAX_OVERSUBSCRIPTION_RATIO


class ControllerCommands(Commands):
    OBJECT_NAME = 'controller'

    def __init__(self):
        super(ControllerCommands, self).__init__()

    def setup_commands(self, parser):
        # Controller commands
        subcmds = [
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions,
            Commands.Subcommands.Version,
            Commands.Subcommands.QueryMaxVlmSize
        ]

        con_parser = parser.add_parser(
            Commands.CONTROLLER,
            aliases=["c"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Controller subcommands")

        con_subp = con_parser.add_subparsers(
            title="Controller commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # Controller - get props
        c_ctrl_props = con_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description='Print current controller config properties.')
        c_ctrl_props.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        c_ctrl_props.set_defaults(func=self.cmd_print_controller_props)

        #  controller - set props
        c_set_ctrl_props = con_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Set a controller config property.')
        Commands.add_parser_keyvalue(c_set_ctrl_props, "controller")
        c_set_ctrl_props.set_defaults(func=self.set_props)

        c_drbd_opts = con_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description=DrbdOptions.description("drbd")
        )
        DrbdOptions.add_arguments(c_drbd_opts, self.OBJECT_NAME)
        c_drbd_opts.set_defaults(func=self.cmd_controller_drbd_opts)

        # Controller - version
        c_shutdown = con_subp.add_parser(
            Commands.Subcommands.Version.LONG,
            aliases=[Commands.Subcommands.Version.SHORT],
            description='Prints the linstor controller version'
        )
        c_shutdown.set_defaults(func=self.cmd_version)

        p_query_max_vlm_size = con_subp.add_parser(
            Commands.Subcommands.QueryMaxVlmSize.LONG,
            aliases=[Commands.Subcommands.QueryMaxVlmSize.SHORT],
            description='Queries the controller for storage pools maximum volume size.')
        p_query_max_vlm_size.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_query_max_vlm_size.add_argument(
            '--storage-pool', '-s',
            type=str,
            help="Storage pool name to query.").completer = self.storage_pool_dfn_completer
        p_query_max_vlm_size.add_argument(
            '--do-not-place-with',
            type=str,
            nargs='+',
            metavar="RESOURCE_NAME",
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = self.resource_completer
        p_query_max_vlm_size.add_argument(
            '--do-not-place-with-regex',
            type=str,
            metavar="RESOURCE_REGEX",
            help='Try to avoid nodes that already have a resource ' +
                 'deployed whos name is matching the given regular expression.'
        )
        p_query_max_vlm_size.add_argument(
            '--replicas-on-same',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with the same given auxiliary node property values.'
        )
        p_query_max_vlm_size.add_argument(
            '--replicas-on-different',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with a different value for the given auxiliary node property.'
        )
        p_query_max_vlm_size.add_argument(
            'replica_count',
            type=int,
            metavar="REPLICA_COUNT",
            help='The least amount of replicas.'
        )
        p_query_max_vlm_size.set_defaults(func=self.query_max_volume_size)

        self.check_subcommands(con_subp, subcmds)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            result.append(lstmsg.properties)
        return result

    def cmd_print_controller_props(self, args):
        lstmsg = self._linstor.controller_props()

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        props = Commands.parse_key_value_pairs([args.key + '=' + args.value])

        replies = []
        for prop_key, prop_value in props['pairs'].items():
            replies.extend(self._linstor.controller_set_prop(prop_key, prop_value))
        for prop_key in props['delete']:
            replies.extend(self._linstor.controller_del_prop(prop_key))

        return self.handle_replies(args, replies)

    def cmd_controller_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = []
        for prop, val in mod_props.items():
            replies.extend(self._linstor.controller_set_prop(prop, val))

        for delkey in del_props:
            replies.extend(self._linstor.controller_del_prop(delkey))

        return self.handle_replies(args, replies)

    def cmd_version(self, args):
        controller_info = self.get_linstorapi().controller_info()
        if controller_info:
            version_info = controller_info.split(',')
            if args.machine_readable:
                print(json.dumps(self.get_linstorapi().controller_version().data(args.output_version)))
            else:
                print("linstor controller " + version_info[2] + "; GIT-hash: " + version_info[3])

    def _show_query_max_volume(self, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("StoragePool")
        tbl.add_column("MaxVolumeSize", just_txt='>')
        tbl.add_column("Provisioning")
        tbl.add_column("Nodes")

        def limited_string(obj_list):
            limit = 40
            s = ""
            list_length = len(obj_list)
            for i in range(0, len(obj_list)):
                obj = obj_list[i]
                s += obj + (", " if i != list_length - 1 else "")
                if len(s) > limit:
                    s = s[:limit-3] + "..."

            return s

        storage_pool_dfns = self.get_linstorapi().storage_pool_dfn_list()[0].storage_pool_definitions

        for candidate in lstmsg.candidates:
            max_vlm_size = SizeCalc.approximate_size_string(candidate.max_volume_size)

            storage_pool_props = [x for x in storage_pool_dfns if x.name == candidate.storage_pool][0].properties
            max_oversubscription_ratio_props = \
                [x for x in storage_pool_props if x.key == KEY_STOR_POOL_DFN_MAX_OVERSUBSCRIPTION_RATIO]
            max_oversubscription_ratio_prop = max_oversubscription_ratio_props[0].value \
                if max_oversubscription_ratio_props \
                else lstmsg.default_max_oversubscription_ratio
            max_oversubscription_ratio = float(max_oversubscription_ratio_prop)

            tbl.add_row([
                candidate.storage_pool,
                max_vlm_size,
                "Thin, oversubscription ratio " + str(max_oversubscription_ratio) if candidate.all_thin else "Thick",
                limited_string(candidate.node_names)
            ])
        tbl.show()

    def query_max_volume_size(self, args):
        replies = self.get_linstorapi().storage_pool_dfn_max_vlm_sizes(
            args.replica_count,
            args.storage_pool,
            args.do_not_place_with,
            args.do_not_place_with_regex,
            [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_same],
            [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_different]
        )

        api_responses = self.get_linstorapi().filter_api_call_response(replies)
        if api_responses:
            return self.handle_replies(args, api_responses)

        return self.output_list(args, replies, self._show_query_max_volume)
