from proto.MsgCrtStorPoolDfn_pb2 import MsgCrtStorPoolDfn
from proto.MsgDelStorPoolDfn_pb2 import MsgDelStorPoolDfn
from proto.MsgLstStorPoolDfn_pb2 import MsgLstStorPoolDfn
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.sharedconsts import (
    API_CRT_STOR_POOL_DFN,
    API_DEL_STOR_POOL_DFN,
    API_LST_STOR_POOL_DFN
)


class StoragePoolDefinitionCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtStorPoolDfn()
        p.stor_pool_name = args.name

        return Commands._create(cc, API_CRT_STOR_POOL_DFN, p)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for storpool_name in args.name:
            p = MsgDelStorPoolDfn()
            p.stor_pool_name = storpool_name

            del_msgs.append(p)

        Commands._delete(cc, args, API_DEL_STOR_POOL_DFN, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn(), args)

        if lstmsg:
            prntfrm = "{storpool:<20s} {uuid:<40s}"
            print(prntfrm.format(storpool="StorpoolDfn-name", uuid="UUID"))
            for storpool_dfn in lstmsg.stor_pool_dfns:
                print(prntfrm.format(storpool=storpool_dfn.stor_pool_name, uuid=storpool_dfn.uuid))

                # for prop in n.node_props:
                #     print('    {key:<30s} {val:<20s}'.format(key=prop.key, val=prop.value))

        return None

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn())

        if lstmsg:
            for storpool_dfn in lstmsg.resources:
                possible.add(storpool_dfn.stor_pool_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible
