from proto.MsgLstStorPool_pb2 import MsgLstStorPool
from proto.MsgCrtStorPool_pb2 import MsgCrtStorPool
from proto.MsgDelStorPool_pb2 import MsgDelStorPool
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands, NodeCommands
from linstor.utils import namecheck
from linstor.sharedconsts import (
    API_CRT_STOR_POOL,
    API_DEL_STOR_POOL,
    API_LST_STOR_POOL
)
from linstor.consts import NODE_NAME, STORPOOL_NAME


class StoragePoolCommands(Commands):

    @staticmethod
    def setup_commands(parser):
        # new-storpol
        p_new_storpool = parser.add_parser(
            'create-storage-pool',
            aliases=['crtstoragepool'],
            description='Defines a Linstor storage pool for use with Linstor.')
        p_new_storpool.add_argument('name', type=namecheck(STORPOOL_NAME), help='Name of the new storage pool')
        p_new_storpool.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the new storage pool').completer = NodeCommands.completer
        # TODO
        p_new_storpool.add_argument(
            'driver',
            choices=StoragePoolCommands.driver_completer(""),
            help='Name of the driver used for the new storage pool').completer = StoragePoolCommands.driver_completer
        p_new_storpool.set_defaults(func=StoragePoolCommands.create)

        # modify-storpool
        # TODO

        # remove-storpool
        # TODO description
        p_rm_storpool = parser.add_parser(
            'delete-storage-pool',
            aliases=['delstoragepool'],
            description=' Removes a storage pool ')
        p_rm_storpool.add_argument(
            '-q', '--quiet',
            action="store_true",
            help='Unless this option is used, drbdmanage will issue a safety question '
            'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool.add_argument('-f', '--force',
                                   action="store_true",
                                   help='If present, then the storage pool entry and all associated assignment '
                                   "entries are removed from drbdmanage's data tables immediately, without "
                                   'taking any action on the cluster nodes that have the storage pool deployed.')
        p_rm_storpool.add_argument('name',
                                   help='Name of the storage pool to delete').completer = StoragePoolCommands.completer
        p_rm_storpool.add_argument(
            'node_name',
            nargs="+",
            help='Name of the Node where the storage pool exists.').completer = NodeCommands.completer
        p_rm_storpool.set_defaults(func=StoragePoolCommands.delete)

        # list storpool
        storpoolgroupby = ('Name')
        storpool_group_completer = Commands.show_group_completer(storpoolgroupby, "groupby")

        p_lstorpool = parser.add_parser(
            'list-storage-pools',
            aliases=['list-storage-pool', 'ls-storage-pool', 'display-storage-pools'],
            description='Prints a list of all storage pool known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpool.add_argument('-m', '--machine-readable', action="store_true")
        p_lstorpool.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpool.add_argument('-g', '--groupby', nargs='+',
                                 choices=storpoolgroupby).completer = storpool_group_completer
        p_lstorpool.add_argument('-R', '--storpool', nargs='+', type=namecheck(STORPOOL_NAME),
                                 help='Filter by list of storage pool').completer = StoragePoolCommands.completer
        p_lstorpool.add_argument('--separators', action="store_true")
        p_lstorpool.set_defaults(func=StoragePoolCommands.list)

        # show properties
        p_sp = parser.add_parser(
            'get-storage-pool-properties',
            aliases=['get-storage-pool-props'],
            description="Prints all properties of the given storage pool.")
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool for which to print the properties").completer = StoragePoolCommands.completer
        p_sp.set_defaults(func=StoragePoolCommands.print_props)

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

        Commands._delete_and_output(cc, args, API_DEL_STOR_POOL, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL, MsgLstStorPool(), args)

        if lstmsg:
            prntfrm = "{storpool:<20s} {uuid:<40s} {node:<30s} {driver:<20s}"
            print(prntfrm.format(storpool="Storpool-name", uuid="UUID", node="Node", driver="Driver"))
            for storpool in lstmsg.stor_pools:
                print(prntfrm.format(
                    storpool=storpool.stor_pool_name,
                    uuid=storpool.stor_pool_uuid,
                    node=storpool.node_name,
                    driver=storpool.driver))

        return None

    @staticmethod
    @need_communication
    def print_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_STOR_POOL, MsgLstStorPool())

        if lstmsg:
            for stp in lstmsg.stor_pools:
                if stp.stor_pool_name == args.storage_pool_name:
                    Commands._print_props(stp.props)
                    break

        return None

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_STOR_POOL, MsgLstStorPool())

        if lstmsg:
            for storpool in lstmsg.resources:
                possible.add(storpool.stor_pool_name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    @staticmethod
    def driver_completer(prefix, **kwargs):
        possible = ["lvm", "lvmthin", "zfs"]

        if prefix:
            return [e for e in possible if e.startswith(prefix)]

        return possible
