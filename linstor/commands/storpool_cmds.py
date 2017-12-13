from proto.MsgHeader_pb2 import MsgHeader
from proto.MsgLstStorPool_pb2 import MsgLstStorPool
from proto.MsgCrtStorPool_pb2 import MsgCrtStorPool
from proto.MsgDelStorPool_pb2 import MsgDelStorPool
from proto.MsgApiCallResponse_pb2 import MsgApiCallResponse
from linstor.commcontroller import need_communication, CommController
from linstor.commands import Commands
from linstor.utils import Output
from linstor.sharedconsts import (
    API_CRT_STOR_POOL,
    API_DEL_STOR_POOL,
    API_LST_STOR_POOL
)


class StoragePoolCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtStorPool()
        p.stor_pool_name = args.name
        p.node_name = args.node_name

        # construct correct driver name
        if args.driver == 'lvmthin':
            driver = 'LvmThin'
        else:
            driver = args.driver.title()

        p.driver = '{driver}Driver'.format(driver=driver)

        return Commands._create(cc, API_CRT_STOR_POOL, p)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for node_name in args.node_name:
            p = MsgDelStorPool()
            p.stor_pool_name = args.name
            p.node_name = node_name

            del_msgs.append(p)

        Commands._delete(cc, args, API_DEL_STOR_POOL, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_STOR_POOL, MsgLstStorPool())
        if isinstance(lstmsg, MsgApiCallResponse):
            return lstmsg

        prntfrm = "{storpool:<20s} {uuid:<40s} {node:<30s} {driver:<20s}"
        print(prntfrm.format(storpool="Storpool-name", uuid="UUID", node="Node", driver="Driver"))
        for storpool in lstmsg.stor_pools:
            print(prntfrm.format(
                storpool=storpool.stor_pool_name,
                uuid=storpool.stor_pool_uuid.decode("utf8"),
                node=storpool.node_name,
                driver=storpool.driver))

        return None
