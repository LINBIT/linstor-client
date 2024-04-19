from __future__ import print_function
import json

import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
import linstor.sharedconsts as apiconsts
from linstor_client.commands import DefaultState, Commands, DrbdOptions, ArgumentError
from linstor_client.commands.vlm_cmds import VolumeCommands
from linstor_client.consts import Color, ExitCode


class ResourceCreateTransactionState(object):
    def __init__(self, terminate_on_error):
        self.rscs = []
        self._terminate_on_error = terminate_on_error

    @property
    def name(self):
        return 'Resource Creation Transaction'

    @property
    def prompt(self):
        return self.name

    @property
    def terminate_on_error(self):
        return self._terminate_on_error


class RscRespWrapper(object):
    def __init__(self, original):
        """

        :param linstor.responses.ResourceResponse original:
        """
        self.resources = original.resources
        self.resource_states = original.resource_states


class ResourceCommands(Commands):
    CONN_OBJECT_NAME = 'rsc-conn'

    _resource_headers = [
        linstor_client.TableHeader("ResourceName"),
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Port"),
        linstor_client.TableHeader("Usage", Color.DARKGREEN),
        linstor_client.TableHeader("Conns", Color.DARKGREEN),
        linstor_client.TableHeader("State", Color.DARKGREEN, alignment_text=linstor_client.TableHeader.ALIGN_RIGHT),
        linstor_client.TableHeader("CreatedOn")
    ]

    def __init__(self, state_service):
        super(ResourceCommands, self).__init__()

        self._state_service = state_service

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.MakeAvailable,
            Commands.Subcommands.List,
            Commands.Subcommands.ListVolumes,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdPeerDeviceOptions,
            Commands.Subcommands.ToggleDisk,
            Commands.Subcommands.CreateTransactional,
            Commands.Subcommands.Activate,
            Commands.Subcommands.Deactivate,
            Commands.Subcommands.Involved
        ]

        # Resource subcommands
        res_parser = parser.add_parser(
            Commands.RESOURCE,
            aliases=["r"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resouce subcommands")
        res_subp = res_parser.add_subparsers(
            title="resource commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new-resource
        p_new_res = res_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Deploys a resource definition to a node.')
        p_new_res.add_argument(
            '--diskless', '-d',
            action="store_true",
            help='DEPRECATED. Use --nvme-initiator or --drbd-diskless instead'
        )
        p_new_res.add_argument(
            '--node-id',
            type=int,
            help='Override the automatic selection of DRBD node ID'
        )
        p_new_res.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_new_res.add_argument(
            '--nvme-initiator',
            action="store_true",
            help='Mark this resource as NVMe initiator'
        )
        p_new_res.add_argument(
            '--drbd-diskless',
            action="store_true",
            help='Mark this resource as DRBD diskless'
        )
        p_new_res.add_argument(
            '--ebs-initiator',
            action="store_true",
            help='Mark this resource as EBS initiator'
        )
        p_new_res.add_argument(
            '--inactive',
            action="store_true",
            help="Marks the resource created as inactive"
        )
        self.add_auto_select_argparse_arguments(p_new_res)
        p_new_res.add_argument(
            'node_name',
            type=str,
            nargs='*',
            help='Name of the node to deploy the resource').completer = self.node_completer
        p_new_res.add_argument(
            'resource_definition_name',
            type=str,
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_res.set_defaults(func=self.create, allowed_states=[DefaultState, ResourceCreateTransactionState])

        # make available
        p_mkavial = res_subp.add_parser(
            Commands.Subcommands.MakeAvailable.LONG,
            aliases=[Commands.Subcommands.MakeAvailable.SHORT],
            description='Make a resource available on a node. Does nothing if resource already exists on the node.')
        p_mkavial.add_argument(
            '--diskful',
            action="store_true",
            help='Make the resource diskful on the node.'
        )
        p_mkavial.add_argument(
            '-l', '--layer-list',
            type=self.layer_data_check,
            help="Comma separated layer list, order is from left to right top-down "
                 "This means the top most layer is on the left. "
                 "Possible layers are: " + ",".join(linstor.Linstor.layer_list()))
        p_mkavial.add_argument(
            'node_name',
            type=str,
            help='Name of the node to deploy the resource').completer = self.node_completer
        p_mkavial.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_mkavial.set_defaults(func=self.make_available)

        # remove-resource
        p_rm_res = res_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Removes a resource. '
            'The resource is undeployed from the node '
            "and the resource entry is marked for removal from LINSTOR's data "
            'tables. After the node has undeployed the resource, the resource '
            "entry is removed from LINSTOR's data tables.")
        p_rm_res.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_rm_res.add_argument('node_name',
                              nargs="+",
                              help='Name of the node').completer = self.node_completer
        p_rm_res.add_argument('name',
                              help='Name of the resource to delete').completer = self.resource_completer
        p_rm_res.set_defaults(func=self.delete)

        resgroupby = [x.name.lower() for x in ResourceCommands._resource_headers]
        res_group_completer = Commands.show_group_completer(resgroupby, "groupby")

        p_lreses = res_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource definitions known to '
            'LINSTOR. By default, the list is printed as a human readable table.')
        p_lreses.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lreses.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=resgroupby,
            type=str.lower).completer = res_group_completer
        p_lreses.add_argument(
            '-r', '--resources',
            nargs='+',
            type=str,
            help='Filter by list of resources').completer = self.resource_completer
        p_lreses.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=str,
            help='Filter by list of nodes').completer = self.node_completer
        p_lreses.add_argument(
            '-a', '--all',
            action="store_true",
            help='Show all resources.')
        p_lreses.add_argument(
            '--faulty',
            action="store_true",
            help='Only show faulty resource.')
        p_lreses.add_argument('--props', nargs='+', type=str, help='Filter list by object properties')
        p_lreses.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lreses.add_argument(
            '--from-file',
            type=argparse.FileType('r'),
            help="Read data to display from the given json file",
        )
        p_lreses.set_defaults(func=self.list)

        p_involved = res_subp.add_parser(
            Commands.Subcommands.Involved.LONG,
            aliases=[Commands.Subcommands.Involved.SHORT],
            description='Prints a list of resources involved on a given node.')
        p_involved.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_involved.add_argument('-i', '--inuse', action="store_true", help='Only show resource bundles that are used.')
        p_involved.add_argument(
            '-d',
            '--diskless-inuse',
            action="store_true",
            help='Only show resource bundles that have a diskless in-use.')
        p_involved.add_argument(
            '-m',
            '--min-diskful',
            type=int,
            default=None,
            help='Only show resource bundles that have less diskful replicas.')
        p_involved.add_argument(
            '-s',
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_involved.add_argument(
            'node',
            type=str,
            help='Node name where a resource is used').completer = self.node_completer
        p_involved.set_defaults(func=self.involved)

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
            type=str,
            help='Filter by list of nodes').completer = self.node_completer
        p_lvlms.add_argument('-s', '--storage-pools', nargs='+', type=str,
                             help='Filter by list of storage pools').completer = self.storage_pool_completer
        p_lvlms.add_argument(
            '-r', '--resources',
            nargs='+',
            type=str,
            help='Filter by list of resources').completer = self.resource_completer
        p_lvlms.add_argument(
            '-a', '--all',
            action="store_true",
            help='Show all resources.'
        )
        p_lvlms.add_argument(
            '--show-props',
            nargs='+',
            type=str,
            default=[],
            help='Show these props in the list. '
                 + 'Can be key=value pairs where key is the property name and value column header')
        p_lvlms.set_defaults(func=self.list_volumes)

        # show properties
        p_sp = res_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given resource.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name',
            help="Node name where the resource is deployed.").completer = self.node_completer
        p_sp.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = res_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the given resource on the given node.')
        p_setprop.add_argument(
            'node_name',
            type=str,
            help='Node name where resource is deployed.').completer = self.node_completer
        p_setprop.add_argument(
            'name',
            type=str,
            help='Name of the resource'
        ).completer = self.resource_completer
        Commands.add_parser_keyvalue(p_setprop, "resource")
        p_setprop.set_defaults(func=self.set_props)

        # drbd peer device Options
        p_drbd_peer_opts = res_subp.add_parser(
            Commands.Subcommands.DrbdPeerDeviceOptions.LONG,
            aliases=[Commands.Subcommands.DrbdPeerDeviceOptions.SHORT],
            description=DrbdOptions.description("peer-device")
        )
        p_drbd_peer_opts.add_argument(
            'node_a',
            type=str,
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'node_b',
            type=str,
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'resource_name',
            type=str,
            help="Resource name"
        ).completer = self.resource_completer

        DrbdOptions.add_arguments(p_drbd_peer_opts, self.CONN_OBJECT_NAME)
        p_drbd_peer_opts.set_defaults(func=self.drbd_peer_opts)

        # toggle-disk
        p_toggle_disk = res_subp.add_parser(
            Commands.Subcommands.ToggleDisk.LONG,
            aliases=[Commands.Subcommands.ToggleDisk.SHORT],
            description='Toggles a resource between diskless and diskful (backed by disk/s).')
        p_toggle_disk_group_storage = p_toggle_disk.add_mutually_exclusive_group(required=False)
        p_toggle_disk_group_storage.add_argument(
            '--storage-pool', '-s',
            type=str,
            help="Add disks to a diskless resource using this storage pool name"
        ).completer = self.storage_pool_dfn_completer
        p_toggle_disk_group_storage.add_argument(
            '--default-storage-pool', '--dflt',
            action='store_true',
            help="Add disks to a diskless resource using the storage pools determined from the properties of the "
                 "objects to which the volumes belong"
        )
        p_toggle_disk_group_storage.add_argument(
            '--diskless', '-d',
            action='store_true',
            help="Remove the disks from a resource (toggles --drbd-diskless)"
        )
        p_toggle_disk.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_toggle_disk.add_argument(
            '--migrate-from',
            type=str,
            metavar="MIGRATION_SOURCE",
            help='Name of the node on which the resource should be deleted once the sync is complete. '
                 'Only applicable when adding a disk to a diskless resource. '
                 'The command will complete once the new disk has been added; '
                 'the deletion will occur later in the background.'
        ).completer = self.node_completer
        p_toggle_disk.add_argument(
            'node_name',
            type=str,
            help='Node name where resource is deployed'
        ).completer = self.node_completer
        p_toggle_disk.add_argument(
            'name',
            type=str,
            help='Name of the resource'
        ).completer = self.resource_dfn_completer
        p_toggle_disk.set_defaults(func=self.toggle_disk, parser=p_toggle_disk)

        # activate/deactivate resource commands
        p_activate = res_subp.add_parser(
            Commands.Subcommands.Activate.LONG,
            aliases=[Commands.Subcommands.Activate.SHORT],
            description='Activate a resource.')
        p_activate.add_argument(
            'node_name',
            type=str,
            help='Node name of the resource').completer = self.node_completer
        p_activate.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource').completer = self.resource_dfn_completer
        p_activate.set_defaults(func=self.activate)

        p_deactivate = res_subp.add_parser(
            Commands.Subcommands.Deactivate.LONG,
            aliases=[Commands.Subcommands.Deactivate.SHORT],
            description='Deactivate a resource.')
        p_deactivate.add_argument(
            'node_name',
            type=str,
            help='Node name of the resource').completer = self.node_completer
        p_deactivate.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource').completer = self.resource_dfn_completer
        p_deactivate.set_defaults(func=self.deactivate)

        # resource creation transaction commands
        transactional_create_subcmds = [
            Commands.Subcommands.Begin,
            Commands.Subcommands.Abort,
            Commands.Subcommands.Commit
        ]

        transactional_create_parser = res_subp.add_parser(
            Commands.Subcommands.CreateTransactional.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[Commands.Subcommands.CreateTransactional.SHORT],
            description="%s subcommands" % Commands.Subcommands.CreateTransactional.LONG)

        transactional_create_subp = transactional_create_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.CreateTransactional.LONG,
            description=Commands.Subcommands.generate_desc(transactional_create_subcmds))

        # begin resource creation transaction
        p_transactional_create_begin = transactional_create_subp.add_parser(
            Commands.Subcommands.Begin.LONG,
            aliases=[Commands.Subcommands.Begin.SHORT],
            description='Define a list of resources to create in a single transaction.')
        p_transactional_create_begin.add_argument(
            '--terminate-on-error',
            action='store_true',
            help='Abort the transaction when any command fails.'
        )
        p_transactional_create_begin.set_defaults(func=self.transactional_create_begin)

        # abort resource creation transaction
        p_transactional_create_abort = transactional_create_subp.add_parser(
            Commands.Subcommands.Abort.LONG,
            aliases=[Commands.Subcommands.Abort.SHORT],
            description='Abort resource creation transaction.')
        p_transactional_create_abort.set_defaults(
            func=self.transactional_create_abort, allowed_states=[ResourceCreateTransactionState])

        # commit resource creation transaction
        p_transactional_create_commit = transactional_create_subp.add_parser(
            Commands.Subcommands.Commit.LONG,
            aliases=[Commands.Subcommands.Commit.SHORT],
            description='Create resources defined in the current resource creation transaction.')
        p_transactional_create_commit.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_transactional_create_commit.set_defaults(
            func=self.transactional_create_commit, allowed_states=[ResourceCreateTransactionState])

        self.check_subcommands(transactional_create_subp, transactional_create_subcmds)
        self.check_subcommands(res_subp, subcmds)

    def create(self, args):
        async_flag = vars(args)["async"]
        current_state = self._state_service.get_state()

        if args.auto_place:
            if current_state.__class__ == ResourceCreateTransactionState:
                print("Error: --auto-place not allowed in state '{state.name}'".format(state=current_state))
                return ExitCode.ILLEGAL_STATE

            place_count, additional_place_count, diskless_type = self.parse_place_count_args(args)

            # auto-place resource
            replies = self._linstor.resource_auto_place(
                args.resource_definition_name,
                place_count,
                args.storage_pool,
                args.do_not_place_with,
                args.do_not_place_with_regex,
                replicas_on_same=self.prepare_argparse_list(args.replicas_on_same,
                                                            linstor.consts.NAMESPC_AUXILIARY + '/'),
                replicas_on_different=self.prepare_argparse_list(
                    args.replicas_on_different, linstor.consts.NAMESPC_AUXILIARY + '/'),
                diskless_on_remaining=self.parse_diskless_on_remaining(args),
                async_msg=async_flag,
                layer_list=args.layer_list,
                provider_list=args.providers,
                additional_place_count=additional_place_count,
                diskless_type=diskless_type,
                diskless_storage_pool=args.diskless_storage_pool
            )

            return self.handle_replies(args, replies)

        else:
            # normal create resource
            # check that node is given
            if not args.node_name:
                raise ArgumentError("resource create: too few arguments: Node name missing.")

            rscs = [
                linstor.ResourceData(
                    node_name,
                    args.resource_definition_name,
                    args.diskless,
                    args.storage_pool[0] if args.storage_pool else None,
                    args.node_id,
                    args.layer_list,
                    args.drbd_diskless,
                    args.nvme_initiator,
                    args.ebs_initiator,
                    not args.inactive
                )
                for node_name in args.node_name
            ]

            if current_state.__class__ == ResourceCreateTransactionState:
                print("{} resource(s) added to transaction".format(len(rscs)))
                current_state.rscs.extend(rscs)
                return ExitCode.OK
            else:
                replies = self._linstor.resource_create(rscs, async_flag)
                return self.handle_replies(args, replies)

    def make_available(self, args):
        replies = self.get_linstorapi().resource_make_available(
            args.node_name, args.resource_name, args.diskful, args.layer_list)
        return self.handle_replies(args, replies)

    def delete(self, args):
        async_flag = vars(args)["async"]

        # execute delete resource and flatten result list
        replies = [x for subx in args.node_name for x in self._linstor.resource_delete(subx, args.name, async_flag)]
        return self.handle_replies(args, replies)

    @classmethod
    def _filter_involved_resources(
            cls,
            res_response,
            on_nodes=None,
            only_inuse=False,
            only_diskless_inuse=False,
            min_replicas=None):
        """
        Filter a RscRespWrapper object according to involved rules.

        :param RscRespWrapper res_response: response resource wrapper where deleting resource is possible
        :param list[str] on_nodes: if resource is on any of these nodes
        :param bool only_inuse: only show resource bundles that are inuse
        :param bool only_diskless_inuse: only show resource bundles where the inuse node is diskless
        :param Optional[int] min_replicas: only show resource bundles that have less diskful replicas
        :return: The res_response argument with filtered resources
        :rtype: RscRespWrapper
        """
        res_del = set()
        rsc_state_lkup = {x.node_name + x.name: x for x in res_response.resource_states}
        if on_nodes:
            look_up_nodes = {}
            for rsc in res_response.resources:
                in_use = rsc_state_lkup.get(rsc.node_name + rsc.name).in_use
                if rsc.name not in look_up_nodes:
                    look_up_nodes[rsc.name] = {
                        'nodes': [rsc.node_name],
                        'inuse': rsc_state_lkup.get(rsc.node_name + rsc.name).in_use,
                        'diskless-inuse': in_use and apiconsts.FLAG_DISKLESS in rsc.flags,
                        'replicas': 1 if apiconsts.FLAG_DISKLESS not in rsc.flags else 0
                    }
                else:
                    look_up_nodes[rsc.name]['nodes'].append(rsc.node_name)
                    look_up_nodes[rsc.name]['inuse'] |= in_use
                    look_up_nodes[rsc.name]['diskless-inuse'] |= in_use and apiconsts.FLAG_DISKLESS in rsc.flags
                    look_up_nodes[rsc.name]['replicas'] += 1 if apiconsts.FLAG_DISKLESS not in rsc.flags else 0
            for i, rsc in enumerate(res_response.resources):
                look_rsc = look_up_nodes[rsc.name]
                for n in on_nodes:
                    if n not in look_rsc['nodes']:
                        res_del.add(i)
                        break
                if only_inuse and not look_rsc['inuse']:
                    res_del.add(i)
                if only_diskless_inuse and not look_rsc['diskless-inuse']:
                    res_del.add(i)
                if min_replicas is not None and min_replicas <= look_rsc['replicas']:
                    res_del.add(i)
            res_del_list = list(res_del)
            res_del_list.sort()
            for ri in reversed(res_del_list):
                del res_response.resources[ri]
        return res_response

    def show(self, args, lstmsg):
        """

        :param args:
        :param RscRespWrapper lstmsg:
        :return:
        """
        rsc_dfns = linstor.responses.ResourceDefinitionResponse([])
        if not args.from_file:
            rsc_dfns = self._linstor.resource_dfn_list_raise(query_volume_definitions=False)

        rsc_dfn_map = {x.name: x for x in rsc_dfns.resource_definitions}
        rsc_state_lkup = {x.node_name + x.name: x for x in lstmsg.resource_states}

        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in ResourceCommands._resource_headers:
            tbl.add_header(hdr)

        show_props = self._append_show_props_hdr(tbl, args.show_props)

        tbl.set_groupby(args.groupby if args.groupby else [ResourceCommands._resource_headers[0].name])

        for rsc in lstmsg.resources:
            rsc_dfn_port = ''
            if rsc.name in rsc_dfn_map:
                drbd_data = rsc_dfn_map[rsc.name].drbd_data
                rsc_dfn_port = drbd_data.port if drbd_data else ""
            marked_delete = apiconsts.FLAG_DELETE in rsc.flags or apiconsts.FLAG_DRBD_DELETE in rsc.flags
            rsc_state_obj = rsc_state_lkup.get(rsc.node_name + rsc.name)
            rsc_state_color = Color.YELLOW
            rsc_state = "Unknown"
            rsc_usage = ""
            rsc_usage_color = None
            if marked_delete:
                rsc_state_color = Color.RED
                rsc_state = "DELETING"
            elif apiconsts.FLAG_RSC_INACTIVE in rsc.flags:
                rsc_state = apiconsts.FLAG_RSC_INACTIVE
            elif rsc_state_obj:
                if rsc_state_obj.in_use is not None:
                    if rsc_state_obj.in_use:
                        rsc_usage_color = Color.GREEN
                        rsc_usage = "InUse"
                    else:
                        rsc_usage = "Unused"
                for vlm in rsc.volumes:
                    rsc_state, rsc_state_color = VolumeCommands.volume_state_cell(vlm, rsc.flags)
                    if apiconsts.FLAG_EVACUATE in rsc.flags:
                        rsc_state += ", Evacuating"
                    if rsc_state_color is not None:
                        break

            if not self.get_linstorapi().api_version_smaller("1.20.2"):
                if "DrbdOptions/SkipDisk" in rsc.effective_properties:
                    skip_disk_eff_prop = rsc.effective_properties["DrbdOptions/SkipDisk"]
                    if skip_disk_eff_prop.value == "True":
                        occurrences = [Commands.EFFECTIVE_PROPS_TYPES[skip_disk_eff_prop.type]]
                        if skip_disk_eff_prop.other:
                            occurrences += [self.EFFECTIVE_PROPS_TYPES[other.type]
                                            for other in skip_disk_eff_prop.other]
                        rsc_state += ", Skip-Disk (" + ', '.join(occurrences) + ")"

                        if not rsc_state_color or rsc_state_color == Color.GREEN:
                            rsc_state_color = Color.YELLOW

            # check if connections failed
            conns_col = ""
            conns_col_entries = None
            if rsc_state != "Unknown" and not self.get_linstorapi().api_version_smaller("1.0.15"):
                failed_conns = {}
                if rsc.layer_data.drbd_resource is not None:
                    connections = rsc.layer_data.drbd_resource.connections
                    for k, v in connections.items():
                        if not v.connected:
                            if v.message not in failed_conns:
                                failed_conns[v.message] = []
                            failed_conns[v.message].append(k)
                conns_col_entries = ["{s}({n})".format(s=k, n=",".join(v)) for k, v in failed_conns.items()]
                conns_col = tbl.color_cell(",".join(conns_col_entries), Color.RED) if conns_col_entries else "Ok"

            show_row = True
            if args.faulty:
                show_row = rsc_state_color is not None or not (conns_col == 'Ok' or conns_col == "")

            if show_row:
                row = [
                    rsc.name,
                    rsc.node_name,
                    rsc_dfn_port,
                    tbl.color_cell(rsc_usage, rsc_usage_color) if rsc_usage_color else rsc_usage,
                    conns_col,
                    tbl.color_cell(rsc_state, Color.RED if conns_col_entries else rsc_state_color),
                    str(rsc.create_datetime)[:19] if rsc.create_datetime else ""
                ]
                for sprop in show_props:
                    row.append(rsc.properties.get(sprop, ''))
                tbl.add_row(row)
        tbl.show()

    def list(self, args):
        args = self.merge_config_args('resource.list', args)
        if args.from_file:
            lstmsg = [linstor.responses.ResourceResponse(json.load(args.from_file))]
        else:
            lstmsg = self._linstor.resource_list(
                filter_by_nodes=args.nodes, filter_by_resources=args.resources, filter_by_props=args.props)
        return self.output_list(args, lstmsg, self.show)

    def list_volumes(self, args):
        args = self.merge_config_args('volume.list', args)
        lstmsg = self._linstor.volume_list(args.nodes, args.storage_pools, args.resources)
        return self.output_list(args, lstmsg, VolumeCommands.show_volumes)

    def show_involved(self, args, lstmsg):
        """
        Filters involved resources and shows them with the normal resource list function.

        :param args: argparse options
        :param linstor.responses.ResourceResponse lstmsg: resource list REST answer from controller.
        :return: None
        """
        args.groupby = None
        args.all = True
        args.faulty = False
        rsc_resp_wrp = RscRespWrapper(lstmsg)
        self._filter_involved_resources(rsc_resp_wrp, [args.node], args.inuse, args.diskless_inuse, args.min_diskful)
        self.show(args, rsc_resp_wrp)

    def involved(self, args):
        lstmsg = self._linstor.resource_list()
        return self.output_list(args, lstmsg, self.show_involved)

    @classmethod
    def _props_show(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc in lstmsg.resources:
                result.append(rsc.properties)
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_list([args.node_name], [args.resource_name])
        return self.output_props_list(args, lstmsg, self._props_show)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.resource_modify(
            args.node_name,
            args.name,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def drbd_peer_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']
        del a['node-a']
        del a['node-b']

        mod_props, del_props = DrbdOptions.parse_opts(a, self.CONN_OBJECT_NAME)

        replies = self._linstor.resource_conn_modify(
            args.resource_name,
            args.node_a,
            args.node_b,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)

    def toggle_disk(self, args):
        async_flag = vars(args)["async"]

        if args.diskless and args.migrate_from:
            args.parser.error("--migrate-from cannot be used with --diskless")

        replies = self._linstor.resource_toggle_disk(
            args.node_name,
            args.name,
            storage_pool=args.storage_pool,
            migrate_from=args.migrate_from,
            diskless=args.diskless,
            async_msg=async_flag
        )
        return self.handle_replies(args, replies)

    def transactional_create_begin(self, args):
        return self._state_service.enter_state(
            ResourceCreateTransactionState(args.terminate_on_error),
            verbose=args.verbose
        )

    def transactional_create_abort(self, _):
        self._state_service.pop_state()
        return ExitCode.OK

    def transactional_create_commit(self, args):
        async_flag = vars(args)["async"]
        replies = self._linstor.resource_create(self._state_service.get_state().rscs, async_flag)
        self._state_service.pop_state()
        return self.handle_replies(args, replies)

    def activate(self, args):
        replies = self.get_linstorapi().resource_activate(
            node_name=args.node_name,
            rsc_name=args.resource_name
        )
        return self.handle_replies(args, replies)

    def deactivate(self, args):
        replies = self.get_linstorapi().resource_deactivate(
            node_name=args.node_name,
            rsc_name=args.resource_name
        )
        return self.handle_replies(args, replies)
