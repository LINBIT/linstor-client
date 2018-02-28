import argparse

import linstor
import linstor.sharedconsts as apiconsts
from linstor.commands import Commands
from linstor.consts import NODE_NAME, RES_NAME, STORPOOL_NAME, Color, ExitCode
from linstor.utils import Output, namecheck


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

        # Resource subcommands
        res_parser = parser.add_parser(
            Commands.RESOURCE,
            aliases=["r"],
            help="Resouce subcommands")
        res_subp = res_parser.add_subparsers(title="resource commands")

        # new-resource
        p_new_res = res_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Defines a DRBD resource for use with linstor. '
            'Unless a specific IP port-number is supplied, the port-number is '
            'automatically selected by the linstor controller on the current node. ')
        p_new_res.add_argument(
            '-s', '--storage-pool',
            type=namecheck(STORPOOL_NAME),
            help="Storage pool name to use.").completer = self.storage_pool_dfn_completer
        p_new_res.add_argument('-d', '--diskless', action="store_true", help='Should the resource be diskless')
        p_new_res.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for deployment on satellites before returning'
        )
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
            nargs='*',
            help='Name of the node to deploy the resource').completer = self.node_completer
        p_new_res.set_defaults(func=self.create)

        # remove-resource
        p_rm_res = res_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
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

        p_lreses = res_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
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
        p_lvlms = res_subp.add_parser(
            Commands.Subcommands.ListVolumes.LONG,
            aliases=[Commands.Subcommands.ListVolumes.SHORT],
            description='Prints a list of all volumes.'
        )
        p_lvlms.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lvlms.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=namecheck(NODE_NAME),
            help='Filter by list of nodes').completer = self.node_completer
        p_lvlms.add_argument('-s', '--storpools', nargs='+', type=namecheck(STORPOOL_NAME),
                             help='Filter by list of storage pools').completer = self.storage_pool_completer
        p_lvlms.add_argument(
            '-r', '--resources',
            nargs='+',
            type=namecheck(RES_NAME),
            help='Filter by list of resources').completer = self.resource_completer
        p_lvlms.set_defaults(func=self.list_volumes)

        # show properties
        p_sp = res_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
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
        p_setprop = res_subp.add_parser(
            Commands.Subcommands.SetProperties.LONG,
            aliases=[Commands.Subcommands.SetProperties.SHORT],
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

    @staticmethod
    def _satellite_not_connected(replies):
        return any(reply.ret_code & apiconsts.WARN_NOT_CONNECTED == apiconsts.WARN_NOT_CONNECTED for reply in replies)

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

            rc = self.handle_replies(args, replies)

            if rc == ExitCode.OK and not args.async:
                def reply_handler(replies):
                    create_watch_rc = self.handle_replies(args, replies)
                    if create_watch_rc != ExitCode.OK:
                        return create_watch_rc
                    return None

                def event_handler(event_header, event_data):
                    if event_header.event_name == apiconsts.EVENT_RESOURCE_DEFINITION_READY:
                        if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_REMOVED:
                            print((Output.color_str('ERROR:', Color.RED, args.no_color)) + " Resource removed")
                            return ExitCode.API_ERROR

                        if event_data is not None:
                            if event_data.error_count > 0:
                                return ExitCode.API_ERROR

                            if event_data.ready_count == args.auto_place:
                                return ExitCode.OK

                    return None

                rc = self._linstor.create_watch(
                    reply_handler,
                    event_handler,
                    resource_name=args.resource_definition_name
                )

            return rc

        else:
            # normal create resource
            # check that node is given
            if not args.node_name:
                raise ArgumentError("create-resource: too few arguments: Node name missing.")

            rc = ExitCode.OK
            satellites_connected = True
            for node_name in args.node_name:
                replies = self._linstor.resource_create(
                    node_name,
                    args.resource_definition_name,
                    args.diskless,
                    args.storage_pool
                )

                create_rc = self.handle_replies(args, replies)

                if create_rc != ExitCode.OK:
                    rc = create_rc

                if ResourceCommands._satellite_not_connected(replies):
                    satellites_connected = False

            if rc == ExitCode.OK and not args.async and not satellites_connected:
                rc = ExitCode.NO_SATELLITE_CONNECTION

            if rc == ExitCode.OK and not args.async:
                for node_name in args.node_name:
                    def reply_handler(replies):
                        create_watch_rc = self.handle_replies(args, replies)
                        if create_watch_rc != ExitCode.OK:
                            return create_watch_rc
                        return None

                    def event_handler(event_header, event_data):
                        if event_header.node_name == node_name:
                            if event_header.event_name in \
                                    [apiconsts.EVENT_RESOURCE_STATE, apiconsts.EVENT_RESOURCE_DEPLOYMENT_STATE]:
                                if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_NO_CONNECTION:
                                    print(Output.color_str('WARNING:', Color.YELLOW, args.no_color) +
                                          " Satellite connection lost")
                                    return ExitCode.NO_SATELLITE_CONNECTION
                                if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_REMOVED:
                                    print((Output.color_str('ERROR:', Color.RED, args.no_color)) + " Resource removed")
                                    return ExitCode.API_ERROR

                            if event_header.event_name == apiconsts.EVENT_RESOURCE_STATE and \
                                    event_data is not None and event_data.ready:
                                return ExitCode.OK

                            if event_header.event_name == apiconsts.EVENT_RESOURCE_DEPLOYMENT_STATE and \
                                    event_data is not None:
                                api_call_responses = [
                                    linstor.linstorapi.ApiCallResponse(response)
                                    for response in event_data.responses
                                ]
                                failure_responses = [
                                    api_call_response for api_call_response in api_call_responses
                                    if not api_call_response.is_success()
                                ]

                                if not failure_responses:
                                    return None

                                self.handle_replies(args, api_call_responses)
                                return ExitCode.API_ERROR

                        return None

                    watch_rc = self._linstor.create_watch(
                        reply_handler,
                        event_handler,
                        node_name=node_name,
                        resource_name=args.resource_definition_name
                    )

                    if watch_rc != ExitCode.OK:
                        rc = watch_rc

            return rc

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

    def show(self, args, lstmsg):
        rsc_dfns = self._linstor.resource_dfn_list()
        if isinstance(rsc_dfns[0], linstor.linstorapi.ApiCallResponse):
            return self.handle_replies(args, rsc_dfns)
        rsc_dfns = rsc_dfns[0].proto_msg.rsc_dfns

        rsc_dfn_map = {x.rsc_name: x for x in rsc_dfns}

        tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in ResourceCommands._resource_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else [ResourceCommands._resource_headers[0].name])

        for rsc in lstmsg.resources:
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

    def list(self, args):
        lstmsg = self._linstor.resource_list(filter_by_nodes=args.nodes, filter_by_resources=args.resources)
        return self.output_list(args, lstmsg, self.show)

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

    @classmethod
    def show_volumes(cls, args, lstmsg):
        tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("Node")
        tbl.add_column("Resource")
        tbl.add_column("StoragePool")
        tbl.add_column("VolumeNr")
        tbl.add_column("MinorNr")
        tbl.add_column("DeviceName")
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
                        if apiconsts.FLAG_DISKLESS not in rsc.rsc_flags:  # unintentional diskless
                            state = tbl.color_cell(state, Color.RED)
                        # else pass -> green diskless
                    elif state in ['Inconsistent', 'Failed']:
                        state = tbl.color_cell(state, Color.RED)
                    elif state in ['UpToDate']:
                        pass  # green text
                    else:
                        state = tbl.color_cell(state, Color.YELLOW)
                tbl.add_row([
                    rsc.node_name,
                    rsc.name,
                    vlm.stor_pool_name,
                    str(vlm.vlm_nr),
                    str(vlm.vlm_minor_nr),
                    "/dev/drbd{minor}".format(minor=vlm.vlm_minor_nr),
                    state
                ])

        tbl.show()

    def list_volumes(self, args):
        lstmsg = self._linstor.volume_list(args.nodes, args.storpools, args.resources)

        return self.output_list(args, lstmsg, self.show_volumes)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc in lstmsg.resources:
                if rsc.name == args.resource_name and rsc.node_name == args.node_name:
                    result.append(rsc.props)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_list()

        return self.output_props_list(args, lstmsg, self._props_list)

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
