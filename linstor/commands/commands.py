import argparse
import getpass
import json
import os
import re
from datetime import datetime, timedelta

import linstor
import linstor.linstorapi as linstorapi
from linstor.sharedconsts import NAMESPC_AUXILIARY, EVENT_VOLUME_DISK_STATE, EVENT_RESOURCE_STATE, \
    EVENT_RESOURCE_DEPLOYMENT_STATE, EVENT_RESOURCE_DEFINITION_READY
from linstor.consts import ExitCode, KEY_LS_CONTROLLERS
from linstor.properties import properties
from linstor.protobuf_to_dict import protobuf_to_dict
from linstor.utils import LinstorClientError, Output


class ArgumentError(Exception):
    def __init__(self, msg):
        self._msg = msg

    @property
    def message(self):
        return self._msg


class Commands(object):
    CONTROLLER = 'controller'
    CRYPT = 'encryption'
    DMMIGRATE = 'dm-migrate'
    EXIT = 'exit'
    GEN_ZSH_COMPLETER = 'gen-zsh-completer'
    CREATE_WATCH = 'create-watch'
    HELP = 'help'
    INTERACTIVE = 'interactive'
    LIST_COMMANDS = 'list-commands'
    NODE = 'node'
    RESOURCE = 'resource'
    RESOURCE_DEF = 'resource-definition'
    ERROR_REPORTS = 'error-reports'
    STORAGE_POOL = 'storage-pool'
    STORAGE_POOL_DEF = 'storage-pool-definition'
    VOLUME_DEF = 'volume-definition'

    MainList = [
        CONTROLLER,
        CRYPT,
        HELP,
        INTERACTIVE,
        LIST_COMMANDS,
        NODE,
        RESOURCE,
        RESOURCE_DEF,
        ERROR_REPORTS,
        STORAGE_POOL,
        STORAGE_POOL_DEF,
        VOLUME_DEF
    ]
    Hidden = [
        DMMIGRATE,
        EXIT,
        GEN_ZSH_COMPLETER,
        CREATE_WATCH
    ]

    def __init__(self):
        self._linstor = None  # type: linstorapi.Linstor
        # _linstor_completer is just here as a cache for completer calls
        self._linstor_completer = None  # type: linstorapi.Linstor

    class Subcommands(object):

        class List(object):
            LONG = "list"
            SHORT = "l"

        class Show(object):
            LONG = "show"
            SHORT = "s"

        class ListProperties(object):
            LONG = "list-properties"
            SHORT = "lp"

        class ListVolumes(object):
            LONG = "list-volumes"
            SHORT = "lv"

        class Create(object):
            LONG = "create"
            SHORT = "c"

        class Modify(object):
            LONG = "modify"
            SHORT = "m"

        class Interface(object):
            LONG = "interface"
            SHORT = "i"

        class CreateDef(object):
            LONG = "create-definition"
            SHORT = "cd"

        class Delete(object):
            LONG = "delete"
            SHORT = "d"

        class SetProperty(object):
            LONG = "set-property"
            SHORT = "sp"

        class EnterPassphrase(object):
            LONG = "enter-passphrase"
            SHORT = "ep"

        class CreatePassphrase(object):
            LONG = "create-passphrase"
            SHORT = "cp"

        class ModifyPassphrase(object):
            LONG = "modify-passphrase"
            SHORT = "mp"

        class Shutdown(object):
            LONG = "shutdown"
            SHORT = "off"

        class Describe(object):
            LONG = "describe"
            SHORT = "dsc"

        class DrbdOptions(object):
            LONG = "drbd-options"
            SHORT = "opt"

        class DrbdPeerDeviceOptions(object):
            LONG = "drbd-peer-options"
            SHORT = "popt"

        @staticmethod
        def generate_desc(subcommands):
            """
            Generates help output based on subcommands.

            :param list[] subcommands: a list of subcommands to
                generate help text for
            :return a string of help output to be assigned to add_subparser
                description keyword argument
            """

            return "\n".join([
                " - {} ({})".format(sub.LONG, sub.SHORT)
                for sub in subcommands])

    @classmethod
    def handle_replies(cls, args, replies):
        rc = ExitCode.OK
        if args and args.machine_readable:
            Commands._print_machine_readable(replies)
            return rc

        for call_resp in replies:
            current_rc = Output.handle_ret(
                call_resp.proto_msg,
                warn_as_error=args.warn_as_error,
                no_color=args.no_color
            )
            if current_rc != ExitCode.OK:
                rc = current_rc

        return rc

    @classmethod
    def check_for_api_replies(cls, replies):
        return isinstance(replies[0], linstor.linstorapi.ApiCallResponse)

    @classmethod
    def output_list(cls, args, replies, output_func, single_item=True):
        if replies:
            if cls.check_for_api_replies(replies):
                return cls.handle_replies(args, replies)

            if args.machine_readable:
                cls._print_machine_readable(replies)
            else:
                output_func(args, replies[0].proto_msg if single_item else replies)

        return ExitCode.OK

    @classmethod
    def output_props_list(cls, args, lstmsg, prop_show_func):
        if cls.check_for_api_replies(lstmsg):
            return cls.handle_replies(args, lstmsg)
        lstmsg = lstmsg[0]

        result = prop_show_func(args, lstmsg.proto_msg)

        Commands._print_props(result, args)
        return ExitCode.OK

    @classmethod
    def _to_json(cls, data):
        return json.dumps(data, indent=2)

    @classmethod
    def _print_machine_readable(cls, data):
        """
        serializes the given protobuf data and prints to stdout.
        """
        assert(isinstance(data, list))
        d = [protobuf_to_dict(x.proto_msg) for x in data]
        s = cls._to_json(d)

        # try:
        #     s = ""
        #     from google.protobuf import json_format
        #     for x in data:
        #         s += json_format.MessageToJson(x, preserving_proto_field_name=True)
        # except ImportError as e:
        #     sys.stderr.write(
        #         "You are using a protobuf version prior to 2.7, which is needed for json output")
        #     return True
        print(s)
        return True

    @classmethod
    def parse_key_value_pairs(cls, kv_pairs):
        """
        Parses a key value pair pairs in an easier to use dict.
        If a key has no value it will be put on the delete list.

        :param list[str] kv_pairs: a list of key value pair strings. ['key=val', 'key2=val2']
        :return dict[str, str]:
        """
        pairs = {}
        delete = []
        for kv in kv_pairs:
            if '=' not in kv:
                raise LinstorClientError(
                    "KeyValueParseError: Key value '{kv}' pair does not contain a '='".format(kv=kv),
                    ExitCode.ARGPARSE_ERROR
                )
            key, value = kv.split('=', 1)
            if value:
                pairs[key] = value
            else:
                delete.append(key)
        return {
            'pairs': pairs,
            'delete': delete
        }

    @classmethod
    def add_parser_keyvalue(cls, parser, property_object=None):
        parser.add_argument('--aux', action="store_true", help="Property is an auxiliary user property.")
        if property_object:
            props = Commands.get_allowed_props(property_object)
            parser.add_argument(
                'key',
                help='; '.join([x['key'] + ': ' + x['info'] for x in props if 'info' in x])
            ).completer = Commands.get_allowed_prop_keys(property_object)
        else:
            parser.add_argument(
                'key',
                help='a property key that will reside in the auxiliary namespace.'
            )
        parser.add_argument(
            'value',
            nargs='?',
            default='',
            help='Value for the chosen property. If empty property will be removed.'
        )

    @classmethod
    def _print_props(cls, prop_list_map, args):
        """Print properties in machine or human readable format"""

        if args.machine_readable:
            d = [[protobuf_to_dict(y) for y in x] for x in prop_list_map]
            s = json.dumps(d, indent=2)
            print(s)
            return None

        for prop_map in prop_list_map:
            tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column("Key")
            tbl.add_column("Value")
            for p in prop_map:
                tbl.add_row([p.key, p.value])
            tbl.show()

    @classmethod
    def get_allowed_props(cls, objname):
        return [x for x in properties[objname] if not x.get('internal', False)] if objname in properties else []

    @classmethod
    def get_allowed_prop_keys(cls, objname):
        return [x['key'] for x in cls.get_allowed_props(objname)]

    def set_props(self, args):
        raise NotImplementedError('abstract')

    @classmethod
    def _attach_aux_prop(cls, args):
        if args.aux:
            args.key = NAMESPC_AUXILIARY + '/' + args.key
        return args

    @staticmethod
    def show_group_completer(lst, where):
        def completer(prefix, parsed_args, **kwargs):
            possible = lst
            opt = where
            if opt == "groupby":
                opt = parsed_args.groupby
            elif opt == "show":
                opt = parsed_args.show
            else:
                return possible

            if opt:
                possible = [i for i in lst if i not in opt]

            return possible
        return completer

    @staticmethod
    def controller_list(cmdl_args_controllers):
        cenv = os.environ.get(KEY_LS_CONTROLLERS, "") + ',' + cmdl_args_controllers

        servers = []
        # add linstor uri scheme
        for hp in cenv.split(','):
            if hp:
                if '://' in hp:
                    servers.append(hp)
                else:
                    servers.append("linstor://" + hp)
        return servers

    def get_linstorapi(self, **kwargs):
        if self._linstor:
            return self._linstor

        if self._linstor_completer:
            return self._linstor_completer

        # TODO also read config overrides
        servers = ['linstor://localhost']
        if 'parsed_args' in kwargs:
            cliargs = kwargs['parsed_args']
            servers = Commands.controller_list(cliargs.controllers)
        if not servers:
            return None

        self._linstor_completer = linstorapi.Linstor(servers[0])
        self._linstor_completer.connect()
        return self._linstor_completer

    def node_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()

        lstmsg = lapi.node_list()[0]
        if lstmsg:
            for node in lstmsg.proto_msg.nodes:
                possible.add(node.name)

            if prefix:
                return [node for node in possible if node.startswith(prefix)]

        return possible

    @classmethod
    def find_node(cls, proto_node_list, node_name):
        """
        Searches the node list for a given node name.

        :param proto_node_list: a node list proto object
        :param node_name: name of the node to find
        :return: The found node proto object or None if not found
        """
        if proto_node_list:
            for n in proto_node_list.nodes:
                if n.name == node_name:
                    return n
        return None

    def netif_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.node_list()[0]

        node = self.find_node(lstmsg.proto_msg, kwargs['parsed_args'].node_name)
        if node:
            for netif in node.net_interfaces:
                possible.add(netif.name)

            if prefix:
                return [netif for netif in possible if netif.startswith(prefix)]

        return possible

    def storage_pool_dfn_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.storage_pool_dfn_list()[0]

        if lstmsg:
            for storpool_dfn in lstmsg.proto_msg.stor_pool_dfns:
                possible.add(storpool_dfn.stor_pool_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    def storage_pool_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.storage_pool_list()[0]

        if lstmsg:
            for storpool in lstmsg.proto_msg.stor_pools:
                possible.add(storpool.stor_pool_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    def resource_dfn_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.resource_dfn_list()[0]

        if lstmsg:
            for rsc_dfn in lstmsg.proto_msg.rsc_dfns:
                possible.add(rsc_dfn.rsc_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    def resource_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.resource_list()[0]

        if lstmsg:
            for rsc in lstmsg.proto_msg.resources:
                possible.add(rsc.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible


class MiscCommands(Commands):
    def __init__(self):
        super(MiscCommands, self).__init__()

    def setup_commands(self, parser):
        # watch
        c_create_watch = parser.add_parser(
            Commands.CREATE_WATCH,
            aliases=[],
            description='Watch events'
        )
        c_create_watch.add_argument('--node-name', help='Name of the node').completer = self.node_completer
        c_create_watch.add_argument('--resource-name', help='Name of the resource').completer = self.resource_completer
        c_create_watch.add_argument('--volume-number', type=int, help='Volume number')
        c_create_watch.set_defaults(func=self.cmd_create_watch)

        # Enryption subcommands
        crypt_parser = parser.add_parser(
            Commands.CRYPT,
            aliases=["e"],
            formatter_class=argparse.RawTextHelpFormatter,
            help="Encryption subcommands")

        crypt_subp = crypt_parser.add_subparsers(
            title="Encryption commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(
                [
                    Commands.Subcommands.EnterPassphrase,
                    Commands.Subcommands.CreatePassphrase,
                    Commands.Subcommands.ModifyPassphrase,
                ]))

        c_crypt_enter_passphr = crypt_subp.add_parser(
            Commands.Subcommands.EnterPassphrase.LONG,
            aliases=[Commands.Subcommands.EnterPassphrase.SHORT],
            description='Enter the crypt passphrase.'
        )
        c_crypt_enter_passphr.add_argument(
            "-p", "--passphrase",
            help='Master passphrase to unlock.'
        )
        c_crypt_enter_passphr.set_defaults(func=self.cmd_crypt_enter_passphrase)

        c_crypt_create_passphr = crypt_subp.add_parser(
            Commands.Subcommands.CreatePassphrase.LONG,
            aliases=[Commands.Subcommands.CreatePassphrase.SHORT],
            description='Create a new crypt passphrase.'
        )
        c_crypt_create_passphr.add_argument(
            "-p", "--passphrase",
            help="Passphrase used for encryption."
        )
        c_crypt_create_passphr.set_defaults(func=self.cmd_crypt_create_passphrase)

        c_crypt_modify_passphr = crypt_subp.add_parser(
            Commands.Subcommands.ModifyPassphrase.LONG,
            aliases=[Commands.Subcommands.ModifyPassphrase.SHORT],
            description='Change the current passphrase.'
        )
        c_crypt_modify_passphr.add_argument(
            "--old-passphrase",
            help="Old passphrase used for encryption."
        )
        c_crypt_modify_passphr.add_argument(
            "--new-passphrase",
            help="New passphrase used for encryption."
        )
        c_crypt_modify_passphr.set_defaults(func=self.cmd_crypt_modify_passphrase)

        # Error subcommands
        error_parser = parser.add_parser(
            Commands.ERROR_REPORTS,
            aliases=["err"],
            formatter_class=argparse.RawTextHelpFormatter,
            help="Error report subcommands")

        error_subp = error_parser.add_subparsers(
            title="Error report commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(
                [
                    Commands.Subcommands.List,
                    Commands.Subcommands.Show
                ]))

        c_list_error_reports = error_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='List error reports.'
        )
        c_list_error_reports.add_argument('-s', '--since', help='Show errors since n days. e.g. "3days"')
        c_list_error_reports.add_argument('-t', '--to', help='Show errors to specified date. Format YYYY-MM-DD.')
        c_list_error_reports.add_argument(
            '-n',
            '--nodes',
            help='Only show error reports from these nodes.',
            nargs='+'
        )
        c_list_error_reports.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        c_list_error_reports.add_argument(
            '--report-id',
            nargs='+',
            help="Restrict to id's that begin with the given ones."
        )
        c_list_error_reports.set_defaults(func=self.cmd_list_error_reports)

        c_error_report = error_subp.add_parser(
            Commands.Subcommands.Show.LONG,
            aliases=[Commands.Subcommands.Show.SHORT],
            description='Output content of an error report.'
        )
        c_error_report.add_argument("report_id", nargs='+')
        c_error_report.set_defaults(func=self.cmd_error_report)

    def cmd_create_watch(self, args):
        def reply_handler(replies):
            create_watch_rc = self.handle_replies(args, replies)
            if create_watch_rc != ExitCode.OK:
                return create_watch_rc
            return None

        event_formatter_table = {
            EVENT_VOLUME_DISK_STATE: lambda event_data: "Disk state: " + event_data.disk_state,
            EVENT_RESOURCE_STATE: lambda event_data: "Resource ready: " + str(event_data.ready),
            EVENT_RESOURCE_DEPLOYMENT_STATE: lambda event_data:
                "Deployment state: " + event_data.responses[0].message_format,
            EVENT_RESOURCE_DEFINITION_READY: lambda event_data:
                "Resource definition; ready: " + str(event_data.ready_count) + ", error: " + str(event_data.error_count)
        }

        def event_handler(event_header, event_data):
            event_header_display = \
                event_header.event_name + \
                " [" + event_header.event_action + "]" + \
                " (" + event_header.node_name + \
                "/" + event_header.resource_name + \
                ("/" + str(event_header.volume_number) if event_header.HasField("volume_number") else "") + \
                ")"

            if event_data:
                event_formatter = event_formatter_table.get(event_header.event_name)
                if event_formatter is None:
                    print(event_header_display)
                else:
                    event_data_display = event_formatter(event_data)
                    print(event_header_display + " " + event_data_display)
            else:
                print(event_header_display)

        self._linstor.create_watch(reply_handler, event_handler,
                                   node_name=args.node_name,
                                   resource_name=args.resource_name,
                                   volume_number=args.volume_number)

    def cmd_crypt_enter_passphrase(self, args):
        if args.passphrase:
            passphrase = args.passphrase
        else:
            # read from keyboard
            passphrase = getpass.getpass("Passphrase: ")
        replies = self._linstor.crypt_enter_passphrase(passphrase)
        return self.handle_replies(args, replies)

    def cmd_crypt_create_passphrase(self, args):
        if args.passphrase:
            passphrase = args.passphrase
        else:
            # read from keyboard
            passphrase = getpass.getpass("Passphrase: ")
        replies = self._linstor.crypt_create_passphrase(passphrase)
        return self.handle_replies(args, replies)

    def cmd_crypt_modify_passphrase(self, args):
        if args.old_passphrase:
            old_passphrase = args.old_passphrase
        else:
            # read from keyboard
            old_passphrase = getpass.getpass("Old passphrase: ")

        if args.new_passphrase:
            new_passphrase = args.new_passphrase
        else:
            # read from keyboard
            new_passphrase = getpass.getpass("New passphrase: ")

        replies = self._linstor.crypt_modify_passphrase(old_passphrase, new_passphrase)
        return self.handle_replies(args, replies)

    def show_error_report_list(self, args, lstmsg):
        tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_header(linstor.TableHeader("Nr.", alignment_text=">"))
        tbl.add_header(linstor.TableHeader("Id"))
        tbl.add_header(linstor.TableHeader("Datetime"))
        tbl.add_header(linstor.TableHeader("Node"))

        i = 1
        for error in lstmsg:
            tbl.add_row([
                str(i),
                error.id,
                str(error.datetime)[:19],
                error.node_names
            ])
            i += 1
        tbl.show()

    def cmd_list_error_reports(self, args):
        since = args.since
        since_dt = None
        if since:
            m = re.match(r'(\d+)\W*d', since)
            if m:
                since_dt = datetime.now()
                since_dt -= timedelta(days=int(m.group(1)))
            else:
                raise LinstorClientError(
                    "Unable to parse since string: '{s_str}'. Use 'NUMdays'".format(s_str=since),
                    ExitCode.ARGPARSE_ERROR
                )

        to_dt = None
        if args.to:
            to_dt = datetime.strptime(args.to, '%Y-%m-%d')
            to_dt = to_dt.replace(hour=23, minute=59, second=59)

        lstmsg = self._linstor.error_report_list(nodes=args.nodes, since=since_dt, to=to_dt, ids=args.report_id)
        return self.output_list(args, lstmsg, self.show_error_report_list, single_item=False)

    def show_error_report(self, args, lstmsg):

        for error in lstmsg:
            print(error.text)

    def cmd_error_report(self, args):
        lstmsg = self._linstor.error_report_list(with_content=True, ids=args.report_id)
        return self.output_list(args, lstmsg, self.show_error_report, single_item=False)
