import sys
import json
from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from proto.MsgControlCtrl_pb2 import MsgControlCtrl
from linstor.utils import Output, Table
from linstor.protobuf_to_dict import protobuf_to_dict
from linstor.commcontroller import ApiCallResponseError, need_communication
from linstor.sharedconsts import API_REPLY, API_CMD_SHUTDOWN, API_CONTROL_CTRL


class Commands(object):
    CREATE_NODE = 'create-node'
    CREATE_RESOURCE = 'create-resource'
    CREATE_RESOURCE_DEF = 'create-resource-definition'
    CREATE_STORAGE_POOL = 'create-storage-pool'
    CREATE_STORAGE_POOL_DEF = 'create-storage-pool-definition'
    CREATE_VOLUME_DEF = 'create-volume-definition'
    DELETE_NODE = 'delete-node'
    DELETE_RESOURCE = 'delete-resource'
    DELETE_RESOURCE_DEF = 'delete-resource-definition'
    DELETE_STORAGE_POOL = 'delete-storage-pool'
    DELETE_STORAGE_POOL_DEF = 'delete-storage-pool-definition'
    DELETE_VOLUME_DEF = 'delete-volume-definition'
    LIST_NODE = 'list-nodes'
    LIST_RESOURCE_DEF = 'list-resource-definitions'
    LIST_RESOURCE = 'list-resources'
    LIST_STORAGE_POOL_DEF = 'list-storage-pool-definitions'
    LIST_STORAGE_POOL = 'list-storage-pools'
    LIST_VOLUME_DEF = 'list-volume-definitions'
    LIST_VOLUME = 'list-volumes'
    DRBD_OPTIONS = 'drbd-options'
    EXIT = 'exit'
    GET_NODE_PROPS = 'get-node-prop'
    GET_RESOURCE_DEF_PROPS = 'get-resource-definition-prop'
    GET_RESOURCE_PROPS = 'get-resource-prop'
    GET_STORAGE_POOL_DEF_PROPS = 'get-storage-pool-definition-prop'
    GET_STORAGE_POOL_PROPS = 'get-storage-pool-prop'
    HELP = 'help'
    INTERACTIVE = 'interactive'
    LIST_COMMANDS = 'list-commands'
    SHUTDOWN = 'shutdown'
    SET_NODE_PROPS = 'set-node-prop'
    SET_RESOURCE_DEF_PROPS = 'set-resource-definition-prop'
    SET_RESOURCE_PROPS = 'set-resource-prop'
    SET_STORAGE_POOL_DEF_PROPS = 'set-storage-pool-definition-prop'
    SET_STORAGE_POOL_PROPS = 'set-storage-pool-prop'

    MainList = [
        CREATE_NODE,
        CREATE_RESOURCE,
        CREATE_RESOURCE_DEF,
        CREATE_STORAGE_POOL,
        CREATE_STORAGE_POOL_DEF,
        CREATE_VOLUME_DEF,
        DELETE_NODE,
        DELETE_RESOURCE,
        DELETE_RESOURCE_DEF,
        DELETE_STORAGE_POOL,
        DELETE_STORAGE_POOL_DEF,
        DELETE_VOLUME_DEF,
        LIST_NODE,
        LIST_RESOURCE_DEF,
        LIST_RESOURCE,
        LIST_STORAGE_POOL_DEF,
        LIST_STORAGE_POOL,
        LIST_VOLUME_DEF,
        LIST_VOLUME,
        DRBD_OPTIONS,
        EXIT,
        GET_NODE_PROPS,
        GET_RESOURCE_DEF_PROPS,
        GET_RESOURCE_PROPS,
        GET_STORAGE_POOL_DEF_PROPS,
        GET_STORAGE_POOL_PROPS,
        HELP,
        INTERACTIVE,
        LIST_COMMANDS,
        SHUTDOWN,
        SET_NODE_PROPS,
        SET_RESOURCE_DEF_PROPS,
        SET_RESOURCE_PROPS,
        SET_STORAGE_POOL_DEF_PROPS,
        SET_STORAGE_POOL_PROPS
    ]

    @classmethod
    def _send_msg(cls, cc, api_call, msg, args=None):
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        responses = cc.send_and_expect_reply(h, msg)

        if args and Commands._print_machine_readable(args, [r.proto_msg for r in responses]):
            return None

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
    def _delete_and_output(cls, cc, args, api_call, del_msgs):
        api_responses = Commands._delete(cc, api_call, del_msgs)  # type: List[List[linstor.commcontroller.ApiCallResponse]]

        flat_responses = [x for subx in api_responses for x in subx]
        if args and Commands._print_machine_readable(args, [x.proto_msg for x in flat_responses]):
            return None

        return flat_responses

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

        if args and Commands._print_machine_readable(args, [lstmsg]):
            return None

        return lstmsg

    @classmethod
    def _print_machine_readable(cls, args, data):
        """
        Checks if machine readable flag is set in args
        and serializes the given lstmsg.
        """
        if args.machine_readable:
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
        return False

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
            key, value = kv.split('=', 1)
            if value:
                parsed['pairs'].append((key, value))
            else:
                parsed['delete'].append(key)
        return parsed

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
    def _get_prop(cls, prop_map, key):
        """Finds a property in the given property map"""
        prop = next((x for x in prop_map if x.key == key), None)
        return prop.value if prop else None

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
    def cmd_shutdown(cc, args):
        mcc = MsgControlCtrl()
        mcc.command = API_CMD_SHUTDOWN

        return Commands._send_msg(cc, API_CONTROL_CTRL, mcc, args)
