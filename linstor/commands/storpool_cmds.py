import argparse

import linstor
from linstor.commands import ArgumentError, Commands
from linstor.consts import NODE_NAME, STORPOOL_NAME
from linstor.sharedconsts import KEY_STOR_POOL_SUPPORTS_SNAPSHOTS
from linstor.utils import SizeCalc, namecheck


class StoragePoolCommands(Commands):
    _stor_pool_headers = [
        linstor.TableHeader("StoragePool"),
        linstor.TableHeader("Node"),
        linstor.TableHeader("Driver"),
        linstor.TableHeader("PoolName"),
        linstor.TableHeader("Free", alignment_text='>'),
        linstor.TableHeader("SupportsSnapshots")
    ]

    def __init__(self):
        super(StoragePoolCommands, self).__init__()

    def setup_commands(self, parser):

        # Storage pool subcommands
        sp_parser = parser.add_parser(
            Commands.STORAGE_POOL,
            aliases=["sp"],
            formatter_class=argparse.RawTextHelpFormatter,
            help="Storage pool subcommands")
        sp_subp = sp_parser.add_subparsers(
            title="Storage pool commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(
                [
                    Commands.Subcommands.Create,
                    Commands.Subcommands.List,
                    Commands.Subcommands.Delete,
                    Commands.Subcommands.SetProperties,
                    Commands.Subcommands.ListProperties,
                ]))

        # new-storpol
        p_new_storpool = sp_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
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
            nargs='?',
            help='Volumegroup/Pool name of the driver e.g. drbdpool')
        p_new_storpool.set_defaults(func=self.create)

        # remove-storpool
        # TODO description
        p_rm_storpool = sp_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
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
            'storage_pool_name',
            help="Storage pool for which to print the properties").completer = self.storage_pool_completer
        p_sp.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Name of the node for the storage pool').completer = self.node_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = sp_subp.add_parser(
            Commands.Subcommands.SetProperties.LONG,
            aliases=[Commands.Subcommands.SetProperties.SHORT],
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
        try:
            replies = self._linstor.storage_pool_create(args.node_name, args.name, driver, args.driver_pool_name)
        except linstor.linstorapi.LinstorError as e:
            raise ArgumentError(e.message)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.node_name for x in self._linstor.storage_pool_delete(subx, args.name)]
        return self.handle_replies(args, replies)

    def show(self, args, lstmsg):
        tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in self._stor_pool_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else [self._stor_pool_headers[0].name])

        for storpool in lstmsg.stor_pools:
            driver_device_prop = [x for x in storpool.props
                                  if x.key == self._linstor.get_driver_key(storpool.driver)]
            driver_device = driver_device_prop[0].value if driver_device_prop else ''

            supports_snapshots_prop = [x for x in storpool.static_traits if x.key == KEY_STOR_POOL_SUPPORTS_SNAPSHOTS]
            supports_snapshots = supports_snapshots_prop[0].value if supports_snapshots_prop else ''

            freespace = ""
            if storpool.driver != 'DisklessDriver' and storpool.HasField("free_space"):
                freespace = SizeCalc.approximate_size_string(storpool.free_space.free_space)

            tbl.add_row([
                storpool.stor_pool_name,
                storpool.node_name,
                storpool.driver,
                driver_device,
                freespace,
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
