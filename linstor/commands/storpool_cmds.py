import linstor
from linstor.commands import Commands
from linstor.utils import namecheck
from linstor.sharedconsts import (
    KEY_STOR_POOL_SUPPORTS_SNAPSHOTS
)
from linstor.consts import NODE_NAME, STORPOOL_NAME, ExitCode


class StoragePoolCommands(Commands):
    def __init__(self):
        super(StoragePoolCommands, self).__init__()

    def setup_commands(self, parser):
        # new-storpol
        p_new_storpool = parser.add_parser(
            Commands.CREATE_STORAGE_POOL,
            aliases=['crtstorpool'],
            description='Defines a Linstor storage pool for use with Linstor.')
        p_new_storpool.add_argument('name', type=namecheck(STORPOOL_NAME), help='Name of the new storage pool')
        p_new_storpool.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the new storage pool').completer = self.node_completer
        p_new_storpool.add_argument(
            'driver',
            choices=StoragePoolCommands.driver_completer(""),
            help='Name of the driver used for the new storage pool').completer = StoragePoolCommands.driver_completer
        p_new_storpool.add_argument(
            'driver_pool_name',
            type=namecheck(STORPOOL_NAME),  # TODO use STORPOOL_NAME check for now
            help='Volumegroup/Pool name of the driver e.g. drbdpool')
        p_new_storpool.set_defaults(func=self.create)

        # remove-storpool
        # TODO description
        p_rm_storpool = parser.add_parser(
            Commands.DELETE_STORAGE_POOL,
            aliases=['delstorpool'],
            description=' Removes a storage pool ')
        p_rm_storpool.add_argument(
            '-q', '--quiet',
            action="store_true",
            help='Unless this option is used, linstor will issue a safety question '
            'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool.add_argument('name',
                                   help='Name of the storage pool to delete').completer = self.storage_pool_completer
        p_rm_storpool.add_argument(
            'node_name',
            nargs="+",
            help='Name of the Node where the storage pool exists.').completer = self.node_completer
        p_rm_storpool.set_defaults(func=self.delete)

        # list storpool
        storpoolgroupby = ('Name')
        storpool_group_completer = Commands.show_group_completer(storpoolgroupby, "groupby")

        p_lstorpool = parser.add_parser(
            Commands.LIST_STORAGE_POOL,
            aliases=['dspstorpool'],
            description='Prints a list of all storage pool known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpool.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpool.add_argument('-g', '--groupby', nargs='+',
                                 choices=storpoolgroupby).completer = storpool_group_completer
        p_lstorpool.add_argument('-R', '--storpool', nargs='+', type=namecheck(STORPOOL_NAME),
                                 help='Filter by list of storage pool').completer = self.storage_pool_completer
        p_lstorpool.set_defaults(func=self.list)

        # show properties
        p_sp = parser.add_parser(
            Commands.GET_STORAGE_POOL_PROPS,
            aliases=['dspstorpoolprp'],
            description="Prints all properties of the given storage pool.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool for which to print the properties").completer = self.storage_pool_completer
        p_sp.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the storage pool').completer = self.node_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = parser.add_parser(
            Commands.SET_STORAGE_POOL_PROP,
            aliases=['setstorpoolprp'],
            description='Sets properties for the given storage pool on the given node.')
        p_setprop.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the storage pool'
        ).completer = self.storage_pool_completer
        p_setprop.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the storage pool').completer = self.node_completer
        Commands.add_parser_keyvalue(p_setprop, 'storagepool')
        p_setprop.set_defaults(func=self.set_props)

    def create(self, args):
        # construct correct driver name
        driver = 'LvmThin' if args.driver == 'lvmthin' else args.driver.title()
        replies = self._linstor.storage_pool_create(args.node_name, args.name, driver, args.driver_pool_name)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.node_name for x in self._linstor.storage_pool_delete(subx, args.name)]
        return self.handle_replies(args, replies)

    def list(self, args):
        lstmsg = self._linstor.storage_pool_list()

        if lstmsg:
            if args.machine_readable:
                self._print_machine_readable([lstmsg])
            else:
                tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
                tbl.add_column("StoragePool")
                tbl.add_column("Node")
                tbl.add_column("Driver")
                tbl.add_column("PoolName")
                tbl.add_column("SupportsSnapshots")
                for storpool in lstmsg.stor_pools:
                    driver_device_prop = [x for x in storpool.props
                                          if x.key == self._linstor.get_driver_key(storpool.driver)]
                    driver_device = driver_device_prop[0].value if driver_device_prop else ''

                    supports_snapshots_prop = [x for x in storpool.static_traits if x.key == KEY_STOR_POOL_SUPPORTS_SNAPSHOTS]
                    supports_snapshots = supports_snapshots_prop[0].value if supports_snapshots_prop else ''

                    tbl.add_row([
                        storpool.stor_pool_name,
                        storpool.node_name,
                        storpool.driver,
                        driver_device,
                        supports_snapshots
                    ])
                tbl.show()

        return ExitCode.OK

    def print_props(self, args):
        lstmsg = self._linstor.storage_pool_list()

        result = []
        if lstmsg:
            for stp in lstmsg.stor_pools:
                if stp.stor_pool_name == args.storage_pool_name and stp.node_name == args.node_name:
                    result.append(stp.props)
                    break

        Commands._print_props(result, args)
        return ExitCode.OK

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.storage_pool_modify(
            args.node_name,
            args.name,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    @staticmethod
    def driver_completer(prefix, **kwargs):
        possible = ["lvm", "lvmthin", "zfs"]

        if prefix:
            return [e for e in possible if e.startswith(prefix)]

        return possible
