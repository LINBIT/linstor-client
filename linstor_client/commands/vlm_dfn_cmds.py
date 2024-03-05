import re
import getpass

import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor import SizeCalc
from linstor.sharedconsts import FLAG_DELETE, FLAG_RESIZE, FLAG_GROSS_SIZE
from linstor_client.commands import Commands, DrbdOptions
from linstor_client.consts import Color, ExitCode
from linstor_client.utils import LinstorClientError


class VolumeDefinitionCommands(Commands):
    OBJECT_NAME = 'volume-definition'

    _vlm_dfn_headers = [
        linstor_client.TableHeader("ResourceName"),
        linstor_client.TableHeader("VolumeNr"),
        linstor_client.TableHeader("VolumeMinor"),
        linstor_client.TableHeader("Size"),
        linstor_client.TableHeader("Gross"),
        linstor_client.TableHeader("State", color=Color.DARKGREEN)
    ]

    VOLUME_SIZE_HELP = \
        'Size of the volume. ' \
        'Valid units: ' + SizeCalc.UNITS_LIST_STR + '. ' \
        'The default unit is GiB (2 ^ 30 bytes). ' \
        'The unit can be specified with a postfix. ' \
        'LINSTOR\'s internal granularity for the capacity of volumes is one ' \
        'kibibyte (2 ^ 10 bytes). The actual size used by LINSTOR ' \
        'is the smallest natural number of kibibytes that is large enough to ' \
        'accommodate a volume of the requested size in the specified size unit.'

    def __init__(self):
        super(VolumeDefinitionCommands, self).__init__()

    def setup_commands(self, parser):
        # volume definition subcommands
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetSize,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions,
            Commands.Subcommands.ModifyPassphrase,
        ]

        vol_def_parser = parser.add_parser(
            Commands.VOLUME_DEF,
            aliases=["vd"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Volume definition subcommands")

        vol_def_subp = vol_def_parser.add_subparsers(
            title="Volume definition commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        p_new_vol = vol_def_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a volume with a capacity of `size` for use with '
            'LINSTOR. If the resource `resource_name` exists already, a new volume is '
            'added to that resource, otherwise the resource is assigned automatically '
            'with default settings. Unless `--minor MINOR` is specified, a minor number '
            "for the volume's DRBD block device is assigned automatically by the "
            'LINSTOR server.')
        p_new_vol.add_argument(
            '--storage-pool', '-s',
            type=str,
            help="Storage pool name to use.").completer = self.storage_pool_dfn_completer
        p_new_vol.add_argument('-n', '--vlmnr', type=int)
        p_new_vol.add_argument('-m', '--minor', type=int)
        p_new_vol.add_argument(
            '--encrypt',
            action="store_true",
            help="DEPCRECATED - use --layer-list ...,LUKS,... instead (when creating resource /-definition)")
        p_new_vol.add_argument('--gross', action="store_true")
        p_new_vol.add_argument(
            '--passphrase',
            type=str,
            action='store',
            nargs='?',
            const='',
            help='User provided passphrase for encrypted volumes. If not provided LINSTOR will create one',
        )
        p_new_vol.add_argument('resource_name', type=str,
                               help='Name of an existing resource').completer = self.resource_dfn_completer
        p_new_vol.add_argument(
            'size',
            help=VolumeDefinitionCommands.VOLUME_SIZE_HELP
        ).completer = VolumeDefinitionCommands.size_completer
        p_new_vol.set_defaults(func=self.create)

        # remove-volume definition
        p_rm_vol = vol_def_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Removes a volume definition from the LINSTOR cluster, and removes '
            'the volume definition from the resource definition. The volume is '
            'undeployed from all nodes and the volume entry is marked for removal '
            "from the resource definition in LINSTOR's data tables. After all "
            'nodes have undeployed the volume, the volume entry is removed from '
            'the resource definition.')
        p_rm_vol.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_rm_vol.add_argument('resource_name',
                              help='Resource name of the volume definition'
                              ).completer = self.resource_dfn_completer
        p_rm_vol.add_argument(
            'volume_nr',
            type=int,
            help="Volume number to delete.")
        p_rm_vol.set_defaults(func=self.delete)

        # list volume definitions
        vlm_dfn_groupby = [x.name.lower() for x in self._vlm_dfn_headers]
        vlm_dfn_group_completer = Commands.show_group_completer(vlm_dfn_groupby, "groupby")

        p_lvols = vol_def_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description=' Prints a list of all volume definitions known to LINSTOR. '
            'By default, the list is printed as a human readable table.')
        p_lvols.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lvols.add_argument('-g', '--groupby', nargs='+',
                             choices=vlm_dfn_groupby,
                             type=str.lower).completer = vlm_dfn_group_completer
        p_lvols.add_argument('-r', '--resource-definitions', nargs='+', type=str,
                             help='Filter by list of resource definitions').completer = self.resource_dfn_completer
        p_lvols.add_argument('-e', '--external-name', action="store_true", help='Show user specified name.')
        p_lvols.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lvols.set_defaults(func=self.list)

        # show properties
        p_sp = vol_def_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given volume definition.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'resource_definition',
            help="Resource definition").completer = self.resource_dfn_completer
        p_sp.add_argument(
            'volume_nr',
            type=int,
            help="Volume number")
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = vol_def_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given volume definition.')
        p_setprop.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_dfn_completer
        p_setprop.add_argument(
            'volume_nr',
            type=int,
            help="Volume number")
        Commands.add_parser_keyvalue(p_setprop, "volume-definition")
        p_setprop.set_defaults(func=self.set_props)

        p_drbd_opts = vol_def_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description=DrbdOptions.description("volume")
        )
        p_drbd_opts.add_argument(
            'resource_name',
            type=str,
            help="Resource name"
        ).completer = self.resource_dfn_completer
        p_drbd_opts.add_argument(
            'volume_nr',
            type=int,
            help="Volume number"
        )
        DrbdOptions.add_arguments(p_drbd_opts, self.OBJECT_NAME)
        p_drbd_opts.set_defaults(func=self.set_drbd_opts)

        # set size
        p_set_size = vol_def_subp.add_parser(
            Commands.Subcommands.SetSize.LONG,
            aliases=[Commands.Subcommands.SetSize.SHORT],
            description='Change the size of a volume. '
            'Decreasing the size is only supported when the specified resource definition does not have any resources. '
            'Increasing the size is supported even when the associated resource definition has resources. '
            'File systems present on the volumes will not be resized.')
        p_set_size.add_argument('resource_name', type=str,
                                help='Name of an existing resource').completer = self.resource_dfn_completer
        p_set_size.add_argument(
            'volume_nr',
            type=int,
            help="Volume number"
        )
        p_set_size.add_argument(
            'size',
            help=VolumeDefinitionCommands.VOLUME_SIZE_HELP
        ).completer = VolumeDefinitionCommands.size_completer
        p_set_size.add_argument('--gross', action="store_true")
        p_set_size.set_defaults(func=self.set_volume_size)

        # modify passphrase
        p_modifypass = vol_def_subp.add_parser(
            Commands.Subcommands.ModifyPassphrase.LONG,
            aliases=[Commands.Subcommands.ModifyPassphrase.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given volume definition.')
        p_modifypass.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_dfn_completer
        p_modifypass.add_argument(
            'volume_nr',
            type=int,
            help="Volume number")
        p_modifypass.add_argument(
            'new_passphrase',
            nargs='?',
            help="New volume definition passphrase",
        )
        p_modifypass.set_defaults(func=self.modify_pass)

        self.check_subcommands(vol_def_subp, subcmds)

    def create(self, args):
        passphrase = None
        if args.passphrase != '':
            passphrase = args.passphrase
        elif args.passphrase == '':
            # read from keyboard
            passphrase = self._ask_passphrase()
        replies = self._linstor.volume_dfn_create(
            args.resource_name,
            Commands.parse_size_str(args.size),
            args.vlmnr,
            args.minor,
            args.encrypt,
            args.storage_pool,
            args.gross,
            passphrase=passphrase
        )
        return self.handle_replies(args, replies)

    def delete(self, args):
        async_flag = vars(args)["async"]

        replies = self._linstor.volume_dfn_delete(args.resource_name, args.volume_nr, async_flag)
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        vlm_dfn_hdrs = list(cls._vlm_dfn_headers)
        if args.external_name:
            vlm_dfn_hdrs.insert(1, linstor_client.TableHeader("External"))
        for hdr in vlm_dfn_hdrs:
            tbl.add_header(hdr)

        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])
        for rsc_dfn in lstmsg.resource_definitions:
            for vlmdfn in rsc_dfn.volume_definitions:
                state = tbl.color_cell("ok", Color.DARKGREEN)
                if FLAG_DELETE in vlmdfn.flags:
                    state = tbl.color_cell("DELETING", Color.RED)
                elif FLAG_RESIZE in vlmdfn.flags:
                    state = tbl.color_cell("resizing", Color.DARKPINK)

                drbd_data = vlmdfn.drbd_data
                row = [
                    rsc_dfn.name,
                    vlmdfn.number,
                    drbd_data.minor if drbd_data else "",
                    SizeCalc.approximate_size_string(vlmdfn.size),
                    "+" if FLAG_GROSS_SIZE in vlmdfn.flags else "",
                    state
                ]
                for sprop in show_props:
                    row.append(vlmdfn.properties.get(sprop, ''))
                tbl.add_row(row)
        tbl.show()

    def list(self, args):
        args = self.merge_config_args('volume-definition.list', args)
        lstmsg = self._linstor.resource_dfn_list(
            query_volume_definitions=True,
            filter_by_resource_definitions=args.resource_definitions
        )
        return self.output_list(args, lstmsg, self.show)

    @staticmethod
    def size_completer(prefix, **kwargs):
        choices = [unit_str for unit_str, _ in SizeCalc.UNITS_MAP.values()]
        m = re.match(r'(\d+)(\D*)', prefix)

        digits = m.group(1)
        unit = m.group(2)

        if unit and unit != "":
            p_units = [x for x in choices if x.startswith(unit)]
        else:
            p_units = choices

        return [digits + u for u in p_units]

    @classmethod
    def _props_show(cls, args, lstmsg):
        result = []
        if lstmsg and lstmsg.resource_definitions:
            for vlmdfn in lstmsg.resource_definitions[0].volume_definitions:
                if vlmdfn.number == args.volume_nr:
                    result.append(vlmdfn.properties)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_dfn_list(
            query_volume_definitions=True,
            filter_by_resource_definitions=[args.resource_definition]
        )

        return self.output_props_list(args, lstmsg, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.volume_dfn_modify(
            args.resource_name,
            args.volume_nr,
            set_properties=mod_prop_dict['pairs'],
            delete_properties=mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def set_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']  # remove resource name key
        del a['volume-nr']

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = self._linstor.volume_dfn_modify(
            args.resource_name,
            args.volume_nr,
            set_properties=mod_props,
            delete_properties=del_props
        )
        return self.handle_replies(args, replies)

    def set_volume_size(self, args):
        replies = self._linstor.volume_dfn_modify(
            args.resource_name,
            args.volume_nr,
            size=self.parse_size_str(args.size),
            gross=args.gross
        )
        return self.handle_replies(args, replies)

    @staticmethod
    def _ask_passphrase():
        passphrase = getpass.getpass("Passphrase: ")
        passphrase2 = getpass.getpass("Retype new passphrase: ")
        if passphrase != passphrase2:
            raise LinstorClientError("Passphrase doesn't match.", ExitCode.ARGPARSE_ERROR)
        return passphrase

    def modify_pass(self, args):
        if args.new_passphrase:
            passphrase = args.new_passphrase
        else:
            # read from keyboard
            passphrase = self._ask_passphrase()

        replies = self._linstor.volume_dfn_modify_passphrase(
            args.resource_name,
            args.volume_nr,
            new_passphrase=passphrase
        )
        return self.handle_replies(args, replies)
