import linstor_client.argparse.argparse as argparse
import getpass
import json
import re
import sys
from datetime import datetime, timedelta

import linstor
from linstor.sharedconsts import NAMESPC_AUXILIARY
from linstor.properties import properties
from linstor import SizeCalc
import linstor_client
from linstor_client.utils import LinstorClientError, Output
from linstor_client.consts import ExitCode, Color


class ArgumentError(Exception):
    def __init__(self, msg):
        self._msg = msg

    @property
    def message(self):
        return self._msg


class DefaultState(object):
    @property
    def name(self):
        return 'default'

    @property
    def prompt(self):
        return 'LINSTOR'

    @property
    def terminate_on_error(self):
        return False


class Commands(object):
    CONTROLLER = 'controller'
    CRYPT = 'encryption'
    DMMIGRATE = 'dm-migrate'
    EXIT = 'exit'
    GEN_ZSH_COMPLETER = 'gen-zsh-completer'
    HELP = 'help'
    INTERACTIVE = 'interactive'
    LIST_COMMANDS = 'list-commands'
    NODE = 'node'
    RESOURCE = 'resource'
    VOLUME = 'volume'
    RESOURCE_CONN = 'resource-connection'
    RESOURCE_DEF = 'resource-definition'
    RESOURCE_GRP = 'resource-group'
    VOLUME_GRP = 'volume-group'
    ERROR_REPORTS = 'error-reports'
    STORAGE_POOL = 'storage-pool'
    STORAGE_POOL_DEF = 'storage-pool-definition'
    VOLUME_DEF = 'volume-definition'
    SNAPSHOT = 'snapshot'
    DRBD_PROXY = 'drbd-proxy'
    PHYSICAL_STORAGE = 'physical-storage'

    MainList = [
        CONTROLLER,
        CRYPT,
        HELP,
        INTERACTIVE,
        LIST_COMMANDS,
        NODE,
        RESOURCE_GRP,
        VOLUME_GRP,
        RESOURCE,
        RESOURCE_CONN,
        RESOURCE_DEF,
        ERROR_REPORTS,
        STORAGE_POOL,
        STORAGE_POOL_DEF,
        VOLUME,
        VOLUME_DEF,
        SNAPSHOT,
        DRBD_PROXY
    ]
    Hidden = [
        DMMIGRATE,
        EXIT,
        GEN_ZSH_COMPLETER,
        PHYSICAL_STORAGE
    ]

    def __init__(self):
        self._linstor = None  # type: linstor.Linstor
        # _linstor_completer is just here as a cache for completer calls
        self._linstor_completer = None  # type: linstor.Linstor

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

        class CreateDevicePool(object):
            LONG = "create-device-pool"
            SHORT = "cdp"

        class Modify(object):
            LONG = "modify"
            SHORT = "m"

        class Interface(object):
            LONG = "interface"
            SHORT = "i"

        class Info(object):
            LONG = "info"
            SHORT = "info"

        class CreateDef(object):
            LONG = "create-definition"
            SHORT = "cd"

        class Delete(object):
            LONG = "delete"
            SHORT = "d"

        class Lost(object):
            LONG = "lost"
            SHORT = "lo"

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

        class Resource(object):
            LONG = "resource"
            SHORT = "r"

        class VolumeDefinition(object):
            LONG = "volume-definition"
            SHORT = "vd"

        class Restore(object):
            LONG = "restore"
            SHORT = "rst"

        class SetSize(object):
            LONG = "set-size"
            SHORT = "size"

        class QueryMaxVlmSize(object):
            LONG = "query-max-volume-size"
            SHORT = "qmvs"

        class ToggleDisk(object):
            LONG = "toggle-disk"
            SHORT = "td"

        class CreateTransactional(object):
            LONG = "create-transactional"
            SHORT = "ct"

        class TransactionBegin(object):
            LONG = "begin"
            SHORT = "b"

        class TransactionAbort(object):
            LONG = "abort"
            SHORT = "a"

        class TransactionCommit(object):
            LONG = "commit"
            SHORT = "c"

        class Version(object):
            LONG = "version"
            SHORT = "v"

        class Spawn(object):
            LONG = "spawn-resources"
            SHORT = "spawn"

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
                for sub in sorted(subcommands, key=lambda x:x.LONG)])

    @classmethod
    def check_subcommands(cls, subp, subcmds):
        parser_keys = set(subp.choices.keys())
        subcmd_keys = set([key for subcmd in subcmds for key in [subcmd.LONG, subcmd.SHORT]])
        assert parser_keys == subcmd_keys, "not all subcommands are defined:\n"\
                                           + str(parser_keys) + "\n" + str(subcmd_keys)
        subp.metavar = "{%s}" % ", ".join(sorted([x.LONG for x in subcmds]))

    @classmethod
    def handle_replies(cls, args, replies):
        rc = ExitCode.OK
        if args and args.machine_readable:
            Commands._print_machine_readable(replies, args.output_version)
            return rc

        for call_resp in replies:
            current_rc = Output.handle_ret(
                call_resp,
                warn_as_error=args.warn_as_error,
                no_color=args.no_color
            )
            if current_rc != ExitCode.OK:
                rc = current_rc

        return rc

    @classmethod
    def get_replies_state(cls, replies):
        """

        :param list[ApiCallResponse] replies:
        :return:
        :rtype: (str, int)
        """
        errors = 0
        warnings = 0
        for reply in replies:
            if reply.is_error():
                errors += 1
            if reply.is_warning():
                warnings += 1
        if errors:
            return "Error", Color.RED
        elif warnings:
            return "Warning", Color.YELLOW

        return "Ok", Color.GREEN

    @classmethod
    def check_for_api_replies(cls, replies):
        return replies and isinstance(replies[0], linstor.ApiCallResponse)

    @classmethod
    def output_list(cls, args, replies, output_func, single_item=True):
        if isinstance(replies, list) and not args.curl:
            if cls.check_for_api_replies(replies):
                return cls.handle_replies(args, replies)

            if args.machine_readable:
                cls._print_machine_readable(replies, args.output_version)
            else:
                output_func(args, replies[0] if single_item else replies)
                api_replies = linstor.Linstor.filter_api_call_response(replies[1:])
                cls.handle_replies(args, api_replies)

        return ExitCode.OK

    @classmethod
    def output_props_list(cls, args, lstmsg, prop_show_func):
        if args.curl:
            return ExitCode.OK

        if cls.check_for_api_replies(lstmsg):
            return cls.handle_replies(args, lstmsg)
        lstmsg = lstmsg[0]

        result = prop_show_func(args, lstmsg)

        Commands._print_props(result, args)
        return ExitCode.OK

    @classmethod
    def _to_json(cls, data):
        return json.dumps(data, indent=2)

    @classmethod
    def _print_machine_readable(cls, data, output_version):
        """
        serializes the given protobuf data and prints to stdout.
        """
        assert(isinstance(data, list))
        if output_version == 'v0':
            s = json.dumps([x.data_v0 for x in data], indent=2)
        elif output_version == 'v1':
            s = json.dumps([x.data_v1 for x in data], indent=2)

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
                help='\n'.join(["'" + x['key'] + "': " + x['info'].replace("%", "%%") for x in props if 'info' in x])
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
            s = ''
            if prop_list_map:
                d = [[{"key": x, "value": prop_list_map[0][x]} for x in prop_list_map[0]]]
                s = json.dumps(d, indent=2)
            print(s)
            return None

        property_map_count = len(prop_list_map)
        if property_map_count == 0:
            print(Output.color_str("No property map found for this entry.", Color.YELLOW, args.no_color))
            return None

        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("Key")
        tbl.add_column("Value")

        if property_map_count > 0:
            prop_map = prop_list_map[0]
            for p in sorted(prop_map.keys()):
                tbl.add_row([p, prop_map[p]])

        tbl.show()

        if property_map_count > 1:
            print(Output.color_str("Unexpected additional property data, ignoring.", Color.YELLOW, args.no_color))

    @classmethod
    def get_allowed_props(cls, objname):
        return [x for x in properties[objname] if not x.get('internal', False)] if objname in properties else []

    @classmethod
    def get_allowed_prop_keys(cls, objname):
        return [x['key'] for x in cls.get_allowed_props(objname)]

    @classmethod
    def _attach_aux_prop(cls, args):
        if args.aux:
            args.key = NAMESPC_AUXILIARY + '/' + args.key
        return args

    @classmethod
    def add_auto_select_argparse_arguments(cls, parser, use_place_count=False):
        parser.add_argument(
            '--storage-pool', '-s',
            type=str,
            help="Storage pool name to use.").completer = cls.storage_pool_dfn_completer
        if use_place_count:
            parser.add_argument(
                '--place-count',
                type=int,
                metavar="REPLICA_COUNT",
                help='Auto place a resource to a specified number of nodes'
            )
        else:
            parser.add_argument(
                '--auto-place',
                type=int,
                metavar="REPLICA_COUNT",
                help='Auto place a resource to a specified number of nodes'
            )
        parser.add_argument(
            '--do-not-place-with',
            type=str,
            nargs='+',
            metavar="RESOURCE_NAME",
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = cls.resource_completer
        parser.add_argument(
            '--do-not-place-with-regex',
            type=str,
            metavar="RESOURCE_REGEX",
            help='Try to avoid nodes that already have a resource ' +
                 'deployed whos name is matching the given regular expression.'
        )
        parser.add_argument(
            '--replicas-on-same',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with the same given auxiliary node property values.'
        )
        parser.add_argument(
            '--replicas-on-different',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with a different value for the given auxiliary node property.'
        )
        parser.add_argument(
            '--diskless-on-remaining',
            action="store_true",
            default=None,
            help='Will add a diskless resource on all non replica nodes.'
        )
        parser.add_argument(
            '-l', '--layer-list',
            type=cls.layer_data_check,
            help="Comma separated layer list, order is from left to right top-down "
                 "This means the top most layer is on the left. "
                 "Possible layers are: " + ",".join(linstor.Linstor.layer_list()))
        parser.add_argument(
            '-p', '--providers',
            type=cls.provider_check,
            help="Comma separated providers list. Only storage pools with the given provider kind "
                 "are considered as auto-place target. "
                 "Possible providers are: " + ",".join(linstor.Linstor.provider_list()))

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

    def get_linstorapi(self, **kwargs):
        if self._linstor:
            return self._linstor

        if self._linstor_completer:
            return self._linstor_completer

        # TODO also read config overrides
        servers = ['linstor://localhost']
        if 'parsed_args' in kwargs:
            cliargs = kwargs['parsed_args']
            servers = linstor.MultiLinstor.controller_uri_list(cliargs.controllers)
        if not servers:
            return None

        self._linstor_completer = linstor.Linstor(servers[0])
        self._linstor_completer.connect()
        return self._linstor_completer

    def node_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()

        lstmsg = lapi.node_list()[0]  # type: linstor.responses.NodeListResponse
        if lstmsg:
            possible = {x.name for x in lstmsg.nodes}

            if prefix:
                return {node for node in possible if node.startswith(prefix)}

        return possible

    @classmethod
    def find_node(cls, node_list, node_name):
        """
        Searches the node list for a given node name.

        :param node_list: a node list proto object
        :param node_name: name of the node to find
        :return: The found node proto object or None if not found
        """
        if node_list:
            for n in node_list.nodes:
                if n.name == node_name:
                    return n
        return None

    def netif_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.node_list()[0]  # type: linstor.responses.NodeListResponse

        node = self.find_node(lstmsg, kwargs['parsed_args'].node_name)
        if node:
            for netif in node.net_interfaces:
                possible.add(netif.name)

            if prefix:
                return [netif for netif in possible if netif.startswith(prefix)]

        return possible

    def storage_pool_dfn_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.storage_pool_dfn_list()[0]  # type: linstor.responses.StoragePoolDefinitionResponse

        if lstmsg:
            for storpool_dfn in lstmsg.storage_pool_definitions:
                possible.add(storpool_dfn.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    def storage_pool_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.storage_pool_list()[0]  # type: linstor.responses.StoragePoolListResponse

        if lstmsg:
            for storpool in lstmsg.storage_pools:
                possible.add(storpool.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    def resource_dfn_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.resource_dfn_list(
            query_volume_definitions=False
        )[0]  # type: linstor.responses.ResourceDefinitionResponse

        if lstmsg:
            for rsc_dfn in lstmsg.resource_definitions:
                possible.add(rsc_dfn.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    def resource_grp_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        try:
            lstmsg = lapi.resource_group_list_raise()  # type: linstor.responses.ResourceGroupResponse

            if lstmsg:
                for rsc_grp in lstmsg.resource_groups:
                    possible.add(rsc_grp.name)

                if prefix:
                    return [res for res in possible if res.startswith(prefix)]
        except linstor.LinstorError:
            pass

        return possible

    def resource_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        lstmsg = lapi.resource_list()[0]  # type: linstor.responses.ResourceResponse

        if lstmsg:
            for rsc in lstmsg.resources:
                possible.add(rsc.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    @classmethod
    def layer_data_check(cls, layer_data):
        """
        Checks and converts the comma separated layer names to a list.

        :param str layer_data:
        :return: List of layer names
        :rtype: list[str]
        """
        layer_list = []
        for layer in layer_data.split(','):
            if layer.lower() not in linstor.Linstor.layer_list():
                raise argparse.ArgumentTypeError('Layer name "{lay}" not valid'.format(lay=layer))
            layer_list.append(layer)
        return layer_list

    @classmethod
    def provider_check(cls, providers):
        """
        Checks and converts the comma separated providers to a list.

        :param str providers:
        :return: List of provider names
        :rtype list[str]
        """
        provider_list = []
        for provider in providers.split(","):
            if provider.upper() not in linstor.Linstor.provider_list():
                raise argparse.ArgumentTypeError('Provider "{prov}" not valid'.format(prov=provider))
            provider_list.append(provider)
        return provider_list

    @classmethod
    def parse_size_str(cls, size_str, default_unit="GiB"):
        if size_str is None:
            return None
        m = re.match(r'(\d+)(\D*)', size_str)

        size = 0
        try:
            size = int(m.group(1))
        except AttributeError:
            sys.stderr.write('Size is not a valid number\n')
            sys.exit(ExitCode.ARGPARSE_ERROR)

        unit_str = m.group(2)
        if unit_str == "":
            unit_str = default_unit
        try:
            _, unit = SizeCalc.UNITS_MAP[unit_str.lower()]
        except KeyError:
            sys.stderr.write('"%s" is not a valid unit!\n' % unit_str)
            sys.stderr.write('Valid units: %s\n' % SizeCalc.UNITS_LIST_STR)
            sys.exit(ExitCode.ARGPARSE_ERROR)

        _, unit = SizeCalc.UNITS_MAP[unit_str.lower()]

        if unit != SizeCalc.UNIT_KiB:
            size = SizeCalc.convert_round_up(size, unit,
                                             SizeCalc.UNIT_KiB)

        return size


class MiscCommands(Commands):
    def __init__(self):
        super(MiscCommands, self).__init__()

    def setup_commands(self, parser):
        # Enryption subcommands
        crypt_subcmds = [
            Commands.Subcommands.EnterPassphrase,
            Commands.Subcommands.CreatePassphrase,
            Commands.Subcommands.ModifyPassphrase,
        ]
        crypt_parser = parser.add_parser(
            Commands.CRYPT,
            aliases=["e"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Encryption subcommands")

        crypt_subp = crypt_parser.add_subparsers(
            title="Encryption commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(crypt_subcmds))

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

        self.check_subcommands(crypt_subp, crypt_subcmds)

        # Error subcommands
        error_subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.Show
        ]
        error_parser = parser.add_parser(
            Commands.ERROR_REPORTS,
            aliases=["err"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Error report subcommands")

        error_subp = error_parser.add_subparsers(
            title="Error report commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(error_subcmds)
        )

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

        self.check_subcommands(error_subp, error_subcmds)

    @staticmethod
    def _summarize_api_call_responses(responses):
        return "; ".join([response.message for response in responses])

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

    @classmethod
    def show_error_report_list(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_header(linstor_client.TableHeader("Nr.", alignment_text=linstor_client.TableHeader.ALIGN_RIGHT))
        tbl.add_header(linstor_client.TableHeader("Id"))
        tbl.add_header(linstor_client.TableHeader("Datetime"))
        tbl.add_header(linstor_client.TableHeader("Node"))

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
            m = re.match(r'(\d+\W*d)?(\d+\W*h)?', since)
            if m:
                since_dt = datetime.now()
                if m.group(1):
                    since_dt -= timedelta(days=int(m.group(1)[:-1]))
                if m.group(2):
                    since_dt -= timedelta(hours=int(m.group(2)[:-1]))
            else:
                raise LinstorClientError(
                    "Unable to parse since string: '{s_str}'. e.g.: 1d10h or 3h'".format(s_str=since),
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
            print(Output.utf8(error.text))

    def cmd_error_report(self, args):
        lstmsg = self._linstor.error_report_list(with_content=True, ids=args.report_id)
        return self.output_list(args, lstmsg, self.show_error_report, single_item=False)
