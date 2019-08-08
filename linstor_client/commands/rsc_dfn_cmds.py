import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
from linstor_client.commands import Commands, DrbdOptions, ArgumentError
from linstor_client.consts import Color
from linstor.sharedconsts import FLAG_DELETE
from linstor_client.utils import rangecheck


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
            Commands.Subcommands.Modify,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions
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
            description='Defines a Linstor resource definition for use with linstor.')
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
            help="Attach the resource definition to this resource group"
        ).completer = self.resource_grp_completer
        p_new_res_dfn.add_argument('name',
                                   nargs="?",
                                   type=str,
                                   help='Name of the new resource definition. Will be ignored if EXTERNAL_NAME is set.')
        p_new_res_dfn.set_defaults(func=self.create)

        # modify-resource definition
        p_mod_res_dfn = res_def_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modifies a Linstor resource definition')
        p_mod_res_dfn.add_argument('--peer-slots', type=rangecheck(1, 31), help='(DRBD) peer slots for new resources')
        p_mod_res_dfn.add_argument(
            'name',
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_mod_res_dfn.set_defaults(func=self.modify)

        # remove-resource definition
        # TODO description
        p_rm_res_dfn = res_def_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description=" Removes a resource definition "
            "from the linstor cluster. The resource is undeployed from all nodes "
            "and the resource entry is marked for removal from linstor's data "
            "tables. After all nodes have undeployed the resource, the resource "
            "entry is removed from linstor's data tables.")
        p_rm_res_dfn.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for actual deletion on satellites before returning'
        )
        p_rm_res_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the resource to delete').completer = self.resource_dfn_completer
        p_rm_res_dfn.set_defaults(func=self.delete)

        rsc_dfn_groupby = [x.name for x in self._rsc_dfn_headers]
        rsc_dfn_group_completer = Commands.show_group_completer(rsc_dfn_groupby, "groupby")

        p_lrscdfs = res_def_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lrscdfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lrscdfs.add_argument('-g', '--groupby', nargs='+',
                               choices=rsc_dfn_groupby).completer = rsc_dfn_group_completer
        p_lrscdfs.add_argument('-R', '--resources', nargs='+', type=str,
                               help='Filter by list of resources').completer = self.resource_dfn_completer
        p_lrscdfs.add_argument('-e', '--external-name', action="store_true", help='Show user specified name.')
        p_lrscdfs.set_defaults(func=self.list)

        # show properties
        p_sp = res_def_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given resource definitions.")
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
            resource_group=args.resource_group
        )
        return self.handle_replies(args, replies)

    def modify(self, args):
        replies = self._linstor.resource_dfn_modify(
            args.name,
            {},
            [],
            args.peer_slots
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

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])

        for rsc_dfn in cls.filter_rsc_dfn_list(lstmsg.resource_definitions, args.resources):
            drbd_data = rsc_dfn.drbd_data
            row = [rsc_dfn.name]
            if args.external_name:
                if isinstance(rsc_dfn.external_name, str):
                    row.append(rsc_dfn.external_name)
                else:
                    row.append(rsc_dfn.external_name)
            row.append(drbd_data.port if drbd_data else "")
            row.append(rsc_dfn.resource_group_name)
            row.append(tbl.color_cell("DELETING", Color.RED)
                       if FLAG_DELETE in rsc_dfn.flags else tbl.color_cell("ok", Color.DARKGREEN))
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.resource_dfn_list(query_volume_definitions=False)
        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc_dfn in lstmsg.resource_definitions:
                if rsc_dfn.name.lower() == args.resource_name.lower():
                    result.append(rsc_dfn.properties)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_dfn_list(query_volume_definitions=False)

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
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
