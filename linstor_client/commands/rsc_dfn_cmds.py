import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
from linstor_client.commands import Commands, DrbdOptions
from linstor_client.consts import RES_NAME, Color, ExitCode
from linstor.sharedconsts import FLAG_DELETE
from linstor_client.utils import namecheck, rangecheck


class ResourceDefinitionCommands(Commands):
    _rsc_dfn_headers = [
        linstor_client.TableHeader("ResourceName"),
        linstor_client.TableHeader("Port"),
        linstor_client.TableHeader("State", color=Color.DARKGREEN)
    ]

    def __init__(self):
        super(ResourceDefinitionCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdOptions
        ]

        # Resource subcommands
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
        p_rm_res_dfn.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for actual deletion on satellites before returning'
        )
        p_rm_res_dfn.add_argument('-q', '--quiet', action="store_true",
                                  help='Unless this option is used, linstor will issue a safety question '
                                  'that must be answered with yes, otherwise the operation is canceled.')
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
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            description='Sets properties for the given resource definition.')
        p_setprop.add_argument('name', type=namecheck(RES_NAME), help='Name of the resource definition')
        Commands.add_parser_keyvalue(p_setprop, 'resource-definition')
        p_setprop.set_defaults(func=self.set_props)

        # drbd options
        p_drbd_opts = res_def_subp.add_parser(
            Commands.Subcommands.DrbdOptions.LONG,
            aliases=[Commands.Subcommands.DrbdOptions.SHORT],
            description="Set drbd resource options."
        )
        p_drbd_opts.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help="Resource name"
        ).completer = self.resource_dfn_completer
        DrbdOptions.add_arguments(
            p_drbd_opts,
            [x for x in DrbdOptions.drbd_options()['options'] if x in DrbdOptions.drbd_options()['filters']['resource']]
        )
        p_drbd_opts.set_defaults(func=self.set_drbd_opts)

        self.check_subcommands(res_def_subp, subcmds)

    def create(self, args):
        replies = self._linstor.resource_dfn_create(args.name, args.port)
        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete rscdfns and flatten result list
        if args.async:
            replies = [x for subx in args.name for x in self._linstor.resource_dfn_delete(subx)]
            return self.handle_replies(args, replies)
        else:
            def delete_rscdfn_handler(event_header, event_data):
                if event_header.event_name in [linstor.consts.EVENT_RESOURCE_DEPLOYMENT_STATE]:
                    if event_header.event_action == linstor.consts.EVENT_STREAM_CLOSE_NO_CONNECTION:
                        print("WARNING: Satellite connection lost")
                        return ExitCode.NO_SATELLITE_CONNECTION
                elif event_header.event_name in [linstor.consts.EVENT_RESOURCE_DEFINITION_READY]:
                    if event_header.event_action == linstor.consts.EVENT_STREAM_CLOSE_REMOVED:
                        return []

                return linstor.Linstor.exit_on_error_event_handler(event_header, event_data)

            all_delete_replies = []
            for rsc_name in args.name:
                replies = self.get_linstorapi().resource_dfn_delete(rsc_name)
                all_delete_replies += replies

                if not self._linstor.all_api_responses_success(replies):
                    return self.handle_replies(args, all_delete_replies)

                watch_result = self.get_linstorapi().watch_events(
                    linstor.Linstor.return_if_failure,
                    delete_rscdfn_handler,
                    linstor.ObjectIdentifier(resource_name=rsc_name)
                )

                if isinstance(watch_result, list):
                    all_delete_replies += watch_result
                    if not self._linstor.all_api_responses_success(watch_result):
                        return self.handle_replies(args, all_delete_replies)
                elif watch_result != ExitCode.OK:
                    return watch_result

            return self.handle_replies(args, all_delete_replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._rsc_dfn_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else [tbl.header_name(0)])
        for rsc_dfn in cls.filter_rsc_dfn_list(lstmsg.rsc_dfns, args.resources):
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

    def set_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']  # remove resource name key

        mod_props, del_props = DrbdOptions.parse_opts(a)

        replies = self._linstor.resource_dfn_modify(
            args.resource_name,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)
