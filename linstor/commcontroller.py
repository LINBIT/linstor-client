#!/usr/bin/env python2

import socket
import struct
import sys
import os
from google.protobuf.internal import encoder
from google.protobuf.internal import decoder
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from functools import wraps
from linstor.consts import KEY_LS_CONTROLLERS
from linstor.sharedconsts import DFLT_CTRL_PORT_PLAIN
from linstor.utils import Output


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
        with CommController(servers) as cc:
            try:
                p = f(cc, *args, **kwargs)
            except MsgApiCallResponse as callresponse:
                sys.exit(Output.handle_ret(args, callresponse))

        if p:  # could be None if no payload or if cmd_xyz does implicit return
            sys.exit(Output.handle_ret(args, p))
        sys.exit(0)

    return wrapper


def completer_communication(f):
    """
    Wrappes the communication code for completer functions
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        cliargs = kwargs['parsed_args']
        servers = CommController.controller_list(cliargs.controllers)
        with CommController(servers) as cc:
            return f(cc, *args, **kwargs)
    return wrapper


class CommController(object):
    # servers is a list of tuples containing host, port pairs
    def __init__(self, servers=[]):
        self.servers_good = servers
        self.servers_bad = []
        self.current_sock = None  # type: socket.Socket
        self.first_connect = True

    def _connect_single(self, server):
        try:
            self.current_sock = socket.create_connection(server)
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
        cenv = os.environ.get(KEY_LS_CONTROLLERS, "") + ',' + cmdl_args_controllers

        servers = []
        for hp in cenv.split(','):
            if ':' not in hp:
                hp += ':' + str(DFLT_CTRL_PORT_PLAIN)
            try:
                h, p = hp.split(':')
                servers.append((h, int(p)))
            except:
                pass
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
            hdr = ""
            while len(hdr) < 16:
                hdr += self.current_sock.recv(16)
        except:
            return []

        # h_type, h_payload_length = hdr[:4], hdr[4:8]  # ignore reserved
        h_payload_length = hdr[4:8]  # ignore reserved
        # we could assert the h_type to 0, but for now ignore

        h_payload_length = struct.unpack("!I", h_payload_length)[0]

        # slurp the whole payload
        try:
            payload = ""
            while len(payload) < h_payload_length:
                payload += self.current_sock.recv(h_payload_length)
        except:
            return []

        # split payload, just a list of pbs, the receiver has to deal with them
        pb_msgs = []
        n = 0
        try:
            while n < len(payload):
                msg_len, new_pos = decoder._DecodeVarint32(payload, n)
                n = new_pos
                msg_buf = payload[n:n+msg_len]
                n += msg_len
                pb_msgs.append(msg_buf)
        except:
            return []

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

    def close(self):
        if self.current_sock:
            self.current_sock.close()
            self.current_sock = None
