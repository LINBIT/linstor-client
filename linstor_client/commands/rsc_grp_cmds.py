import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
from linstor import SizeCalc
# flake8: noqa
import json
from linstor.responses import ResourceGroupResponse
from linstor_client.commands import Commands, DrbdOptions
from linstor_client.consts import ExitCode
from linstor_client.utils import rangecheck


class ResourceGroupCommands(Commands):
    OBJECT_NAME = 'resource-definition'  # resource-definition is used here for properties

    _rsc_grp_headers = [
        linstor_client.TableHeader("ResourceGroup"),
        linstor_client.TableHeader("SelectFilter"),
        linstor_client.TableHeader("VlmNrs"),
        linstor_client.TableHeader("Description")
    ]

    def __init__(self):
        super(ResourceGroupCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.Modify,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions,
            Commands.Subcommands.Spawn,
            Commands.Subcommands.QueryMaxVlmSize,
            Commands.Subcommands.QuerySizeInfo,
            Commands.Subcommands.Adjust
        ]

        # Resource group subcommands
        res_grp_parser = parser.add_parser(
            Commands.RESOURCE_GRP,
            aliases=["rg"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resource group subcommands")

        res_grp_subp = res_grp_parser.add_subparsers(
            title="resource group subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        #  ------------ CREATE START
        p_new_res_grp = res_grp_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a LINSTOR resource group.')
        p_new_res_grp.add_argument(
            '-d', '--description',
            help="Description for the resource group."
        )
        p_new_res_grp.add_argument(
            '--peer-slots',
            type=rangecheck(1, 31),
            help='(DRBD) peer slots for new resources')
        self.add_auto_select_argparse_arguments(p_new_res_grp, use_place_count=True)
        p_new_res_grp.add_argument('name',
                                   type=str,
                                   help='Name of the resource group.')
        p_new_res_grp.set_defaults(func=self.create)
        #  ------------ CREATE END

        #  ------------ MODIFY START
        p_mod_res_grp = res_grp_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modifies the specified attribute(s) of a LINSTOR resource group.')
        p_mod_res_grp.add_argument(
            '-d', '--description',
            help="Description for the resource group."
        )
        p_mod_res_grp.add_argument(
            '--peer-slots',
            type=rangecheck(1, 31),
            help='(DRBD) peer slots for new resources')
        self.add_auto_select_argparse_arguments(p_mod_res_grp, use_place_count=True)
        p_mod_res_grp.add_argument(
            'name',
            help='Name of the resource group').completer = self.resource_grp_completer
        p_mod_res_grp.set_defaults(func=self.modify)
        #  ------------ MODIFY END

        #  ------------ DELETE START
        p_rm_res_grp = res_grp_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=" Removes a resource group from the LINSTOR cluster.")
        p_rm_res_grp.add_argument(
            'name',
            help='Name of the resource group to delete').completer = self.resource_grp_completer
        p_rm_res_grp.set_defaults(func=self.delete)
        #  ------------ DELETE END

        #  ------------ LIST START
        rsc_grp_groupby = [x.name.lower() for x in self._rsc_grp_headers]
        rsc_grp_group_completer = Commands.show_group_completer(rsc_grp_groupby, "groupby")

        p_lrscgrps = res_grp_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource groups known to '
            'LINSTOR. By default, the list is printed as a human readable table.')
        p_lrscgrps.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lrscgrps.add_argument('-g', '--groupby', nargs='+',
                                choices=rsc_grp_groupby,
                                type=str.lower).completer = rsc_grp_group_completer
        p_lrscgrps.add_argument('-r', '--resource-groups', nargs='+', type=str,
                                help='Filter by list of resource groups').completer = self.resource_grp_completer
        p_lrscgrps.add_argument('--props', nargs='+', type=str, help='Filter list by object properties')
        p_lrscgrps.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lrscgrps.add_argument(
            '--from-file',
            type=argparse.FileType('r'),
            help="Read data to display from the given json file",
        )
        p_lrscgrps.set_defaults(func=self.list)
        #  ------------ LIST END

        #  ------------ LISTPROPS START
        p_sp = res_grp_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties set on a given resource group.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'name',
            help="Resource group for which to print the properties"
        ).completer = self.resource_grp_completer
        p_sp.set_defaults(func=self.print_props)
        #  ------------ LISTPROPS END

        #  ------------ SETPROPS START
        p_setprop = res_grp_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given resource group.')
        p_setprop.add_argument(
            'name',
            type=str,
            help='Name of the resource group').completer = self.resource_grp_completer
        Commands.add_parser_keyvalue(p_setprop, self.OBJECT_NAME)
        p_setprop.set_defaults(func=self.set_props)
        #  ------------ SETPROPS END

        #  ------------ SETDRBDOPTS START
        p_drbd_opts = res_grp_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description=DrbdOptions.description("resource")
        )
        p_drbd_opts.add_argument(
            'name',
            type=str,
            help="Resource group name"
        ).completer = self.resource_grp_completer
        DrbdOptions.add_arguments(p_drbd_opts, self.OBJECT_NAME)
        p_drbd_opts.set_defaults(func=self.set_drbd_opts)
        #  ------------ SETDRBDOPTS END

        #  ------------ SPAWN START
        p_spawn = res_grp_subp.add_parser(
            Commands.Subcommands.Spawn.LONG,
            aliases=[Commands.Subcommands.Spawn.SHORT],
            description="Spawns a new resource with the settings of the specified resource group."
        )
        p_spawn.add_argument(
            '-p', '--partial', action='store_true', help="Allow mismatching volume sizes."
        )
        p_spawn.add_argument(
            '-d', '--definition-only', action='store_true', help="Do not auto-place resource, only create definitions"
        )
        p_spawn.add_argument(
            '--volume-passphrase', nargs='*', help="User provided volume passphrases"
        )
        p_spawn.add_argument(
            'resource_group_name', help="Resource group name to spawn from."
        ).completer = self.resource_grp_completer
        p_spawn.add_argument(
            'resource_definition_name',
            help="New Resource definition name to create. Will be ignored if EXTERNAL_NAME is set."
        )
        p_spawn.add_argument(
            '--external-name', type=str, help="User specified name"
        )
        p_spawn.add_argument(
            'volume_sizes',
            nargs='*'
        )
        p_spawn.add_argument(
            '--peer-slots',
            type=rangecheck(1, 31),
            help='(DRBD) peer slots for new resources')
        self.add_auto_select_argparse_arguments(p_spawn, use_place_count=True, use_p_for_providers=False)
        p_spawn.set_defaults(func=self.spawn)
        #  ------------ SPAWN END

        #  ------------ QMVS START
        p_qmvs = res_grp_subp.add_parser(
            Commands.Subcommands.QueryMaxVlmSize.LONG,
            aliases=[Commands.Subcommands.QueryMaxVlmSize.SHORT],
            description="[DEPRECATED] Use `linstor resource-group query-size-info` instead. Shows maximum volume size information for a specified resource group.",
        )
        p_qmvs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_qmvs.add_argument(
            'resource_group_name', help="Resource group name to read auto-config settings from"
        ).completer = self.resource_grp_completer
        p_qmvs.set_defaults(func=self.qmvs)
        #  ------------ QMVS END

        #  ------------ QSI START
        p_qsi = res_grp_subp.add_parser(
            Commands.Subcommands.QuerySizeInfo.LONG,
            aliases=[Commands.Subcommands.QuerySizeInfo.SHORT],
            description="Shows volume size information for a specified resource group."
        )
        p_qsi.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_qsi.add_argument(
            'resource_group_name', help="Resource group name to read auto-config settings from"
        ).completer = self.resource_grp_completer
        self.add_auto_select_argparse_arguments(p_qsi, use_place_count=True, use_p_for_providers=False)
        p_qsi.set_defaults(func=self.qsi)
        #  ------------ QSI END

        #  ------------ ADJUST START
        p_adjust = res_grp_subp.add_parser(
            Commands.Subcommands.Adjust.LONG,
            aliases=[Commands.Subcommands.Adjust.SHORT],
            description="Adjusts all resource definitions of the given resource group.\n"
                        "CAUTION: This operation might take a long time and even exceed the default five minute timeout!"
        )
        p_adjust.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_adjust.add_argument(
            'resource_group_name',
            nargs="?",
            default=None,
            help="Resource group to adjust. If omitted, all resource groups will be adjusted"
        ).completer = self.resource_grp_completer
        # p_adjust.add_argument('-o', '--overprovision',
        #                       help='Multiplier of thin storage pool\'s free space. Default: 2.0')
        p_adjust.set_defaults(func=self.adjust)
        #  ------------ ADJUST END

        self.check_subcommands(res_grp_subp, subcmds)

    def create(self, args):
        replies = self._linstor.resource_group_create(
            args.name,
            description=args.description,
            place_count=args.place_count,
            storage_pool=args.storage_pool,
            do_not_place_with=self.prepare_argparse_list(args.do_not_place_with),
            do_not_place_with_regex=args.do_not_place_with_regex,
            replicas_on_same=self.prepare_argparse_list(args.replicas_on_same, linstor.consts.NAMESPC_AUXILIARY + '/'),
            replicas_on_different=self.prepare_argparse_list(
                args.replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/'),
            diskless_on_remaining=self.parse_diskless_on_remaining(args),
            layer_list=self.prepare_argparse_list(args.layer_list),
            provider_list=self.prepare_argparse_list(args.providers),
            diskless_storage_pool=self.prepare_argparse_list(args.diskless_storage_pool),
            peer_slots=args.peer_slots
        )
        return self.handle_replies(args, replies)

    def modify(self, args):
        replies = self._linstor.resource_group_modify(
            args.name,
            description=args.description,
            place_count=args.place_count,
            storage_pool=args.storage_pool,
            do_not_place_with=self.prepare_argparse_list(args.do_not_place_with),
            do_not_place_with_regex=args.do_not_place_with_regex,
            replicas_on_same=self.prepare_argparse_list(args.replicas_on_same, linstor.consts.NAMESPC_AUXILIARY + '/'),
            replicas_on_different=self.prepare_argparse_list(
                args.replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/'),
            diskless_on_remaining=self.parse_diskless_on_remaining(args),
            layer_list=args.layer_list,
            provider_list=args.providers,
            property_dict={},
            delete_props=[],
            diskless_storage_pool=self.prepare_argparse_list(args.diskless_storage_pool),
            peer_slots=args.peer_slots
        )
        return self.handle_replies(args, replies)

    def delete(self, args):
        replies = self._linstor.resource_group_delete(args.name)
        return self.handle_replies(args, replies)

    def show(self, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        for hdr in self._rsc_grp_headers:
            tbl.add_header(hdr)

        show_props = self._append_show_props_hdr(tbl, args.show_props)

        rsc_grps = lstmsg  # type: ResourceGroupResponse

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])

        for rsc_grp in rsc_grps.resource_groups:
            vlm_grps = []
            if not args.from_file:
                vlm_grps = self.get_linstorapi().volume_group_list_raise(rsc_grp.name).volume_groups
            row = [
                rsc_grp.name,
                str(rsc_grp.select_filter),
                ",".join([str(x.number) for x in vlm_grps]),
                rsc_grp.description
            ]
            for sprop in show_props:
                row.append(rsc_grp.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        args = self.merge_config_args('resource-group.list', args)
        if args.from_file:
            lstmsg = [linstor.responses.ResourceGroupResponse(json.load(args.from_file))]
        else:
            lstmsg = [self._linstor.resource_group_list_raise(args.resource_groups, filter_by_props=args.props)]
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_show(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc_grp in lstmsg.resource_groups:
                result.append(rsc_grp.properties)
        return result

    def print_props(self, args):
        lstmsg = [self._linstor.resource_group_list_raise(filter_by_resource_groups=[args.name])]

        return self.output_props_list(args, lstmsg, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.resource_group_modify(
            args.name,
            property_dict=mod_prop_dict['pairs'],
            delete_props=mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def set_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['name']  # remove resource group key

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = self._linstor.resource_group_modify(
            args.name,
            property_dict=mod_props,
            delete_props=del_props
        )
        return self.handle_replies(args, replies)

    def spawn(self, args):
        replies = self.get_linstorapi().resource_group_spawn(
            args.resource_group_name,
            args.resource_definition_name,
            vlm_sizes=args.volume_sizes,
            partial=args.partial,
            definitions_only=args.definition_only,
            external_name=args.external_name,
            place_count=args.place_count,
            storage_pool=args.storage_pool,
            do_not_place_with=self.prepare_argparse_list(args.do_not_place_with),
            do_not_place_with_regex=args.do_not_place_with_regex,
            replicas_on_same=self.prepare_argparse_list(args.replicas_on_same, linstor.consts.NAMESPC_AUXILIARY + '/'),
            replicas_on_different=self.prepare_argparse_list(
                args.replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/'),
            diskless_on_remaining=self.parse_diskless_on_remaining(args),
            layer_list=self.prepare_argparse_list(args.layer_list),
            provider_list=self.prepare_argparse_list(args.providers),
            diskless_storage_pool=self.prepare_argparse_list(args.diskless_storage_pool),
            peer_slots=args.peer_slots,
            volume_passphrases=args.volume_passphrase,
        )
        return self.handle_replies(args, replies)

    def qmvs(self, args):
        replies = self.get_linstorapi().resource_group_qmvs(
            args.resource_group_name
        )
        api_responses = self.get_linstorapi().filter_api_call_response(replies)
        if api_responses:
            return self.handle_replies(args, api_responses)

        return self.output_list(args, replies, self._show_query_max_volume)

    @staticmethod
    def _show_query_size_info(args, info):
        """

        :param args:
        :param linstor.responses.QuerySizeInfoResponseSpaceInfo info:
        :return:
        """
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("MaxVolumeSize", just_txt='>')
        tbl.add_column("AvailableSize", just_txt='>')
        tbl.add_column("Capacity", just_txt='>')
        tbl.add_column("Next Spawn Result", just_txt='<')

        if info.next_spawn_result:
            next_result = '\n'.join([x.stor_pool_name + " on " + x.node_name for x in info.next_spawn_result])
        else:
            next_result = "-"
        row = [
            SizeCalc.approximate_size_string(info.max_vlm_size_in_kib),
            SizeCalc.approximate_size_string(info.available_size_in_kib),
            SizeCalc.approximate_size_string(info.capacity_in_kib),
            next_result
        ]

        tbl.add_row(row)
        tbl.show()
        return ExitCode.OK

    def qsi(self, args):
        info = self.get_linstorapi().resource_group_query_size_info(
            args.resource_group_name,
            place_count=args.place_count,
            storage_pool=args.storage_pool,
            do_not_place_with=self.prepare_argparse_list(args.do_not_place_with),
            do_not_place_with_regex=args.do_not_place_with_regex,
            replicas_on_same=self.prepare_argparse_list(args.replicas_on_same, linstor.consts.NAMESPC_AUXILIARY + '/'),
            replicas_on_different=self.prepare_argparse_list(
                args.replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/'),
            diskless_on_remaining=self.parse_diskless_on_remaining(args),
            layer_list=self.prepare_argparse_list(args.layer_list),
            provider_list=self.prepare_argparse_list(args.providers),
            diskless_storage_pool=self.prepare_argparse_list(args.diskless_storage_pool)
        )

        if info is None:  # --curl
            return ExitCode.OK

        if info.reports:
            return self.handle_replies(args, info.reports)

        if args.machine_readable:
            print(self._to_json(info.data(args.output_version)))
            return ExitCode.OK

        return self._show_query_size_info(args, info.space_info)

    def adjust(self, args):
        replies = self.get_linstorapi().resource_group_adjust(
            args.resource_group_name
            # args.overprovision
        )
        return self.handle_replies(args, replies)
