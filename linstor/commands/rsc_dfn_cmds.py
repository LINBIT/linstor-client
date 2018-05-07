import argparse

import linstor
from linstor.commands import Commands
from linstor.consts import RES_NAME, Color
from linstor.sharedconsts import FLAG_DELETE
from linstor.utils import Output, namecheck, rangecheck


class ResourceDefinitionCommands(Commands):
    def __init__(self):
        super(ResourceDefinitionCommands, self).__init__()

    def setup_commands(self, parser):

        # Resource subcommands
        res_def_parser = parser.add_parser(
            Commands.RESOURCE_DEF,
            aliases=["rd"],
            formatter_class=argparse.RawTextHelpFormatter,
            help="Resouce definition subcommands")

        res_def_subp = res_def_parser.add_subparsers(
            title="resource definition subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(
                [
                    Commands.Subcommands.Create,
                    Commands.Subcommands.List,
                    Commands.Subcommands.Delete,
                    Commands.Subcommands.SetAuxProperties,
                    Commands.Subcommands.ListProperties,
                ]))

        p_new_res_dfn = res_def_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Defines a Linstor resource definition for use with linstor.')
        p_new_res_dfn.add_argument('-p', '--port', type=rangecheck(1, 65535))
        # p_new_res_dfn.add_argument('-s', '--secret', type=str)
        p_new_res_dfn.add_argument('name', type=namecheck(RES_NAME), help='Name of the new resource definition')
        p_new_res_dfn.set_defaults(func=self.create)

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
        p_rm_res_dfn.add_argument('-q', '--quiet', action="store_true",
                                  help='Unless this option is used, linstor will issue a safety question '
                                  'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_res_dfn.add_argument(
            'name',
            nargs="+",
            help='Name of the resource to delete').completer = self.resource_dfn_completer
        p_rm_res_dfn.set_defaults(func=self.delete)

        resverbose = ('Port',)
        resgroupby = ('Name', 'Port', 'State')
        res_verbose_completer = Commands.show_group_completer(resverbose, "show")
        res_group_completer = Commands.show_group_completer(resgroupby, "groupby")

        p_lrscdfs = res_def_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lrscdfs.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lrscdfs.add_argument('-s', '--show', nargs='+',
                               choices=resverbose).completer = res_verbose_completer
        p_lrscdfs.add_argument('-g', '--groupby', nargs='+',
                               choices=resgroupby).completer = res_group_completer
        p_lrscdfs.add_argument('-R', '--resources', nargs='+', type=namecheck(RES_NAME),
                               help='Filter by list of resources').completer = self.resource_dfn_completer
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
            Commands.Subcommands.SetAuxProperties.LONG,
            aliases=[Commands.Subcommands.SetAuxProperties.SHORT],
            description='Sets properties for the given resource definition.')
        p_setprop.add_argument('name', type=namecheck(RES_NAME), help='Name of the resource definition')
        Commands.add_parser_keyvalue(p_setprop, 'resource-definition')
        p_setprop.set_defaults(func=self.set_props)

    def create(self, args):
        replies = self._linstor.resource_dfn_create(args.name, args.port)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.name for x in self._linstor.resource_dfn_delete(subx)]
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("ResourceName")
        tbl.add_column("Port")
        tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color))
        for rsc_dfn in lstmsg.rsc_dfns:
            tbl.add_row([
                rsc_dfn.rsc_name,
                rsc_dfn.rsc_dfn_port,
                tbl.color_cell("DELETING", Color.RED)
                if FLAG_DELETE in rsc_dfn.rsc_dfn_flags else tbl.color_cell("ok", Color.DARKGREEN)
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.resource_dfn_list()

        return self.output_list(args, lstmsg, self.show)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc_dfn in lstmsg.rsc_dfns:
                if rsc_dfn.rsc_name == args.resource_name:
                    result.append(rsc_dfn.rsc_dfn_props)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_dfn_list()

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.resource_dfn_modify(args.name, mod_prop_dict['pairs'], mod_prop_dict['delete'])
        return self.handle_replies(args, replies)
