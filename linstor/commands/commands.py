import sys
import json
from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.utils import Output, Table
from linstor.protobuf_to_dict import protobuf_to_dict
from linstor.commcontroller import ApiCallResponseError
from linstor.sharedconsts import API_REPLY


class Commands(object):

    @classmethod
    def _create(cls, cc, api_call, msg, args=None):
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
    def _print_props(cls, prop_map):
        """Print properties in human readable format"""
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
    def cmd_enoimp(args):
        Output.err('This command is deprecated or not implemented', args.no_color)
