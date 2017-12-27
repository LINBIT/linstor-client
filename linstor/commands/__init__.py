import sys
from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.utils import Output, Table


class Commands(object):

    @classmethod
    def _create(cls, cc, api_call, msg):
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        pbmsgs = cc.sendrec(h, msg)

        if pbmsgs:
            h = MsgHeader()
            h.ParseFromString(pbmsgs[0])
            p = MsgApiCallResponse()
            p.ParseFromString(pbmsgs[1])

        else:
            sys.stderr.write('No msg recieved from controller {ctrl}'.format(ctrl=cc.servers_good))
            sys.exit(1)

        return p

    @classmethod
    def _delete(cls, cc, api_call, del_msgs):
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        api_responses = []
        for msg in del_msgs:
            pbmsgs = cc.sendrec(h, msg)

            ret_hdr = MsgHeader()
            ret_hdr.ParseFromString(pbmsgs[0])
            assert(ret_hdr.msg_id == h.msg_id)
            p = MsgApiCallResponse()
            p.ParseFromString(pbmsgs[1])

            # exit if delete wasn't successful?
            api_responses.append(p)

            h.msg_id += 1
        return api_responses

    @classmethod
    def _delete_and_output(cls, cc, args, api_call, del_msgs):
        api_responses = Commands._delete(cc, api_call, del_msgs)

        for ar in api_responses:
            Output.handle_ret([args], ar)

    @classmethod
    def _request_list(cls, cc, api_call, lstMsg):
        h = MsgHeader()

        h.api_call = api_call
        h.msg_id = 1

        pbmsgs = cc.sendrec(h)

        h = MsgHeader()
        h.ParseFromString(pbmsgs[0])
        if h.api_call != api_call:
            p = MsgApiCallResponse()
            p.ParseFromString(pbmsgs[1])
            return p

        lstMsg.ParseFromString(pbmsgs[1])
        return lstMsg

    @classmethod
    def _get_list_message(cls, cc, api_call, request_msg, args=None):
        """
        Sends the given api_call request to the controller connect cc.
        Checks the result is the expected request_msg and returns it.
        If a MsgApiCallResponse was recieved an exception is raised with it
        that is handled by the @needs_communication wrapper.
        Or if the machine_readable flag is set, it is printed and None is returned.
        """
        lstmsg = Commands._request_list(cc, api_call, request_msg)
        if isinstance(lstmsg, MsgApiCallResponse):
            raise lstmsg

        if args and Commands._print_machine_readable(args, lstmsg):
            return None

        return lstmsg

    @classmethod
    def _print_machine_readable(cls, args, lstmsg):
        """
        Checks if machine readable flag is set in args
        and serializes the given lstmsg.
        """
        if args.machine_readable:
            from google.protobuf import json_format
            s = json_format.MessageToJson(lstmsg)
            print(s)
            return True
        return False

    @classmethod
    def _print_props(cls, prop_map):
        tbl = Table()
        tbl.add_column("Key")
        tbl.add_column("Value")
        for p in prop_map:
            tbl.add_row([p.key, p.value])
        tbl.show()

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
        Output.err('This command is deprecated or not implemented')


from node_cmds import NodeCommands
from rsc_dfn_cmds import ResourceDefinitionCommands
from storpool_dfn_cmds import StoragePoolDefinitionCommands
from storpool_cmds import StoragePoolCommands
from rsc_cmds import ResourceCommands
from vlm_dfn_cmds import VolumeDefinitionCommands
from drbd_setup_cmds import DrbdOptions
