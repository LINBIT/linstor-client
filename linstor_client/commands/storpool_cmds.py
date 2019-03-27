import linstor_client.argparse.argparse as argparse

import linstor
from linstor import SizeCalc
import linstor_client
from linstor_client.commands import ArgumentError, Commands
from linstor.sharedconsts import KEY_STOR_POOL_SUPPORTS_SNAPSHOTS
from linstor.responses import StoragePoolListResponse


class StoragePoolCommands(Commands):
    class Lvm(object):
        LONG = "lvm"
        SHORT = "lvm"

    class LvmThin(object):
        LONG = "lvmthin"
        SHORT = "lvmthin"

    class Zfs(object):
        LONG = "zfs"
        SHORT = "zfs"

    class ZfsThin(object):
        LONG = "zfsthin"
        SHORT = "zfsthin"

    class SwordfishTarget(object):
        LONG = "swordfish_target"
        SHORT = "sft"

    class SwordfishInitiator(object):
        LONG = "swordfish_initiator"
        SHORT = "sfi"

    class Diskless(object):
        LONG = "diskless"
        SHORT = "diskless"

    _stor_pool_headers = [
        linstor_client.TableHeader("StoragePool"),
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Driver"),
        linstor_client.TableHeader("PoolName"),
        linstor_client.TableHeader("FreeCapacity", alignment_text=linstor_client.TableHeader.ALIGN_RIGHT),
        linstor_client.TableHeader("TotalCapacity", alignment_text=linstor_client.TableHeader.ALIGN_RIGHT),
        linstor_client.TableHeader("SupportsSnapshots")
    ]

    def __init__(self):
        super(StoragePoolCommands, self).__init__()

    @classmethod
    def _create_pool_args(cls, parser, shared_space=True):
        parser.add_argument(
            'node_name',
            type=str,
            help='Name of the node for the new storage pool').completer = cls.node_completer
        parser.add_argument('name', type=str, help='Name of the new storage pool')
        if shared_space:
            parser.add_argument(
                '--shared-space',
                type=str,
                help='Name of used shared space'
            )

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

        subcmd_create = [
            StoragePoolCommands.Lvm,
            StoragePoolCommands.LvmThin,
            StoragePoolCommands.Zfs,
            StoragePoolCommands.ZfsThin,
            StoragePoolCommands.Diskless,
            StoragePoolCommands.SwordfishTarget,
            StoragePoolCommands.SwordfishInitiator
        ]

        sp_c_parser = sp_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Defines a Linstor storage pool for use with Linstor.'
        )
        create_subp = sp_c_parser.add_subparsers(
            title="Storage pool create commands",
            metavar="{" + ",".join([x.LONG for x in subcmd_create]) + "}",
            description=Commands.Subcommands.generate_desc(subcmd_create)
        )

        p_new_lvm_pool = create_subp.add_parser(
            StoragePoolCommands.Lvm.LONG,
            aliases=[StoragePoolCommands.Lvm.SHORT],
            description='Create a lvm storage pool'
        )
        self._create_pool_args(p_new_lvm_pool)
        p_new_lvm_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The Lvm volume group to use.'
        )
        p_new_lvm_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.LVM)

        p_new_lvm_thin_pool = create_subp.add_parser(
            StoragePoolCommands.LvmThin.LONG,
            aliases=[StoragePoolCommands.LvmThin.SHORT],
            description='Create a lvm thin storage pool'
        )
        self._create_pool_args(p_new_lvm_thin_pool)
        p_new_lvm_thin_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The LvmThin volume group to use. The full name of the thin pool, namely VG/LV'
        )
        p_new_lvm_thin_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.LVMThin)

        p_new_zfs_pool = create_subp.add_parser(
            StoragePoolCommands.Zfs.LONG,
            aliases=[StoragePoolCommands.Zfs.SHORT],
            description='Create a zfs storage pool'
        )
        self._create_pool_args(p_new_zfs_pool)
        p_new_zfs_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The name of the zpool to use.'
        )
        p_new_zfs_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.ZFS)

        p_new_zfsthin_pool = create_subp.add_parser(
            StoragePoolCommands.ZfsThin.LONG,
            aliases=[StoragePoolCommands.ZfsThin.SHORT],
            description='Create a zfs storage pool'
        )
        self._create_pool_args(p_new_zfsthin_pool)
        p_new_zfsthin_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The name of the zpool to use.'
        )
        p_new_zfsthin_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.ZFSThin)

        p_new_diskless_pool = create_subp.add_parser(
            StoragePoolCommands.Diskless.LONG,
            aliases=[StoragePoolCommands.Diskless.SHORT],
            description='Create a diskless pool'
        )
        self._create_pool_args(p_new_diskless_pool, shared_space=False)
        p_new_diskless_pool.set_defaults(
            func=self.create,
            driver=linstor.StoragePoolDriver.Diskless,
            driver_pool_name=None
        )

        p_new_swordfish_target_pool = create_subp.add_parser(
            StoragePoolCommands.SwordfishTarget.LONG,
            aliases=[StoragePoolCommands.SwordfishTarget.SHORT],
            description='Create a swordfish target'
        )
        self._create_pool_args(p_new_swordfish_target_pool)
        p_new_swordfish_target_pool.add_argument(
            'swordfish_storage_pool',
            type=str,
            help="Swordfish storage pool"
        )
        p_new_swordfish_target_pool.set_defaults(
            func=self.create_swordfish,
            driver=linstor.StoragePoolDriver.SwordfishTarget
        )

        p_new_swordfish_initiator_pool = create_subp.add_parser(
            StoragePoolCommands.SwordfishInitiator.LONG,
            aliases=[StoragePoolCommands.SwordfishInitiator.SHORT],
            description='Create a swordfish initiator'
        )
        self._create_pool_args(p_new_swordfish_initiator_pool)
        p_new_swordfish_initiator_pool.set_defaults(
            func=self.create,
            driver=linstor.StoragePoolDriver.SwordfishInitiator,
            driver_pool_name=None
        )

        # END CREATE SUBCMDS

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
        p_lstorpool.add_argument('-s', '--storpools', nargs='+', type=str,
                                 help='Filter by list of storage pools').completer = self.storage_pool_completer
        p_lstorpool.add_argument('-n', '--nodes', nargs='+', type=str,
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
            type=str,
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
            type=str,
            help='Name of the node for the storage pool').completer = self.node_completer
        p_setprop.add_argument(
            'name',
            type=str,
            help='Name of the storage pool'
        ).completer = self.storage_pool_completer
        Commands.add_parser_keyvalue(p_setprop, 'storagepool')
        p_setprop.set_defaults(func=self.set_props)

        self.check_subcommands(sp_subp, subcmds)

    def create(self, args):
        try:
            shrd_space = None if args.driver == linstor.StoragePoolDriver.Diskless else args.shared_space
            replies = self.get_linstorapi().storage_pool_create(
                args.node_name,
                args.name,
                args.driver,
                args.driver_pool_name,
                shared_space=shrd_space
            )
        except linstor.LinstorError as e:
            raise ArgumentError(e.message)
        return self.handle_replies(args, replies)

    def create_swordfish(self, args):
        prefix_key = linstor.consts.NAMESPC_STORAGE_DRIVER + '/'
        properties = {
            prefix_key + linstor.consts.KEY_STOR_POOL_SF_STOR_POOL: args.swordfish_storage_pool
        }
        try:
            replies = self.get_linstorapi().storage_pool_create(
                args.node_name,
                args.name,
                args.driver,
                None,
                shared_space=args.shared_space,
                property_dict=properties
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

        storage_pool_resp = StoragePoolListResponse(lstmsg)

        tbl.set_groupby(args.groupby if args.groupby else [self._stor_pool_headers[0].name])

        for storpool in storage_pool_resp.storage_pools:
            driver_device = linstor.StoragePoolDriver.storage_props_to_driver_pool(
                storpool.provider_kind,
                storpool.properties)

            supports_snapshots = storpool.static_traits.get(KEY_STOR_POOL_SUPPORTS_SNAPSHOTS, '')

            free_capacity = ""
            total_capacity = ""
            if not storpool.is_diskless() and storpool.free_space is not None:
                free_capacity = SizeCalc.approximate_size_string(storpool.free_space.free_capacity)
                total_capacity = SizeCalc.approximate_size_string(storpool.free_space.total_capacity)

            tbl.add_row([
                storpool.name,
                storpool.node_name,
                storpool.provider_kind,
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
                if stp.stor_pool_name.lower() == args.storage_pool_name.lower() \
                        and stp.node_name.lower() == args.node_name.lower():
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

