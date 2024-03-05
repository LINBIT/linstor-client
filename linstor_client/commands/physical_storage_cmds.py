import linstor_client.argparse.argparse as argparse

from linstor_client.commands import Commands
from linstor_client import Table, TableHeader


class PhysicalStorageCommands(Commands):
    _phys_storage_headers = [
        TableHeader("Size"),
        TableHeader("Rotational"),
        TableHeader("Nodes")
    ]

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.CreateDevicePool
        ]

        phys_parser = parser.add_parser(
            Commands.PHYSICAL_STORAGE,
            aliases=["ps"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Physical-storage subcommands"
        )

        phys_subp = phys_parser.add_subparsers(
            title="Physical-storage commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        p_lphys = phys_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all physical storage available for LINSTOR use. By default, the list is '
            'printed as a human readable table. Criteria are:\n'
            '  * Device size must be greater than 1GiB\n'
            '  * Device must be a root device, for example, `/dev/vda`, `/dev/sda`, and not have any children.\n'
            '  * Device must not have any file system or other `blkid` marker.\n'
            '  * Device must not be an existing DRBD device.')
        p_lphys.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lphys.set_defaults(func=self.list)

        p_create = phys_subp.add_parser(
            Commands.Subcommands.CreateDevicePool.LONG,
            aliases=[Commands.Subcommands.CreateDevicePool.SHORT],
            description='Creates an LVM or ZFS(thin) pool with an optional VDO on the device.'
        )
        p_create.add_argument('provider_kind',
                              choices=[x.lower() for x in ["LVM", "LVMTHIN", "ZFS", "ZFSTHIN", "SPDK"]],
                              type=str.lower,
                              help='Provider kind')
        p_create.add_argument('node_name', help="Node name").completer = self.node_completer
        p_create.add_argument('device_paths', nargs='+', help="List of full device paths to use")
        p_create.add_argument(
            '--pool-name',
            required=True,
            help="Name of the new pool"
        )
        p_create.add_argument('--vdo-enable', action="store_true", help="Use VDO.(only Centos/RHEL)")
        p_create.add_argument('--vdo-logical-size', help="VDO logical size.")
        p_create.add_argument('--vdo-slab-size', help="VDO slab size.")
        p_create.add_argument("--storage-pool", help="Create a Linstor storage pool with the given name")
        p_create.add_argument('--sed',
                              action="store_true",
                              help="Setup self encrypting drive with Linstor. "
                                   + "Needs SED/OPAL2 capable drive and sedutil installed and --storage-pool")
        p_create.set_defaults(func=self.create_device_pool)

        self.check_subcommands(phys_subp, subcmds)

    @classmethod
    def show_physical_storage(cls, args, physical_storage_list):
        """

        :param args:
        :param PhysicalStorageList physical_storage_list:
        :return:
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._phys_storage_headers:
            tbl.add_header(hdr)

        for devices in physical_storage_list.physical_devices:
            node_rows = []
            for node, node_devices in devices.nodes.items():
                s = node + '['
                node_out_devs = []
                for device_obj in node_devices:
                    ns = device_obj.device
                    node_data = []
                    if device_obj.serial:
                        node_data.append(device_obj.serial)
                    if device_obj.wwn:
                        node_data.append(device_obj.wwn)
                    if node_data:
                        ns += '(' + ','.join(node_data) + ')'
                    node_out_devs.append(ns)
                s += ','.join(node_out_devs) + ']'
                node_rows.append(s)
            tbl.add_row([
                devices.size,
                devices.rotational,
                "\n".join(node_rows)
            ])

        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.physical_storage_list()

        return self.output_list(args, [lstmsg], self.show_physical_storage)

    def create_device_pool(self, args):
        replies = self.get_linstorapi().physical_storage_create_device_pool(
            node_name=args.node_name,
            provider_kind=args.provider_kind,
            device_paths=args.device_paths,
            pool_name=args.pool_name,
            vdo_enable=args.vdo_enable,
            vdo_logical_size_kib=Commands.parse_size_str(args.vdo_logical_size, "KiB"),
            vdo_slab_size_kib=Commands.parse_size_str(args.vdo_slab_size, "KiB"),
            storage_pool_name=args.storage_pool,
            sed=args.sed,
        )
        return self.handle_replies(args, replies)
