from proto.MsgCrtRsc_pb2 import MsgCrtRsc
from proto.MsgDelRsc_pb2 import MsgDelRsc
from proto.MsgLstRsc_pb2 import MsgLstRsc
from proto.MsgLstRscDfn_pb2 import MsgLstRscDfn
from proto.MsgLstStorPool_pb2 import MsgLstStorPool
from proto.LinStorMapEntry_pb2 import LinStorMapEntry
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands, NodeCommands, StoragePoolDefinitionCommands, StoragePoolCommands
from linstor.utils import namecheck, Table, Output
from linstor.consts import Color
from linstor.sharedconsts import (
    API_CRT_RSC,
    API_DEL_RSC,
    API_LST_RSC,
    API_LST_RSC_DFN,
    API_LST_STOR_POOL,
    KEY_STOR_POOL_NAME,
    FLAG_DELETE,
    FLAG_DISKLESS
)

from linstor.consts import BOOL_TRUE, BOOL_FALSE, NODE_NAME, RES_NAME, STORPOOL_NAME


class ResourceCommands(Commands):

    @staticmethod
    def setup_commands(parser):
        # new-resource
        p_new_res = parser.add_parser(
            'create-resource',
            aliases=['crtrsc'],
            description='Defines a DRBD resource for use with linstor. '
            'Unless a specific IP port-number is supplied, the port-number is '
            'automatically selected by the linstor controller on the current node. ')
        p_new_res.add_argument(
            '-s', '--storage-pool',
            type=namecheck(STORPOOL_NAME),
            help="Storage pool name to use.").completer = StoragePoolDefinitionCommands.completer
        p_new_res.add_argument('-d', '--diskless', action="store_true", help='Should the resource be diskless')
        p_new_res.add_argument('name', type=namecheck(RES_NAME), help='Name of the new resource')
        p_new_res.add_argument('node_name',
                               type=namecheck(NODE_NAME),
                               help='Name of the new resource').completer = NodeCommands.completer
        p_new_res.set_defaults(func=ResourceCommands.create)

        # modify-resource
        p_mod_res_command = 'modify-resource'
        p_mod_res = parser.add_parser(
            p_mod_res_command,
            aliases=['mr'],
            description='Modifies a DRBD resource.')
        p_mod_res.add_argument('-m', '--managed', choices=(BOOL_TRUE, BOOL_FALSE))
        p_mod_res.add_argument('name', type=namecheck(RES_NAME),
                               help='Name of the resource').completer = ResourceCommands.completer
        p_mod_res.set_defaults(func=Commands.cmd_enoimp)
        p_mod_res.set_defaults(command=p_mod_res_command)

        # remove-resource
        p_rm_res = parser.add_parser(
            'delete-resource',
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
                              help='Name of the resource to delete').completer = ResourceCommands.completer
        p_rm_res.add_argument('node_name',
                              nargs="+",
                              help='Name of the node').completer = NodeCommands.completer
        p_rm_res.set_defaults(func=ResourceCommands.delete)

        resverbose = ('Port',)
        resgroupby = ('Name', 'Port', 'State')
        res_verbose_completer = Commands.show_group_completer(resverbose, "show")
        res_group_completer = Commands.show_group_completer(resgroupby, "groupby")

        p_lreses = parser.add_parser(
            'list-resources',
            aliases=['list-resource', 'ls-rsc', 'display-resources'],
            description='Prints a list of all resource definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lreses.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lreses.add_argument(
            '-s', '--show',
            nargs='+',
            choices=resverbose).completer = res_verbose_completer
        p_lreses.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=resgroupby).completer = res_group_completer
        p_lreses.add_argument(
            '-R', '--resources',
            nargs='+',
            type=namecheck(RES_NAME),
            help='Filter by list of resources').completer = ResourceCommands.completer
        p_lreses.set_defaults(func=ResourceCommands.list)

        # list volumes
        p_lvlms = parser.add_parser(
            'list-volumes',
            aliases=['list-volume', 'ls-vlm', 'display-volumes'],
            description='Prints a list of all volumes.'
        )
        p_lvlms.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lvlms.add_argument('resource', nargs='?')
        p_lvlms.set_defaults(func=ResourceCommands.list_volumes)

        # show properties
        p_sp = parser.add_parser(
            'get-resource-properties',
            aliases=['get-resource-props'],
            description="Prints all properties of the given resource.")
        p_sp.add_argument(
            'resource_name',
            help="Resource for which to print the properties").completer = ResourceCommands.completer
        p_sp.set_defaults(func=ResourceCommands.print_props)

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtRsc()
        p.rsc.name = args.name
        p.rsc.node_name = args.node_name

        if not args.diskless and args.storage_pool:
            prop = LinStorMapEntry()
            prop.key = KEY_STOR_POOL_NAME
            prop.value = args.storage_pool
            p.rsc.props.extend([prop])

        if args.diskless:
            p.rsc.rsc_flags.append(FLAG_DISKLESS)

        return Commands._create(cc, API_CRT_RSC, p, args)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for node_name in args.node_name:
            p = MsgDelRsc()
            p.rsc_name = args.name
            p.node_name = node_name

            del_msgs.append(p)

        return Commands._delete_and_output(cc, args, API_DEL_RSC, del_msgs)

    @staticmethod
    def find_rsc_state(rsc_states, rsc_name, node_name):
        for rscst in rsc_states:
            if rscst.rsc_name == rsc_name and rscst.node_name == node_name:
                return rscst
        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_RSC, MsgLstRsc(), args)

        if lstmsg:
            rsc_dfns = Commands._get_list_message(cc, API_LST_RSC_DFN, MsgLstRscDfn(), args).rsc_dfns
            rsc_dfn_map = {x.rsc_name: x for x in rsc_dfns}

            stor_pools = Commands._get_list_message(cc, API_LST_STOR_POOL, MsgLstStorPool(), args).stor_pools
            stor_pool_map = {x.stor_pool_name: x for x in stor_pools}

            tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
            tbl.add_column("ResourceName")
            tbl.add_column("Node")
            tbl.add_column("Port")
            tbl.add_column("Device", color=Output.color(Color.DARKGREEN, args.no_color))
            tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color), just_txt='>')

            for rsc in lstmsg.resources:
                rsc_dfn = rsc_dfn_map[rsc.name]
                diskless = FLAG_DISKLESS in rsc.rsc_flags
                if not diskless:
                    storage_pool_name = Commands._get_prop(rsc.props, KEY_STOR_POOL_NAME)
                    storage_pool = stor_pool_map[storage_pool_name]
                    driver_key = StoragePoolCommands.get_driver_key(storage_pool.driver)
                    block_device = Commands._get_prop(storage_pool.props, driver_key)
                    # print(storage_pool)
                marked_delete = FLAG_DELETE in rsc.rsc_flags
                # rsc_state = ResourceCommands.find_rsc_state(lstmsg.resource_states, rsc.name, rsc.node_name)
                tbl.add_row([
                    rsc.name,
                    rsc.node_name,
                    rsc_dfn.rsc_dfn_port,
                    tbl.color_cell("DISKLESS", Color.GREEN) if diskless else block_device,
                    tbl.color_cell("DELETING", Color.RED) if marked_delete else "ok"
                ])
            tbl.show()

        return None

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

    @staticmethod
    @need_communication
    def list_volumes(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_RSC, MsgLstRsc(), args)  # type: MsgLstRsc

        if lstmsg:
            tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
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
                    state = tbl.color_cell("unknown", Color.YELLOW)
                    if vlm_state:
                        state = "ok"
                        problems = []
                        if not vlm_state.is_present:
                            problems.append("not present")
                        if vlm_state.disk_failed:
                            problems.append("disk failed")

                        if problems:
                            state = tbl.color_cell(", ".join(problems), Color.RED)
                    tbl.add_row([
                        rsc.node_name,
                        rsc.name,
                        str(vlm.vlm_nr),
                        str(vlm.vlm_minor_nr),
                        state
                    ])

            tbl.show()

        return None

    @staticmethod
    @need_communication
    def print_props(cc, args):
        lstmsg = Commands._request_list(cc, API_LST_RSC, MsgLstRsc())

        if lstmsg:
            for rsc in lstmsg.resources:
                if rsc.name == args.resource_name:
                    Commands._print_props(rsc.props)
                    break

        return None

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_RSC, MsgLstRsc())

        if lstmsg:
            for rsc in lstmsg.resources:
                possible.add(rsc.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible

    @staticmethod
    @completer_communication
    def completer_volume(cc, prefix, **kwargs):
        possible = set()
        return possible
