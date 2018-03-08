import linstor
from linstor.commands import Commands
from linstor.utils import namecheck
from linstor.consts import ExitCode
from linstor.consts import STORPOOL_NAME


class StoragePoolDefinitionCommands(Commands):
    def __init__(self):
        super(StoragePoolDefinitionCommands, self).__init__()

    def setup_commands(self, parser):
        # new-storpol definition
        p_new_storpool_dfn = parser.add_parser(
            Commands.CREATE_STORAGE_POOL_DEF,
            aliases=['crtstorpooldfn'],
            description='Defines a Linstor storpool definition for use with linstor.')
        p_new_storpool_dfn.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the new storpool definition')
        p_new_storpool_dfn.set_defaults(func=self.create)

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
            help='Name of the storage pool to delete').completer = self.storage_pool_dfn_completer
        p_rm_storpool_dfn.set_defaults(func=self.delete)

        # list storpool definitions
        storpooldfngroupby = ('Name')
        storpooldfn_group_completer = Commands.show_group_completer(storpooldfngroupby, "groupby")

        p_lstorpooldfs = parser.add_parser(
            Commands.LIST_STORAGE_POOL_DEF,
            aliases=['dspstorpooldfn'],
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
        p_sp = parser.add_parser(
            Commands.GET_STORAGE_POOL_DEF_PROPS,
            aliases=['dspstorpooldfnprp'],
            description="Prints all properties of the given storage pool definition.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'storage_pool_name',
            help="Storage pool definition for which to print the properties"
        ).completer = self.storage_pool_dfn_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        # disabled until there are properties
        # p_setprop = parser.add_parser(
        #     Commands.SET_STORAGE_POOL_DEF_PROP,
        #     aliases=['setstorpooldfnprp'],
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
            aliases=['setstorpooldfnauxprp'],
            description='Sets auxiliary properties for the given storage pool definition.')
        p_setauxprop.add_argument(
            'name',
            type=namecheck(STORPOOL_NAME),
            help='Name of the storage pool definition'
        ).competer = self.storage_pool_dfn_completer
        Commands.add_parser_keyvalue(p_setauxprop)
        p_setauxprop.set_defaults(func=self.set_prop_aux)

    def create(self, args):
        replies = self._linstor.storage_pool_dfn_create(args.name)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.name for x in self._linstor.storage_pool_dfn_delete(subx)]
        return self.handle_replies(args, replies)

    def list(self, args):
        lstmsg = self._linstor.storage_pool_dfn_list()

        if lstmsg:
            if args.machine_readable:
                self._print_machine_readable([lstmsg])
            else:
                tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
                tbl.add_column("StoragePool")
                for storpool_dfn in lstmsg.stor_pool_dfns:
                    tbl.add_row([
                        storpool_dfn.stor_pool_name
                    ])
                tbl.show()

        return ExitCode.OK

    def print_props(self, args):
        lstmsg = self._linstor.storage_pool_dfn_list()

        result = []
        if lstmsg:
            for storpool_dfn in lstmsg.stor_pool_dfns:
                if storpool_dfn.stor_pool_name == args.storage_pool_name:
                    result.append(storpool_dfn.props)
                    break

        Commands._print_props(result, args)
        return ExitCode.OK

    def set_props(self, args):
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.storage_pool_dfn_modify(args.name, mod_prop_dict['pairs'], mod_prop_dict['delete'])
        return self.handle_replies(args, replies)
