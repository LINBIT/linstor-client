import linstor_client.argparse.argparse as argparse

import linstor
from linstor import SizeCalc
import linstor_client
from linstor_client.commands import ArgumentError, Commands
from linstor_client.consts import NODE_NAME, STORPOOL_NAME
from linstor.sharedconsts import KEY_STOR_POOL_SUPPORTS_SNAPSHOTS
from linstor_client.utils import namecheck


class StoragePoolCommands(Commands):
    _stor_pool_headers = [
        linstor_client.TableHeader("StoragePool"),
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Driver"),
        linstor_client.TableHeader("PoolName"),
        linstor_client.TableHeader("FreeCapacity", alignment_text='>'),
        linstor_client.TableHeader("TotalCapacity", alignment_text='>'),
        linstor_client.TableHeader("SupportsSnapshots")
    ]

    def __init__(self):
        super(StoragePoolCommands, self).__init__()

    def setup_commands(self, parser):
        # Storage pool subcommands
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties
        ]

        sp_parser = parser.add_parser(
            Commands.STORAGE_POOL,
            aliases=["sp"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Storage pool subcommands")
        sp_subp = sp_parser.add_subparsers(
            title="Storage pool commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new-storpol
        p_new_storpool = sp_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Defines a Linstor storage pool for use with Linstor.')
        p_new_storpool.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the new storage pool').completer = self.node_completer
        p_new_storpool.add_argument('name', type=namecheck(STORPOOL_NAME), help='Name of the new storage pool')
        p_new_storpool.add_argument(
            '--shared-space',
            type=namecheck(STORPOOL_NAME),
            help='Name of used shared space'
        )
        p_new_storpool.add_argument(
            'driver',
            choices=StoragePoolCommands.driver_completer(""),
            help='Name of the driver used for the new storage pool').completer = StoragePoolCommands.driver_completer
        p_new_storpool.add_argument(
            'driver_pool_name',
            type=str,
            nargs='?',
            help='Volume group/pool to use, e.g. drbdpool. '
            'For \'lvm\', the volume group; '
            'for \'lvmthin\', the full name of the thin pool, namely VG/LV; '
            'for \'zfs\', the zPool.')
        p_new_storpool.set_defaults(func=self.create)

        # remove-storpool
        p_rm_storpool = sp_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=' Removes a storage pool ')
        p_rm_storpool.add_argument(
            '-q', '--quiet',
            action="store_true",
            help='Unless this option is used, linstor will issue a safety question '
            'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool.add_argument(
            'node_name',
            nargs="+",
            help='Name of the Node where the storage pool exists.').completer = self.node_completer
        p_rm_storpool.add_argument('name',
                                   help='Name of the storage pool to delete').completer = self.storage_pool_completer
        p_rm_storpool.set_defaults(func=self.delete)

        # list storpool
        storpoolgroupby = [x.name for x in self._stor_pool_headers]
        storpool_group_completer = Commands.show_group_completer(storpoolgroupby, "groupby")

        p_lstorpool = sp_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all storage pool known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpool.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpool.add_argument('-g', '--groupby', nargs='+',
                                 choices=storpoolgroupby).completer = storpool_group_completer
        p_lstorpool.add_argument('-s', '--storpools', nargs='+', type=namecheck(STORPOOL_NAME),
                                 help='Filter by list of storage pools').completer = self.storage_pool_completer
        p_lstorpool.add_argument('-n', '--nodes', nargs='+', type=namecheck(NODE_NAME),
                                 help='Filter by list of nodes').completer = self.node_completer
        p_lstorpool.set_defaults(func=self.list)

        # show properties
        p_sp = sp_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given storage pool.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the storage pool').completer = self.node_completer
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool for which to print the properties").completer = self.storage_pool_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = sp_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            description='Sets properties for the given storage pool on the given node.')
        p_setprop.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the storage pool').completer = self.node_completer
        p_setprop.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the storage pool'
        ).completer = self.storage_pool_completer
        Commands.add_parser_keyvalue(p_setprop, 'storagepool')
        p_setprop.set_defaults(func=self.set_props)

        self.check_subcommands(sp_subp, subcmds)

    def create(self, args):
        # construct correct driver name
        driver = 'LvmThin' if args.driver == 'lvmthin' else args.driver.title()
        try:
            replies = self._linstor.storage_pool_create(
                args.node_name,
                args.name,
                driver,
                args.driver_pool_name,
                shared_space=args.shared_space
            )
        except linstor.LinstorError as e:
            raise ArgumentError(e.message)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.node_name for x in self._linstor.storage_pool_delete(subx, args.name)]
        return self.handle_replies(args, replies)

    def show(self, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in self._stor_pool_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else [self._stor_pool_headers[0].name])

        for storpool in lstmsg.stor_pools:
            driver_device = self._linstor.storage_props_to_driver_pool(storpool.driver[:-len('Driver')], storpool.props)

            supports_snapshots_prop = [x for x in storpool.static_traits if x.key == KEY_STOR_POOL_SUPPORTS_SNAPSHOTS]
            supports_snapshots = supports_snapshots_prop[0].value if supports_snapshots_prop else ''

            free_capacity = ""
            total_capacity = ""
            if storpool.driver != 'DisklessDriver' and storpool.HasField("free_space"):
                free_capacity = SizeCalc.approximate_size_string(storpool.free_space.free_capacity)
                total_capacity = SizeCalc.approximate_size_string(storpool.free_space.total_capacity)

            tbl.add_row([
                storpool.stor_pool_name,
                storpool.node_name,
                storpool.driver,
                driver_device,
                free_capacity,
                total_capacity,
                supports_snapshots
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.storage_pool_list(args.nodes, args.storpools)

        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for stp in lstmsg.stor_pools:
                if stp.stor_pool_name == args.storage_pool_name and stp.node_name == args.node_name:
                    result.append(stp.props)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.storage_pool_list()

        return self.output_props_list(args, lstmsg, self._props_list)

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
        possible = ["lvm", "lvmthin", "zfs", "diskless"]

        if prefix:
            return [e for e in possible if e.startswith(prefix)]

        return possible
