import sys
import json
from linstor.proto.MsgHeader_pb2 import MsgHeader
from linstor.proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.proto.MsgControlCtrl_pb2 import MsgControlCtrl
from linstor.proto.MsgLstCtrlCfgProps_pb2 import MsgLstCtrlCfgProps
from linstor.proto.MsgSetCtrlCfgProp_pb2 import MsgSetCtrlCfgProp
from linstor.utils import Output, Table, LinstorError
from linstor.protobuf_to_dict import protobuf_to_dict
from linstor.commcontroller import ApiCallResponseError, need_communication
from linstor.sharedconsts import (
    API_REPLY, API_CMD_SHUTDOWN, API_CONTROL_CTRL, API_LST_CFG_VAL, API_SET_CFG_VAL,
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
    DRBD_OPTIONS = 'drbd-options'
    EXIT = 'exit'
    GET_NODE_PROPS = 'get-node-prop'
    GET_RESOURCE_DEF_PROPS = 'get-resource-definition-prop'
    GET_RESOURCE_PROPS = 'get-resource-prop'
    GET_STORAGE_POOL_DEF_PROPS = 'get-storage-pool-definition-prop'
    GET_STORAGE_POOL_PROPS = 'get-storage-pool-prop'
    GET_VOLUME_DEF_PROPS = 'get-volume-definition-prop'
    GET_CONTROLLER_PROPS = 'get-controller-prop'
    HELP = 'help'
    INTERACTIVE = 'interactive'
    LIST_COMMANDS = 'list-commands'
    SHUTDOWN = 'shutdown'
    # SET_NODE_PROP = 'set-node-prop'
    # SET_RESOURCE_DEF_PROP = 'set-resource-definition-prop'
    SET_RESOURCE_PROP = 'set-resource-prop'
    # SET_STORAGE_POOL_DEF_PROP = 'set-storage-pool-definition-prop'
    SET_STORAGE_POOL_PROP = 'set-storage-pool-prop'
    # SET_VOLUME_DEF_PROP = 'set-volume-definition-prop'
    SET_CONTROLLER_PROP = 'set-controller-prop'
    SET_NODE_AUX_PROP = 'set-node-aux-prop'
    SET_RESOURCE_DEF_AUX_PROP = 'set-resource-definition-aux-prop'
    SET_RESOURCE_AUX_PROP = 'set-resource-aux-prop'
    SET_STORAGE_POOL_DEF_AUX_PROP = 'set-storage-pool-definition-aux-prop'
    SET_STORAGE_POOL_AUX_PROP = 'set-storage-pool-aux-prop'
    SET_VOLUME_DEF_AUX_PROP = 'set-volume-definition-aux-prop'

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
        DRBD_OPTIONS,
        EXIT,
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

    @classmethod
    def _send_msg(cls, cc, api_call, msg, args=None):
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        responses = cc.send_and_expect_reply(h, msg)

        if args and args.machine_readable:
            Commands._print_machine_readable([r.proto_msg for r in responses])
            return None

        return responses

    @classmethod
    def _send_msg_without_output(cls, cc, api_call, msg):
        """
        Use this method if you call it multiple times and handle machine readable output later at once.
        :param cc: CommunicationController to use
        :param api_call: api call constant
        :param msg: proto msg payload to send
        :return: a list of ApiCallResponses
        """
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        responses = cc.send_and_expect_reply(h, msg)

        return responses

    @classmethod
    def _delete(cls, cc, api_call, del_msgs):
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        api_responses = []
        for msg in del_msgs:
            p = cc.send_and_expect_reply(h, msg)

            # exit if delete wasn't successful?
            api_responses.append(p)

            h.msg_id += 1

        return api_responses

    @classmethod
    def _output_or_flatten(cls, args, api_responses):
        flat_responses = [x for subx in api_responses for x in subx]
        if args and args.machine_readable:
            Commands._print_machine_readable([x.proto_msg for x in flat_responses])
            return None
        return flat_responses

    @classmethod
    def _delete_and_output(cls, cc, args, api_call, del_msgs):
        api_responses = Commands._delete(cc, api_call, del_msgs)  # type: List[List[linstor.commcontroller.ApiCallResponse]]

        return Commands._output_or_flatten(args, api_responses)

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

        Args:
            kv_pairs (list): a list of key value pair strings. ['key=val', 'key2=val2']

        Returns:
            dict: A dictionary in the following format.

            { 'pairs': [('key', 'val')], 'delete': ['key', 'key'] }

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
    def fill_override_prop(cls, msg, key, value):
        """
        Pack a key value pair into a list and call fill_override_props
        :param msg:
        :param key:
        :param value:
        :return:
        """
        return cls.fill_override_props(msg, [key + '=' + value])

    @classmethod
    def fill_override_props(cls, msg, kv_pairs):
        """Fill override props and deletes in a modify protobuf message"""
        mod_prop_dict = Commands.parse_key_value_pairs(kv_pairs)
        msg.delete_prop_keys.extend(mod_prop_dict['delete'])
        for kv in mod_prop_dict['pairs']:
            lin_kv = msg.override_props.add()
            lin_kv.key = kv[0]
            lin_kv.value = kv[1]

        return msg

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
    def _print_props(cls, prop_list_map, machine_readable):
        """Print properties in machine or human readable format"""

        if machine_readable:
            d = [[protobuf_to_dict(y) for y in x] for x in prop_list_map]
            s = json.dumps(d, indent=2)
            print(s)
            return None

        for prop_map in prop_list_map:
            tbl = Table()
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

    @classmethod
    def _get_prop(cls, prop_map, key):
        """Finds a property in the given property map"""
        prop = next((x for x in prop_map if x.key == key), None)
        return prop.value if prop else None

    @classmethod
    def set_prop_aux(cls, args):
        args.key = NAMESPC_AUXILIARY + '/' + args.key
        return cls.set_props(args)

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
    @need_communication
    def cmd_print_controller_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_CFG_VAL, MsgLstCtrlCfgProps())

        result = []
        if lstmsg:
            result.append(lstmsg.props)

        Commands._print_props(result, args.machine_readable)
        return None

    @staticmethod
    @need_communication
    def cmd_set_controller_props(cc, args):
        props = Commands.parse_key_value_pairs([args.key + '=' + args.value])

        api_responses = []
        for mod_prop in props['pairs']:
            msccp = MsgSetCtrlCfgProp()
            ns_pos = mod_prop[0].rfind('/')
            msccp.key = mod_prop[0]
            msccp.value = mod_prop[1]
            if ns_pos >= 0:
                msccp.namespace = msccp.key[:ns_pos]
                msccp.key = msccp.key[ns_pos + 1:]

            api_responses.append(Commands._send_msg_without_output(cc, API_SET_CFG_VAL, msccp))

        return Commands._output_or_flatten(args, api_responses)

    @staticmethod
    @need_communication
    def cmd_shutdown(cc, args):
        mcc = MsgControlCtrl()
        mcc.command = API_CMD_SHUTDOWN

        return Commands._send_msg(cc, API_CONTROL_CTRL, mcc, args)
