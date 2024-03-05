from __future__ import print_function
import json

import linstor
import linstor_client
import linstor_client.argparse.argparse as argparse
import linstor.sharedconsts as apiconsts
from linstor import SizeCalc
# flake8: noqa
from linstor.responses import StoragePoolListResponse
from linstor_client.commands import ArgumentError, Commands
from linstor_client.utils import Output


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

    class Diskless(object):
        LONG = "diskless"
        SHORT = "diskless"

    class File(object):
        LONG = "file"
        SHORT = "file"

    class FileThin(object):
        LONG = "filethin"
        SHORT = "filethin"

    class SPDK(object):
        LONG = "spdk"
        SHORT = "spdk"

    class RemoteSPDK(object):
        LONG = "remotespdk"
        SHORT = "remotespdk"

    class Exos(object):
        LONG = "exos"
        SHORT = "exos"

    class StorageSpaces(object):
        LONG = "storagespaces"
        SHORT = "storagespaces"

    class StorageSpacesThin(object):
        LONG = "storagespacesthin"
        SHORT = "storagespacesthin"

    class EbsInit(object):
        LONG = "ebs_initiator"
        SHORT = "ebs_init"

    _stor_pool_headers = [
        linstor_client.TableHeader("StoragePool"),
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Driver"),
        linstor_client.TableHeader("PoolName"),
        linstor_client.TableHeader("FreeCapacity", alignment_text=linstor_client.TableHeader.ALIGN_RIGHT),
        linstor_client.TableHeader("TotalCapacity", alignment_text=linstor_client.TableHeader.ALIGN_RIGHT),
        linstor_client.TableHeader("CanSnapshots"),
        linstor_client.TableHeader("State"),
        linstor_client.TableHeader("SharedName")
    ]

    def __init__(self):
        super(StoragePoolCommands, self).__init__()

    @classmethod
    def _create_pool_args(cls, parser, shared_space=True, external_locking=True):
        parser.add_argument(
            'node_name',
            type=str,
            help='Name of the node for the new storage pool').completer = cls.node_completer
        parser.add_argument('name', type=str, help='Name of the new storage pool')
        if shared_space:
            parser.add_argument(
                '--shared-space',
                type=str,
                help='Unique identifier of backing storage shared by multiple nodes. If omitted Linstor will assume '
                     'the pool is unique for each node.  When using shared volume groups with LVM2 the volume group '
                     'UUID could be used as the SHARED_SPACE identifier.'
            )
        if external_locking:
            parser.add_argument(
                '--external-locking',
                action="store_true",
                help='Skip Linstors internal locking for shared storage pools'
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
            StoragePoolCommands.File,
            StoragePoolCommands.FileThin,
            StoragePoolCommands.SPDK,
            StoragePoolCommands.RemoteSPDK,
            StoragePoolCommands.Exos,
            StoragePoolCommands.StorageSpaces,
            StoragePoolCommands.StorageSpacesThin,
            StoragePoolCommands.EbsInit
        ]

        sp_c_parser = sp_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Defines a LINSTOR storage pool.'
        )
        create_subp = sp_c_parser.add_subparsers(
            title="Storage pool create commands",
            metavar="",
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

        p_new_spdk_pool = create_subp.add_parser(
            StoragePoolCommands.SPDK.LONG,
            aliases=[StoragePoolCommands.SPDK.SHORT],
            description='Create a spdk storage pool'
        )
        self._create_pool_args(p_new_spdk_pool)
        p_new_spdk_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The Spdk logical volume store to use.'
        )
        p_new_spdk_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.SPDK)

        p_new_remote_spdk_pool = create_subp.add_parser(
            StoragePoolCommands.RemoteSPDK.LONG,
            aliases=[StoragePoolCommands.RemoteSPDK.SHORT],
            description='Create a remote-spdk storage pool'
        )
        self._create_pool_args(p_new_remote_spdk_pool)
        p_new_remote_spdk_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The remote Spdk logical volume store to use.'
        )
        p_new_remote_spdk_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.REMOTE_SPDK)

        p_new_storage_spaces_pool = create_subp.add_parser(
            StoragePoolCommands.StorageSpaces.LONG,
            aliases=[StoragePoolCommands.StorageSpaces.SHORT],
            description='Create a Microsoft storage spaces storage pool (thick provisioned)'
        )
        self._create_pool_args(p_new_storage_spaces_pool)
        p_new_storage_spaces_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The storage pool name to use. It must have been created with ServerManager or similar tools'
        )
        p_new_storage_spaces_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.STORAGE_SPACES)

        p_new_storage_spaces_thin_pool = create_subp.add_parser(
            StoragePoolCommands.StorageSpacesThin.LONG,
            aliases=[StoragePoolCommands.StorageSpacesThin.SHORT],
            description='Create a Microsoft storage spaces storage pool (thin provisioned)'
        )
        self._create_pool_args(p_new_storage_spaces_thin_pool)
        p_new_storage_spaces_thin_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The storage pool name to use. It must have been created with ServerManager or similar tools'
        )
        p_new_storage_spaces_thin_pool.set_defaults(
            func=self.create,
            driver=linstor.StoragePoolDriver.STORAGE_SPACES_THIN
        )

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
        self._create_pool_args(p_new_diskless_pool, shared_space=False, external_locking=False)
        p_new_diskless_pool.set_defaults(
            func=self.create,
            driver=linstor.StoragePoolDriver.Diskless,
            driver_pool_name=None
        )

        p_new_file_pool = create_subp.add_parser(
            StoragePoolCommands.File.LONG,
            aliases=[StoragePoolCommands.File.SHORT],
            description='Create a file storage pool'
        )
        self._create_pool_args(p_new_file_pool)
        p_new_file_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The directory to use.'
        )
        p_new_file_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.FILE)

        p_new_file_thin_pool = create_subp.add_parser(
            StoragePoolCommands.FileThin.LONG,
            aliases=[StoragePoolCommands.FileThin.SHORT],
            description='Create a file thin storage pool'
        )
        self._create_pool_args(p_new_file_thin_pool)
        p_new_file_thin_pool.add_argument(
            'driver_pool_name',
            type=str,
            help='The directory to use.'
        )
        p_new_file_thin_pool.set_defaults(func=self.create, driver=linstor.StoragePoolDriver.FILEThin)

        p_new_exos_pool = create_subp.add_parser(
            StoragePoolCommands.Exos.LONG,
            aliases=[StoragePoolCommands.Exos.SHORT],
            description='Create an EXOS storage pool'
        )
        self._create_pool_args(p_new_exos_pool)
        p_new_exos_pool.add_argument(
            'enclosure_name',
            type=str,
            help='Enclosure name'
        )
        p_new_exos_pool.add_argument(
            'pool_sn',
            type=str,
            help='Exos Pool Serial Number'
        )
        p_new_exos_pool.set_defaults(func=self.create_exos, driver=linstor.StoragePoolDriver.EXOS)

        p_new_ebs_init_pool = create_subp.add_parser(
            StoragePoolCommands.EbsInit.LONG,
            aliases=[StoragePoolCommands.EbsInit.SHORT],
            description='Create an EBS initiator storage pool'
        )
        self._create_pool_args(p_new_ebs_init_pool, shared_space=False, external_locking=False)
        p_new_ebs_init_pool.add_argument(
            'ebs_remote_name',
            type=str,
            help='EBS Remote name'
        )
        p_new_ebs_init_pool.set_defaults(func=self.create_ebs)

        # END CREATE SUBCMDS

        # remove-storpool
        p_rm_storpool = sp_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=' Removes a storage pool.')
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
        storpoolgroupby = [x.name.lower() for x in self._stor_pool_headers]
        storpool_group_completer = Commands.show_group_completer(storpoolgroupby, "groupby")

        p_lstorpool = sp_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all storage pools in the LINSTOR cluster. '
            'By default, the list is printed as a human readable table.')
        p_lstorpool.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpool.add_argument('-g', '--groupby', nargs='+',
                                 choices=storpoolgroupby,
                                 type=str.lower).completer = storpool_group_completer
        p_lstorpool.add_argument('-s', '--storage-pools', nargs='+', type=str,
                                 help='Filter by list of storage pools').completer = self.storage_pool_completer
        p_lstorpool.add_argument('-n', '--nodes', nargs='+', type=str,
                                 help='Filter by list of nodes').completer = self.node_completer
        p_lstorpool.add_argument('--props', nargs='+', type=str, help='Filter list by object properties')
        p_lstorpool.add_argument(
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lstorpool.add_argument(
            '--from-file',
            type=argparse.FileType('r'),
            help="Read data to display from the given json file",
        )
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
            formatter_class=argparse.RawTextHelpFormatter,
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

        self.check_subcommands(create_subp, subcmd_create)
        self.check_subcommands(sp_subp, subcmds)

    def create(self, args):
        try:
            shrd_space = None if "shared_space" not in args else args.shared_space
            ext_locking = None if "external_locking" not in args else args.external_locking
            replies = self.get_linstorapi().storage_pool_create(
                args.node_name,
                args.name,
                args.driver,
                args.driver_pool_name,
                shared_space=shrd_space,
                external_locking=ext_locking
            )
        except linstor.LinstorError as e:
            raise ArgumentError(e.message)
        return self.handle_replies(args, replies)

    def create_exos(self, args):
        try:
            # no shared-space and no external locking. shared-space calculated by server, external locking not allowed
            props = {
                apiconsts.NAMESPC_EXOS + '/' + apiconsts.KEY_STOR_POOL_EXOS_ENCLOSURE: args.enclosure_name,
                apiconsts.NAMESPC_EXOS + '/' + apiconsts.KEY_STOR_POOL_EXOS_POOL_SN: args.pool_sn
            }
            replies = self.get_linstorapi().storage_pool_create(
                args.node_name,
                args.name,
                args.driver,
                args.enclosure_name + '_' + args.pool_sn,
                property_dict=props
            )
        except linstor.LinstorError as e:
            raise ArgumentError(e.message)
        return self.handle_replies(args, replies)

    def create_ebs(self, args):
        try:
            # no shared-space and no external locking. shared-space calculated by server, external locking not allowed
            ebs_remote_key = apiconsts.NAMESPC_STORAGE_DRIVER + '/' + apiconsts.NAMESPC_EBS + '/' + apiconsts.KEY_REMOTE
            props = {
                ebs_remote_key: args.ebs_remote_name
            }
            replies = self.get_linstorapi().storage_pool_create(
                args.node_name,
                args.name,
                linstor.StoragePoolDriver.EBS_INIT,
                None,
                property_dict=props
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

        show_props = self._append_show_props_hdr(tbl, args.show_props)

        storage_pool_resp = lstmsg  # type: StoragePoolListResponse

        tbl.set_groupby(args.groupby if args.groupby else [self._stor_pool_headers[0].name])

        errors = []
        for storpool in storage_pool_resp.storage_pools:
            driver_device = linstor.StoragePoolDriver.storage_props_to_driver_pool(
                storpool.provider_kind,
                storpool.properties)

            free_capacity = ""
            total_capacity = ""
            if not storpool.is_diskless() and storpool.free_space is not None and \
                    storpool.provider_kind != "EBS_TARGET":
                free_capacity = SizeCalc.approximate_size_string(storpool.free_space.free_capacity)
                total_capacity = SizeCalc.approximate_size_string(storpool.free_space.total_capacity)

            for error in storpool.reports:
                if error not in errors:
                    errors.append(error)

            state_str, state_color = self.get_replies_state(storpool.reports)
            row = [
                storpool.name,
                storpool.node_name,
                storpool.provider_kind,
                driver_device,
                free_capacity,
                total_capacity,
                storpool.supports_snapshots(),
                tbl.color_cell(state_str, state_color),
                storpool.free_space_mgr_name if ':' not in storpool.free_space_mgr_name else ''
            ]
            for sprop in show_props:
                row.append(storpool.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()
        for err in errors:
            Output.handle_ret(
                err,
                warn_as_error=args.warn_as_error,
                no_color=args.no_color
            )

    def list(self, args):
        args = self.merge_config_args('storage-pool.list', args)
        if args.from_file:
            lstmsg = [linstor.responses.StoragePoolListResponse(json.load(args.from_file))]
        else:
            lstmsg = self._linstor.storage_pool_list(args.nodes, args.storage_pools, args.props)
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_show(cls, args, lstmsg):
        result = []
        if lstmsg:
            response = lstmsg  # type: StoragePoolListResponse
            for stor_pool in response.storage_pools:
                result.append(stor_pool.properties)
        return result

    def print_props(self, args):
        lstmsg = self._linstor.storage_pool_list([args.node_name], [args.storage_pool_name])
        return self.output_props_list(args, lstmsg, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.storage_pool_modify(
            args.node_name,
            args.name,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)
