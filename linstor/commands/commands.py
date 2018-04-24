import os
import json
import getpass
import linstor
from linstor.utils import Output, LinstorClientError
from linstor.protobuf_to_dict import protobuf_to_dict
import linstor.linstorapi as linstorapi
from linstor.sharedconsts import NAMESPC_AUXILIARY, EVENT_VOLUME_DISK_STATE, EVENT_RESOURCE_STATE
from linstor.consts import ExitCode, KEY_LS_CONTROLLERS
from linstor.properties import properties


class ArgumentError(Exception):
    def __init__(self, msg):
        self._msg = msg

    @property
    def message(self):
        return self._msg


class Commands(object):
    CREATE_NODE = 'create-node'
    CREATE_RESOURCE = 'create-resource'
    CREATE_RESOURCE_DEF = 'create-resource-definition'
    CREATE_STORAGE_POOL = 'create-storage-pool'
    CREATE_STORAGE_POOL_DEF = 'create-storage-pool-definition'
    CREATE_VOLUME_DEF = 'create-volume-definition'
    CREATE_NETINTERFACE = 'create-netinterface'
    MODIFY_NETINTERFACE = 'modify-netinterface'
    DELETE_NODE = 'delete-node'
    DELETE_RESOURCE = 'delete-resource'
    DELETE_RESOURCE_DEF = 'delete-resource-definition'
    DELETE_STORAGE_POOL = 'delete-storage-pool'
    DELETE_STORAGE_POOL_DEF = 'delete-storage-pool-definition'
    DELETE_VOLUME_DEF = 'delete-volume-definition'
    DELETE_NETINTERFACE = 'delete-netinterface'
    DESCRIBE_NODE = 'describe-node'
    LIST_NODE = 'list-nodes'
    LIST_RESOURCE_DEF = 'list-resource-definitions'
    LIST_RESOURCE = 'list-resources'
    LIST_STORAGE_POOL_DEF = 'list-storage-pool-definitions'
    LIST_STORAGE_POOL = 'list-storage-pools'
    LIST_VOLUME_DEF = 'list-volume-definitions'
    LIST_VOLUME = 'list-volumes'
    LIST_NETINTERFACE = 'list-netinterfaces'
    DRBD_OPTIONS = 'drbd-options'
    DRBD_RESOURCE_OPTIONS = 'drbd-resource-options'
    DRBD_VOLUME_OPTIONS = 'drbd-volume-options'
    EXIT = 'exit'
    GET_NODE_PROPS = 'list-node-properties'
    GET_RESOURCE_DEF_PROPS = 'list-resource-definition-properties'
    GET_RESOURCE_PROPS = 'list-resource-properties'
    GET_STORAGE_POOL_DEF_PROPS = 'list-storage-pool-definition-properties'
    GET_STORAGE_POOL_PROPS = 'list-storage-pool-properties'
    GET_VOLUME_DEF_PROPS = 'list-volume-definition-properties'
    GET_CONTROLLER_PROPS = 'list-controller-properties'
    CREATE_WATCH = 'create-watch'
    HELP = 'help'
    INTERACTIVE = 'interactive'
    LIST_COMMANDS = 'list-commands'
    SHUTDOWN = 'shutdown'
    DMMIGRATE = 'dm-migrate'
    SET_NODE_PROP = 'set-node-property'
    SET_RESOURCE_DEF_PROP = 'set-resource-definition-property'
    SET_RESOURCE_PROP = 'set-resource-property'
    SET_STORAGE_POOL_DEF_PROP = 'set-storage-pool-definition-property'
    SET_STORAGE_POOL_PROP = 'set-storage-pool-property'
    SET_VOLUME_DEF_PROP = 'set-volume-definition-property'
    SET_CONTROLLER_PROP = 'set-controller-property'
    CRYPT_ENTER_PASSPHRASE = 'crypt-enter-passphrase'
    CRYPT_CREATE_PASSPHRASE = 'crypt-create-passphrase'
    CRYPT_MODIFY_PASSPHRASE = 'crypt-modify-passphrase'

    GEN_ZSH_COMPLETER = 'gen-zsh-completer'

    MainList = [
        CREATE_NODE,
        CREATE_RESOURCE,
        CREATE_RESOURCE_DEF,
        CREATE_STORAGE_POOL,
        CREATE_STORAGE_POOL_DEF,
        CREATE_VOLUME_DEF,
        CREATE_NETINTERFACE,
        MODIFY_NETINTERFACE,
        DELETE_NODE,
        DELETE_RESOURCE,
        DELETE_RESOURCE_DEF,
        DELETE_STORAGE_POOL,
        DELETE_STORAGE_POOL_DEF,
        DELETE_VOLUME_DEF,
        DELETE_NETINTERFACE,
        DESCRIBE_NODE,
        LIST_NODE,
        LIST_RESOURCE_DEF,
        LIST_RESOURCE,
        LIST_STORAGE_POOL_DEF,
        LIST_STORAGE_POOL,
        LIST_VOLUME_DEF,
        LIST_VOLUME,
        LIST_NETINTERFACE,
        DRBD_OPTIONS,
        DRBD_RESOURCE_OPTIONS,
        DRBD_VOLUME_OPTIONS,
        GET_NODE_PROPS,
        GET_RESOURCE_DEF_PROPS,
        GET_RESOURCE_PROPS,
        GET_STORAGE_POOL_DEF_PROPS,
        GET_STORAGE_POOL_PROPS,
        GET_VOLUME_DEF_PROPS,
        GET_CONTROLLER_PROPS,
        HELP,
        INTERACTIVE,
        LIST_COMMANDS,
        SHUTDOWN,
        SET_NODE_PROP,
        SET_RESOURCE_DEF_PROP,
        SET_RESOURCE_PROP,
        SET_STORAGE_POOL_DEF_PROP,
        SET_STORAGE_POOL_PROP,
        SET_VOLUME_DEF_PROP,
        SET_CONTROLLER_PROP,
        CRYPT_ENTER_PASSPHRASE,
        CRYPT_CREATE_PASSPHRASE,
        CRYPT_MODIFY_PASSPHRASE
    ]
    Hidden = [
        EXIT,
        DMMIGRATE,
        GEN_ZSH_COMPLETER
    ]

    def __init__(self):
        self._linstor = None  # type: linstorapi.Linstor
        # _linstor_completer is just here as a cache for completer calls
        self._linstor_completer = None  # type: linstorapi.Linstor

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
    def output_list(cls, args, replies, output_func):
        if replies:
            if cls.check_for_api_replies(replies):
                return cls.handle_replies(args, replies)

            if args.machine_readable:
                cls._print_machine_readable(replies)
            else:
                output_func(args, replies[0].proto_msg)

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
        return [x for x in properties[objname] if not x.get('internal', False)]

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
        # controller - get props
        c_ctrl_props = parser.add_parser(Commands.GET_CONTROLLER_PROPS,
                                       aliases=['dspctrlprp'],
                                       description='Print current controller config properties.')
        c_ctrl_props.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        c_ctrl_props.set_defaults(func=self.cmd_print_controller_props)

        #  controller - set props
        c_set_ctrl_props = parser.add_parser(Commands.SET_CONTROLLER_PROP,
                                           aliases=['setctrlprp'],
                                           description='Set a controller config property.')
        Commands.add_parser_keyvalue(c_set_ctrl_props, "controller")
        c_set_ctrl_props.set_defaults(func=self.cmd_set_controller_props)

        # shutdown
        c_shutdown = parser.add_parser(
            Commands.SHUTDOWN,
            aliases=['shtdwn'],
            description='Shutdown the linstor controller'
        )
        c_shutdown.set_defaults(func=self.cmd_shutdown)

        # watch
        c_create_watch = parser.add_parser(
            Commands.CREATE_WATCH,
            aliases=[],
            description='Watch events'
        )
        c_create_watch.set_defaults(func=self.cmd_create_watch)

        # crypt
        c_crypt_enter_passphr = parser.add_parser(
            Commands.CRYPT_ENTER_PASSPHRASE,
            description='Enter the crypt passphrase.'
        )
        c_crypt_enter_passphr.add_argument(
            "-p", "--passphrase",
            help='Master passphrase to unlock.'
        )
        c_crypt_enter_passphr.set_defaults(func=self.cmd_crypt_enter_passphrase)

        c_crypt_create_passphr = parser.add_parser(
            Commands.CRYPT_CREATE_PASSPHRASE,
            description='Create a new crypt passphrase.'
        )
        c_crypt_create_passphr.add_argument(
            "-p", "--passphrase",
            help="Passphrase used for encryption."
        )
        c_crypt_create_passphr.set_defaults(func=self.cmd_crypt_create_passphrase)

        c_crypt_modify_passphr = parser.add_parser(
            Commands.CRYPT_MODIFY_PASSPHRASE,
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

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            result.append(lstmsg.props)
        return result

    def cmd_print_controller_props(self, args):
        lstmsg = self._linstor.controller_props()

        return self.output_props_list(args, lstmsg, self._props_list)

    def cmd_set_controller_props(self, args):
        props = Commands.parse_key_value_pairs([args.key + '=' + args.value])

        replies = [x for subx in props['pairs'] for x in self._linstor.controller_set_prop(subx[0], subx[1])]
        return self.handle_replies(args, replies)

    def cmd_shutdown(self, args):
        replies = self._linstor.shutdown_controller()
        return self.handle_replies(args, replies)

    def cmd_create_watch(self, args):
        def reply_handler(replies):
            return self.handle_replies(args, replies) == ExitCode.OK

        event_formatter_table = {
            EVENT_VOLUME_DISK_STATE: lambda event_data: "Disk state: " + event_data.disk_state,
            EVENT_RESOURCE_STATE: lambda event_data: "Resource state: " + event_data.state
        }

        def event_handler(event_header, event_data):
            event_data_display = event_formatter_table[event_header.event_name](event_data)

            print(
                event_header.event_name +
                " (" + event_header.node_name +
                "/" + event_header.resource_name +
                ("/" + str(event_header.volume_number) if event_header.HasField("volume_number") else "") +
                "): " + event_data_display
            )

        self._linstor.create_watch(reply_handler, event_handler)

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
