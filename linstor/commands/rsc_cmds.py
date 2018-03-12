import linstor
from linstor.commands import Commands
from linstor.utils import namecheck, Output, LinstorClientError
from linstor.consts import Color, ExitCode, NODE_NAME, RES_NAME, STORPOOL_NAME
import linstor.sharedconsts as apiconsts


class ResourceCommands(Commands):
    _resource_headers = [
        linstor.TableHeader("ResourceName"),
        linstor.TableHeader("Node"),
        linstor.TableHeader("Port"),
        linstor.TableHeader("State", Color.DARKGREEN, alignment_text='>')
    ]

    def __init__(self):
        super(ResourceCommands, self).__init__()

    def setup_commands(self, parser):
        """

        :param argparse.ArgumentParser parser:
        :return:
        """
        # new-resource
        p_new_res = parser.add_parser(
            Commands.CREATE_RESOURCE,
            aliases=['crtrsc'],
            description='Defines a DRBD resource for use with linstor. '
            'Unless a specific IP port-number is supplied, the port-number is '
            'automatically selected by the linstor controller on the current node. ')
        p_new_res.add_argument(
            '-s', '--storage-pool',
            type=namecheck(STORPOOL_NAME),
            help="Storage pool name to use.").completer = self.storage_pool_dfn_completer
        p_new_res.add_argument('-d', '--diskless', action="store_true", help='Should the resource be diskless')
        p_new_res.add_argument(
            '--auto-place',
            help='Auto place a resource to a specified number of nodes',
            type=int
        )
        p_new_res.add_argument(
            '--do-not-place-with',
            type=namecheck(RES_NAME),
            nargs='+',
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = self.resource_completer
        p_new_res.add_argument(
            '--do-not-place-with-regex',
            type=str,
            help='Try to avoid nodes that already have a resource deployed whos name is matching the given regular expression.'
        )
        p_new_res.add_argument(
            'resource_definition_name',
            type=namecheck(RES_NAME),
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_res.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            nargs='?',
            help='Name of the node to deploy the resource').completer = self.node_completer
        p_new_res.set_defaults(func=self.create)

        # remove-resource
        p_rm_res = parser.add_parser(
            Commands.DELETE_RESOURCE,
            aliases=['delrsc'],
            description=' Removes a resource and its associated resource definition '
            'from the linstor cluster. The resource is undeployed from all nodes '
            "and the resource entry is marked for removal from linstor's data "
            'tables. After all nodes have undeployed the resource, the resource '
            "entry is removed from linstor's data tables.")
        p_rm_res.add_argument('-q', '--quiet', action="store_true",
                              help='Unless this option is used, linstor will issue a safety question '
                              'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_res.add_argument('name',
                              help='Name of the resource to delete').completer = self.resource_completer
        p_rm_res.add_argument('node_name',
                              nargs="+",
                              help='Name of the node').completer = self.node_completer
        p_rm_res.set_defaults(func=self.delete)

        resgroupby = [x.name for x in ResourceCommands._resource_headers]
        res_group_completer = Commands.show_group_completer(resgroupby, "groupby")

        p_lreses = parser.add_parser(
            Commands.LIST_RESOURCE,
            aliases=['dsprsc'],
            description='Prints a list of all resource definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lreses.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lreses.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=resgroupby).completer = res_group_completer
        p_lreses.add_argument(
            '-r', '--resources',
            nargs='+',
            type=namecheck(RES_NAME),
            help='Filter by list of resources').completer = self.resource_completer
        p_lreses.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=namecheck(NODE_NAME),
            help='Filter by list of nodes').completer = self.node_completer
        p_lreses.set_defaults(func=self.list)

        # list volumes
        p_lvlms = parser.add_parser(
            Commands.LIST_VOLUME,
            aliases=['dspvlm'],
            description='Prints a list of all volumes.'
        )
        p_lvlms.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lvlms.add_argument('resource', nargs='?')
        p_lvlms.set_defaults(func=self.list_volumes)

        # show properties
        p_sp = parser.add_parser(
            Commands.GET_RESOURCE_PROPS,
            aliases=['dsprscprp'],
            description="Prints all properties of the given resource.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_completer
        p_sp.add_argument(
            'node_name',
            help="Node name where the resource is deployed.").completer = self.node_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = parser.add_parser(
            Commands.SET_RESOURCE_PROP,
            aliases=['setrscprp'],
            description='Sets properties for the given resource on the given node.')
        p_setprop.add_argument(
            'name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_completer
        p_setprop.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Node name where resource is deployed.').completer = self.node_completer
        Commands.add_parser_keyvalue(p_setprop, "resource")
        p_setprop.set_defaults(func=self.set_props)

    def create(self, args):
        if args.auto_place:
            # auto-place resource
            replies = self._linstor.resource_auto_place(
                args.resource_definition_name,
                args.auto_place,
                args.storage_pool,
                args.do_not_place_with,
                args.do_not_place_with_regex
            )
        else:
            # normal create resource
            # check that node is given
            if not args.node_name:
                raise LinstorClientError("create-resource: too few arguments: Node name missing.", ExitCode.ARGPARSE_ERROR)

            replies = self._linstor.resource_create(
                args.node_name,
                args.resource_definition_name,
                args.diskless,
                args.storage_pool
            )

        return self.handle_replies(args, replies)

    def delete(self, args):
        # execute delete storpooldfns and flatten result list
        replies = [x for subx in args.node_name for x in self._linstor.resource_delete(subx, args.name)]
        return self.handle_replies(args, replies)

    @staticmethod
    def find_rsc_state(rsc_states, rsc_name, node_name):
        for rscst in rsc_states:
            if rscst.rsc_name == rsc_name and rscst.node_name == node_name:
                return rscst
        return None

    def list(self, args):
        lstmsg = self._linstor.resource_list()

        if lstmsg:
            if args.machine_readable:
                self._print_machine_readable([lstmsg])
            else:
                rsc_dfns = self._linstor.resource_dfn_list().rsc_dfns
                rsc_dfn_map = {x.rsc_name: x for x in rsc_dfns}

                tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
                for hdr in ResourceCommands._resource_headers:
                    tbl.add_header(hdr)

                tbl.set_groupby(args.groupby if args.groupby else [ResourceCommands._resource_headers[0].name])

                filter_res = args.resources
                filter_nodes = args.nodes

                disp_list = lstmsg.resources
                if filter_res:
                    disp_list = [rsc for rsc in disp_list if rsc.name in filter_res]
                if filter_nodes:
                    disp_list = [rsc for rsc in disp_list if rsc.node_name in filter_nodes]

                for rsc in disp_list:
                    rsc_dfn = rsc_dfn_map[rsc.name]
                    marked_delete = apiconsts.FLAG_DELETE in rsc.rsc_flags
                    # rsc_state = ResourceCommands.find_rsc_state(lstmsg.resource_states, rsc.name, rsc.node_name)
                    tbl.add_row([
                        rsc.name,
                        rsc.node_name,
                        rsc_dfn.rsc_dfn_port,
                        tbl.color_cell("DELETING", Color.RED) if marked_delete else "ok"
                    ])
                tbl.show()

        return ExitCode.OK

    @staticmethod
    def get_resource_state(res_states, node_name, resource_name):
        for rsc_state in res_states:
            if rsc_state.node_name == node_name and rsc_state.rsc_name == resource_name:
                return rsc_state
        return None

    @staticmethod
    def get_volume_state(volume_states, volume_nr):
        for volume_state in volume_states:
            if volume_state.vlm_nr == volume_nr:
                return volume_state
        return None

    def list_volumes(self, args):
        lstmsg = self._linstor.resource_list()

        if lstmsg:
            if args.machine_readable:
                self._print_machine_readable([lstmsg])
            else:
                tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
                tbl.add_column("Node")
                tbl.add_column("Resource")
                tbl.add_column("VolumeNr")
                tbl.add_column("MinorNr")
                tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color), just_txt='>')

                for rsc in lstmsg.resources:
                    rsc_state = ResourceCommands.get_resource_state(lstmsg.resource_states, rsc.node_name, rsc.name)
                    for vlm in rsc.vlms:
                        if rsc_state:
                            vlm_state = ResourceCommands.get_volume_state(rsc_state.vlm_states, vlm.vlm_nr)
                        else:
                            vlm_state = None
                        state = tbl.color_cell("Unknown", Color.YELLOW)
                        if vlm_state and vlm_state.HasField("disk_state") and vlm_state.disk_state:
                            state = vlm_state.disk_state

                            if state == 'DUnknown':
                                state = tbl.color_cell("Unknown", Color.YELLOW)
                            elif state == 'Diskless':
                                if vlm_state.disk_failed:
                                    state = tbl.color_cell("DiskFailed", Color.RED)
                            elif state in ['Inconsistent', 'Failed']:
                                state = tbl.color_cell(state, Color.RED)
                            elif state in ['UpToDate']:
                                pass  # green text
                            else:
                                state = tbl.color_cell(state, Color.YELLOW)
                        tbl.add_row([
                            rsc.node_name,
                            rsc.name,
                            str(vlm.vlm_nr),
                            str(vlm.vlm_minor_nr),
                            state
                        ])

                tbl.show()

        return ExitCode.OK

    def print_props(self, args):
        lstmsg = self._linstor.resource_list()

        result = []
        if lstmsg:
            for rsc in lstmsg.resources:
                if rsc.name == args.resource_name and rsc.node_name == args.node_name:
                    result.append(rsc.props)
                    break

        Commands._print_props(result, args)
        return ExitCode.OK

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.resource_modify(
            args.node_name,
            args.name,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    @staticmethod
    def completer_volume(prefix, **kwargs):
        possible = set()
        return possible
