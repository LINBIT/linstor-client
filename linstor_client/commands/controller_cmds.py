import json
import argparse
import textwrap

import linstor
import linstor_client
from linstor import LogLevelEnum, ApiCallResponse
from linstor_client.commands import Commands, DrbdOptions
from linstor.config import Config, ConfigFileLevel


class ControllerCommands(Commands):
    _command_name = Commands.CONTROLLER
    _command_aliases = ["c"]
    _command_description = "Controller subcommands"

    OBJECT_NAME = 'controller'

    _auth_token_headers = [
        linstor_client.TableHeader("ID"),
        linstor_client.TableHeader("Description"),
        linstor_client.TableHeader("Created"),
        linstor_client.TableHeader("Active"),
        linstor_client.TableHeader("UserToken"),
        linstor_client.TableHeader("IpFilter"),
        linstor_client.TableHeader("Expires"),
    ]

    def __init__(self):
        super(ControllerCommands, self).__init__()

    def setup_commands(self, parser):
        # Controller commands
        subcmds = [
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions,
            Commands.Subcommands.Version,
            Commands.Subcommands.QueryMaxVlmSize,
            Commands.Subcommands.Which,
            Commands.Subcommands.BackupDb,
            Commands.Subcommands.ExportDb,
            Commands.Subcommands.LogLevel,
            Commands.Subcommands.Auth,
        ]

        con_parser = parser.add_parser(
            self._command_name,
            aliases=self._command_aliases,
            formatter_class=argparse.RawTextHelpFormatter,
            description=self._command_description)

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

        # Controller - set-log-level
        c_set_log_level = con_subp.add_parser(
            Commands.Subcommands.LogLevel.LONG,
            aliases=[Commands.Subcommands.LogLevel.SHORT],
            description="Sets the log level")
        c_set_log_level.add_argument('level',
                                     type=LogLevelEnum.check,
                                     choices=list(LogLevelEnum))
        c_set_log_level.add_argument('--library', '--lib',
                                     action='store_true',
                                     help='Modify the log level of external libraries instead of LINSTOR itself')
        c_set_log_level.add_argument('--global',
                                     action='store_true',
                                     dest='glob',  # "global" is a reserved keyword
                                     help='Set the log level for the controller and ALL satellites')
        c_set_log_level.set_defaults(func=self.cmd_controller_set_log_level)

        # Controller - version
        c_shutdown = con_subp.add_parser(
            Commands.Subcommands.Version.LONG,
            aliases=[Commands.Subcommands.Version.SHORT],
            description='Prints the LINSTOR controller version.'
        )
        c_shutdown.set_defaults(func=self.cmd_version)

        p_query_max_vlm_size = con_subp.add_parser(
            Commands.Subcommands.QueryMaxVlmSize.LONG,
            aliases=[Commands.Subcommands.QueryMaxVlmSize.SHORT],
            description='Queries the controller for the maximum volume size of storage pools, given a specified '
            'replica count.')
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
            help='Try to avoid nodes that already have a resource '
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
            '--x-replicas-on-different',
            nargs='*',
            metavar="AUX_PROPERTY",
            help='Accepts a list of pairs as argument. Example: "--x-replicas-on-different datacenter 2" will allow 2 '
            'replicas on nodes that have the same value for the property "Aux/datacenter"'
        )
        p_query_max_vlm_size.add_argument(
            'replica_count',
            type=int,
            metavar="REPLICA_COUNT",
            help='The least amount of replicas.'
        )
        p_query_max_vlm_size.set_defaults(func=self.query_max_volume_size)

        p_which_controller = con_subp.add_parser(
            Commands.Subcommands.Which.LONG,
            description='Shows controller currently used.')
        p_which_controller.set_defaults(func=self.which_controller)

        p_backup_db = con_subp.add_parser(
            Commands.Subcommands.BackupDb.LONG,
            aliases=[Commands.Subcommands.BackupDb.SHORT],
            description=f'DEPRECATED: Use "linstor {Commands.CONTROLLER} '
                        f'{Commands.Subcommands.ExportDb.LONG} [EXPORT_NAME]" instead'
        )
        p_backup_db.add_argument(
            'backup_name',
            metavar="BACKUP_NAME",
            help='Base name of the backup'
        )
        p_backup_db.set_defaults(func=self.backup_controller_db)

        p_export_db = con_subp.add_parser(
            Commands.Subcommands.ExportDb.LONG,
            aliases=[Commands.Subcommands.ExportDb.SHORT],
            description='Exports the database of the controller into a JSON format.'
        )
        p_export_db.add_argument(
            'export_name',
            metavar="EXPORT_NAME",
            nargs="?",
            help='Name of the backup'
        )
        p_export_db.set_defaults(func=self.export_controller_db)

        # Auth commands
        auth_subcmds = [
            Commands.Subcommands.Init,
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Modify,
            Commands.Subcommands.Delete
        ]

        auth_parser = con_subp.add_parser(
            Commands.Subcommands.Auth.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[Commands.Subcommands.Auth.SHORT],
            description="%s subcommands" % Commands.Subcommands.Auth.LONG)

        auth_subp = auth_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.Auth.LONG,
            metavar="",
            description=Commands.Subcommands.generate_desc(auth_subcmds))

        # init auth token
        p_init_auth_token = auth_subp.add_parser(
            Commands.Subcommands.Init.LONG,
            aliases=[Commands.Subcommands.Init.SHORT],
            description='Initializes auth token authentication on the controller.'
        )
        p_init_auth_token.add_argument(
            'token_description', help="Description for the initial auth token."
        )
        p_init_auth_token.add_argument(
            '--only-satellites',
            action="store_true",
            help="Only initialize auth for satellites, not for client connections."
        )
        p_init_auth_token.add_argument(
            '--no-https',
            action="store_true",
            help="Allow non-HTTPS connections with token authentication."
        )
        p_init_auth_token.add_argument(
            '--do-not-save-token',
            action="store_true",
            help="Don't save the new auth token to linstor-client configuration file."
        )
        p_init_auth_token.set_defaults(func=self.init_auth_token)

        # create auth token
        p_create_auth_token = auth_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a new auth token.'
        )
        p_create_auth_token.add_argument(
            'token_description', help="Name/Description of the new auth token."
        )
        p_create_auth_token.add_argument(
            '--ip-filter',
            type=str,
            help="IP filter to restrict token usage to specific IP addresses or ranges."
        )
        p_create_auth_token.add_argument(
            '--expires-at',
            type=str,
            help="Expiration date in ISO format (e.g. 2025-12-31)."
        )
        p_create_auth_token.add_argument(
            '--save-token',
            action="store_true",
            help="save the new auth token to linstor-client configuration file."
        )
        p_create_auth_token.set_defaults(func=self.create_auth_token)

        # list auth tokens
        auth_token_groupby = [h.name.lower() for h in self._auth_token_headers]
        p_list_auth_token = auth_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Lists all auth tokens.'
        )
        p_list_auth_token.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_list_auth_token.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=auth_token_groupby,
            type=str.lower,
            help='Group by specified column(s)'
        )
        p_list_auth_token.add_argument(
            '-a', '--all',
            action="store_true",
            help='Show all tokens including system/satellite tokens'
        )
        p_list_auth_token.set_defaults(func=self.list_auth_tokens)

        # modify auth token
        p_modify_auth_token = auth_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modifies an existing auth token.'
        )
        p_modify_auth_token.add_argument(
            'id',
            type=int,
            help="The auth token ID to modify."
        )
        p_modify_auth_token.add_argument(
            '--description',
            type=str,
            help="New description for the token."
        )
        p_modify_auth_token.add_argument(
            '--active',
            choices=['true', 'false'],
            help="Set token active or inactive."
        )
        p_modify_auth_token.add_argument(
            '--ip-filter',
            type=str,
            help="IP filter to restrict token usage to specific IP address, to unset specify empty string ''."
        )
        p_modify_auth_token.set_defaults(func=self.modify_auth_token)

        # delete auth token
        p_delete_auth_token = auth_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Deletes/revokes an auth token.'
        )
        p_delete_auth_token.add_argument(
            'id',
            type=int,
            help="The auth token ID to delete."
        )
        p_delete_auth_token.set_defaults(func=self.delete_auth_token)

        self.check_subcommands(auth_subp, auth_subcmds)
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
        props = Commands.parse_key_value_pairs([(args.key, args.value)])

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

    def cmd_controller_set_log_level(self, args):
        replies = self._linstor.controller_set_log_level(
            args.level,
            args.glob if args.glob else False,
            args.library if args.library else False)

        return self.handle_replies(args, replies)

    def cmd_version(self, args):
        controller_info = self.get_linstorapi().controller_info()
        if controller_info:
            version_info = controller_info.split(',')
            if args.machine_readable:
                print(json.dumps(self.get_linstorapi().controller_version().data(args.output_version)))
            else:
                print("linstor controller " + version_info[2] + "; GIT-hash: " + version_info[3])

    def query_max_volume_size(self, args):
        replies = self.get_linstorapi().storage_pool_dfn_max_vlm_sizes(
            args.replica_count,
            args.storage_pool,
            args.do_not_place_with,
            args.do_not_place_with_regex,
            [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_same],
            [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_different],
            self.prepare_argparse_dict_str_int(args.x_replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/')
        )

        api_responses = self.get_linstorapi().filter_api_call_response(replies)
        if api_responses:
            return self.handle_replies(args, api_responses)

        return self.output_list(args, replies, self._show_query_max_volume)

    def which_controller(self, args):
        ctrl_uri = self.get_linstorapi().controller_host()
        if args.machine_readable:
            print(json.dumps({"controller_uri": ctrl_uri}))
        else:
            print(ctrl_uri)

    def backup_controller_db(self, args):
        replies = self.get_linstorapi().controller_backupdb(args.backup_name)
        return self.handle_replies(args, replies)

    def export_controller_db(self, args):
        replies = self.get_linstorapi().controller_exportdb(args.export_name)
        return self.handle_replies(args, replies)

    def init_auth_token(self, args):
        replies = self.get_linstorapi().controller_init_auth_token(
            args.token_description,
            only_satellites=args.only_satellites,
            no_https=args.no_https
        )
        if not args.do_not_save_token and replies[0].is_success():
            Config.set_value("global", "auth-token", replies[0].object_refs["token"])
            print("Token saved to config file: " + ConfigFileLevel.USER.to_config_path())
        return self.handle_replies(args, replies)

    def create_auth_token(self, args):
        replies: list[ApiCallResponse] = self.get_linstorapi().controller_create_auth_token(
            args.token_description,
            ip_filter=args.ip_filter,
            expires_at=args.expires_at
        )
        if args.save_token and replies[0].is_success():
            Config.set_value("global", "auth-token", replies[0].object_refs["token"])
            print("Token saved to config file: " + ConfigFileLevel.USER.to_config_path())
        return self.handle_replies(args, replies)

    def list_auth_tokens(self, args):
        lstmsg = self.get_linstorapi().controller_list_auth_tokens()
        return self.output_list(args, lstmsg, self.show_auth_tokens, machine_readable_raw=True)

    def modify_auth_token(self, args):
        replies = self.get_linstorapi().controller_modify_auth_token(
            args.id,
            description=args.description,
            is_active=args.active.lower() == 'true' if args.active else None,
            ip_filter=args.ip_filter
        )
        return self.handle_replies(args, replies)

    def delete_auth_token(self, args):
        replies = self.get_linstorapi().controller_delete_auth_token(args.id)
        return self.handle_replies(args, replies)

    @classmethod
    def show_auth_tokens(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._auth_token_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else ["Created"])

        for token in lstmsg.auth_tokens:
            if not args.all and not token.is_user_token:
                continue
            tbl.add_row([
                token.id,
                textwrap.fill(token.description, width=80) if token.description else "",
                token.created_at.strftime("%Y-%m-%d %H:%M:%S") if token.created_at else "",
                "Yes" if token.is_active else "No",
                "Yes" if token.is_user_token else "No",
                token.ip_filter or "-",
                token.expires_at.strftime("%Y-%m-%d") if token.expires_at else "-"
            ])

        tbl.show()
