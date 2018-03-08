import sys
import json
import linstor
from linstor.proto.MsgHeader_pb2 import MsgHeader
from linstor.proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.utils import Output, LinstorError
from linstor.protobuf_to_dict import protobuf_to_dict
from linstor.commcontroller import ApiCallResponseError
import linstor.linstorapi as linstorapi
from linstor.sharedconsts import (
    API_REPLY,
    NAMESPC_AUXILIARY
)
from linstor.consts import ExitCode
from linstor.properties import properties


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
    LIST_NODE = 'list-nodes'
    LIST_RESOURCE_DEF = 'list-resource-definitions'
    LIST_RESOURCE = 'list-resources'
    LIST_STORAGE_POOL_DEF = 'list-storage-pool-definitions'
    LIST_STORAGE_POOL = 'list-storage-pools'
    LIST_VOLUME_DEF = 'list-volume-definitions'
    LIST_VOLUME = 'list-volumes'
    LIST_NETINTERFACE = 'list-netinterfaces'
    # DRBD_OPTIONS = 'drbd-options'
    EXIT = 'exit'
    GET_NODE_PROPS = 'list-node-properties'
    GET_RESOURCE_DEF_PROPS = 'list-resource-definition-properties'
    GET_RESOURCE_PROPS = 'list-resource-properties'
    GET_STORAGE_POOL_DEF_PROPS = 'list-storage-pool-definition-properties'
    GET_STORAGE_POOL_PROPS = 'list-storage-pool-properties'
    GET_VOLUME_DEF_PROPS = 'list-volume-definition-properties'
    GET_CONTROLLER_PROPS = 'list-controller-properties'
    HELP = 'help'
    INTERACTIVE = 'interactive'
    LIST_COMMANDS = 'list-commands'
    SHUTDOWN = 'shutdown'
    DMMIGRATE = 'dm-migrate'
    # SET_NODE_PROP = 'set-node-property'
    # SET_RESOURCE_DEF_PROP = 'set-resource-definition-property'
    SET_RESOURCE_PROP = 'set-resource-property'
    # SET_STORAGE_POOL_DEF_PROP = 'set-storage-pool-definition-property'
    SET_STORAGE_POOL_PROP = 'set-storage-pool-property'
    # SET_VOLUME_DEF_PROP = 'set-volume-definition-property'
    SET_CONTROLLER_PROP = 'set-controller-property'
    SET_NODE_AUX_PROP = 'set-node-aux-property'
    SET_RESOURCE_DEF_AUX_PROP = 'set-resource-definition-aux-property'
    SET_RESOURCE_AUX_PROP = 'set-resource-aux-property'
    SET_STORAGE_POOL_DEF_AUX_PROP = 'set-storage-pool-definition-aux-property'
    SET_STORAGE_POOL_AUX_PROP = 'set-storage-pool-aux-property'
    SET_VOLUME_DEF_AUX_PROP = 'set-volume-definition-aux-property'

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
        LIST_NODE,
        LIST_RESOURCE_DEF,
        LIST_RESOURCE,
        LIST_STORAGE_POOL_DEF,
        LIST_STORAGE_POOL,
        LIST_VOLUME_DEF,
        LIST_VOLUME,
        LIST_NETINTERFACE,
        # DRBD_OPTIONS,
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
        # SET_NODE_PROP,
        # SET_RESOURCE_DEF_PROP,
        SET_RESOURCE_PROP,
        # SET_STORAGE_POOL_DEF_PROP,
        SET_STORAGE_POOL_PROP,
        # SET_VOLUME_DEF_PROP,
        SET_CONTROLLER_PROP,
        SET_NODE_AUX_PROP,
        SET_RESOURCE_DEF_AUX_PROP,
        SET_RESOURCE_AUX_PROP,
        SET_STORAGE_POOL_DEF_AUX_PROP,
        SET_STORAGE_POOL_AUX_PROP,
        SET_VOLUME_DEF_AUX_PROP
    ]
    Hidden = [
        EXIT,
        DMMIGRATE,
        GEN_ZSH_COMPLETER
    ]

    def __init__(self):
        self._linstor = None  # type: linstorapi.Linstor

    @classmethod
    def handle_replies(cls, args, replies):
        if args and args.machine_readable:
            Commands._print_machine_readable([r.proto_msg for r in replies])
            return ExitCode.OK

        rc = ExitCode.OK
        for call_resp in replies:
            current_rc = Output.handle_ret(call_resp.proto_msg, warn_as_error=args.warn_as_error, no_color=args.no_color)
            if current_rc != ExitCode.OK:
                rc = current_rc

        return rc

    @classmethod
    def _request_list(cls, cc, api_call, lstMsg):
        h = MsgHeader()

        h.api_call = api_call
        h.msg_id = 1

        pbmsgs = cc.sendrec(h)

        h = MsgHeader()
        h.ParseFromString(pbmsgs[0])
        if h.api_call != api_call:
            if h.api_call == API_REPLY:
                p = MsgApiCallResponse()
                p.ParseFromString(pbmsgs[1])
                return p
            else:
                cc.unexpected_reply(h)
                return None

        lstMsg.ParseFromString(pbmsgs[1])
        return lstMsg

    @classmethod
    def _get_list_message(cls, cc, api_call, request_msg, args=None):
        """
        Sends the given api_call request to the controller connect cc.
        Checks the result is the expected request_msg and returns it.
        If a MsgApiCallResponse was received an exception is raised with it
        that is handled by the @needs_communication wrapper.
        Or if the machine_readable flag is set, it is printed and None is returned.
        """
        lstmsg = Commands._request_list(cc, api_call, request_msg)
        if isinstance(lstmsg, MsgApiCallResponse):
            raise ApiCallResponseError(lstmsg)

        if args and args.machine_readable:
            Commands._print_machine_readable([lstmsg])
            return None

        return lstmsg

    @classmethod
    def _print_machine_readable(cls, data):
        """
        serializes the given protobuf data and prints to stdout.
        """
        assert(isinstance(data, list))
        d = [protobuf_to_dict(x) for x in data]
        s = json.dumps(d, indent=2)

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
        parsed = {
            'pairs': [],
            'delete': []
        }
        for kv in kv_pairs:
            if '=' not in kv:
                raise LinstorError(
                    "KeyValueParseError: Key value '{kv}' pair does not contain a '='".format(kv=kv),
                    ExitCode.ARGPARSE_ERROR
                )
            key, value = kv.split('=', 1)
            if value:
                parsed['pairs'].append((key, value))
            else:
                parsed['delete'].append(key)
        return parsed

    @classmethod
    def add_parser_keyvalue(cls, parser, property_object=None):
        if property_object:
            props = Commands.get_allowed_props(property_object)
            parser.add_argument(
                'key',
                choices=Commands.get_allowed_prop_keys(property_object),
                help='; '.join([x['key'] + ': ' + x['info'] for x in props if 'info' in x])
            )
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

    def set_prop_aux(self, args):
        args.key = NAMESPC_AUXILIARY + '/' + args.key
        return self.set_props(args)

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


class MiscCommands(Commands):
    def __init__(self):
        super(MiscCommands, self).__init__()

    def cmd_print_controller_props(self, args):
        lstmsg = self._linstor.controller_props()
        result = []
        if lstmsg:
            result.append(lstmsg.props)

        Commands._print_props(result, args)
        return ExitCode.OK

    def cmd_set_controller_props(self, args):
        props = Commands.parse_key_value_pairs([args.key + '=' + args.value])

        replies = [x for subx in props['pairs'] for x in self._linstor.controller_set_prop(subx[0], subx[1])]
        return self.handle_replies(args, replies)

    def cmd_shutdown(self, args):
        replies = self._linstor.shutdown_controller()
        return self.handle_replies(args, replies)
