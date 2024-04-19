from __future__ import print_function

import json

import linstor.responses
import linstor.sharedconsts as apiconsts
import linstor_client.argparse.argparse as argparse


from linstor import SizeCalc
# flake8: noqa
from linstor.responses import Resource
from linstor_client import Table
from linstor_client.commands import Commands
from linstor_client.utils import Output
from linstor_client.consts import Color


class VolumeCommands(Commands):

    def setup_commands(self, parser):
        """

        :param parser:
        :return:
        """
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties
        ]

        vlm_parser = parser.add_parser(
            Commands.VOLUME,
            aliases=['v'],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Volume subcommands")
        vlm_sub = vlm_parser.add_subparsers(
            title="volume commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # list volumes
        p_lvlms = vlm_sub.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
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
        p_lvlms.add_argument(
            '--from-file',
            type=argparse.FileType('r'),
            help="Read data to display from the given json file",
        )
        p_lvlms.set_defaults(func=self.list_volumes)

        # show properties
        p_lp = vlm_sub.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Lists all properties set on the specified volume.")
        p_lp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lp.add_argument(
            'node_name',
            help="Node name where the resource is deployed.").completer = self.node_completer
        p_lp.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_completer
        p_lp.add_argument('volume_number', type=int, help="Volume number")
        p_lp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = vlm_sub.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='Sets properties for the specified volume of a specified resource and node.')
        p_setprop.add_argument(
            'node_name',
            type=str,
            help='Node name where resource is deployed.').completer = self.node_completer
        p_setprop.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource'
        ).completer = self.resource_completer
        p_setprop.add_argument('volume_number', type=int, help='Volume number')
        Commands.add_parser_keyvalue(p_setprop, "volume")
        p_setprop.set_defaults(func=self.set_props)

        self.check_subcommands(vlm_sub, subcmds)

    @staticmethod
    def get_volume_state(volume_states, volume_nr):
        for volume_state in volume_states:
            if volume_state.number == volume_nr:
                return volume_state
        return None

    @staticmethod
    def volume_expects_disk_state(vlm):
        """
        Returns true if we expect disk state to be set for this resource, i.e. the top layer is of type DRBD

        :param vlm: vlm proto
        :return: True if the volume should have a disk state, False otherwise
        """
        layer_data = vlm.data_v1.get('layer_data_list', [])
        if len(layer_data) == 0:
            return False
        return layer_data[0].get('type') == linstor.consts.DeviceLayerKind.DRBD.value

    @staticmethod
    def volume_disk_state(vlm):
        """
        Returns the disk state, if any, on the volume

        :param vlm: vlm proto
        :return: The disk state as a string, None otherwise
        """
        return vlm.data_v1.get('state', {}).get('disk_state')

    @staticmethod
    def volume_state_cell(vlm, rsc_flags):
        """
        Determains the status of a drbd volume for table display.

        :param vlm: vlm proto
        :param rsc_flags: rsc flags
        :return: A tuple (state_text, color)
        """
        tbl_color = None
        state_prefix = 'Resizing, ' if apiconsts.FLAG_RESIZE in vlm.flags else ''
        state = state_prefix + "Unknown"
        expect_state = VolumeCommands.volume_expects_disk_state(vlm)
        disk_state = VolumeCommands.volume_disk_state(vlm)
        if not expect_state:
            state = state_prefix + 'Created'
        elif disk_state:
            if disk_state == 'DUnknown':
                state = state_prefix + "Unknown"
                tbl_color = Color.YELLOW
            elif disk_state == 'Diskless':
                if apiconsts.FLAG_DISKLESS not in rsc_flags:  # unintentional diskless
                    state = state_prefix + disk_state
                    tbl_color = Color.RED
                elif apiconsts.FLAG_TIE_BREAKER in rsc_flags:
                    state = 'TieBreaker'
                    tbl_color = None
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
        """

        :param args:
        :param responses.ResourceResponse lstmsg: resource response data to display
        :return: None
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("Node")
        tbl.add_column("Resource")
        tbl.add_column("StoragePool")
        tbl.add_column("VolNr", just_txt='>')
        tbl.add_column("MinorNr", just_txt='>')
        tbl.add_column("DeviceName")
        tbl.add_column("Allocated", just_txt='>')
        tbl.add_column("InUse", color=Output.color(Color.DARKGREEN, args.no_color))
        tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color), just_txt='>')

        show_props = cls._append_show_props_hdr(tbl, args.show_props)

        rsc_state_lkup = {x.node_name + x.name: x for x in lstmsg.resource_states}

        reports = []
        for rsc in lstmsg.resources:
            if apiconsts.FLAG_RSC_INACTIVE in rsc.flags and not apiconsts.FLAG_EVICTED in rsc.flags:
                continue  # do not show non existing volumes for inactive resources

            rsc_state = rsc_state_lkup.get(rsc.node_name + rsc.name)
            rsc_usage = ""
            if rsc_state and rsc_state.in_use is not None:
                if rsc_state.in_use:
                    rsc_usage = tbl.color_cell("InUse", Color.GREEN)
                else:
                    rsc_usage = "Unused"
            for vlm in rsc.volumes:
                if apiconsts.FLAG_RSC_INACTIVE in rsc.flags:
                    state_txt = apiconsts.FLAG_RSC_INACTIVE
                    color = Color.YELLOW
                else:
                    state_txt, color = cls.volume_state_cell(vlm, rsc.flags)
                has_errors = any([x.is_error() for x in vlm.reports])
                conn_failed = (rsc.layer_data.drbd_resource
                               and any(not v.connected for k, v in rsc.layer_data.drbd_resource.connections.items()))
                if conn_failed:
                    color = Color.RED

                state = tbl.color_cell(state_txt, color) if color else state_txt
                if has_errors:
                    state = tbl.color_cell("Error", Color.RED)
                for x in vlm.reports:
                    reports.append(x)
                vlm_drbd_data = vlm.drbd_data
                row = [
                    rsc.node_name,
                    rsc.name,
                    vlm.storage_pool_name,
                    str(vlm.number),
                    str(vlm_drbd_data.drbd_volume_definition.minor) if vlm_drbd_data else "",
                    vlm.device_path,
                    SizeCalc.approximate_size_string(vlm.allocated_size) if vlm.allocated_size else "",
                    rsc_usage,
                    state
                ]
                for sprop in show_props:
                    row.append(vlm.properties.get(sprop, ''))
                tbl.add_row(row)

        tbl.show()
        for x in reports:
            Output.handle_ret(x, args.no_color, warn_as_error=args.warn_as_error)

    def list_volumes(self, args):
        args = self.merge_config_args('volume.list', args)
        if args.from_file:
            lstmsg = [linstor.responses.ResourceResponse(json.load(args.from_file))]
        else:
            lstmsg = self._linstor.volume_list(args.nodes, args.storage_pools, args.resources)
        return self.output_list(args, lstmsg, VolumeCommands.show_volumes)

    @classmethod
    def _props_list(cls, args, lstmsg):
        if lstmsg and lstmsg.resources:
            rsc = lstmsg.resources[0]  # type: Resource
            vlms = [x for x in rsc.volumes if x.number == args.volume_number]
            if vlms:
                return [vlms[0].properties]
        return []

    def print_props(self, args):
        lstmsg = self._linstor.volume_list([args.node_name], filter_by_resources=[args.resource_name])

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([(args.key, args.value)])
        replies = self._linstor.volume_modify(
            args.node_name,
            args.resource_name,
            args.volume_number,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)
