from proto.MsgCrtStorPoolDfn_pb2 import MsgCrtStorPoolDfn
from proto.MsgDelStorPoolDfn_pb2 import MsgDelStorPoolDfn
from proto.MsgLstStorPoolDfn_pb2 import MsgLstStorPoolDfn
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.utils import namecheck, Output, Table
from linstor.sharedconsts import (
    API_CRT_STOR_POOL_DFN,
    API_DEL_STOR_POOL_DFN,
    API_LST_STOR_POOL_DFN
)
from linstor.consts import STORPOOL_NAME


class StoragePoolDefinitionCommands(Commands):

    @staticmethod
    def setup_commands(parser):
        # new-storpol definition
        p_new_storpool_dfn = parser.add_parser(
            'create-storage-pool-definition',
            aliases=['crtstoragepooldfn'],
            description='Defines a Linstor storpool definition for use with linstor.')
        p_new_storpool_dfn.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the new storpool definition')
        p_new_storpool_dfn.set_defaults(func=StoragePoolDefinitionCommands.argsparse_create)

        # modify-storpool

        # remove-storpool definition
        # TODO description
        p_rm_storpool_dfn = parser.add_parser(
            'delete-storage-pool-definition',
            aliases=['delstoragepooldfn'],
            description=' Removes a storage pool definition ')
        p_rm_storpool_dfn.add_argument('-q', '--quiet', action="store_true",
                                       help='Unless this option is used, linstor will issue a safety question '
                                       'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the storage pool to delete').completer = StoragePoolDefinitionCommands.completer
        p_rm_storpool_dfn.set_defaults(func=StoragePoolDefinitionCommands.argparse_delete)

        # list storpool definitions
        storpooldfngroupby = ('Name')
        storpooldfn_group_completer = Commands.show_group_completer(storpooldfngroupby, "groupby")

        p_lstorpooldfs = parser.add_parser(
            'list-storage-pool-definitions',
            aliases=['list-storage-pool-definition', 'ls-storage-pool-dfn', 'display-storage-pool-definition'],
            description='Prints a list of all storage pool definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpooldfs.add_argument('-m', '--machine-readable', choices=['text', 'json'], const='json', nargs='?')
        p_lstorpooldfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpooldfs.add_argument('-g', '--groupby', nargs='+',
                                    choices=storpooldfngroupby).completer = storpooldfn_group_completer
        p_lstorpooldfs.add_argument(
            '-R', '--storpool', nargs='+', type=namecheck(STORPOOL_NAME),
            help='Filter by list of storage pool'
        ).completer = StoragePoolDefinitionCommands.completer
        p_lstorpooldfs.add_argument('--separators', action="store_true")
        p_lstorpooldfs.set_defaults(func=StoragePoolDefinitionCommands.list)

        # show properties
        p_sp = parser.add_parser(
            'get-storage-pool-definition-properties',
            aliases=['get-storage-pool-definition-props'],
            description="Prints all properties of the given storage pool definition.")
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool definition for which to print the properties"
        ).completer = StoragePoolDefinitionCommands.completer
        p_sp.set_defaults(func=StoragePoolDefinitionCommands.print_props)

    @staticmethod
    @need_communication
    def argsparse_create(cc, args):
        return StoragePoolDefinitionCommands.create(cc, args.name)

    @staticmethod
    def create(cc, storage_pool_name):
        p = MsgCrtStorPoolDfn()
        p.stor_pool_name = storage_pool_name

        return Commands._create(cc, API_CRT_STOR_POOL_DFN, p)

    @staticmethod
    @need_communication
    def argparse_delete(cc, args):
        api_responses = StoragePoolDefinitionCommands.delete(cc, args, args.name)

        for ar in api_responses:
            Output.handle_ret([args], ar.proto_msg)
        return None

    @staticmethod
    def delete(cc, args, storage_pool_names):
        del_msgs = []
        for storpool_name in storage_pool_names:
            p = MsgDelStorPoolDfn()
            p.stor_pool_name = storpool_name

            del_msgs.append(p)

        return Commands._delete(cc, API_DEL_STOR_POOL_DFN, del_msgs)

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn(), args)

        if lstmsg:
            tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column("StoragePool")
            for storpool_dfn in lstmsg.stor_pool_dfns:
                tbl.add_row([
                    storpool_dfn.stor_pool_name
                ])
            tbl.show()

            # prntfrm = "{storpool:<20s} {uuid:<40s}"
            # print(prntfrm.format(storpool="StorpoolDfn-name", uuid="UUID"))
            # for storpool_dfn in lstmsg.stor_pool_dfns:
            #     print(prntfrm.format(storpool=storpool_dfn.stor_pool_name, uuid=storpool_dfn.uuid))

        return None

    @staticmethod
    @need_communication
    def print_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn())

        if lstmsg:
            for storpool_dfn in lstmsg.stor_pool_dfns:
                if storpool_dfn.stor_pool_name == args.storage_pool_name:
                    Commands._print_props(storpool_dfn.props)
                    break

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
