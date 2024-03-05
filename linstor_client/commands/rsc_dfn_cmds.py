import sys

import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
from linstor_client.commands import Commands, DrbdOptions, ArgumentError
from linstor_client.consts import Color, ExitCode
from linstor.sharedconsts import FLAG_DELETE
from linstor_client.utils import rangecheck, Output


class ResourceDefinitionCommands(Commands):
    OBJECT_NAME = 'resource-definition'

    _rsc_dfn_headers = [
        linstor_client.TableHeader("ResourceName"),
        linstor_client.TableHeader("Port"),
        linstor_client.TableHeader("ResourceGroup"),
        linstor_client.TableHeader("State", color=Color.DARKGREEN)
    ]

    def __init__(self):
        super(ResourceDefinitionCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.AutoPlace,
            Commands.Subcommands.Modify,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions,
            Commands.Subcommands.Clone,
            Commands.Subcommands.WaitSync,
        ]

        # Resource definition subcommands
        res_def_parser = parser.add_parser(
            Commands.RESOURCE_DEF,
            aliases=["rd"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resource definition subcommands")

        res_def_subp = res_def_parser.add_subparsers(
            title="resource definition subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        p_new_res_dfn = res_def_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Defines a LINSTOR resource definition for use with LINSTOR.')
        p_new_res_dfn.add_argument('-p', '--port', type=rangecheck(1, 65535))
        p_new_res_dfn.add_argument('-e', '--external-name', type=str, help='User specified name.')
        # p_new_res_dfn.add_argument('-s', '--secret', type=str)
        p_new_res_dfn.add_argument(
            '-l', '--layer-list',
            type=self.layer_data_check,
            help="Comma separated layer list, order is from right to left. "
                 "This means the top most layer is on the left. "
                 "Possible layers are: " + ",".join(linstor.Linstor.layer_list()))
        p_new_res_dfn.add_argument('--peer-slots', type=rangecheck(1, 31), help='(DRBD) peer slots for new resources')
        p_new_res_dfn.add_argument(
            '--resource-group',
            help="Attach the resource definition to this resource group."
        ).completer = self.resource_grp_completer
        p_new_res_dfn.add_argument('name',
                                   nargs="?",
                                   type=str,
                                   help='Name of the new resource definition. Will be ignored if EXTERNAL_NAME is set.')
        p_new_res_dfn.set_defaults(func=self.create)

        p_auto_place = res_def_subp.add_parser(
            Commands.Subcommands.AutoPlace.LONG,
            aliases=[Commands.Subcommands.AutoPlace.SHORT],
            description='Auto place a resource definition.')
        self.add_auto_select_argparse_arguments(p_auto_place, use_place_count=True)
        p_auto_place.add_argument(
            'resource_definition_name',
            help='Name of the resource definition to auto place'
        )
        p_auto_place.add_argument(
            '--nvme-initiator',
            action="store_true",
            help='Mark this resource as initiator'
        )
        p_auto_place.add_argument(
            '--drbd-diskless',
            action="store_true",
            help='Mark this resource as drbd diskless'
        )
        p_auto_place.set_defaults(func=self.auto_place)

        # modify-resource definition
        p_mod_res_dfn = res_def_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modifies a LINSTOR resource definition.')
        p_mod_res_dfn.add_argument('--peer-slots', type=rangecheck(1, 31), help='(DRBD) peer slots for new resources')
        p_mod_res_dfn.add_argument(
            '--resource-group',
            help='Change resource group to the given one.').completer = self.resource_grp_completer
        p_mod_res_dfn.add_argument(
            'name',
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_mod_res_dfn.set_defaults(func=self.modify)

        # remove-resource definition
        p_rm_res_dfn = res_def_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=" Removes a resource definition "
            "from the LINSTOR cluster. The resource is undeployed from all nodes "
            "and the resource entry is marked for removal from LINSTOR's data "
            "tables. After all nodes have undeployed the resource, the resource "
            "entry is removed from LINSTOR's data tables.")
        p_rm_res_dfn.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_rm_res_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the resource to delete').completer = self.resource_dfn_completer
        p_rm_res_dfn.set_defaults(func=self.delete)

        rsc_dfn_groupby = [x.name.lower() for x in self._rsc_dfn_headers]
        rsc_dfn_group_completer = Commands.show_group_completer(rsc_dfn_groupby, "groupby")

        p_clone_rscdfn = res_def_subp.add_parser(
            Commands.Subcommands.Clone.LONG,
            aliases=[Commands.Subcommands.Clone.SHORT],
            description="Clones a resource definition with all resources and volumes (including data).")
        p_clone_rscdfn.add_argument('-e', '--external-name', type=str, help='User specified name.')
        p_clone_rscdfn.add_argument('--no-wait', action="store_true", help="Wait till cloning is done.")
        p_clone_rscdfn.add_argument('--wait-timeout',
                                    type=int, help="Wait specified number of seconds for the clone to finish.")
        p_clone_rscdfn.add_argument(
            '--use-zfs-clone',
            action="store_true",
            default=None,
            help="Use ZFS clone instead send/recv, but have a dependent snapshot")
        p_clone_rscdfn.add_argument(
            '--volume-passphrase', nargs='*', help="User provided volume passphrases"
        )
        p_clone_rscdfn.add_argument(
            'source_resource',
            help="Source resource definition name").completer = self.resource_dfn_completer
        p_clone_rscdfn.add_argument('clone_name',
                                    nargs="?",
                                    type=str,
                                    help='Name of the new resource definition. '
                                         'Will be ignored if EXTERNAL_NAME is set.')
        p_clone_rscdfn.set_defaults(func=self.clone)

        p_wait_sync = res_def_subp.add_parser(
            Commands.Subcommands.WaitSync.LONG,
            aliases=[Commands.Subcommands.WaitSync.SHORT],
            description="Wait until the specified resource is synchronized (DRBD peers are up-to-date). "
            "For use when cloning a resource definition (see `linstor resource-definition clone --help`). Cloning a "
            "resource definition might take longer than the LINSTOR client's default timeout period (5 "
            "minutes). To prevent a potentially endless wait, in case something goes wrong and DRBD peers never reach "
            "an up-to-date state, you can specify a `--wait-timeout` value. If the wait timeout is exceeded, the "
            "command will exit, even if the resource is not synchronized.")
        p_wait_sync.add_argument('--wait-timeout', type=int, help="Wait this seconds for the clone to finish.")
        p_wait_sync.add_argument(
            "resource_name", help="Resource name to be checked.").completer = self.resource_dfn_completer
        p_wait_sync.set_defaults(func=self.wait_sync)

        p_lrscdfs = res_def_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource definitions known to '
            'LINSTOR. By default, the list is printed as a human readable table.')
        p_lrscdfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lrscdfs.add_argument('-g', '--groupby', nargs='+',
                               choices=rsc_dfn_groupby,
                               type=str.lower).completer = rsc_dfn_group_completer
        p_lrscdfs.add_argument('-r', '--resource-definitions', nargs='+', type=str,
                               help='Filter by list of resource definitions').completer = self.resource_dfn_completer
        p_lrscdfs.add_argument('-e', '--external-name', action="store_true", help='Show user specified name.')
        p_lrscdfs.add_argument('--props', nargs='+', type=str, help='Filter list by object properties')
        p_lrscdfs.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lrscdfs.set_defaults(func=self.list)

        # show properties
        p_sp = res_def_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the specified resource definitions.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'resource_name',
            help="Resource definition for which to print the properties"
        ).completer = self.resource_dfn_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = res_def_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given resource definition.')
        p_setprop.add_argument('name', type=str, help='Name of the resource definition')
        Commands.add_parser_keyvalue(p_setprop, 'resource-definition')
        p_setprop.set_defaults(func=self.set_props)

        # drbd options
        p_drbd_opts = res_def_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description=DrbdOptions.description("resource")
        )
        p_drbd_opts.add_argument(
            'resource_name',
            type=str,
            help="Resource name"
        ).completer = self.resource_dfn_completer
        DrbdOptions.add_arguments(p_drbd_opts, self.OBJECT_NAME)
        p_drbd_opts.set_defaults(func=self.set_drbd_opts)

        self.check_subcommands(res_def_subp, subcmds)

    def create(self, args):
        if not args.name and not args.external_name:
            raise ArgumentError("ArgumentError: At least resource name or external name has to be specified.")
        replies = self._linstor.resource_dfn_create(
            args.name,
            args.port,
            external_name=args.external_name
            if not isinstance(args.external_name, bytes) else args.external_name.decode('utf-8'),  # py2-3
            layer_list=args.layer_list,
            resource_group=args.resource_group,
            peer_slots=args.peer_slots
        )
        return self.handle_replies(args, replies)

    def auto_place(self, args):

        place_count, additional_place_count, diskless_type = self.parse_place_count_args(args, use_place_count=True)

        replies = self.get_linstorapi().resource_auto_place(
            rsc_name=args.resource_definition_name,
            place_count=place_count,
            storage_pool=args.storage_pool,
            do_not_place_with=args.do_not_place_with,
            do_not_place_with_regex=args.do_not_place_with_regex,
            replicas_on_same=self.prepare_argparse_list(args.replicas_on_same, linstor.consts.NAMESPC_AUXILIARY + '/'),
            replicas_on_different=self.prepare_argparse_list(
                args.replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/'),
            diskless_on_remaining=self.parse_diskless_on_remaining(args),
            layer_list=args.layer_list,
            provider_list=args.providers,
            additional_place_count=additional_place_count,
            diskless_type=diskless_type)
        return self.handle_replies(args, replies)

    def clone(self, args):
        clone_resp = self.get_linstorapi().resource_dfn_clone(
            args.source_resource,
            args.clone_name,
            args.external_name,
            use_zfs_clone=args.use_zfs_clone,
            volume_passphrases=args.volume_passphrase
        )

        rc = self.handle_replies(args, clone_resp.messages)

        if rc == ExitCode.OK and not args.no_wait:
            if not args.machine_readable:
                print("Waiting for cloning to complete...")
            try:
                res = self.get_linstorapi().resource_dfn_clone_wait_complete(
                    clone_resp.source_name, clone_resp.clone_name, timeout=args.wait_timeout)
                if not res:
                    rc = ExitCode.API_ERROR
                if not args.machine_readable:
                    if res:
                        print("{msg} cloning {c}.".format(
                            c=clone_resp.clone_name, msg=Output.color_str("Completed", Color.GREEN, args.no_color)))
                    else:
                        print("{msg} cloning {c}, please check resource status or satellite errors.".format(
                            c=clone_resp.clone_name, msg=Output.color_str("Failed", Color.RED, args.no_color)))
            except linstor.LinstorApiCallError as e:
                rc = ExitCode.API_ERROR
                Output.handle_ret(e.main_error, args.no_color, False, sys.stderr)

        return rc

    def wait_sync(self, args):
        # this method either returns True or raises
        self.get_linstorapi().resource_dfn_wait_synced(args.resource_name, timeout=args.wait_timeout)
        return ExitCode.OK

    def modify(self, args):
        replies = self._linstor.resource_dfn_modify(
            args.name,
            {},
            [],
            args.peer_slots,
            resource_group=args.resource_group
        )
        return self.handle_replies(args, replies)

    def delete(self, args):
        async_flag = vars(args)["async"]

        # execute delete rscdfns and flatten result list
        replies = [x for subx in args.name for x in self._linstor.resource_dfn_delete(subx, async_flag)]
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        rsc_dfn_hdr = list(cls._rsc_dfn_headers)

        if args.external_name:
            rsc_dfn_hdr.insert(1, linstor_client.TableHeader("External"))

        for hdr in rsc_dfn_hdr:
            tbl.add_header(hdr)

        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])

        for rsc_dfn in lstmsg.resource_definitions:
            drbd_data = rsc_dfn.drbd_data
            row = [rsc_dfn.name]
            if args.external_name and isinstance(rsc_dfn.external_name, str):
                row.append(rsc_dfn.external_name)
            row.append(drbd_data.port if drbd_data else "")
            row.append(rsc_dfn.resource_group_name)
            row.append(tbl.color_cell("DELETING", Color.RED)
                       if FLAG_DELETE in rsc_dfn.flags else tbl.color_cell("ok", Color.DARKGREEN))
            for sprop in show_props:
                row.append(rsc_dfn.properties.get(sprop, ''))
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        args = self.merge_config_args('resource-definition.list', args)
        lstmsg = self._linstor.resource_dfn_list(
            query_volume_definitions=False,
            filter_by_resource_definitions=args.resource_definitions,
            filter_by_props=args.props
        )
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_show(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc_dfn in lstmsg.resource_definitions:
                result.append(rsc_dfn.properties)
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_dfn_list(
            query_volume_definitions=False,
            filter_by_resource_definitions=[args.resource_name]
        )
        return self.output_props_list(args, lstmsg, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.resource_dfn_modify(args.name, mod_prop_dict['pairs'], mod_prop_dict['delete'])
        return self.handle_replies(args, replies)

    def set_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']  # remove resource name key

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = self._linstor.resource_dfn_modify(
            args.resource_name,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)
