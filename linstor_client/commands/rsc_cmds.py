from __future__ import print_function

import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
import linstor.sharedconsts as apiconsts
from linstor_client.commands import DefaultState, Commands, DrbdOptions, ArgumentError
from linstor_client.consts import NODE_NAME, RES_NAME, STORPOOL_NAME, Color, ExitCode
from linstor_client.utils import Output, namecheck


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


class ResourceCommands(Commands):
    CONN_OBJECT_NAME = 'rsc-conn'

    _resource_headers = [
        linstor_client.TableHeader("ResourceName"),
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Port"),
        linstor_client.TableHeader("Usage", Color.DARKGREEN),
        linstor_client.TableHeader("State", Color.DARKGREEN, alignment_text=linstor_client.TableHeader.ALIGN_RIGHT)
    ]

    def __init__(self, state_service):
        super(ResourceCommands, self).__init__()

        self._state_service = state_service

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.ListVolumes,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdPeerDeviceOptions,
            Commands.Subcommands.ToggleDisk,
            Commands.Subcommands.CreateTransactional
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
            '--storage-pool', '-s',
            type=namecheck(STORPOOL_NAME),
            help="Storage pool name to use.").completer = self.storage_pool_dfn_completer
        p_new_res.add_argument('--diskless', '-d', action="store_true", help='Should the resource be diskless')
        p_new_res.add_argument(
            '--node-id',
            type=int,
            help='Override the automatic selection of DRBD node ID'
        )
        p_new_res.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for deployment on satellites before returning'
        )
        p_new_res.add_argument(
            '--auto-place',
            type=int,
            metavar="REPLICA_COUNT",
            help = 'Auto place a resource to a specified number of nodes'
        )
        p_new_res.add_argument(
            '--do-not-place-with',
            type=namecheck(RES_NAME),
            nargs='+',
            metavar="RESOURCE_NAME",
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = self.resource_completer
        p_new_res.add_argument(
            '--do-not-place-with-regex',
            type=str,
            metavar="RESOURCE_REGEX",
            help='Try to avoid nodes that already have a resource ' +
                 'deployed whos name is matching the given regular expression.'
        )
        p_new_res.add_argument(
            '--replicas-on-same',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with the same given auxiliary node property values.'
        )
        p_new_res.add_argument(
            '--replicas-on-different',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with a different value for the given auxiliary node property.'
        )
        p_new_res.add_argument(
            '--diskless-on-remaining',
            action="store_true",
            help='Will add a diskless resource on all non replica nodes.'
        )
        p_new_res.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            nargs='*',
            help='Name of the node to deploy the resource').completer = self.node_completer
        p_new_res.add_argument(
            'resource_definition_name',
            type=namecheck(RES_NAME),
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_res.set_defaults(func=self.create, allowed_states=[DefaultState, ResourceCreateTransactionState])

        # remove-resource
        p_rm_res = res_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Removes a resource. '
            'The resource is undeployed from the node '
            "and the resource entry is marked for removal from linstor's data "
            'tables. After the node has undeployed the resource, the resource '
            "entry is removed from linstor's data tables.")
        p_rm_res.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for actual deletion on satellites before returning'
        )
        p_rm_res.add_argument('node_name',
                              nargs="+",
                              help='Name of the node').completer = self.node_completer
        p_rm_res.add_argument('name',
                              help='Name of the resource to delete').completer = self.resource_completer
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
            description='Sets properties for the given resource on the given node.')
        p_setprop.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Node name where resource is deployed.').completer = self.node_completer
        p_setprop.add_argument(
            'name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_completer
        Commands.add_parser_keyvalue(p_setprop, "resource")
        p_setprop.set_defaults(func=self.set_props)

        # drbd peer device options
        p_drbd_peer_opts = res_subp.add_parser(
            Commands.Subcommands.DrbdPeerDeviceOptions.LONG,
            aliases=[Commands.Subcommands.DrbdPeerDeviceOptions.SHORT],
            description=DrbdOptions.description("peer-device")
        )
        p_drbd_peer_opts.add_argument(
            'node_a',
            type=namecheck(NODE_NAME),
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'node_b',
            type=namecheck(NODE_NAME),
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help="Resource name"
        ).completer = self.resource_completer

        DrbdOptions.add_arguments(p_drbd_peer_opts, self.CONN_OBJECT_NAME)
        p_drbd_peer_opts.set_defaults(func=self.drbd_peer_opts)

        # toggle-disk
        p_toggle_disk = res_subp.add_parser(
            Commands.Subcommands.ToggleDisk.LONG,
            aliases=[Commands.Subcommands.ToggleDisk.SHORT],
            description='Toggles a resource between diskless and having disks.')
        p_toggle_disk_group_storage = p_toggle_disk.add_mutually_exclusive_group(required=True)
        p_toggle_disk_group_storage.add_argument(
            '--storage-pool', '-s',
            type=namecheck(STORPOOL_NAME),
            help="Add disks to a diskless resource using this storage pool name"
        ).completer = self.storage_pool_dfn_completer
        p_toggle_disk_group_storage.add_argument(
            '--default-storage-pool', '-dflt',
            action='store_true',
            help="Add disks to a diskless resource using the storage pools determined from the properties of the "
                 "objects to which the volumes belong"
        )
        p_toggle_disk_group_storage.add_argument(
            '--diskless', '-d',
            action='store_true',
            help="Remove the disks from a resource"
        )
        p_toggle_disk.add_argument(
            '--async',
            action='store_true',
            help='Do not wait to apply changes on satellites before returning'
        )
        p_toggle_disk.add_argument(
            '--migrate-from',
            type=namecheck(NODE_NAME),
            metavar="MIGRATION_SOURCE",
            help='Name of the node on which the resource should be deleted once the sync is complete. '
                 'Only applicable when adding a disk to a diskless resource. '
                 'The command will complete once the new disk has been added; '
                 'the deletion will occur later in the background.'
        ).completer = self.node_completer
        p_toggle_disk.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Node name where resource is deployed'
        ).completer = self.node_completer
        p_toggle_disk.add_argument(
            'name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_dfn_completer
        p_toggle_disk.set_defaults(func=self.toggle_disk, parser=p_toggle_disk)

        # resource creation transaction commands
        transactional_create_subcmds = [
            Commands.Subcommands.TransactionBegin,
            Commands.Subcommands.TransactionAbort,
            Commands.Subcommands.TransactionCommit
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
            Commands.Subcommands.TransactionBegin.LONG,
            aliases=[Commands.Subcommands.TransactionBegin.SHORT],
            description='Start group of resources to create in a single transaction.')
        p_transactional_create_begin.add_argument(
            '--terminate-on-error',
            action='store_true',
            help='Abort the transaction when any command fails'
        )
        p_transactional_create_begin.set_defaults(func=self.transactional_create_begin)

        # abort resource creation transaction
        p_transactional_create_abort = transactional_create_subp.add_parser(
            Commands.Subcommands.TransactionAbort.LONG,
            aliases=[Commands.Subcommands.TransactionAbort.SHORT],
            description='Abort resource creation transaction.')
        p_transactional_create_abort.set_defaults(
            func=self.transactional_create_abort, allowed_states=[ResourceCreateTransactionState])

        # commit resource creation transaction
        p_transactional_create_commit = transactional_create_subp.add_parser(
            Commands.Subcommands.TransactionCommit.LONG,
            aliases=[Commands.Subcommands.TransactionCommit.SHORT],
            description='Create resources defined in the current resource creation transaction.')
        p_transactional_create_commit.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for deployment on satellites before returning'
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

            # auto-place resource
            replies = self._linstor.resource_auto_place(
                args.resource_definition_name,
                args.auto_place,
                args.storage_pool,
                args.do_not_place_with,
                args.do_not_place_with_regex,
                [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_same],
                [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_different],
                diskless_on_remaining=args.diskless_on_remaining,
                async_msg=async_flag
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
                    args.storage_pool,
                    args.node_id
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

    def delete(self, args):
        async_flag = vars(args)["async"]

        # execute delete resource and flatten result list
        replies = [x for subx in args.node_name for x in self._linstor.resource_delete(subx, args.name, async_flag)]
        return self.handle_replies(args, replies)

    def show(self, args, lstmsg):
        rsc_dfns = self._linstor.resource_dfn_list()
        if isinstance(rsc_dfns[0], linstor.ApiCallResponse):
            return self.handle_replies(args, rsc_dfns)
        rsc_dfns = rsc_dfns[0].proto_msg.rsc_dfns

        rsc_dfn_map = {x.rsc_name: x for x in rsc_dfns}
        rsc_state_lkup = {x.node_name + x.rsc_name: x for x in lstmsg.resource_states}

        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in ResourceCommands._resource_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else [ResourceCommands._resource_headers[0].name])

        for rsc in lstmsg.resources:
            rsc_dfn_port = ''
            if rsc.name in rsc_dfn_map:
                rsc_dfn_port = rsc_dfn_map[rsc.name].rsc_dfn_port
            marked_delete = apiconsts.FLAG_DELETE in rsc.rsc_flags
            rsc_state_proto = rsc_state_lkup.get(rsc.node_name + rsc.name)
            rsc_state = tbl.color_cell("Unknown", Color.YELLOW)
            rsc_usage = ""
            if marked_delete:
                rsc_state = tbl.color_cell("DELETING", Color.RED)
            elif rsc_state_proto:
                if rsc_state_proto.HasField('in_use') and rsc_state_proto.in_use:
                    rsc_usage = tbl.color_cell("InUse", Color.GREEN)
                else:
                    rsc_usage = "Unused"
                for vlm in rsc.vlms:
                    vlm_state = ResourceCommands.get_volume_state(rsc_state_proto.vlm_states,
                                                                  vlm.vlm_nr) if rsc_state_proto else None
                    state_txt, color = self.volume_state_cell(vlm_state, rsc.rsc_flags, vlm.vlm_flags)
                    rsc_state = tbl.color_cell(state_txt, color)
                    if color is not None:
                        break
            tbl.add_row([
                rsc.name,
                rsc.node_name,
                rsc_dfn_port,
                rsc_usage,
                rsc_state
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.resource_list(filter_by_nodes=args.nodes, filter_by_resources=args.resources)
        return self.output_list(args, lstmsg, self.show)

    @staticmethod
    def get_volume_state(volume_states, volume_nr):
        for volume_state in volume_states:
            if volume_state.vlm_nr == volume_nr:
                return volume_state
        return None

    @staticmethod
    def volume_state_cell(vlm_state, rsc_flags, vlm_flags):
        """
        Determains the status of a drbd volume for table display.

        :param vlm_state: vlm_state proto
        :param rsc_flags: rsc flags
        :param vlm_flags: vlm flags
        :return: A tuple (state_text, color)
        """
        tbl_color = None
        state_prefix = 'Resizing, ' if apiconsts.FLAG_RESIZE in vlm_flags else ''
        state = state_prefix + "Unknown"
        if vlm_state and vlm_state.HasField("disk_state") and vlm_state.disk_state:
            disk_state = vlm_state.disk_state

            if disk_state == 'DUnknown':
                state = state_prefix + "Unknown"
                tbl_color = Color.YELLOW
            elif disk_state == 'Diskless':
                if apiconsts.FLAG_DISKLESS not in rsc_flags:  # unintentional diskless
                    state = state_prefix + disk_state
                    tbl_color = Color.RED
                else:
                    state = state_prefix + disk_state  # green text
            elif disk_state in ['Inconsistent', 'Failed', 'To: Creating', 'To: Attachable', 'To: Attaching']:
                state = state_prefix + disk_state
                tbl_color = Color.RED
            elif disk_state in ['UpToDate', 'Created', 'Attached']:
                state = state_prefix + disk_state  # green text
            else:
                state = state_prefix + disk_state
                tbl_color = Color.YELLOW
        else:
            tbl_color = Color.YELLOW
        return state, tbl_color

    @classmethod
    def show_volumes(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("Node")
        tbl.add_column("Resource")
        tbl.add_column("StoragePool")
        tbl.add_column("VolumeNr")
        tbl.add_column("MinorNr")
        tbl.add_column("DeviceName")
        tbl.add_column("Allocated")
        tbl.add_column("InUse", color=Output.color(Color.DARKGREEN, args.no_color))
        tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color), just_txt='>')

        rsc_state_lkup = {x.node_name + x.rsc_name: x for x in lstmsg.resource_states}

        for rsc in lstmsg.resources:
            rsc_state = rsc_state_lkup.get(rsc.node_name + rsc.name)
            rsc_usage = ""
            if rsc_state:
                if rsc_state.HasField('in_use') and rsc_state.in_use:
                    rsc_usage = tbl.color_cell("InUse", Color.GREEN)
                else:
                    rsc_usage = "Unused"
            for vlm in rsc.vlms:
                vlm_state = ResourceCommands.get_volume_state(rsc_state.vlm_states, vlm.vlm_nr) if rsc_state else None
                state_txt, color = cls.volume_state_cell(vlm_state, rsc.rsc_flags, vlm.vlm_flags)
                state = tbl.color_cell(state_txt, color) if color else state_txt
                tbl.add_row([
                    rsc.node_name,
                    rsc.name,
                    vlm.stor_pool_name,
                    str(vlm.vlm_nr),
                    str(vlm.vlm_minor_nr),
                    vlm.device_path,
                    linstor.SizeCalc.approximate_size_string(vlm.allocated) if vlm.allocated else "",
                    rsc_usage,
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
                if rsc.name == args.resource_name and rsc.node_name.lower() == args.node_name.lower():
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
