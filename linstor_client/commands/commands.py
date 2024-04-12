import linstor_client.argparse.argparse as argparse
import getpass
import json
import re
import sys
from datetime import datetime, timedelta

import linstor
import linstor.sharedconsts as apiconsts
from linstor.properties import properties
from linstor import SizeCalc, Config
import linstor_client
from linstor_client.utils import LinstorClientError, Output
from linstor_client.consts import ExitCode, Color
from linstor.sharedconsts import KEY_STOR_POOL_MAX_OVERSUBSCRIPTION_RATIO


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
    NODE_CONN = 'node-connection'
    RESOURCE = 'resource'
    VOLUME = 'volume'
    RESOURCE_CONN = 'resource-connection'
    RESOURCE_DEF = 'resource-definition'
    RESOURCE_GRP = 'resource-group'
    VOLUME_GRP = 'volume-group'
    ERROR_REPORTS = 'error-reports'
    STORAGE_POOL = 'storage-pool'
    VOLUME_DEF = 'volume-definition'
    SNAPSHOT = 'snapshot'
    DRBD_PROXY = 'drbd-proxy'
    PHYSICAL_STORAGE = 'physical-storage'
    SOS_REPORT = 'sos-report'
    SPACE_REPORTING = 'space-reporting'
    EXOS = "exos"
    ADVISE = "advise"
    BACKUP = "backup"
    REMOTE = "remote"
    FILE = "file"
    SCHEDULE = "schedule"
    KEY_VALUE_STORE = "key-value-store"

    MainList = [
        CONTROLLER,
        CRYPT,
        HELP,
        INTERACTIVE,
        LIST_COMMANDS,
        NODE,
        NODE_CONN,
        RESOURCE_GRP,
        VOLUME_GRP,
        RESOURCE,
        RESOURCE_CONN,
        RESOURCE_DEF,
        ERROR_REPORTS,
        STORAGE_POOL,
        VOLUME,
        VOLUME_DEF,
        SNAPSHOT,
        DRBD_PROXY,
        PHYSICAL_STORAGE,
        SOS_REPORT,
        SPACE_REPORTING,
        EXOS,
        ADVISE,
        BACKUP,
        REMOTE,
        FILE,
        SCHEDULE,
        KEY_VALUE_STORE
    ]
    Hidden = [
        DMMIGRATE,
        EXIT,
        GEN_ZSH_COMPLETER
    ]

    EFFECTIVE_PROPS_TYPES = {
        "SATELLITE": "C",
        "NODE": "N",
        "RESOURCE_DEFINITION": "RD",
        "RESOURCE": "R",
        "STORAGEPOOL": "SP"
    }

    def __init__(self):
        self._linstor = None  # type: Optional[linstor.Linstor]
        # _linstor_completer is just here as a cache for completer calls
        self._linstor_completer = None  # type: Optional[linstor.Linstor]

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

        class MakeAvailable(object):
            LONG = "make-available"
            SHORT = "mkavail"

        class AutoPlace(object):
            LONG = "auto-place"
            SHORT = "ap"

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

        class Evacuate(object):
            LONG = "evacuate"
            SHORT = "evac"

        class SetSize(object):
            LONG = "set-size"
            SHORT = "size"

        class QueryMaxVlmSize(object):
            LONG = "query-max-volume-size"
            SHORT = "qmvs"

        class QuerySizeInfo(object):
            LONG = "query-size-info"
            SHORT = "qsi"

        class ToggleDisk(object):
            LONG = "toggle-disk"
            SHORT = "td"

        class CreateTransactional(object):
            LONG = "create-transactional"
            SHORT = "ct"

        class Begin(object):
            LONG = "begin"
            SHORT = "b"

        class Abort(object):
            LONG = "abort"
            SHORT = "a"

        class Commit(object):
            LONG = "commit"
            SHORT = "c"

        class Version(object):
            LONG = "version"
            SHORT = "v"

        class Spawn(object):
            LONG = "spawn-resources"
            SHORT = "spawn"

        class Download(object):
            LONG = "download"
            SHORT = "dl"

        class Activate(object):
            LONG = "activate"
            SHORT = "act"

        class Deactivate(object):
            LONG = "deactivate"
            SHORT = "deact"

        class Rollback(object):
            LONG = "rollback"
            SHORT = "rb"

        class Ship(object):
            LONG = "ship"
            SHORT = "sh"

        class ShipList(object):
            LONG = "ship-list"
            SHORT = "shl"

        class Query(object):
            LONG = "query"
            SHORT = "qry"

        class Involved(object):
            LONG = "involved"
            SHORT = "inv"

        class Which(object):
            LONG = "which"
            SHORT = "which"

        class Clone(object):
            LONG = "clone"
            SHORT = "cln"

        class WaitSync(object):
            LONG = "wait-sync"
            SHORT = "ws"

        class Adjust(object):
            LONG = "adjust"
            SHORT = "adj"

        class Deploy(object):
            LONG = "deploy"
            SHORT = "dep"

        class Undeploy(object):
            LONG = "undeploy"
            SHORT = "und"

        class BackupDb(object):
            LONG = "backupdb"
            SHORT = "bakdb"

        class Enable(object):
            LONG = "enable"
            SHORT = "en"

        class Disable(object):
            LONG = "disable"
            SHORT = "dis"

        class Schedule(object):
            LONG = "schedule"
            SHORT = "sched"

        class LogLevel(object):
            LONG = "set-log-level"
            SHORT = "setloglevel"

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
                " - {} ({})".format(sub.LONG, sub.SHORT) if hasattr(sub, 'SHORT') else " - {}".format(sub.LONG)
                for sub in sorted(subcommands, key=lambda x: x.LONG)])

    @classmethod
    def check_subcommands(cls, subp, subcmds):
        parser_keys = set(subp.choices.keys())
        subcmd_keys = set()
        for subcmd in subcmds:
            subcmd_keys.add(subcmd.LONG)
            if hasattr(subcmd, 'SHORT'):
                subcmd_keys.add(subcmd.SHORT)
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
    def output_list(cls, args, replies, output_func, single_item=True, machine_readable_raw=False):
        if isinstance(replies, list) and not args.curl:
            if cls.check_for_api_replies(replies):
                return cls.handle_replies(args, replies)

            if args.machine_readable:
                cls._print_machine_readable(replies, args.output_version, machine_readable_raw)
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
    def _merge_config_argparseargs(cls, section, args):
        for k, v in section.items():
            safe_key = k.replace("-", "_")
            try:
                current = getattr(args, safe_key)
            except AttributeError:
                current = None
            config_val = json.loads(v)
            if isinstance(current, list):
                setattr(args, safe_key, current + config_val)
            else:
                setattr(args, safe_key, config_val)
        return args

    @classmethod
    def merge_config_args(cls, section, args):
        if not args.disable_config:
            list_config = Config.get_section(section)
            return cls._merge_config_argparseargs(list_config, args)
        return args

    @classmethod
    def _to_json(cls, data):
        return json.dumps(data, indent=2)

    @classmethod
    def _print_machine_readable(cls, data, output_version, single_item=False):
        """
        serializes the given protobuf data and prints to stdout.
        """
        assert (isinstance(data, list))
        output = None
        if output_version == 'v0':
            if single_item:
                output = data[0].data_v0
            else:
                output = [x.data_v0 for x in data]
        elif output_version == 'v1':
            if single_item:
                output = data[0].data_v1
            else:
                output = [x.data_v1 for x in data]

        s = cls._to_json(output)
        print(s)
        return True

    @classmethod
    def parse_key_value_pairs(cls, kv_pairs):
        """
        Parses a key value pair pairs in an easier to use dict.
        If a key has no value it will be put on the delete list.

        :param list[Tuple[str,str]] kv_pairs: a list of key value pair strings. [('key','val'), ('key2','val2')]
        :return: dict with key 'pairs': [key: value] and 'delete': [array]
        :rtype Dict[str, str]
        """
        pairs = {}
        delete = []
        for kv in kv_pairs:
            key, value = kv
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
            help_list = []
            for prop in props:
                prop_help = "'" + prop['key'] + "': " + prop.get('info', '-').replace("%", "%%")
                if 'values' in prop:
                    prop_help += '; Allowed: ' + str(prop['values'])
                help_list.append(prop_help)
            parser.add_argument(
                'key',
                help='\n'.join(help_list)
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
    def _append_show_props_hdr(cls, tbl, args_props):
        """

        :param linstor_client.Table tbl: list of table header to add to
        :param list[str] args_props: show prop arguments
        :return: list of plain property names for the object
        :rtype: list[str]
        """
        show_props = []
        for sprop in args_props:
            show_prop_split = sprop.split("=")
            prop = show_prop_split[0]
            col_name = show_prop_split[1] if len(show_prop_split) > 1 else prop
            show_props.append(prop)
            tbl.add_header(linstor_client.TableHeader(col_name))
        return show_props

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
            args.key = apiconsts.NAMESPC_AUXILIARY + '/' + args.key
        return args

    @classmethod
    def add_auto_select_argparse_arguments(cls, parser, use_place_count=False, use_p_for_providers=True):
        parser.add_argument(
            '--storage-pool', '-s',
            type=str,
            nargs='*',
            help="Storage pool name to use, set empty string to remove.").completer = cls.storage_pool_dfn_completer
        parser.add_argument(
            '--diskless-storage-pool',
            type=str,
            nargs='*',
            help="Diskless storage pool name to use, set empty string to \
                remove.").completer = cls.storage_pool_dfn_completer
        if use_place_count:
            parser.add_argument(
                '--place-count',
                type=str,
                metavar="REPLICA_COUNT",
                help='Auto place a resource to a specified number of nodes, set 0 to remove'
            )
        else:
            parser.add_argument(
                '--auto-place',
                type=str,
                metavar="REPLICA_COUNT",
                help='Auto place a resource to a specified number of nodes'
            )
        parser.add_argument(
            '--do-not-place-with',
            type=str,
            nargs='*',
            metavar="RESOURCE_NAME",
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = cls.resource_completer
        parser.add_argument(
            '--do-not-place-with-regex',
            nargs='?',
            type=str,
            metavar="RESOURCE_REGEX",
            help="Try to avoid nodes that already have a resource "
                 "deployed who's name is matching the given regular expression."
        )
        parser.add_argument(
            '--replicas-on-same',
            nargs='*',
            metavar="AUX_PROPERTY",
            help='Tries to place resources on nodes with the same given auxiliary node property values.'
        )
        parser.add_argument(
            '--replicas-on-different',
            nargs='*',
            metavar="AUX_PROPERTY",
            help='Tries to place resources on nodes with a different value for the given auxiliary node property.'
        )
        parser.add_argument(
            '--diskless-on-remaining',
            nargs='?',
            default=argparse.SUPPRESS,
            help='Will add a diskless resource on all non replica nodes. '
                 'Setting can be unset if "false" is given as argument'
        )
        parser.add_argument(
            '-l', '--layer-list',
            type=cls.layer_data_check,
            help="Comma separated layer list, order is from left to right top-down "
                 "This means the top most layer is on the left. "
                 "Possible layers are: " + ",".join(linstor.Linstor.layer_list()))
        parser.add_argument(
            '--providers', '-p' if use_p_for_providers else '--prov',
            type=cls.provider_check,
            help="Comma separated providers list. Only storage pools with the given provider kind "
                 "are considered as auto-place target. "
                 "Possible providers are: " + ",".join(linstor.Linstor.provider_list()))

    @classmethod
    def parse_place_count_args(cls, args, use_place_count=False):
        """

        :param args: argparse arguments
        :param bool use_place_count: if replica count is named `place-count` or `auto-place`
        :return: Tuple with (place_count, additional_place_count, diskless_type)
        """
        if args.drbd_diskless:
            diskless_type = apiconsts.FLAG_DRBD_DISKLESS
        elif args.nvme_initiator:
            diskless_type = apiconsts.FLAG_NVME_INITIATOR
        elif hasattr(args, "diskless") and args.diskless:
            diskless_type = apiconsts.FLAG_DISKLESS
        else:
            diskless_type = None

        place_count_arg = args.place_count if use_place_count else args.auto_place

        additional_place_count = None
        place_count = None

        if place_count_arg:
            if place_count_arg.startswith("+"):
                additional_place_count = int(place_count_arg[1:])
            elif place_count_arg in ['max', 'all']:
                place_count = -1
                additional_place_count = 0
            else:
                place_count = int(place_count_arg)

        return place_count, additional_place_count, diskless_type

    @classmethod
    def parse_diskless_on_remaining(cls, args):
        if hasattr(args, 'diskless_on_remaining'):
            if args.diskless_on_remaining is None:
                return True
            else:
                return args.diskless_on_remaining.lower() not in ['false']
        return None

    @staticmethod
    def parse_time_str(timestr):
        """
        Parses a day and hour string to a datetime from the current time.
        e.g.: `1d10h or 3h`
        :param str timestr: string to parse
        :return: datetime of the timestr
        :rtype: datetime
        """
        m = re.match(r'(\d+\W*d)?(\d+\W*h)?', timestr)
        if m:
            since_dt = datetime.now()
            if m.group(1):
                since_dt -= timedelta(days=int(m.group(1)[:-1]))
            if m.group(2):
                since_dt -= timedelta(hours=int(m.group(2)[:-1]))
            return since_dt
        else:
            raise LinstorClientError(
                "Unable to parse since string: '{s_str}'. e.g.: 1d10h or 3h'".format(s_str=timestr),
                ExitCode.ARGPARSE_ERROR
            )

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

    def remote_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = []
        lstmsg = lapi.remote_list()[0]  # type: linstor.responses.RemoteListResponse

        if lstmsg:
            possible += [x.remote_name for x in lstmsg.s3_remotes]
            possible += [x.remote_name for x in lstmsg.linstor_remotes]

            if prefix:
                return [res for res in set(possible) if res.startswith(prefix)]

        return set(possible)

    def schedule_completer(self, prefix, **kwargs):
        lapi = self.get_linstorapi(**kwargs)
        possible = set()
        sched_resp = lapi.schedule_list()  # type: linstor.responses.ScheduleListResponse

        for schedule in sched_resp.schedules:
            possible.add(schedule.schedule_name)

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
        if layer_data is None:
            return None

        if not layer_data:
            return []

        layer_list = []
        for layer in layer_data.split(','):
            if layer.lower() not in linstor.Linstor.layer_list():
                raise ArgumentError('Layer name "{lay}" not valid'.format(lay=layer))
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
        if providers is None:
            return None

        if not providers:
            return []

        provider_list = []
        for provider in providers.split(","):
            if provider.upper() not in linstor.Linstor.provider_list():
                raise ArgumentError('Provider "{prov}" not valid'.format(prov=provider))
            provider_list.append(provider)
        return provider_list

    @classmethod
    def prepare_argparse_list(cls, pre_list, prefix=''):
        """
        argparse returns either None, a empty list, or a list with values.
        :param list[str] pre_list: list to prefix ith Aux/ and convert
        :param str prefix: will prefix every list value with this str
        :return: converted list
        :rtype: Optional[list[str]]
        """
        if pre_list is not None:
            if pre_list and pre_list[0]:
                return [prefix + x for x in pre_list]
            else:
                return []
        return None

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
                    s = s[:limit - 3] + "..."

            return s

        storage_pool_dfns = self.get_linstorapi().storage_pool_dfn_list()[0].storage_pool_definitions

        for candidate in lstmsg.candidates:
            max_vlm_size = SizeCalc.approximate_size_string(candidate.max_volume_size)

            storage_pool_props = [x for x in storage_pool_dfns if x.name == candidate.storage_pool][0].properties
            max_oversubscription_ratio = float(storage_pool_props.get(
                KEY_STOR_POOL_MAX_OVERSUBSCRIPTION_RATIO, lstmsg.default_max_oversubscription_ratio))

            tbl.add_row([
                candidate.storage_pool,
                max_vlm_size,
                "Thin, oversubscription ratio " + str(max_oversubscription_ratio) if candidate.all_thin else "Thick",
                limited_string(candidate.node_names)
            ])
        tbl.show()


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

        sos_subcommands = [
            Commands.Subcommands.Create,
            Commands.Subcommands.Download
        ]
        sos_parser = parser.add_parser(
            Commands.SOS_REPORT,
            aliases=["sos"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="SOS report subcommands")

        sos_subp = sos_parser.add_subparsers(
            title="SOS report commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(sos_subcommands)
        )

        c_sos_create = sos_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Create an SOS report on the controller (by default in the `/var/log/linstor-controller` '
            'directory).'
        )
        c_sos_create.add_argument('-s', '--since',
                                  help='Create an SOS report with logs since n days, for example, "3days"')
        c_sos_create.add_argument(
            '-n',
            '--nodes',
            nargs='+',
            type=str,
            help='Only include the specified nodes in the SOS report'
        ).completer = self.node_completer
        c_sos_create.add_argument(
            '-r',
            '--resources',
            nargs='+',
            type=str,
            help='Only include in the SOS report nodes that have the specified resources deployed.'
        ).completer = self.resource_completer
        c_sos_create.add_argument(
            '-e',
            '--exclude-nodes',
            nargs='+',
            type=str,
            help='Do not include the specified nodes in the SOS report.'
        ).completer = self.node_completer
        c_sos_create.add_argument(
            '--no-controller',
            action='store_true',
            help='Do not include the controller in the sos-report'
        )
        c_sos_create.set_defaults(func=self.cmd_sos_report_create)

        c_sos_download = sos_subp.add_parser(
            Commands.Subcommands.Download.LONG,
            aliases=[Commands.Subcommands.Download.SHORT],
            description='Create a sos report and downloads it'
        )
        c_sos_download.add_argument('-s', '--since', help='Create sos-report with logs since n days. e.g. "3days"')
        c_sos_download.add_argument(
            'path', nargs='?', help='Directory where to download the sos report')
        c_sos_download.add_argument(
            '-n',
            '--nodes',
            nargs='+',
            type=str,
            help='Only include the given nodes in the sos-report'
        ).completer = self.node_completer
        c_sos_download.add_argument(
            '-r',
            '--resources',
            nargs='+',
            type=str,
            help='Only include nodes that have the given resources deployed in the sos-report'
        ).completer = self.resource_completer
        c_sos_download.add_argument(
            '-e',
            '--exclude-nodes',
            nargs='+',
            type=str,
            help='Do not include the given nodes in the sos-report'
        ).completer = self.node_completer
        c_sos_download.add_argument(
            '--no-controller',
            action='store_true',
            help='Do not include the controller in the sos-report'
        )
        c_sos_download.set_defaults(func=self.cmd_sos_report_download)
        self.check_subcommands(sos_subp, sos_subcommands)

        space_reporting_subcmds = [
            Commands.Subcommands.Query
        ]
        spc_rep_parser = parser.add_parser(
            Commands.SPACE_REPORTING,
            aliases=["spr"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Space reporting subcommands")

        spc_rep_subp = spc_rep_parser.add_subparsers(
            title="Space reporting commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(space_reporting_subcmds)
        )

        c_spc_report_query = spc_rep_subp.add_parser(
            Commands.Subcommands.Query.LONG,
            aliases=[Commands.Subcommands.Query.SHORT],
            description='Show a report of monthly storage space tracking for the LINSTOR cluster.'
        )
        c_spc_report_query.add_argument(
            '--from-file',
            type=argparse.FileType('r'),
            help="Read data to display from the given json file",
        )
        c_spc_report_query.set_defaults(func=self.cmd_spc_report_query)

        self.check_subcommands(spc_rep_subp, space_reporting_subcmds)

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
            re_passphrase = getpass.getpass("Reenter passphrase: ")
            if passphrase != re_passphrase:
                raise LinstorClientError("Passphrase doesn't match.", ExitCode.ARGPARSE_ERROR)
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
            passphrase2 = getpass.getpass("Retype new passphrase: ")
            if new_passphrase != passphrase2:
                raise LinstorClientError("Passphrase doesn't match.", ExitCode.ARGPARSE_ERROR)

        replies = self._linstor.crypt_modify_passphrase(old_passphrase, new_passphrase)
        return self.handle_replies(args, replies)

    def cmd_sos_report_create(self, args):
        since_dt = None
        if args.since:
            since_dt = MiscCommands.parse_time_str(args.since)
        replies = self.get_linstorapi().sos_report_create(
            since=since_dt,
            nodes=args.nodes,
            rscs=args.resources,
            exclude=args.exclude_nodes,
            include_ctrl=not args.no_controller
        )
        return self.handle_replies(args, replies)

    def cmd_sos_report_download(self, args):
        since_dt = None
        if args.since:
            since_dt = MiscCommands.parse_time_str(args.since)
        return self.handle_replies(
            args,
            self.get_linstorapi().sos_report_download(
                since=since_dt,
                to_file=args.path,
                nodes=args.nodes,
                rscs=args.resources,
                exclude=args.exclude_nodes,
                include_ctrl=not args.no_controller
            )
        )

    def show_space_report(self, args, space_report):
        """

        :param args:
        :param space_report: responses.SpaceReport
        :return:
        """
        print(space_report.report)

    def cmd_spc_report_query(self, args):
        if args.from_file:
            reply = [linstor.responses.SpaceReport(json.load(args.from_file))]
        else:
            reply = self.get_linstorapi().space_reporting_query()
        return self.output_list(args, reply, self.show_space_report)
