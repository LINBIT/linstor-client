#!/usr/bin/env python2

import socket
import struct
import sys
import os
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from google.protobuf.internal import encoder
from google.protobuf.internal import decoder
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from proto.MsgHeader_pb2 import MsgHeader
from functools import wraps
from linstor.consts import KEY_LS_CONTROLLERS
from linstor.sharedconsts import DFLT_CTRL_PORT_PLAIN, API_REPLY, MASK_ERROR, MASK_WARN, MASK_INFO
from linstor.utils import Output
from linstor import utils


def need_communication(f):
    """
    This wrapper tries to eliminate most of the boiler-plate code required for communication
    In the common/simple case users setup header/payload, call sendrec, and return the payload they got back
    The wrapper does the connection to the controller and handles the return message processing (i.e., error
    codes/info messages).
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        cliargs = args[0]
        servers = CommController.controller_list(cliargs.controllers)

        p = None
        with CommController(servers, cliargs.timeout) as cc:
            try:
                p = f(cc, *args, **kwargs)
            except ApiCallResponseError as callresponse:
                return callresponse.apicallresponse.output(
                    no_color=args[0].no_color,
                    warn_as_error=args[0].warn_as_error
                )

        if p:  # could be None if no payload or if cmd_xyz does implicit return
            if isinstance(p, list):
                for call_resp in p:
                    rc = call_resp.output(warn_as_error=args[0].warn_as_error, no_color=args[0].no_color)
                    if rc:
                        return rc
            else:
                return Output.handle_ret(p, no_color=args[0].no_color, warn_as_error=args[0].warn_as_error)
        return 0

    return wrapper


def completer_communication(f):
    """
    Wrappes the communication code for completer functions
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        cliargs = kwargs['parsed_args']
        servers = CommController.controller_list(cliargs.controllers)
        with CommController(servers, cliargs.timeout) as cc:
            return f(cc, *args, **kwargs)
    return wrapper


class ApiCallResponse(object):
    def __init__(self, proto_response):
        self._proto_msg = proto_response  # type: MsgApiCallResponse

    @classmethod
    def from_json(cls, json_data):
        apiresp = MsgApiCallResponse()
        apiresp.ret_code = json_data["ret_code"]
        if "message_format" in json_data:
            apiresp.message_format = json_data["message_format"]
        if "details_format" in json_data:
            apiresp.details_format = json_data["details_format"]

        return ApiCallResponse(apiresp)

    def is_error(self):
        return True if self.ret_code & MASK_ERROR == MASK_ERROR else False

    def is_warning(self):
        return True if self.ret_code & MASK_WARN == MASK_WARN else False

    def is_info(self):
        return True if self.ret_code & MASK_INFO == MASK_INFO else False

    def is_success(self):
        return not self.is_error() and not self.is_warning() and not self.is_info()

    @property
    def ret_code(self):
        return self._proto_msg.ret_code

    @property
    def proto_msg(self):
        return self._proto_msg

    def output(self, warn_as_error, no_color):
        return Output.handle_ret(
            self._proto_msg, no_color=no_color, warn_as_error=warn_as_error
        )

    def __str__(self):
        sio = StringIO()
        Output.handle_ret(self._proto_msg, no_color=True, warn_as_error=False, outstream=sio)
        return sio.getvalue()

    def __repr__(self):
        return "ApiCallResponse({retcode}, {msg})".format(retcode=self.ret_code, msg=self.proto_msg.message_format)


class ApiCallResponseError(BaseException):
    """Exception thrown if an ApiCall error was received."""

    def __init__(self, proto_msg):
        self._apicallresp = ApiCallResponse(proto_msg)

    @property
    def apicallresponse(self):
        return self._apicallresp


class CommController(object):
    # servers is a list of tuples containing host, port pairs
    def __init__(self, servers=[], timeout=20):
        self.servers_good = servers
        self.servers_bad = []
        self.current_sock = None  # type: socket.SocketType
        self.first_connect = True
        self.timeout = timeout  # type: int

    def _connect_single(self, server):
        try:
            self.current_sock = socket.create_connection(server, timeout=self.timeout)
            self.current_sock.settimeout(self.timeout)
        except:
            self.current_sock = None

    def __enter__(self):
        if not self.connect():
            sys.stderr.write('Could not connect to any controller %s\n' % (self.servers_bad))
            sys.exit(1)
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @staticmethod
    def controller_list(cmdl_args_controllers):
        cenv = cmdl_args_controllers + ',' + os.environ.get(KEY_LS_CONTROLLERS, "")

        servers = []
        for hp in cenv.split(','):
            host, port = utils.parse_host(hp)
            if not port:
                port = DFLT_CTRL_PORT_PLAIN
            servers.append((host, int(port)))
        return servers

    # Can be called multiple times and tries to find a good one
    def connect(self):
        for s in self.servers_good[:]:
            self._connect_single(s)
            if self.current_sock:
                self.first_connect = False
                return True
            self.servers_good.remove(s)
            self.servers_bad.append(s)

        if self.first_connect:
            # we don't give the servers a second chance that failed.
            # unlikely that they recovered that fast...
            return False

        # give the bad ones a 2nd chance
        for s in self.servers_bad[:]:
            self._connect_single(s)
            if self.current_sock:
                self.servers_good.append(s)
                self.servers_bad.remove(s)
                return True

        return False

    def add_controllers(self, servers):
        for s in servers:
            self.servers_good.append(s)

    def add_controller(self, server):
        self.add_controllers([server])

    def del_controller(self, server):
        try:
            self.servers_good.remove(server)
        except:
            pass
        try:
            self.servers_bad.remove(server)
        except:
            pass

    # currently only one, might be a list in the future
    def sendall(self, header, payload=None):
        if self.current_sock is None:
            return False

        h_type = struct.pack("!I", 0)  # currently always 0, 32 bit
        h_reserved = struct.pack("!Q", 0)  # reserved, 64 bit

        msg_serialized = bytes()

        header_serialized = header.SerializeToString()
        delim = encoder._VarintBytes(len(header_serialized))
        msg_serialized += delim + header_serialized

        if payload is not None:
            payload_serialized = payload.SerializeToString()
            delim = encoder._VarintBytes(len(payload_serialized))
            msg_serialized += delim + payload_serialized

        h_payload_length = len(msg_serialized)
        h_payload_length = struct.pack("!I", h_payload_length)  # 32 bit

        overall = h_type + h_payload_length + h_reserved + msg_serialized

        if len(msg_serialized) == 0:
            return False

        try:
            if self.current_sock.sendall(overall) is None:
                return True
        except:
            return False

        return False

    # return a list of pb msgs, receiver has to deal with it
    def recv(self):
        if self.current_sock is None:
            return []

        try:
            hdr = bytes()
            while len(hdr) < 16:
                hdr += self.current_sock.recv(16)

            # h_type, h_payload_length = hdr[:4], hdr[4:8]  # ignore reserved
            h_payload_length = hdr[4:8]  # ignore reserved
            # we could assert the h_type to 0, but for now ignore

            h_payload_length = struct.unpack("!I", h_payload_length)[0]

            # slurp the whole payload
            payload = bytes()
            while len(payload) < h_payload_length:
                payload += self.current_sock.recv(h_payload_length)
        except socket.timeout as st:
            sys.stderr.write("Error: Connection timeout receiving data from {addr}\n".format(
                addr=CommController._adrtuple2str(self.current_sock.getpeername()))
            )
            sys.exit(20)

        # split payload, just a list of pbs, the receiver has to deal with them
        pb_msgs = []
        n = 0
        while n < len(payload):
            msg_len, new_pos = decoder._DecodeVarint32(payload, n)
            n = new_pos
            msg_buf = payload[n:n + msg_len]
            n += msg_len
            pb_msgs.append(msg_buf)

        return pb_msgs

    def sendrec(self, header, payload=None):
        succ = self.sendall(header, payload)
        if not succ:
            succ = self.connect()
            if not succ:
                return []
            succ = self.sendall(header, payload)

        pb_msgs = []
        if succ:
            pb_msgs = self.recv()

        return pb_msgs

    def send_and_expect_reply(self, header, payload=None):
        """
        Sends the given header and payload messages via sendrec
        and expects as return an apicallresponse message

        Args:
            header (bytes): header byte data
            payload (bytes): payload byte data

        Returns:
            ApiCallResponse: An ApiCallResponse object
        """
        proto_messages = self.sendrec(header, payload)

        ret_hdr = MsgHeader()
        ret_hdr.ParseFromString(proto_messages[0])
        assert(ret_hdr.msg_id == header.msg_id)
        assert(ret_hdr.api_call == API_REPLY)
        assert(len(proto_messages) > 1)

        responses = []
        for reply_msg in proto_messages[1:]:
            p = MsgApiCallResponse()
            p.ParseFromString(reply_msg)
            responses.append(ApiCallResponse(p))

        return responses

    def close(self):
        if self.current_sock:
            self.current_sock.close()
            self.current_sock = None

    @staticmethod
    def _adrtuple2str(tuple):
        ip = tuple[0]
        port = tuple[1]
        s = "[{ip}]".format(ip=ip) if ':' in ip else ip
        s += ":" + str(port)
        return s
