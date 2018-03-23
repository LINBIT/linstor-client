"""
    LINSTOR - management of distributed storage/DRBD9 resources
    Copyright (C) 2013 - 2018 LINBIT HA-Solutions GmbH
    Author: Rene Peinthor

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import struct
import threading
import logging
import socket
import select
import ssl
from google.protobuf.internal import encoder
from google.protobuf.internal import decoder
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from linstor.proto.MsgHeader_pb2 import MsgHeader
from linstor.proto.MsgApiVersion_pb2 import MsgApiVersion
from linstor.proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.proto.MsgCrtNode_pb2 import MsgCrtNode
from linstor.proto.MsgModNode_pb2 import MsgModNode
from linstor.proto.MsgDelNode_pb2 import MsgDelNode
from linstor.proto.MsgCrtNetInterface_pb2 import MsgCrtNetInterface
from linstor.proto.MsgModNetInterface_pb2 import MsgModNetInterface
from linstor.proto.MsgDelNetInterface_pb2 import MsgDelNetInterface
from linstor.proto.MsgLstNode_pb2 import MsgLstNode
from linstor.proto.MsgCrtStorPoolDfn_pb2 import MsgCrtStorPoolDfn
from linstor.proto.MsgModStorPoolDfn_pb2 import MsgModStorPoolDfn
from linstor.proto.MsgDelStorPoolDfn_pb2 import MsgDelStorPoolDfn
from linstor.proto.MsgLstStorPoolDfn_pb2 import MsgLstStorPoolDfn
from linstor.proto.MsgCrtStorPool_pb2 import MsgCrtStorPool
from linstor.proto.MsgModStorPool_pb2 import MsgModStorPool
from linstor.proto.MsgDelStorPool_pb2 import MsgDelStorPool
from linstor.proto.MsgLstStorPool_pb2 import MsgLstStorPool
from linstor.proto.MsgCrtRscDfn_pb2 import MsgCrtRscDfn
from linstor.proto.MsgModRscDfn_pb2 import MsgModRscDfn
from linstor.proto.MsgDelRscDfn_pb2 import MsgDelRscDfn
from linstor.proto.MsgLstRscDfn_pb2 import MsgLstRscDfn
from linstor.proto.MsgCrtVlmDfn_pb2 import MsgCrtVlmDfn
from linstor.proto.MsgAutoPlaceRsc_pb2 import MsgAutoPlaceRsc
from linstor.proto.MsgModVlmDfn_pb2 import MsgModVlmDfn
from linstor.proto.MsgDelVlmDfn_pb2 import MsgDelVlmDfn
from linstor.proto.MsgCrtRsc_pb2 import MsgCrtRsc
from linstor.proto.MsgModRsc_pb2 import MsgModRsc
from linstor.proto.MsgDelRsc_pb2 import MsgDelRsc
from linstor.proto.MsgLstRsc_pb2 import MsgLstRsc
from linstor.proto.MsgSetCtrlCfgProp_pb2 import MsgSetCtrlCfgProp
from linstor.proto.MsgLstCtrlCfgProps_pb2 import MsgLstCtrlCfgProps
from linstor.proto.MsgControlCtrl_pb2 import MsgControlCtrl
from linstor.proto.Filter_pb2 import Filter
import linstor.sharedconsts as apiconsts

API_VERSION = 1
API_VERSION_MIN = 1


logging.basicConfig(level=logging.WARNING)


class AtomicInt(object):
    """
    This is a thread-safe integer type for incrementing, mostly reassembling modern atomic types,
    but with the overhead of a lock.
    """
    def __init__(self, init=0):
        self.val = init
        self.lock = threading.RLock()

    def get_and_inc(self):
        with self.lock:
            val = self.val
            self.val += 1
        return val


class LinstorError(Exception):
    """
    Linstor basic error class with a message
    """
    def __init__(self, msg, more_errors=None):
        self._msg = msg
        if more_errors is None:
            more_errors = []
        self._errors = more_errors

    def all_errors(self):
        return self._errors

    @property
    def message(self):
        return self._msg

    def __str__(self):
        return "Error: {msg}".format(msg=self._msg)

    def __repr__(self):
        return "LinstorError('{msg}')".format(msg=self._msg)


class LinstorNetworkError(LinstorError):
    """
    Linstor Error indicating an network/connection error.
    """
    def __init__(self, msg, more_errors=None):
        super(LinstorNetworkError, self).__init__(msg, more_errors)


class ApiCallResponse(object):
    """
    This is a wrapper class for a proto MsgApiCallResponse.
    It provides some additional methods for easier state checking of the ApiCallResponse.
    """
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
        return True if self.ret_code & apiconsts.MASK_ERROR == apiconsts.MASK_ERROR else False

    def is_warning(self):
        return True if self.ret_code & apiconsts.MASK_WARN == apiconsts.MASK_WARN else False

    def is_info(self):
        return True if self.ret_code & apiconsts.MASK_INFO == apiconsts.MASK_INFO else False

    def is_success(self):
        return not self.is_error() and not self.is_warning() and not self.is_info()

    @property
    def ret_code(self):
        return self._proto_msg.ret_code

    @property
    def proto_msg(self):
        return self._proto_msg

    def __repr__(self):
        return "ApiCallResponse({retcode}, {msg})".format(retcode=self.ret_code, msg=self.proto_msg.message_format)


class _LinstorNetClient(threading.Thread):
    IO_SIZE = 4096

    def __init__(self, timeout=20):
        super(_LinstorNetClient, self).__init__()
        self._socket = None  # type: socket.socket
        self._host = None  # type: str
        self._timeout = timeout
        self._slock = threading.RLock()
        self._cv_sock = threading.Condition(self._slock)
        self._logger = logging.getLogger('LinstorNetClient')
        self._replies = {}
        self._errors = []  # list of errors that happened in the select thread
        self._api_version = None
        self._cur_msg_id = AtomicInt(1)

    def __del__(self):
        self.disconnect()

    @classmethod
    def parse_host(cls, host_str):
        """
        Tries to parse an ipv4, ipv6 or host address.

        Args:
            host_str (str): host/ip string
        Returns:
          Tuple(str, str): a tuple with the ip/host and port
        """
        if not host_str:
            return host_str, None

        if host_str[0] == '[':
            # ipv6 with port
            brace_close_pos = host_str.rfind(']')
            if brace_close_pos == -1:
                raise ValueError("No closing brace found in '{s}'".format(s=host_str))

            host_ipv6 = host_str[:brace_close_pos + 1].strip('[]')
            port_ipv6 = host_str[brace_close_pos + 2:]
            return host_ipv6, port_ipv6 if port_ipv6 else None

        if host_str.count(':') == 1:
            return host_str.split(':')

        return host_str, None

    @classmethod
    def _split_proto_msgs(cls, payload):
        """
        Splits a linstor payload into each raw proto buf message
        :param bytes payload: payload data
        :return: list of raw proto buf messages
        :rtype: list
        """
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

    @classmethod
    def _parse_proto_msgs(cls, type_tuple, data):
        """
        Parses a list of proto buf messages into their protobuf and/or wrapper classes,
        defined in the type_tuple.
        :param type_tuple: first item specifies the protobuf message, second item is a wrapper class or None
        :param list data: a list of raw protobuf message data
        :return: A list with protobuf or wrapper classes from the data
        """
        msg_resps = []
        msg_type = type_tuple[0]
        wrapper_type = type_tuple[1]

        if msg_type is None:
            return msg_resps

        for msg in data:
            resp = msg_type()
            resp.ParseFromString(msg)
            if wrapper_type:
                msg_resps.append(wrapper_type(resp))
            else:
                msg_resps.append(resp)
        return msg_resps

    @classmethod
    def _parse_proto_msg(cls, msg_type, data):
        msg = msg_type()
        msg.ParseFromString(data)
        return msg

    def _parse_api_version(self, data):
        """
        Parses data as a MsgApiVersion and checks if we support the api version.

        :param bytes data: byte data containing the MsgApiVersion message
        :return: True if parsed correctly and version supported
        :raises LinstorError: if the parsed api version is not supported
        """
        msg = self._parse_proto_msg(MsgApiVersion, data)
        if self._api_version is None:
            self._api_version = msg.version
            if API_VERSION_MIN > msg.version or msg.version > API_VERSION:
                raise LinstorError("Client API version '{v}' is incompatible with controller version '{r}'.\n".format(
                        v=API_VERSION,
                        r=msg.version)
                )
        else:
            self._logger.warning("API version message already received.")
        return True

    @classmethod
    def _parse_payload_length(cls, header):
        """
        Parses the payload length from a linstor header.

        :param bytes header: 16 bytes header data
        :return: Length of the payload
        """
        struct_format = "!xxxxIxxxxxxxx"
        assert(struct.calcsize(struct_format) == len(header))
        exp_pkg_len, = struct.unpack(struct_format, header)
        return exp_pkg_len

    def _read_api_version_blocking(self):
        """
        Receives a api version message with blocking reads from the _socket and parses/checks it.

        :return: True
        """
        api_msg_data = self._socket.recv(self.IO_SIZE)
        while len(api_msg_data) < 16:
            api_msg_data += self._socket.recv(self.IO_SIZE)

        pkg_len = self._parse_payload_length(api_msg_data[:16])

        while len(api_msg_data) < pkg_len + 16:
            api_msg_data += self._socket.recv(self.IO_SIZE)

        msgs = self._split_proto_msgs(api_msg_data[16:])
        assert (len(msgs) > 0)
        hdr = self._parse_proto_msg(MsgHeader, msgs[0])

        assert(hdr.api_call == apiconsts.API_VERSION)
        self._parse_api_version(msgs[1])
        return True

    def fetch_errors(self):
        """
        Get all errors that are currently on this object, list will be cleared.
        This error list will contain all errors that happened within the select thread.
        Usually you want this list after your socket was closed unexpected.

        :return: A list of LinstorErrors
        :rtype: list[LinstorError]
        """
        errors = self._errors
        self._errors = []
        return errors

    def connect(self, server):
        """
        Connects to the given server.
        The url has to be given in the linstor uri scheme. either linstor:// or linstor+ssl://

        :param str server: uri to the server
        :return: True if connected, else raises an LinstorError
        :raise LinstorError: if connection fails.
        """
        self._logger.debug("connecting to " + server)
        try:
            url = urlparse(server)

            if not url.scheme.startswith('linstor'):
                raise LinstorError("Unknown uri scheme '{sc}' in '{uri}'.".format(sc=url.scheme, uri=server))

            host, port = self.parse_host(url.netloc)
            if not port:
                port = apiconsts.DFLT_CTRL_PORT_SSL if url.scheme == 'linstor+ssl' else apiconsts.DFLT_CTRL_PORT_PLAIN
            self._socket = socket.create_connection((host, port), timeout=self._timeout)

            # check if ssl
            if url.scheme == 'linstor+ssl':
                self._socket = ssl.wrap_socket(self._socket)
            self._socket.settimeout(self._timeout)

            # read api version
            self._read_api_version_blocking()

            self._socket.setblocking(0)
            self._logger.debug("connected to " + server)
            self._host = server
            return True
        except socket.error as err:
            self._socket = None
            raise LinstorNetworkError("Unable connecting to {hp}: {err}".format(hp=server, err=err))

    def disconnect(self):
        """
        Disconnects your current connection.

        :return: True if socket was connected, else False
        """
        with self._slock:
            if self._socket:
                self._logger.debug("disconnecting")
                self._socket.close()
                self._socket = None
                return True
        return False

    def run(self):
        """
        Runs the main select loop that handles incoming messages, parses them and
        puts them on the self._replies map.
        Errors that happen within this thread will be collected on the self._errors list
        and can be fetched with the fetch_errors() methods.

        :return:
        """
        self._errors = []
        package = bytes()  # current package data
        exp_pkg_len = 0  # expected package length

        while self._socket:
            rds = []
            wds = []
            eds = []
            try:
                rds, wds, eds = select.select([self._socket], [], [self._socket], 2)
            except (IOError, TypeError):
                pass  # maybe check if socket is None, so we know it was closed on purpose

            self._logger.debug("select exit with:" + ",".join([str(rds), str(wds), str(eds)]))

            if eds:
                self._logger.debug("Socket exception on {hp}".format(hp=self._adrtuple2str(self._socket.getpeername())))
                self._errors.append(LinstorNetworkError(
                    "Socket exception on {hp}".format(hp=self._adrtuple2str(self._socket.getpeername()))))

            for sock in rds:
                with self._slock:
                    if self._socket is None:  # socket was closed
                        break

                    read = self._socket.recv(4096)

                    if len(read) == 0:
                        self._logger.debug(
                            "No data from {hp}, closing connection".format(
                                hp=self._adrtuple2str(self._socket.getpeername())))
                        self._socket.close()
                        self._socket = None
                        self._errors.append(
                            LinstorNetworkError("Remote '{hp}' closed connection dropped.".format(hp=self._host)))

                    package += read
                    pkg_len = len(package)
                    self._logger.debug("pkg_len: " + str(pkg_len))
                    if pkg_len > 15 and exp_pkg_len == 0:  # header is 16 bytes
                        exp_pkg_len = self._parse_payload_length(package[:16])

                    self._logger.debug("exp_pkg_len: " + str(exp_pkg_len))
                    if exp_pkg_len and pkg_len == (exp_pkg_len + 16):  # check if we received the full data pkg
                        msgs = self._split_proto_msgs(package[16:])
                        assert (len(msgs) > 0)  # we should have at least a header message

                        # reset state variables
                        package = bytes()
                        exp_pkg_len = 0

                        hdr = self._parse_proto_msg(MsgHeader, msgs[0])  # parse header
                        self._logger.debug(str(hdr))

                        reply_map = {
                            apiconsts.API_PONG: (None, None),
                            apiconsts.API_REPLY: (MsgApiCallResponse, ApiCallResponse),
                            apiconsts.API_LST_STOR_POOL_DFN: (MsgLstStorPoolDfn, None),
                            apiconsts.API_LST_STOR_POOL: (MsgLstStorPool, None),
                            apiconsts.API_LST_NODE: (MsgLstNode, None),
                            apiconsts.API_LST_RSC_DFN: (MsgLstRscDfn, None),
                            apiconsts.API_LST_RSC: (MsgLstRsc, None),
                            apiconsts.API_LST_VLM: (MsgLstRsc, None),
                            apiconsts.API_LST_CFG_VAL: (MsgLstCtrlCfgProps, None)
                        }

                        if hdr.api_call == apiconsts.API_VERSION:  # this shouldn't happen
                            self._parse_api_version(msgs[1])
                            assert False  # this should not be sent a second time
                        elif hdr.api_call == apiconsts.API_PING:
                            self.send_msg(apiconsts.API_PONG)

                        elif hdr.api_call in reply_map.keys():
                            # parse other message according to the reply_map and add them to the self._replies
                            replies = self._parse_proto_msgs(reply_map[hdr.api_call], msgs[1:])
                            with self._cv_sock:
                                self._replies[hdr.msg_id] = replies
                                self._cv_sock.notifyAll()
                        else:
                            self._logger.error("Unknown linstor api message reply: " + hdr.api_call)
                            self.disconnect()
                            with self._cv_sock:
                                self._cv_sock.notifyAll()

    @property
    def connected(self):
        """Check if the socket is currently connected."""
        return self._socket is not None

    def send_msg(self, api_call_type, msg=None):
        """
        Sends a single or just a header message.

        :param str api_call_type: api call type that is set in the header message.
        :param msg: Message to be sent, if None only the header will be sent.
        :return: Message id of the message for wait_for_result()
        :rtype: int
        """
        return self.send_msgs(api_call_type, [msg] if msg else None)

    def send_msgs(self, api_call_type, msgs=None):
        """
        Sends a list of message or just a header.

        :param str api_call_type: api call type that is set in the header message.
        :param list msgs: List of message to be sent, if None only the header will be sent.
        :return: Message id of the message for wait_for_result()
        :rtype: int
        """
        hdr_msg = MsgHeader()
        hdr_msg.api_call = api_call_type
        hdr_msg.msg_id = self._cur_msg_id.get_and_inc()

        h_type = struct.pack("!I", 0)  # currently always 0, 32 bit
        h_reserved = struct.pack("!Q", 0)  # reserved, 64 bit

        msg_serialized = bytes()

        header_serialized = hdr_msg.SerializeToString()
        delim = encoder._VarintBytes(len(header_serialized))
        msg_serialized += delim + header_serialized

        if msgs:
            for msg in msgs:
                payload_serialized = msg.SerializeToString()
                delim = encoder._VarintBytes(len(payload_serialized))
                msg_serialized += delim + payload_serialized

        h_payload_length = len(msg_serialized)
        h_payload_length = struct.pack("!I", h_payload_length)  # 32 bit

        full_msg = h_type + h_payload_length + h_reserved + msg_serialized

        with self._slock:
            if not self.connected:
                raise LinstorNetworkError("Not connected to controller.", self.fetch_errors())

            msg_len = len(full_msg)
            self._logger.debug("sending " + str(msg_len))
            sent = 0
            while sent < msg_len:
                sent += self._socket.send(full_msg)
            self._logger.debug("sent " + str(sent))
        return hdr_msg.msg_id

    def wait_for_result(self, msg_id):
        """
        This method blocks and waits for an answer to the given msg_id.

        :param int msg_id:
        :return: A list with the replies.
        """
        with self._cv_sock:
            while msg_id not in self._replies:
                if not self.connected:
                    return None
                self._cv_sock.wait(1)
            return self._replies.pop(msg_id)

    @staticmethod
    def _adrtuple2str(tuple):
        ip = tuple[0]
        port = tuple[1]
        s = "[{ip}]".format(ip=ip) if ':' in ip else ip
        s += ":" + str(port)
        return s


class Linstor(object):
    _storage_pool_key_map = {
        'Lvm': apiconsts.KEY_STOR_POOL_VOLUME_GROUP,
        'LvmThin': apiconsts.KEY_STOR_POOL_THIN_POOL,
        'Zfs': apiconsts.KEY_STOR_POOL_ZPOOL,
        'Diskless': None
    }

    _node_types = [
        apiconsts.VAL_NODE_TYPE_CTRL,
        apiconsts.VAL_NODE_TYPE_AUX,
        apiconsts.VAL_NODE_TYPE_CMBD,
        apiconsts.VAL_NODE_TYPE_STLT
    ]

    def __init__(self, ctrl_host):
        """
        Constructs a Linstor api object.
        The controller host address has to be specified as linstor url.
        e.g: linstor://localhost linstor+ssl://localhost

        :param str ctrl_host: Linstor uri to the controller e.g. linstor://192.168.0.1
        """
        self._ctrl_host = ctrl_host
        self._linstor_client = _LinstorNetClient()
        self._logger = logging.getLogger('Linstor')

    def __del__(self):
        self.disconnect()

    def __enter__(self):
        self.connect()  # raises exception if error
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    @classmethod
    def _modify_props(cls, msg, property_dict, delete_props=None):
        for kv in property_dict:
            lin_kv = msg.override_props.add()
            lin_kv.key = kv[0]
            lin_kv.value = kv[1]

        if delete_props:
            msg.delete_prop_keys.extend(delete_props)
        return msg

    def _send_and_wait(self, api_call, msg=None):
        """
        Helper function that sends a api call[+msg] and waits for the answer from the controller

        :param str api_call: API call identifier
        :param msg: Proto message to send
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg_id = self._linstor_client.send_msg(api_call, msg)
        replies = self._linstor_client.wait_for_result(msg_id)
        return replies

    def connect(self):
        """
        Connects the internal linstor network client.

        :return: True
        """
        self._linstor_client.connect(self._ctrl_host)
        self._linstor_client.daemon = True
        self._linstor_client.start()
        return True

    @property
    def connected(self):
        """
        Checks if the Linstor object is connect to a controller.

        :return: True if connected, else False.
        """
        return self._linstor_client.connected

    def disconnect(self):
        """
        Disconnects the current connection.

        :return: True if the object was connected else False.
        """
        return self._linstor_client.disconnect()

    def node_create(
            self,
            node_name,
            node_type,
            ip,
            com_type=apiconsts.VAL_NETCOM_TYPE_PLAIN,
            port=None,
            netif_name='default'
    ):
        """
        Creates a node on the controller.

        :param str node_name: Name of the node.
        :param str node_type: Node type of the new node
        :param str ip: IP address to use for the nodes default netinterface.
        :param str com_type: Communication type of the node.
        :param int port: Port number of the node.
        :param str netif_name: Netinterface name that is created.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgCrtNode()

        msg.node.name = node_name
        if node_type not in self._node_types:
            raise LinstorError(
                "Unknown node type '{nt}'. Known types are: {kt}".format(nt=node_type, kt=", ".join(self._node_types))
            )
        msg.node.type = node_type
        netif = msg.node.net_interfaces.add()
        netif.name = netif_name
        netif.address = ip

        if port is None:
            if com_type == apiconsts.VAL_NETCOM_TYPE_PLAIN:
                port = apiconsts.DFLT_CTRL_PORT_PLAIN \
                    if msg.node.type == apiconsts.VAL_NODE_TYPE_CTRL else apiconsts.DFLT_STLT_PORT_PLAIN
            elif com_type == apiconsts.VAL_NETCOM_TYPE_SSL:
                port = apiconsts.DFLT_CTRL_PORT_SSL
            else:
                raise LinstorError("Communication type %s has no default port" % com_type)

            netif.stlt_port = port
            netif.stlt_encryption_type = com_type

        return self._send_and_wait(apiconsts.API_CRT_NODE, msg)

    def node_modify(self, node_name, property_dict, delete_props=None):
        """
        Modify the properties of a given node.

        :param str node_name: Name of the node to modify.
        :param dict[str, str] property_dict: Dict containing key, value pairs for new values.
        :param list[str] delete_props: List of properties to delete
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModNode()
        msg.node_name = node_name

        msg = self._modify_props(msg, property_dict, delete_props)

        return self._send_and_wait(apiconsts.API_MOD_NODE, msg)

    def node_delete(self, node_name):
        """
        Deletes the given node on the controller.

        :param str node_name: Node name to delete.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelNode()
        msg.node_name = node_name

        return self._send_and_wait(apiconsts.API_DEL_NODE, msg)

    def netinterface_create(self, node_name, interface_name, ip, port=None, com_type=None):
        """
        Create a netinterface for a given node.

        :param str node_name: Name of the node to add the interface.
        :param str interface_name: Name of the new interface.
        :param str ip: IP address of the interface.
        :param int port: Port of the interface
        :param str com_type: Communication type to use on the interface.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgCrtNetInterface()
        msg.node_name = node_name

        msg.net_if.name = interface_name
        msg.net_if.address = ip

        if port:
            msg.net_if.stlt_port = port
            msg.net_if.stlt_encryption_type = com_type

        return self._send_and_wait(apiconsts.API_CRT_NET_IF, msg)

    def netinterface_modify(self, node_name, interface_name, ip, port=None, com_type=None):
        """
        Modify a netinterface on the given node.

        :param str node_name: Name of the node.
        :param str interface_name: Name of the netinterface to modify.
        :param str ip: New IP address of the netinterface
        :param int port: New Port of the netinterface
        :param str com_type: New communication type of the netinterface
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModNetInterface()

        msg.node_name = node_name
        msg.net_if.name = interface_name
        msg.net_if.address = ip

        if port:
            msg.net_if.stlt_port = port
            msg.net_if.stlt_encryption_type = com_type

        return self._send_and_wait(apiconsts.API_MOD_NET_IF, msg)

    def netinterface_delete(self, node_name, interface_name):
        """
        Deletes a netinterface on the given node.

        :param str node_name: Name of the node.
        :param str interface_name: Name of the netinterface to delete.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelNetInterface()
        msg.node_name = node_name
        msg.net_if_name = interface_name

        return self._send_and_wait(apiconsts.API_DEL_NET_IF, msg)

    def node_list(self):
        """
        Request a list of all nodes known to the controller.
        :return: A MsgLstNode proto message containing all information.
        :rtype: list
        """
        return self._send_and_wait(apiconsts.API_LST_NODE)

    def storage_pool_dfn_create(self, name):
        """
        Creates a new storage pool definition on the controller.

        :param str name: Storage pool definition name.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgCrtStorPoolDfn()
        msg.stor_pool_dfn.stor_pool_name = name

        return self._send_and_wait(apiconsts.API_CRT_STOR_POOL_DFN, msg)

    def storage_pool_dfn_modify(self, name, property_dict, delete_props=None):
        """
        Modify properties of a given storage pool definition.

        :param str name: Storage pool definition name to modify
        :param dict[str, str] property_dict: Dict containing key, value pairs for new values.
        :param list[str] delete_props: List of properties to delete
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModStorPoolDfn()
        msg.stor_pool_name = name

        msg = self._modify_props(msg, property_dict, delete_props)

        return self._send_and_wait(apiconsts.API_MOD_STOR_POOL_DFN, msg)

    def storage_pool_dfn_delete(self, name):
        """
        Delete a given storage pool definition.

        :param str name: Storage pool definition name to delete.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelStorPoolDfn()
        msg.stor_pool_name = name

        return self._send_and_wait(apiconsts.API_DEL_STOR_POOL_DFN, msg)

    def storage_pool_dfn_list(self):
        """
        Request a list of all storage pool definitions known to the controller.

        :return: A MsgLstStorPoolDfn proto message containing all information.
        :rtype: list
        """
        return self._send_and_wait(apiconsts.API_LST_STOR_POOL_DFN)

    @classmethod
    def get_driver_key(cls, driver_name):
        """
        Returns the correct storage pool driver property key, for the given driver name

        :param str driver_name: Driver name e.g. [LvmDriver, LvmThinDriver, ZfsDriver]
        :return: The correct storage driver property key
        :rtype: str
        """
        return apiconsts.NAMESPC_STORAGE_DRIVER + '/' + cls._storage_pool_key_map[driver_name[:-len('Driver')]]

    def storage_pool_create(self, node_name, storage_pool_name, storage_driver, driver_pool_name):
        """
        Creates a new storage pool on the given node.
        If there doesn't yet exist a storage pool definition the controller will implicitly create one.

        :param str node_name: Node on which to create the storage pool.
        :param str storage_pool_name: Name of the storage pool.
        :param str storage_driver: Storage driver to use.
        :param str driver_pool_name: Name of the pool the storage driver should use on the node.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgCrtStorPool()
        msg.stor_pool.stor_pool_name = storage_pool_name
        msg.stor_pool.node_name = node_name

        if storage_driver not in self._storage_pool_key_map.keys():
            raise LinstorError("Unknown storage driver '{drv}', known drivers: {kd}".format(
                drv=storage_driver, kd=", ".join(self._storage_pool_key_map.keys()))
            )

        msg.stor_pool.driver = '{driver}Driver'.format(driver=storage_driver)

        # set driver device pool property
        if msg.stor_pool.driver not in ['DisklessDriver']:
            if not driver_pool_name:
                raise LinstorError(
                    "Driver '{d}' needs an existing driver pool name.".format(
                        d=storage_driver
                    )
                )
            prop = msg.stor_pool.props.add()
            prop.key = self.get_driver_key(msg.stor_pool.driver)
            prop.value = driver_pool_name

        return self._send_and_wait(apiconsts.API_CRT_STOR_POOL, msg)

    def storage_pool_modify(self, node_name, storage_pool_name, property_dict, delete_props=None):
        """
        Modify properties of a given storage pool on the given node.

        :param str node_name: Node on which the storage pool resides.
        :param str storage_pool_name: Name of the storage pool.
        :param dict[str, str] property_dict: Dict containing key, value pairs for new values.
        :param list[str] delete_props: List of properties to delete
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModStorPool()
        msg.node_name = node_name
        msg.stor_pool_name = storage_pool_name

        msg = self._modify_props(msg, property_dict, delete_props)

        return self._send_and_wait(apiconsts.API_MOD_STOR_POOL, msg)

    def storage_pool_delete(self, node_name, storage_pool_name):
        """
        Deletes a storage pool on the given node.

        :param str node_name: Node on which the storage pool resides.
        :param str storage_pool_name: Name of the storage pool.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelStorPool()
        msg.node_name = node_name
        msg.stor_pool_name = storage_pool_name

        return self._send_and_wait(apiconsts.API_DEL_STOR_POOL, msg)

    def storage_pool_list(self, filter_by_nodes=None, filter_by_stor_pools=None):
        """
        Request a list of all storage pool known to the controller.

        :param list[str] filter_by_nodes: Filter storage pools by nodes.
        :param list[str] filter_by_stor_pools: Filter storage pools by storage pool names.
        :return: A MsgLstStorPool proto message containing all information.
        :rtype: list
        """
        f = Filter()
        if filter_by_nodes:
            f.node_names.extend(filter_by_nodes)
        if filter_by_stor_pools:
            f.stor_pool_names.extend(filter_by_stor_pools)
        return self._send_and_wait(apiconsts.API_LST_STOR_POOL, f)

    def resource_dfn_create(self, name, port=None):
        """
        Creates a resource definition.

        :param str name: Name of the new resource definition.
        :param int port: Port the resource definition should use.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgCrtRscDfn()
        msg.rsc_dfn.rsc_name = name
        if port is not None:
            msg.rsc_dfn.rsc_dfn_port = port
        # if args.secret:
        #     p.secret = args.secret
        return self._send_and_wait(apiconsts.API_CRT_RSC_DFN, msg)

    def resource_dfn_modify(self, name, property_dict, delete_props=None):
        """
        Modify properties of the given resource definition.

        :param str name: Name of the resource definition to modify.
        :param dict[str, str] property_dict: Dict containing key, value pairs for new values.
        :param list[str] delete_props: List of properties to delete
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModRscDfn()
        msg.rsc_name = name

        msg = self._modify_props(msg, property_dict, delete_props)

        return self._send_and_wait(apiconsts.API_MOD_RSC_DFN, msg)

    def resource_dfn_delete(self, name):
        """
        Delete a given resource definition.

        :param str name: Resource definition name to delete.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelRscDfn()
        msg.rsc_name = name

        return self._send_and_wait(apiconsts.API_DEL_RSC_DFN, msg)

    def resource_dfn_list(self):
        """
        Request a list of all resource definitions known to the controller.

        :return: A MsgLstRscDfn proto message containing all information.
        :rtype: list
        """
        return self._send_and_wait(apiconsts.API_LST_RSC_DFN)

    def volume_dfn_create(self, rsc_name, size, volume_nr=None, minor_nr=None):
        """
        Create a new volume definition on the controller.

        :param str rsc_name: Name of the resource definition it is linked to.
        :param int size: Size of the volume definition in kilo bytes.
        :param int volume_nr: Volume number to use.
        :param int minor_nr: Minor number to use.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgCrtVlmDfn()
        msg.rsc_name = rsc_name

        vlmdf = msg.vlm_dfns.add()
        vlmdf.vlm_size = size
        if minor_nr is not None:
            vlmdf.vlm_minor = minor_nr

        if volume_nr is not None:
            vlmdf.vlm_nr = volume_nr

        return self._send_and_wait(apiconsts.API_CRT_VLM_DFN, msg)

    def volume_dfn_modify(self, rsc_name, volume_nr, property_dict, delete_props=None):
        """
        Modify properties of the given volume definition.

        :param str rsc_name: Name of the resource definition.
        :param int volume_nr: Volume number of the volume definition.
        :param dict[str, str] property_dict: Dict containing key, value pairs for new values.
        :param list[str] delete_props: List of properties to delete
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModVlmDfn()
        msg.rsc_name = rsc_name
        msg.vlm_nr = volume_nr

        msg = self._modify_props(msg, property_dict, delete_props)

        return self._send_and_wait(apiconsts.API_MOD_VLM_DFN, msg)

    def volume_dfn_delete(self, rsc_name, volume_nr):
        """
        Delete a given volume definition.

        :param str rsc_name: Resource definition name of the volume definition.
        :param volume_nr: Volume number.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelVlmDfn()
        msg.rsc_name = rsc_name
        msg.vlm_nr = volume_nr

        return self._send_and_wait(apiconsts.API_DEL_VLM_DFN, msg)

    def resource_create(self, node_name, rsc_name, diskless=False, storage_pool=None):
        """
        Creates a new resource on the given node.

        :param str node_name:
        :param str rsc_name:
        :param bool diskless: Should the resource be diskless
        :param storage_pool:
        :return:
        """
        msg = MsgCrtRsc()
        msg.rsc.name = rsc_name
        msg.rsc.node_name = node_name

        if not diskless and storage_pool:
            prop = msg.rsc.props.add()
            prop.key = apiconsts.KEY_STOR_POOL_NAME
            prop.value = storage_pool
            msg.rsc.props.extend([prop])

        if diskless:
            msg.rsc.rsc_flags.append(apiconsts.FLAG_DISKLESS)

        return self._send_and_wait(apiconsts.API_CRT_RSC, msg)

    def resource_auto_place(
            self,
            rsc_name,
            place_count,
            storage_pool=None,
            do_not_place_with=None,
            do_not_place_with_regex=None
    ):
        """
        Auto places(deploys) a resource to the amount of place_count.

        :param str rsc_name: Name of the resource definition to deploy
        :param int place_count: Number of placements, on how many different nodes
        :param str storage_pool: Storage pool to use
        :param list[str] do_not_place_with: Do not place with resource names in this list
        :param str do_not_place_with_regex: A regex string that rules out resources
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgAutoPlaceRsc()
        msg.rsc_name = rsc_name
        msg.place_count = place_count

        if storage_pool:
            msg.storage_pool = storage_pool
        if do_not_place_with:
            msg.not_place_with_rsc.extend(do_not_place_with)
        if do_not_place_with_regex:
            msg.not_place_with_rsc_regex = do_not_place_with_regex

        return self._send_and_wait(apiconsts.API_AUTO_PLACE_RSC, msg)

    def resource_modify(self, node_name, rsc_name, property_dict, delete_props=None):
        """
        Modify properties of a given resource.

        :param str node_name: Node name where the resource is deployed.
        :param str rsc_name: Name of the resource.
        :param dict[str, str] property_dict: Dict containing key, value pairs for new values.
        :param list[str] delete_props: List of properties to delete
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgModRsc()
        msg.node_name = node_name
        msg.rsc_name = rsc_name

        msg = self._modify_props(msg, property_dict, delete_props)

        return self._send_and_wait(apiconsts.API_MOD_RSC, msg)

    def resource_delete(self, node_name, rsc_name):
        """
        Deletes a given resource on the given node.

        :param str node_name: Name of the node where the resource is deployed.
        :param str rsc_name: Name of the resource.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgDelRsc()
        msg.node_name = node_name
        msg.rsc_name = rsc_name

        return self._send_and_wait(apiconsts.API_DEL_RSC, msg)

    def resource_list(self, filter_by_nodes=None, filter_by_resources=None):
        """
        Request a list of all resources known to the controller.

        :param list[str] filter_by_nodes: filter resources by nodes
        :param list[str] filter_by_resources: filter resources by resource names
        :return: A MsgLstRsc proto message containing all information.
        :rtype: list
        """
        f = Filter()
        if filter_by_nodes:
            f.node_names.extend(filter_by_nodes)
        if filter_by_resources:
            f.resource_names.extend(filter_by_resources)
        return self._send_and_wait(apiconsts.API_LST_RSC, f)

    def volume_list(self, filter_by_nodes=None, filter_by_stor_pools=None, filter_by_resources=None):
        """
        Request a list of all volumes known to the controller.

        :param list[str] filter_by_nodes: filter resources by nodes
        :param list[str] filter_by_stor_pools: filter resources by storage pool names
        :param list[str] filter_by_resources: filter resources by resource names
        :return: A MsgLstRsc proto message containing all information.
        :rtype: list
        """
        f = Filter()
        if filter_by_nodes:
            f.node_names.extend(filter_by_nodes)
        if filter_by_stor_pools:
            f.stor_pool_names.extend(filter_by_stor_pools)
        if filter_by_resources:
            f.resource_names.extend(filter_by_resources)
        return self._send_and_wait(apiconsts.API_LST_VLM, f)

    def controller_props(self):
        """
        Request a list of all controller properties.

        :return: A MsgLstCtrlCfgProps proto message containing all controller props.
        :rtype: list
        """
        return self._send_and_wait(apiconsts.API_LST_CFG_VAL)

    def controller_set_prop(self, key, value):
        """
        Sets a property on the controller.

        :param str key: Key of the property.
        :param str value:  New Value of the property.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgSetCtrlCfgProp()
        ns_pos = key.rfind('/')
        msg.key = key
        msg.value = value
        if ns_pos >= 0:
            msg.namespace = msg.key[:ns_pos]
            msg.key = msg.key[ns_pos + 1:]

        return self._send_and_wait(apiconsts.API_SET_CFG_VAL, msg)

    def shutdown_controller(self):
        """
        Sends a shutdown command to the controller.

        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        msg = MsgControlCtrl()
        msg.command = apiconsts.API_CMD_SHUTDOWN
        return self._send_and_wait(apiconsts.API_CONTROL_CTRL, msg)

    def ping(self):
        """
        Sends a ping message to the controller.

        :return: Message id used for this message
        :rtype: int
        """
        return self._linstor_client.send_msg(apiconsts.API_PING)

    def wait_for_message(self, msg_id):
        """
        Wait for a message from the controller.

        :param int msg_id: Message id to wait for.
        :return: A list containing ApiCallResponses from the controller.
        :rtype: list[ApiCallResponse]
        """
        return self._linstor_client.wait_for_result(msg_id)


if __name__ == "__main__":
    lin = Linstor("linstor://127.0.0.1")
    lin.connect()
    id = lin.ping()
    print(id)
    lin.wait_for_message(id)

    #print(lin.node_create('testnode', apiconsts.VAL_NODE_TYPE_STLT, '10.0.0.1'))
    for x in range(1, 20):
        print(lin.node_create('testnode' + str(x), apiconsts.VAL_NODE_TYPE_STLT, '10.0.0.' + str(x)))

    for x in range(1, 20):
        print(lin.node_delete('testnode' + str(x)))
    # replies = lin.storage_pool_list()
    # print(replies)
    # print(lin.list_nodes())
    # print(lin.list_resources())
