#!/usr/bin/env python2

import socket
import struct
from google.protobuf.internal import encoder
from google.protobuf.internal import decoder


class CommController(object):
    # servers is a list of tuples containing host, port pairs
    def __init__(self, servers=[]):
        self.servers_good = servers
        self.servers_bad = []
        self.current_sock = None
        self.first_connect = True

    def _connect_single(self, server):
        try:
            self.current_sock = socket.create_connection(server)
        except:
            self.current_sock = None

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
            hdr = self.current_sock.recv(16)
        except:
            return []

        # h_type, h_payload_length = hdr[:4], hdr[4:8]  # ignore reserved
        h_payload_length = hdr[4:8]  # ignore reserved
        # we could assert the h_type to 0, but for now ignore

        h_payload_length = struct.unpack("!I", h_payload_length)[0]

        # slurp the whole payload
        try:
            payload = self.current_sock.recv(h_payload_length)
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
            try:
                while True:
                    pb_msgs = self.recv()
                    msg_hdr = MsgHeader()
                    msg_hdr.parseFromString(pbmsgs[0])
                    if msg_hdr.msg_id == 1:
                        break
            except:
                # FIXME: Protocol error
                pass

        return pb_msgs

    def close(self):
        if self.current_sock:
            self.current_sock.close()
