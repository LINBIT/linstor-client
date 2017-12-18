import sys
from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from google.protobuf import json_format
from linstor.utils import Output


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
    def _delete(cls, cc, args, api_call, del_msgs):
        h = MsgHeader()
        h.api_call = api_call
        h.msg_id = 1

        for msg in del_msgs:
            pbmsgs = cc.sendrec(h, msg)

            ret_hdr = MsgHeader()
            ret_hdr.ParseFromString(pbmsgs[0])
            assert(ret_hdr.msg_id == h.msg_id)
            p = MsgApiCallResponse()
            p.ParseFromString(pbmsgs[1])

            retcode = Output.handle_ret([args], p)
            # exit if delete wasn't successful?

            h.msg_id += 1

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
            s = json_format.MessageToJson(lstmsg)
            print(s)
            return True
        return False


from rsc_cmds import ResourceCommands
from rsc_dfn_cmds import ResourceDefinitionCommands
from storpool_cmds import StoragePoolCommands
from storpool_dfn_cmds import StoragePoolDefinitionCommands
from node_cmds import NodeCommands
from vlm_dfn_cmds import VolumeDefinitionCommands
