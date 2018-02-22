import linstor
from linstor.proto.MsgCrtStorPoolDfn_pb2 import MsgCrtStorPoolDfn
from linstor.proto.MsgDelStorPoolDfn_pb2 import MsgDelStorPoolDfn
from linstor.proto.MsgLstStorPoolDfn_pb2 import MsgLstStorPoolDfn
from linstor.proto.MsgModStorPoolDfn_pb2 import MsgModStorPoolDfn
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.utils import namecheck
from linstor.sharedconsts import (
    API_CRT_STOR_POOL_DFN,
    API_DEL_STOR_POOL_DFN,
    API_LST_STOR_POOL_DFN,
    API_MOD_STOR_POOL_DFN
)
from linstor.consts import STORPOOL_NAME


class StoragePoolDefinitionCommands(Commands):

    @staticmethod
    def setup_commands(parser):
        # new-storpol definition
        p_new_storpool_dfn = parser.add_parser(
            Commands.CREATE_STORAGE_POOL_DEF,
            aliases=['crtstorpooldfn'],
            description='Defines a Linstor storpool definition for use with linstor.')
        p_new_storpool_dfn.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the new storpool definition')
        p_new_storpool_dfn.set_defaults(func=StoragePoolDefinitionCommands.create)

        # remove-storpool definition
        # TODO description
        p_rm_storpool_dfn = parser.add_parser(
            Commands.DELETE_STORAGE_POOL_DEF,
            aliases=['delstorpooldfn'],
            description=' Removes a storage pool definition ')
        p_rm_storpool_dfn.add_argument('-q', '--quiet', action="store_true",
                                       help='Unless this option is used, linstor will issue a safety question '
                                       'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the storage pool to delete').completer = StoragePoolDefinitionCommands.completer
        p_rm_storpool_dfn.set_defaults(func=StoragePoolDefinitionCommands.delete)

        # list storpool definitions
        storpooldfngroupby = ('Name')
        storpooldfn_group_completer = Commands.show_group_completer(storpooldfngroupby, "groupby")

        p_lstorpooldfs = parser.add_parser(
            Commands.LIST_STORAGE_POOL_DEF,
            aliases=['list-storage-pool-definition', 'ls-storage-pool-dfn', 'display-storage-pool-definition',
                     'dspstorpooldfn'],
            description='Prints a list of all storage pool definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpooldfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpooldfs.add_argument('-g', '--groupby', nargs='+',
                                    choices=storpooldfngroupby).completer = storpooldfn_group_completer
        p_lstorpooldfs.add_argument(
            '-R', '--storpool', nargs='+', type=namecheck(STORPOOL_NAME),
            help='Filter by list of storage pool'
        ).completer = StoragePoolDefinitionCommands.completer
        p_lstorpooldfs.set_defaults(func=StoragePoolDefinitionCommands.list)

        # show properties
        p_sp = parser.add_parser(
            Commands.GET_STORAGE_POOL_DEF_PROPS,
            aliases=['get-storage-pool-definition-properties', 'dspstorpoolprp'],
            description="Prints all properties of the given storage pool definition.")
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool definition for which to print the properties"
        ).completer = StoragePoolDefinitionCommands.completer
        p_sp.set_defaults(func=StoragePoolDefinitionCommands.print_props)

        # set properties
        # disabled until there are properties
        # p_setprop = parser.add_parser(
        #     Commands.SET_STORAGE_POOL_DEF_PROP,
        #     aliases=['set-storage-pool-definition-property', 'setstorpooldfnprp'],
        #     description='Sets properties for the given storage pool definition.')
        # p_setprop.add_argument(
        #     'name',
        #     type=namecheck(STORPOOL_NAME),
        #     help='Name of the storage pool definition'
        # ).competer = StoragePoolDefinitionCommands.completer
        # Commands.add_parser_keyvalue(p_setprop, "storagepool-definition")
        # p_setprop.set_defaults(func=StoragePoolDefinitionCommands.set_props)

        # set properties
        p_setauxprop = parser.add_parser(
            Commands.SET_STORAGE_POOL_DEF_AUX_PROP,
            aliases=['set-storage-pool-definition-aux-property', 'setstorpooldfnauxprp'],
            description='Sets auxiliary properties for the given storage pool definition.')
        p_setauxprop.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the storage pool definition'
        ).competer = StoragePoolDefinitionCommands.completer
        Commands.add_parser_keyvalue(p_setauxprop)
        p_setauxprop.set_defaults(func=StoragePoolDefinitionCommands.set_prop_aux)

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtStorPoolDfn()
        p.stor_pool_dfn.stor_pool_name = args.name

        return Commands._send_msg(cc, API_CRT_STOR_POOL_DFN, p, args)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for storpool_name in args.name:
            p = MsgDelStorPoolDfn()
            p.stor_pool_name = storpool_name

            del_msgs.append(p)

        return Commands._delete_and_output(cc, args, API_DEL_STOR_POOL_DFN, del_msgs)

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn(), args)

        if lstmsg:
            tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column("StoragePool")
            for storpool_dfn in lstmsg.stor_pool_dfns:
                tbl.add_row([
                    storpool_dfn.stor_pool_name
                ])
            tbl.show()

        return None

    @staticmethod
    @need_communication
    def print_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn())

        result = []
        if lstmsg:
            for storpool_dfn in lstmsg.stor_pool_dfns:
                if storpool_dfn.stor_pool_name == args.storage_pool_name:
                    result.append(storpool_dfn.props)
                    break

        Commands._print_props(result, args.machine_readable)
        return None

    @staticmethod
    @need_communication
    def set_props(cc, args):
        mmn = MsgModStorPoolDfn()
        mmn.stor_pool_name = args.name

        Commands.fill_override_prop(mmn, args.key, args.value)

        return Commands._send_msg(cc, API_MOD_STOR_POOL_DFN, mmn, args)

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL_DFN, MsgLstStorPoolDfn())

        if lstmsg:
            for storpool_dfn in lstmsg.stor_pool_dfns:
                possible.add(storpool_dfn.stor_pool_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible
