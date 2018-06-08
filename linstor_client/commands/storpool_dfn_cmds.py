import linstor_client.argparse.argparse as argparse

import linstor_client
from linstor_client.commands import Commands
from linstor_client.consts import STORPOOL_NAME
from linstor_client.utils import namecheck


class StoragePoolDefinitionCommands(Commands):
    def __init__(self):
        super(StoragePoolDefinitionCommands, self).__init__()

    def setup_commands(self, parser):
        # storpool subcommands
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties
        ]

        spd_parser = parser.add_parser(
            Commands.STORAGE_POOL_DEF,
            aliases=["spd"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Storage pool definition subcommands")
        spd_subp = spd_parser.add_subparsers(
            title="Storage pool definition subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new-storpol definition
        p_new_storpool_dfn = spd_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Defines a Linstor storpool definition for use with linstor.')
        p_new_storpool_dfn.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the new storpool definition')
        p_new_storpool_dfn.set_defaults(func=self.create)

        # remove-storpool definition
        # TODO description
        p_rm_storpool_dfn = spd_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=' Removes a storage pool definition ')
        p_rm_storpool_dfn.add_argument('-q', '--quiet', action="store_true",
                                       help='Unless this option is used, linstor will issue a safety question '
                                       'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_storpool_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the storage pool to delete').completer = self.storage_pool_dfn_completer
        p_rm_storpool_dfn.set_defaults(func=self.delete)

        # list storpool definitions
        storpooldfngroupby = ('Name')
        storpooldfn_group_completer = Commands.show_group_completer(storpooldfngroupby, "groupby")

        p_lstorpooldfs = spd_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all storage pool definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lstorpooldfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lstorpooldfs.add_argument('-g', '--groupby', nargs='+',
                                    choices=storpooldfngroupby).completer = storpooldfn_group_completer
        p_lstorpooldfs.add_argument(
            '-R', '--storpool', nargs='+', type=namecheck(STORPOOL_NAME),
            help='Filter by list of storage pool'
        ).completer = self.storage_pool_dfn_completer
        p_lstorpooldfs.set_defaults(func=self.list)

        # show properties
        p_sp = spd_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given storage pool definition.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool definition for which to print the properties"
        ).completer = self.storage_pool_dfn_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = spd_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            description='Sets properties for the given storage pool definition.')
        p_setprop.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the storage pool definition'
        ).competer = self.storage_pool_dfn_completer
        Commands.add_parser_keyvalue(p_setprop, "storagepool-definition")
        p_setprop.set_defaults(func=self.set_props)

        self.check_subcommands(spd_subp, subcmds)

    def create(self, args):
        replies = self._linstor.storage_pool_dfn_create(args.name)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.name for x in self._linstor.storage_pool_dfn_delete(subx)]
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("StoragePool")
        for storpool_dfn in lstmsg.stor_pool_dfns:
            tbl.add_row([
                storpool_dfn.stor_pool_name
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.storage_pool_dfn_list()

        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for storpool_dfn in lstmsg.stor_pool_dfns:
                if storpool_dfn.stor_pool_name == args.storage_pool_name:
                    result.append(storpool_dfn.props)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.storage_pool_dfn_list()

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.storage_pool_dfn_modify(args.name, mod_prop_dict['pairs'], mod_prop_dict['delete'])
        return self.handle_replies(args, replies)
