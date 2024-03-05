import linstor_client.argparse.argparse as argparse

import linstor_client
# flake8: noqa
from linstor.responses import VolumeGroupResponse
from linstor_client.commands import Commands, DrbdOptions


class VolumeGroupCommands(Commands):
    OBJECT_NAME = 'volume-definition'

    _vlm_grp_headers = [
        linstor_client.TableHeader("VolumeNr"),
        linstor_client.TableHeader("Flags")
    ]

    def __init__(self):
        super(VolumeGroupCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions
        ]

        # volume group subcommands
        vlm_grp_parser = parser.add_parser(
            Commands.VOLUME_GRP,
            aliases=["vg"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resource definition subcommands")

        vlm_grp_subp = vlm_grp_parser.add_subparsers(
            title="resource definition subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        #  ------------ CREATE START
        p_new_vlm_grp = vlm_grp_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a LINSTOR volume group.')
        p_new_vlm_grp.add_argument('name',
                                   type=str,
                                   help='Name of the resource group.')
        p_new_vlm_grp.add_argument('-n', '--vlmnr', type=int)
        p_new_vlm_grp.add_argument('--gross', action="store_true", help="Size for this volume is gross size.")
        p_new_vlm_grp.set_defaults(func=self.create)
        #  ------------ CREATE END

        #  ------------ DELETE START
        p_rm_vlm_grp = vlm_grp_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=" Removes a volume group from the LINSTOR cluster.")
        p_rm_vlm_grp.add_argument(
            'name',
            help='Name of the resource group').completer = self.resource_grp_completer
        p_rm_vlm_grp.add_argument(
            'volume_nr',
            type=int,
            help="Volume number to delete.")
        p_rm_vlm_grp.set_defaults(func=self.delete)
        #  ------------ DELETE END

        #  ------------ LIST START
        vlm_grp_groupby = [x.name.lower() for x in self._vlm_grp_headers]
        vlm_grp_group_completer = Commands.show_group_completer(vlm_grp_groupby, "groupby")

        p_lvlmgrps = vlm_grp_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Lists all volume groups for a specified resource group. By default, the list is printed as a human readable table.')
        p_lvlmgrps.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lvlmgrps.add_argument('-g', '--groupby', nargs='+',
                                choices=vlm_grp_groupby,
                                type=str.lower).completer = vlm_grp_group_completer
        p_lvlmgrps.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lvlmgrps.add_argument('name', help="Resource group name.")
        p_lvlmgrps.set_defaults(func=self.list)
        #  ------------ LIST END

        #  ------------ LISTPROPS START
        p_sp = vlm_grp_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Shows all properties of the specified volume group.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'name',
            help="Resource group for which to print the properties"
        ).completer = self.resource_grp_completer
        p_sp.add_argument(
            'volume_nr',
            type=int,
            help="Volume number")
        p_sp.set_defaults(func=self.print_props)
        #  ------------ LISTPROPS END

        #  ------------ SETPROPS START
        p_setprop = vlm_grp_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given volume group.')
        p_setprop.add_argument('name', type=str, help='Name of the resource group')
        p_setprop.add_argument(
            'volume_nr',
            type=int,
            help="Volume number")
        Commands.add_parser_keyvalue(p_setprop, self.OBJECT_NAME)
        p_setprop.set_defaults(func=self.set_props)
        #  ------------ SETPROPS END

        #  ------------ SETDRBDOPTS START
        p_drbd_opts = vlm_grp_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description=DrbdOptions.description("resource")
        )
        p_drbd_opts.add_argument(
            'name',
            type=str,
            help="Resource group name"
        ).completer = self.resource_grp_completer
        p_drbd_opts.add_argument(
            'volume_nr',
            type=int,
            help="Volume number")
        DrbdOptions.add_arguments(p_drbd_opts, self.OBJECT_NAME)
        p_drbd_opts.set_defaults(func=self.set_drbd_opts)
        #  ------------ SETDRBDOPTS END

        self.check_subcommands(vlm_grp_subp, subcmds)

    def create(self, args):
        replies = self._linstor.volume_group_create(
            args.name,
            volume_nr=args.vlmnr,
            gross=args.gross
        )
        return self.handle_replies(args, replies)

    def delete(self, args):
        replies = self._linstor.volume_group_delete(args.name, args.volume_nr)
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        vlm_grps = lstmsg  # type: VolumeGroupResponse
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        for hdr in cls._vlm_grp_headers:
            tbl.add_header(hdr)

        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])

        for vlm_grp in vlm_grps.volume_groups:
            row = [str(vlm_grp.number), ", ".join(vlm_grp.flags)]
            for sprop in show_props:
                row.append(vlm_grp.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        args = self.merge_config_args('volume-group.list', args)
        lstmsg = [self._linstor.volume_group_list_raise(args.name)]
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_list(cls, args, lstmsg):
        """

        :param args:
        :param linstor.responses.VolumeGroupResponse lstmsg:
        :return:
        """
        result = []
        if lstmsg:
            for vlm_grp in lstmsg.volume_groups:
                if vlm_grp.number == args.volume_nr:
                    result.append(vlm_grp.properties)
                    break
        return result

    def print_props(self, args):
        lstmsg = [self._linstor.volume_group_list_raise(args.name)]

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.volume_group_modify(
            args.name,
            args.volume_nr,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def set_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['name']  # remove resource group key
        del a['volume-nr']

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = self._linstor.volume_group_modify(
            args.name,
            args.volume_nr,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)
