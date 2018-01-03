#!/usr/bin/env python2
"""
    LINSTOR - management of distributed storage/DRBD9 resources
    Copyright (C) 2013 - 2017  LINBIT HA-Solutions GmbH
    Author: Robert Altnoeder, Roland Kammerer

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os
import re
# import locale
import linstor.argparse.argparse as argparse
import linstor.argcomplete as argcomplete
from linstor.commands import (
    Commands,
    VolumeDefinitionCommands,
    StoragePoolDefinitionCommands,
    StoragePoolCommands,
    ResourceDefinitionCommands,
    ResourceCommands,
    NodeCommands,
    DrbdOptions
)

from linstor.commcontroller import need_communication, CommController

from proto.MsgHeader_pb2 import MsgHeader

from linstor.consts import (
    FILE_GLOBAL_COMMON_CONF,
    GITHASH,
    KEY_LS_CONTROLLERS,
    VERSION,
    NODE_NAME,
    RES_NAME,
    SNAPS_NAME
)

from linstor.utils import (
    Output,
    filter_prohibited,
    namecheck,
    rangecheck,
    ip_completer,
    COLOR_BROWN,
    COLOR_DARKPINK,
    COLOR_GREEN,
    COLOR_NONE,
    COLOR_RED,
    COLOR_TEAL
)

from linstor.sharedconsts import (
    DFLT_CTRL_PORT_PLAIN
)

if hasattr(__builtins__, 'raw_input'):
    input = raw_input


class LinStorCLI(object):
    """
    linstor command line client
    """

    def __init__(self):
        self._all_commands = None
        self._colors = True
        self._utf8 = True

        self._parser = self.setup_parser()
        self._all_commands = self.parser_cmds()

        self.cc = CommController()

    def setup_parser(self):
        parser = argparse.ArgumentParser(prog='linstor_client')
        parser.add_argument('--version', '-v', action='version',
                            version='%(prog)s ' + VERSION + '; ' + GITHASH)
        parser.add_argument('--no-color', action="store_true",
                            help='Do not use colors in output. Usefull for old terminals/scripting.')
        parser.add_argument('--no-utf8', action="store_true",
                            help='Do not use utf-8 characters in output (i.e., tables).')
        parser.add_argument('--warn-as-error', action="store_true",
                            help='Treat WARN return code as error (i.e., return code > 0).')
        parser.add_argument('--controllers', default='localhost:%s' % str(DFLT_CTRL_PORT_PLAIN),
                            help='Comma separated list of controllers (e.g.: "host1:port,host2:port"). '
                            'If the environment variable %s is set, '
                            'the ones set via this argument get appended.' % (KEY_LS_CONTROLLERS))

        subp = parser.add_subparsers(title='subcommands',
                                     description='valid subcommands',
                                     help='Use the list command to print a '
                                     'nicer looking overview of all valid '
                                     'commands')

        # interactive mode
        parser_ia = subp.add_parser('interactive',
                                    description='Start interactive mode')
        parser_ia.set_defaults(func=self.cmd_interactive)

        # help
        p_help = subp.add_parser('help',
                                 description='Print help for a command')
        p_help.add_argument('command')
        p_help.set_defaults(func=self.cmd_help)

        # list
        p_list = subp.add_parser('list', aliases=['commands', 'list-commands'],
                                 description='List available commands')
        p_list.set_defaults(func=self.cmd_list)

        # exit
        p_exit = subp.add_parser('exit', aliases=['quit'],
                                 description='Only useful in interactive mode')
        p_exit.set_defaults(func=self.cmd_exit)

        # poke
        p_poke = subp.add_parser('poke')
        p_poke.add_argument('-q', '--quiet', action="store_true")
        p_poke.set_defaults(func=self.cmd_enoimp)

        # type checkers (generate them only once)
        check_node_name = namecheck(NODE_NAME)
        check_res_name = namecheck(RES_NAME)
        check_snaps_name = namecheck(SNAPS_NAME)

        # Quorum control, completion of the action parameter
        quorum_completer_possible = ('ignore', 'unignore')

        def quorum_action_completer(prefix, **kwargs):
            possible = list(quorum_completer_possible)
            if prefix is not None and prefix != "":
                possible = [item for item in possible if item.startswith(prefix)]
            return possible

        p_quorum = subp.add_parser("quorum-control",
                                   aliases=["qc"],
                                   description="Sets quorum parameters on linstor cluster nodes")
        p_quorum.add_argument('-o', '--override', action="store_true",
                              help="Override change protection in a partition without quorum")
        p_quorum.add_argument(
            "action", choices=quorum_completer_possible, help="The action to perform on the affected nodes"
        ).completer = quorum_action_completer
        p_quorum.add_argument(
            "name", nargs="+", type=check_node_name, help="Name of the affected node or nodes"
        ).completer = NodeCommands.completer
        p_quorum.set_defaults(func=self.cmd_enoimp)

        # add all node commands
        NodeCommands.setup_commands(subp)

        # new-resource definition
        ResourceDefinitionCommands.setup_commands(subp)

        # add all resource commands
        ResourceCommands.setup_commands(subp)

        # add all storage pool definition commands
        StoragePoolDefinitionCommands.setup_commands(subp)

        # add all storage pools commands
        StoragePoolCommands.setup_commands(subp)

        # add all volume definition commands
        VolumeDefinitionCommands.setup_commands(subp)

        # new-volume
        def size_completer(prefix, **kwargs):
            # TODO(rck): why not use UNITS_MAP?
            choices = ('kB', 'MB', 'GB', 'TB', 'PB', 'kiB', 'MiB', 'GiB',
                       'TiB', 'PiB')
            m = re.match('(\d+)(\D*)', prefix)

            digits = m.group(1)
            unit = m.group(2)

            if unit and unit != "":
                p_units = [x for x in choices if x.startswith(unit)]
            else:
                p_units = choices

            return [digits + u for u in p_units]

        def vol_completer(prefix, parsed_args, **kwargs):
            server_rc, res_list = self.__list_resources(True)
            possible = set()
            for r in res_list:
                name, _, vol_list = r
                if name == parsed_args.name:
                    vol_list.sort(key=lambda vol_entry: vol_entry[0])
                    for v in vol_list:
                        vol_id, _ = v
                        possible.add(str(vol_id))

            return possible

        # resize-volume
        p_resize_vol_command = 'resize-volume'
        p_resize_vol = subp.add_parser(p_resize_vol_command,
                                       aliases=['resize'],
                                       description='Resizes a volume to the specified size, which must be '
                                       'greater than the current size of the volume.')
        p_resize_vol.add_argument('name', type=check_res_name,
                                  help='Name of the resource').completer = ResourceCommands.completer
        p_resize_vol.add_argument('id', help='Volume ID', type=int).completer = vol_completer
        p_resize_vol.add_argument(
            'size',
            help='New size of the volume. '
            'The default unit for size is GiB (size * (2 ^ 30) bytes). '
            'Another unit can be specified by using an according postfix. '
            "linstor's internal granularity for the capacity of volumes is one "
            'Kibibyte (2 ^ 10 bytes). All other unit specifications are implicitly '
            'converted to Kibibyte, so that the actual size value used by linstor '
            'is the smallest natural number of Kibibytes that is large enough to '
            'accommodate a volume of the requested size in the specified size unit.'
        ).completer = size_completer
        p_resize_vol.set_defaults(func=self.cmd_enoimp)
        p_resize_vol.set_defaults(command=p_resize_vol_command)

        # modify-volume
        p_mod_vol_command = 'modify-volume'
        p_mod_vol = subp.add_parser(p_mod_vol_command,
                                    aliases=['mv'],
                                    description='Modifies a DRBD volume.')
        p_mod_vol.add_argument('name', type=check_res_name,
                               help='Name of the resource').completer = ResourceCommands.completer
        p_mod_vol.add_argument('id', help='Volume id', type=int).completer = vol_completer
        p_mod_vol.add_argument('-m', '--minor', type=rangecheck(0, 1048575))
        p_mod_vol.set_defaults(func=self.cmd_enoimp)
        p_mod_vol.set_defaults(command=p_mod_vol_command)

        # modify-assignment
        p_mod_assg_command = 'modify-assignment'
        p_mod_assg = subp.add_parser(p_mod_assg_command,
                                     aliases=['ma'],
                                     description='Modifies a linstor assignment.')
        p_mod_assg.add_argument('resource', type=check_res_name,
                                help='Name of the resource').completer = ResourceCommands.completer
        p_mod_assg.add_argument('node', help='Name of the node').completer = NodeCommands.completer
        p_mod_assg.add_argument('-o', '--overwrite')
        p_mod_assg.add_argument('-d', '--discard')
        p_mod_assg.set_defaults(func=self.cmd_enoimp)
        p_mod_assg.set_defaults(command=p_mod_assg_command)

        # connect
        p_conn = subp.add_parser('connect-resource', description='Connect resource on node',
                                 aliases=['connect'])
        p_conn.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_conn.add_argument('node', type=check_node_name).completer = NodeCommands.completer
        p_conn.set_defaults(func=self.cmd_enoimp)

        # reconnect
        p_reconn = subp.add_parser('reconnect-resource', description='Reconnect resource on node',
                                   aliases=['reconnect'])
        p_reconn.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_reconn.add_argument('node', type=check_node_name).completer = NodeCommands.completer
        p_reconn.set_defaults(func=self.cmd_enoimp)

        # disconnect
        p_disconn = subp.add_parser('disconnect-resource', description='Disconnect resource on node',
                                    aliases=['disconnect'])
        p_disconn.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_disconn.add_argument('node', type=check_node_name).completer = NodeCommands.completer
        p_disconn.set_defaults(func=self.cmd_enoimp)

        # flags
        p_flags = subp.add_parser('set-flags', description='Set flags of resource on node',
                                  aliases=['flags'])
        p_flags.add_argument('resource', type=check_res_name,
                             help='Name of the resource').completer = ResourceCommands.completer
        p_flags.add_argument('node', type=check_node_name,
                             help='Name of the node').completer = NodeCommands.completer
        p_flags.add_argument('--reconnect', choices=(0, 1), type=int)
        p_flags.add_argument('--updcon', choices=(0, 1), type=int)
        p_flags.add_argument('--overwrite', choices=(0, 1), type=int)
        p_flags.add_argument('--discard', choices=(0, 1), type=int)
        p_flags.set_defaults(func=self.cmd_enoimp)

        # attach
        p_attach = subp.add_parser('attach-volume', description='Attach volume from node',
                                   aliases=['attach'])
        p_attach.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_attach.add_argument('id', help='Volume ID', type=int).completer = vol_completer
        p_attach.add_argument('node', type=check_node_name).completer = NodeCommands.completer
        p_attach.set_defaults(func=self.cmd_enoimp, fname='attach')
        # detach
        p_detach = subp.add_parser('detach-volume', description='Detach volume from node',
                                   aliases=['detach'])
        p_detach.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_detach.add_argument('id', help='Volume ID', type=int).completer = vol_completer
        p_detach.add_argument('node', type=check_node_name).completer = NodeCommands.completer
        p_detach.set_defaults(func=self.cmd_enoimp, fname='detach')

        # assign
        p_assign = subp.add_parser('assign-resource',
                                   aliases=['assign'],
                                   description='Creates an assignment for the deployment of the '
                                   'specified resource on the specified node.')
        p_assign.add_argument('--client', action="store_true")
        p_assign.add_argument('--overwrite', action="store_true",
                              help='If specified, linstor will issue a "drbdmadm -- --force primary" '
                              'after the resource has been started.')
        p_assign.add_argument('--discard', action="store_true",
                              help='If specified, linstor will issue a "drbdadm -- --discard-my-data" '
                              'connect after the resource has been started.')
        p_assign.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_assign.add_argument('node', type=check_node_name, nargs="+").completer = NodeCommands.completer
        p_assign.set_defaults(func=self.cmd_enoimp)

        # free space
        def redundancy_type(r):
            r = int(r)
            if r < 1:
                raise argparse.ArgumentTypeError('Minimum redundancy is 1')
            return r
        p_fspace = subp.add_parser('list-free-space',
                                   description='Queries the maximum size of a'
                                   ' volume that could be deployed with the'
                                   ' specified level of redundancy',
                                   aliases=['free-space'])
        p_fspace.add_argument('-m', '--machine-readable', action="store_true")
        p_fspace.add_argument('-s', '--site', default='',
                              help="only consider nodes from this site")
        p_fspace.add_argument('redundancy', type=redundancy_type,
                              help='Redundancy level (>=1)')
        p_fspace.set_defaults(func=self.cmd_enoimp)

        # deploy
        p_deploy = subp.add_parser('deploy-resource',
                                   aliases=['deploy'],
                                   description='Deploys a resource on n automatically selected nodes '
                                   "of the linstor cluster. Using the information in linstor's data "
                                   'tables, the linstor server tries to find n nodes that have enough '
                                   'free storage capacity to deploy the resource resname.')
        p_deploy.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_deploy.add_argument('-i', '--increase', action="store_true",
                              help='Increase the redundancy count relative to'
                              ' the currently set value by a number of'
                              ' <redundancy_count>')
        p_deploy.add_argument('-d', '--decrease', action="store_true",
                              help='Decrease the redundancy count relative to'
                              ' the currently set value by a number of'
                              ' <redundancy_count>')
        p_deploy.add_argument('redundancy_count', type=redundancy_type,
                              help='The redundancy count specifies the number'
                              ' of nodes to which the resource should be'
                              ' deployed. It must be at least 1 and at most'
                              ' the number of nodes in the cluster')
        p_deploy.add_argument('--with-clients', action="store_true")
        p_deploy.add_argument('-s', '--site', default='',
                              help="only consider nodes from this site")
        p_deploy.set_defaults(func=self.cmd_enoimp)

        # undeploy
        p_undeploy = subp.add_parser('undeploy-resource',
                                     aliases=['undeploy'],
                                     description='Undeploys a resource from all nodes. The resource '
                                     "definition is still kept in linstor's data tables.")
        p_undeploy.add_argument('-q', '--quiet', action="store_true")
        p_undeploy.add_argument('-f', '--force', action="store_true")
        p_undeploy.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_undeploy.set_defaults(func=self.cmd_enoimp)

        # update-pool
        p_upool = subp.add_parser('update-pool',
                                  description='Checks the storage pool total size and free space on '
                                  'the local node and updates the associated values in the data '
                                  'tables on the control volume.')
        p_upool.set_defaults(func=self.cmd_enoimp)

        # reconfigure
        p_reconfigure = subp.add_parser('reconfigure',
                                        description='Re-reads server configuration and'
                                        ' reloads storage plugin')
        p_reconfigure.set_defaults(func=self.cmd_enoimp)

        # save
        p_save = subp.add_parser('save',
                                 description='Orders the linstor server to save the current '
                                 "configuration of linstor's resources to the data tables "
                                 'on the drbdmanaege control volume')
        p_save.set_defaults(func=self.cmd_enoimp)

        # load
        p_save = subp.add_parser('load',
                                 description='Orders the linstor server to reload the current '
                                 "configuration of linstor's resources from the data tables on "
                                 'the linstor control volume')
        p_save.set_defaults(func=self.cmd_enoimp)

        # unassign
        p_unassign = subp.add_parser('unassign-resource',
                                     aliases=['unassign'],
                                     description='Undeploys the specified resource from the specified '
                                     "node and removes the assignment entry from linstor's data "
                                     'tables after the node has finished undeploying the resource. '
                                     'If the resource had been assigned to a node, but that node has '
                                     'not deployed the resource yet, the assignment is canceled.')
        p_unassign.add_argument('-q', '--quiet', action="store_true",
                                help='Unless this option is used, linstor will issue a safety question '
                                'that must be answered with yes, otherwise the operation is canceled.')
        p_unassign.add_argument('-f', '--force', action="store_true",
                                help="If present, the assignment entry will be removed from linstor's "
                                'data tables immediately, without taking any action on the node where '
                                'the resource is been deployed.')
        p_unassign.add_argument('resource', type=check_res_name).completer = ResourceCommands.completer
        p_unassign.add_argument('node', type=check_node_name, nargs="+").completer = NodeCommands.completer
        p_unassign.set_defaults(func=self.cmd_enoimp)

        # new-snapshot
        p_nsnap = subp.add_parser('add-snapshot',
                                  aliases=['ns', 'create-snapshot', 'cs',
                                           'new-snapshot', 'as'],
                                  description='Create a LVM snapshot')
        p_nsnap.add_argument('snapshot', type=check_snaps_name, help='Name of the snapshot')
        p_nsnap.add_argument('resource', type=check_res_name,
                             help='Name of the resource').completer = ResourceCommands.completer
        p_nsnap.add_argument('nodes', type=check_node_name,
                             help='List of nodes', nargs='+').completer = NodeCommands.completer
        p_nsnap.set_defaults(func=self.cmd_enoimp)

        # Snapshot commands:
        # These commands do not follow the usual option order:
        # For example remove-snapshot should have the snapshot name as first argument and the resource as
        # second argument. BUT: There are (potentially) more snapshots than resources, so specifying the
        # resource first and then completing only the snapshots for that resource makes more sense.

        # remove-snapshot
        def snaps_completer(prefix, parsed_args, **kwargs):
            server_rc, res_list = self._list_snapshots()
            possible = set()
            for r in res_list:
                res_name, snaps_list = r
                if res_name == parsed_args.resource:
                    for s in snaps_list:
                        snaps_name, _ = s
                        possible.add(snaps_name)

            return possible

        p_rmsnap = subp.add_parser('remove-snapshot',
                                   aliases=['delete-snapshot', 'ds'],
                                   description='Remove LVM snapshot of a resource')
        p_rmsnap.add_argument('-f', '--force', action="store_true")
        p_rmsnap.add_argument('resource', type=check_res_name,
                              help='Name of the resource').completer = ResourceCommands.completer
        p_rmsnap.add_argument('snapshot', type=check_snaps_name, nargs="+",
                              help='Name of the snapshot').completer = snaps_completer
        p_rmsnap.set_defaults(func=self.cmd_enoimp)

        # remove-snapshot-assignment
        p_rmsnapas = subp.add_parser('remove-snapshot-assignment',
                                     aliases=['rsa',
                                              'delete-snapshot-assignment',
                                              'dsa'],
                                     description='Remove snapshot assignment')
        p_rmsnapas.add_argument('-f', '--force', action="store_true")
        p_rmsnapas.add_argument('resource', type=check_res_name,
                                help='Name of the resource').completer = ResourceCommands.completer
        p_rmsnapas.add_argument('snapshot', type=check_snaps_name,
                                help='Name of the snapshot').completer = snaps_completer
        p_rmsnapas.add_argument('node', type=check_node_name,
                                help='Name of the node').completer = NodeCommands.completer
        p_rmsnapas.set_defaults(func=self.cmd_enoimp)

        # restore-snapshot
        p_restsnap = subp.add_parser('restore-snapshot',
                                     aliases=['rs'],
                                     description='Restore snapshot')
        p_restsnap.add_argument('resource', type=check_res_name,
                                help='Name of the new resource that gets created from existing snapshot')
        p_restsnap.add_argument('snapshot_resource', type=check_res_name,
                                help='Name of the resource that was snapshoted').completer = ResourceCommands.completer
        p_restsnap.add_argument('snapshot', type=check_snaps_name,
                                help='Name of the snapshot').completer = snaps_completer
        p_restsnap.set_defaults(func=self.cmd_enoimp)

        # resume-all
        p_resume_all = subp.add_parser('resume-all',
                                       description="Resumes all failed assignments")
        p_resume_all.set_defaults(func=self.cmd_enoimp)

        def shutdown_restart(command, description, func, aliases=False):
            if aliases:
                p_cmd = subp.add_parser(command, aliases=aliases, description=description)
            else:
                p_cmd = subp.add_parser(command, description=description)
            p_cmd.add_argument('-l', '--satellite', action="store_true",
                               help='If given, also send a shutdown command to connected satellites.',
                               default=False)
            p_cmd.add_argument('-q', '--quiet', action="store_true",
                               help='Unless this option is used, linstor will issue a safety question '
                               'that must be answered with yes, otherwise the operation is canceled.')
            p_cmd.add_argument('-r', '--resources', action="store_true",
                               help='Shutdown all linstor-controlled resources too',
                               default=False)
            p_cmd.add_argument('-c', '--ctrlvol', action="store_true",
                               help='Do not drbdadm down the control volume',
                               default=False)
            p_cmd.set_defaults(func=func)

        # shutdown
        shutdown_restart('shutdown', description='Stops the local linstor server process.',
                         func=self.cmd_enoimp)
        # restart
        shutdown_restart('restart', description='Restarts the local linstor server process.',
                         func=self.cmd_enoimp)

        # snapshots
        snapgroupby = ("Resource", "Name", "State")
        snap_group_completer = Commands.show_group_completer(snapgroupby, "groupby")

        p_lsnaps = subp.add_parser('list-snapshots', aliases=['s', 'snapshots'],
                                   description='List available snapshots')
        p_lsnaps.add_argument('-m', '--machine-readable', action="store_true")
        p_lsnaps.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lsnaps.add_argument('-g', '--groupby', nargs='+',
                              choices=snapgroupby).completer = snap_group_completer
        p_lsnaps.add_argument('--separators', action="store_true")
        p_lsnaps.add_argument('-R', '--resources', nargs='+', type=check_res_name,
                              help='Filter by list of resources').completer = ResourceCommands.completer
        p_lsnaps.set_defaults(func=self.cmd_enoimp)

        # snapshot-assignments
        snapasgroupby = ("Resource", "Name", "Node", "State")

        snapas_group_completer = Commands.show_group_completer(snapasgroupby, "groupby")

        p_lsnapas = subp.add_parser('list-snapshot-assignments', aliases=['sa', 'snapshot-assignments'],
                                    description='List snapshot assignments')
        p_lsnapas.add_argument('-m', '--machine-readable', action="store_true")
        p_lsnapas.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lsnapas.add_argument('-g', '--groupby', nargs='+',
                               choices=snapasgroupby).completer = snapas_group_completer
        p_lsnapas.add_argument('--separators', action="store_true")
        p_lsnapas.add_argument('-N', '--nodes', nargs='+', type=check_node_name,
                               help='Filter by list of nodes').completer = NodeCommands.completer
        p_lsnapas.add_argument('-R', '--resources', nargs='+', type=check_res_name,
                               help='Filter by list of resources').completer = ResourceCommands.completer
        p_lsnapas.set_defaults(func=self.cmd_enoimp)

        # assignments
        assignverbose = ('Blockdevice', 'Node_ID')
        assigngroupby = ('Node', 'Resource', 'Vol_ID', 'Blockdevice',
                         'Node_ID', 'State')

        ass_verbose_completer = Commands.show_group_completer(assignverbose, "show")
        ass_group_completer = Commands.show_group_completer(assigngroupby, "groupby")

        p_assignments = subp.add_parser('list-assignments', aliases=['a', 'assignments'],
                                        description="Prints a list of each node's assigned resources."
                                        "Nodes that do not have any resources assigned do not appear in the "
                                        "list. By default, the list is printed as a human readable table.")
        p_assignments.add_argument('-m', '--machine-readable',
                                   action="store_true")
        p_assignments.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_assignments.add_argument('-s', '--show', nargs='+',
                                   choices=assignverbose).completer = ass_verbose_completer
        p_assignments.add_argument('-g', '--groupby', nargs='+',
                                   choices=assigngroupby).completer = ass_group_completer
        p_assignments.add_argument('--separators', action="store_true")
        p_assignments.add_argument('-N', '--nodes', nargs='+', type=check_node_name,
                                   help='Filter by list of nodes').completer = NodeCommands.completer
        p_assignments.add_argument('-R', '--resources', nargs='+', type=check_res_name,
                                   help='Filter by list of resources').completer = ResourceCommands.completer
        p_assignments.set_defaults(func=self.cmd_enoimp)

        # export
        def exportnamecheck(name):
            if name == '*':
                return name
            return check_res_name(name)

        p_export = subp.add_parser('export-res', aliases=['export'],
                                   description='Exports the configuration files of the specified '
                                   'linstor resource for use with drbdadm. If "*" is used as '
                                   'resource name, the configuration files of all linstor resources '
                                   'deployed on the local node are exported. The configuration files will '
                                   'be created (or updated) in the linstor directory for temporary '
                                   'configuration files, typically /var/lib/drbd.d.')
        p_export.add_argument('resource', nargs="+", type=exportnamecheck,
                              help='Name of the resource').completer = ResourceCommands.completer
        p_export.set_defaults(func=self.cmd_enoimp)

        # howto-join
        p_howtojoin = subp.add_parser('howto-join',
                                      description='Print the command to'
                                      ' execute on the given node in order to'
                                      ' join the cluster')
        p_howtojoin.add_argument('node', type=check_node_name,
                                 help='Name of the node to join').completer = NodeCommands.completer
        p_howtojoin.add_argument('-q', '--quiet', action="store_true",
                                 help="If the --quiet option is used, the join command is printed "
                                      "with a --quiet option")
        p_howtojoin.set_defaults(func=self.cmd_enoimp)

        # free-port-nr
        p_free_port_nr = subp.add_parser('free-port-nr',
                                         description='Find an unallocated TCP/IP port number')
        p_free_port_nr.set_defaults(func=self.cmd_enoimp)

        # free-minor-nr
        p_free_minor_nr = subp.add_parser('free-minor-nr',
                                          description='Find an unallocated minor number')
        p_free_minor_nr.set_defaults(func=self.cmd_enoimp)

        # query-port-nr
        p_query_port_nr = subp.add_parser('query-port-nr',
                                          description='Query the allocation status of a TCP/IP port number')
        p_query_port_nr.add_argument('port', help='TCP/IP port number')
        p_query_port_nr.set_defaults(func=self.cmd_enoimp)

        # query-minor-nr
        p_query_minor_nr = subp.add_parser('query-minor-nr',
                                           description='Query the allocation status of a minor number')
        p_query_minor_nr.add_argument('minor', help='Device file minor number')
        p_query_minor_nr.set_defaults(func=self.cmd_enoimp)

        def ll_debug_cmd_completer(prefix, **kwargs):
            self.dbus_init()
            # needed to wait for completion
            self._server.Introspect()
            fns = []
            expected = DBUS_DRBDMANAGED + "."
            expected_len = len(expected)
            for fn in self._server._introspect_method_map.iterkeys():
                if not fn.startswith(expected):
                    continue
                fn_short = fn[expected_len:]
                if fn_short.startswith(prefix):
                    fns.append(fn_short)
            return fns

        p_lowlevel_debug = subp.add_parser("lowlevel-debug", description="JSON-to-DBus debug interface")
        p_lowlevel_debug.add_argument("cmd",
                                      help="DBusServer function to call").completer = ll_debug_cmd_completer

        def ll_debug_json_completer(prefix, parsed_args=None, **kwargs):
            self.dbus_init()
            fn = getattr(self._server, parsed_args.cmd)
            if not fn:
                return []

            # TODO: introspect fn, to see whether array/dict/etc. is wanted..
            if prefix == '':
                return ['[]', '{}']
            return []
        p_lowlevel_debug.add_argument("json",
                                      help="JSON to deserialize",
                                      nargs="*").completer = ll_debug_json_completer
        p_lowlevel_debug.set_defaults(func=self.cmd_enoimp)

        # server-version
        p_server_version = subp.add_parser('server-version',
                                           description='Queries version information from the '
                                           'linstor server')
        p_server_version.set_defaults(func=self.cmd_enoimp)

        # message-log
        p_message_log = subp.add_parser('list-message-log', aliases=['message-log', 'list-ml', 'ml'],
                                        description='Queries the server\'s message log')
        p_message_log.set_defaults(func=self.cmd_enoimp)

        # clear-message-log
        p_message_log = subp.add_parser('clear-message-log', aliases=['clear-ml', 'cml'],
                                        description='Queries the server\'s message log')
        p_message_log.set_defaults(func=self.cmd_enoimp)

        # query-conf
        p_queryconf = subp.add_parser('query-conf',
                                      description='Print the DRBD'
                                      ' configuration file for a given'
                                      ' resource on a given node')
        p_queryconf.add_argument('node', type=check_node_name,
                                 help='Name of the node').completer = NodeCommands.completer
        p_queryconf.add_argument('resource', type=check_res_name,
                                 help='Name of the resource').completer = ResourceCommands.completer
        p_queryconf.set_defaults(func=self.cmd_enoimp)

        # ping
        p_ping = subp.add_parser('ping', description='Pings the server. The '
                                 'server should answer with a "Pong"')
        p_ping.set_defaults(func=self.cmd_ping)

        # wait-for-startup
        p_ping = subp.add_parser('wait-for-startup', description='Wait until server is started up')
        p_ping.set_defaults(func=self.cmd_enoimp)

        # startup
        p_startup = subp.add_parser('startup',
                                    description='Start the server via D-Bus')
        p_startup.set_defaults(func=self.cmd_enoimp)

        class IPAddressCheck(object):
            def __init__(self):
                pass

            # used for "in" via "choices":
            def __contains__(self, key):
                import socket
                try:
                    ips = socket.getaddrinfo(key, 0)
                except socket.gaierror:
                    return None
                if len(ips) == 0:
                    return None
                return ips[0][4][0]

            def __iter__(self):
                return iter([])  # gives no sane text
                return iter(["any valid IP address"])  # completes this text

        # join
        p_join = subp.add_parser('join-cluster',
                                 description='Join an existing cluster',
                                 aliases=['join'])
        p_join.add_argument('-a', '--address-family', metavar="FAMILY",
                            default='ipv4', choices=['ipv4', 'ipv6'],
                            help='FAMILY: "ipv4" (default) or "ipv6"')
        p_join.add_argument('-p', '--port', type=rangecheck(1, 65535),
                            default=1234)  # TODO(rck): fix/rm
        p_join.add_argument('-q', '--quiet', action="store_true")
        p_join.add_argument('local_ip')
        p_join.add_argument('local_node_id')
        p_join.add_argument('peer_name', type=check_node_name)
        p_join.add_argument('peer_ip').completer = ip_completer("peer_ip")
        p_join.add_argument('peer_node_id')
        p_join.add_argument('secret')
        p_join.set_defaults(func=self.cmd_enoimp)

        # initcv
        p_join = subp.add_parser('initcv',
                                 description='Initialize control volume')
        p_join.add_argument('-q', '--quiet', action="store_true")
        p_join.add_argument('dev', help='Path to the control volume')
        p_join.set_defaults(func=self.cmd_enoimp)

        # debug
        p_debug = subp.add_parser('debug')
        p_debug.add_argument('cmd')
        p_debug.set_defaults(func=self.cmd_enoimp)

        # drbd options
        drbd_options = DrbdOptions()
        drbd_options.setup_commands(subp)

        # handlers
        # currently we do not parse the xml-output because drbd-utils are not ready for it
        # number and handler names are very static, so use a list for now and add this feature to
        # drbd-utils later
        handlers = (
            'after-resync-target', 'before-resync-target', 'fence-peer', 'initial-split-brain',
            'local-io-error', 'pri-lost', 'pri-lost-after-sb', 'pri-on-incon-degr', 'split-brain',
        )
        p_handlers = subp.add_parser('handlers',
                                     description='Set or unset event handlers.')
        p_handlers.add_argument('--common', action="store_true")
        p_handlers.add_argument('--resource', type=check_res_name,
                                help='Name of the resource to modify').completer = ResourceCommands.completer
        for handler in handlers:
            p_handlers.add_argument('--' + handler, help='Please refer to drbd.conf(5)', metavar='cmd')
            p_handlers.add_argument('--unset-' + handler, action='store_true')
        p_handlers.set_defaults(func=self.cmd_enoimp)

        # list-options
        p_listopts = subp.add_parser('list-options',
                                     description='List drbd options set',
                                     aliases=['show-options'])
        p_listopts.add_argument('resource', type=check_res_name,
                                help='Name of the resource to show').completer = ResourceCommands.completer
        p_listopts.set_defaults(func=self.cmd_enoimp)
        # p_listopts.set_defaults(doobj=do)
        # p_listopts.set_defaults(noobj=no)
        # p_listopts.set_defaults(roobj=ro)
        # p_listopts.set_defaults(pdoobj=pdo)

        # edit config
        p_editconf = subp.add_parser('modify-config',
                                     description='Modify linstor configuration',
                                     aliases=['edit-config'])
        p_editconf.add_argument('--node', '-n', type=check_node_name,
                                help='Name of the node. This enables node specific options '
                                '(e.g. plugin settings)').completer = NodeCommands.completer
        p_editconf.set_defaults(func=self.cmd_enoimp)
        p_editconf.set_defaults(type="edit")

        # export config
        p_exportconf = subp.add_parser('export-config',
                                       description='Export linstor configuration',
                                       aliases=['cat-config'])
        p_exportconf.add_argument('--node', '-n', type=check_node_name,
                                  help='Name of the node.').completer = NodeCommands.completer
        p_exportconf.add_argument('--file', '-f',
                                  help='File to save configuration')
        p_exportconf.set_defaults(func=self.cmd_enoimp)
        p_exportconf.set_defaults(type="export")

        # export ctrl-vol
        p_exportctrlvol = subp.add_parser('export-ctrlvol',
                                          description='Export linstor control volume as json blob')
        p_exportctrlvol.add_argument('--file', '-f',
                                     help='File to save configuration json blob, if not given: stdout')
        p_exportctrlvol.set_defaults(func=self.cmd_enoimp)

        # import ctrl-vol
        p_importctrlvol = subp.add_parser('import-ctrlvol',
                                          description='Import linstor control volume from json blob')
        p_importctrlvol.add_argument('-q', '--quiet', action="store_true",
                                     help='Unless this option is used, linstor will issue a safety '
                                     'question that must be answered with yes, otherwise the operation '
                                     'is canceled.')
        p_importctrlvol.add_argument('--file', '-f',
                                     help='File to load configuration json blob, if not given: stdin')
        p_importctrlvol.set_defaults(func=self.cmd_enoimp)

        # role
        p_role = subp.add_parser('role',
                                 description='Show role of local linstor (controlnode/satellite/unknown)')
        p_role.set_defaults(func=self.cmd_enoimp)

        # reelect
        p_reelect = subp.add_parser('reelect', description='Reelect leader. DO NOT USE this command '
                                    'if you do not understand all implications!')
        p_reelect.add_argument('--force-win', action='store_true',
                               help='This is a last resort command to bring up a single leader '
                               'in order to get access to the control volume (e.g. remove node '
                               'in 2 node cluster)')
        p_reelect.set_defaults(func=self.cmd_enoimp)

        argcomplete.autocomplete(parser)

        return parser

    def parse(self, pargs):
        return self._parser.parse_args(pargs)

    def parse_and_execute(self, pargs):
        args = self.parse(pargs)
        return args.func(args)

    def parser_cmds(self):
        # AFAIK there is no other way to get the subcommands out of argparse.
        # This avoids at least to manually keep track of subcommands

        cmds = dict()
        subparsers_actions = [
            action for action in self._parser._actions if isinstance(action,
                                                                     argparse._SubParsersAction)]
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                parser_hash = subparser.__hash__
                if parser_hash not in cmds:
                    cmds[parser_hash] = list()
                cmds[parser_hash].append(choice)

        # sort subcommands and their aliases,
        # subcommand dictates sortorder, not its alias (assuming alias is
        # shorter than the subcommand itself)
        cmds_sorted = [sorted(cmd, key=len, reverse=True) for cmd in
                       cmds.values()]

        # "add" and "new" have the same length (as well as "delete" and
        # "remove), therefore prefer one of them to group commands for the
        # "list" command
        for cmds in cmds_sorted:
            idx = 0
            found = False
            for idx, cmd in enumerate(cmds):
                if cmd.startswith("add-") or cmd.startswith("remove-"):
                    found = True
                    break
            if found:
                cmds.insert(0, cmds.pop(idx))

        # sort subcommands themselves
        cmds_sorted.sort(key=lambda a: a[0])
        return cmds_sorted

    def parser_cmds_description(self, all_commands):
        toplevel = [top[0] for top in all_commands]

        subparsers_actions = [
            action for action in self._parser._actions if isinstance(action,
                                                                     argparse._SubParsersAction)]
        description = {}
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                if choice in toplevel:
                    description[choice] = subparser.description

        return description

    def cmd_list(self, args):
        sys.stdout.write('Use "help <command>" to get help for a specific command.\n\n')
        sys.stdout.write('Available commands:\n')
        # import pprint
        # pp = pprint.PrettyPrinter()
        # pp.pprint(self._all_commands)
        for cmd in self._all_commands:
            sys.stdout.write("- " + cmd[0])
            if len(cmd) > 1:
                sys.stdout.write("(%s)" % (", ".join(cmd[1:])))
            sys.stdout.write("\n")

    def cmd_interactive(self, args):
        all_cmds = [i for sl in self._all_commands for i in sl]

        # helper function
        def unknown(cmd):
            sys.stdout.write("\n" + "Command \"%s\" not known!\n" % (cmd))
            self.cmd_list(args)

        # helper function
        def parsecatch(cmds, stoprec=False):
            try:
                self.parse_and_execute(cmds)
            except SystemExit:  # raised by argparse
                if stoprec:
                    return

                cmd = cmds[0]
                if cmd == "exit":
                    sys.exit(0)
                elif cmd == "help":
                    if len(cmds) == 1:
                        self.cmd_list(args)
                        return
                    else:
                        cmd = " ".join(cmds[1:])
                        if cmd not in all_cmds:
                            unknown(cmd)
                elif cmd in all_cmds:
                    if '-h' in cmds or '--help' in cmds:
                        return
                    sys.stdout.write("\nIncorrect syntax. Use the command as follows:\n")
                    parsecatch(["help", cmd], stoprec=True)
                else:
                    unknown(cmd)

        # main part of interactive mode:

        # try to load readline
        # if loaded, raw_input makes use of it
        try:
            import readline
            # seems after importing readline it is not possible to output to sys.stderr
            completer = argcomplete.CompletionFinder(self._parser)
            readline.set_completer_delims("")
            readline.set_completer(completer.rl_complete)
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

        self.cmd_list(args)
        while True:
            try:
                sys.stdout.write("\n")
                cmds = input('> ').strip()

                cmds = [cmd.strip() for cmd in cmds.split()]
                if not cmds:
                    self.cmd_list(args)
                else:
                    parsecatch(cmds)
            except (EOFError, KeyboardInterrupt):  # raised by ctrl-d, ctrl-c
                sys.stdout.write("\n")  # additional newline, makes shell prompt happy
                return

    def cmd_help(self, args):
        sys.exit(self.parse_and_execute([args.command, "-h"]))

    def cmd_exit(self, _):
        exit(0)

    def run(self):
        # TODO(rck): try/except
        sys.exit(self.parse_and_execute(sys.argv[1:]))

    def cmd_enoimp(self, args):
        Output.err('This command is deprecated or not implemented')

    @need_communication
    def cmd_ping(self, args):
        from linstor.sharedconsts import (API_PING, API_PONG)
        h = MsgHeader()
        h.api_call = API_PING
        h.msg_id = 1

        pbmsgs = self.cc.sendrec(h)

        h = MsgHeader()
        h.ParseFromString(pbmsgs[0])
        sys.stdout.write('%s\n' % (h.api_call))
        if h.api_call != API_PONG:
            sys.stderr.write('Did not reveive %s\n' % (API_PONG))
            sys.exit(1)

        # no return is fine, implicitly returns None, which need_communication handles

    def color(self, col, args=None):
        if args and args[0].no_color:
            return ''
        else:
            return col

    # Code that we most likely want to use anyways/hacks to keep the current state happy

    def _list_snapshots(self, resource_filter=[]):
        # TODO(rck): hack to make the snaps_completer happy
        return (0, [])

    def _level_color(self, level):
        """
        Selects a color for a level returned by GenericView subclasses
        """
        # TODO(rck): just a hack
        level_color = COLOR_RED
        return Output.color(level_color)

    def check_mutex_opts(self, args, names):
        target = ""
        for o in names:
            if args.__dict__[o]:
                if target:
                    sys.stderr.write("--%s and --%s are mutually exclusive\n" % (o, target))
                    sys.exit(1)
                target = o

        if not target:
            sys.stderr.write("You have to specify (exactly) one of %s\n" % ('--' + ' --'.join(names)))
            sys.exit(1)

        return target

    def cmd_handlers(self, args):
        fn_rc = 1
        target = self.check_mutex_opts(args, ("common", "resource"))
        from linstor.utils import filter_new_args
        newopts = filter_new_args('unset', args)
        if not newopts:
            sys.stderr.write('No new options found\n')
            return fn_rc

        newopts["target"] = target
        newopts["type"] = "handlers"

        return self._set_drbdsetup_props(newopts)

    def cmd_list_options(self, args):
        net_options = args.noobj.get_options()
        disk_options = args.doobj.get_options()
        peer_device_options = args.pdoobj.get_options()
        resource_options = args.roobj.get_options()

        # filter net-options drbdmanage sets unconditionally.
        net_options = filter_prohibited(net_options, ('shared-secret', 'cram-hmac-alg'))

        colors = {
            'net-options': Output.color(COLOR_TEAL, args),
            'disk-options': Output.color(COLOR_BROWN, args),
            'peer-device-options': Output.color(COLOR_GREEN, args),
            'resource-options': Output.color(COLOR_DARKPINK, args),
        }

        # TODO(rck):
        # ret, conf = self.dsc(self._server.get_selected_config_values, [KEY_DRBD_CONFPATH])
        conf_path = "/dev/null"
        return

        res_file = 'linstor_' + args.resource + '.res'
        # TODO(rck):
        # conf_path = self._get_conf_path(conf)
        res_file = os.path.join(conf_path, res_file)
        if not os.path.isfile(res_file):
            sys.stderr.write('Resource file "' + res_file + '" does not exist\n')
            sys.exit(1)

        common_file = os.path.join(conf_path, FILE_GLOBAL_COMMON_CONF)

        def highlight(option_type, color, found):
            if found:
                return True
            for o in option_type:
                if line.find(o) != -1:
                    sys.stdout.write(Output.color_str(line.rstrip(), color, args) + '\n')
                    return True
            return False

        for res_f in (common_file, res_file):
            sys.stdout.write(res_f + ":\n")
            with open(res_f) as f:
                for line in f:
                    if line.find('{') != -1 or line.find('}') != -1:
                        sys.stdout.write(line)
                        continue

                    found = highlight(net_options, colors['net-options'], False)
                    found = highlight(disk_options, colors['disk-options'], found)
                    found = highlight(peer_device_options, colors['peer-device-options'], found)
                    found = highlight(resource_options, colors['resource-options'], found)
                    if not found:
                        sys.stdout.write(line)
            sys.stdout.write("\n")

        sys.stdout.write("Legend:\n")
        for k, v in colors.items():
            sys.stdout.write(v + k + COLOR_NONE + "\n")
        sys.stdout.write("\nNote: Do not directly edit these auto-generated"
                         " files as they will be overwritten.\n")
        sys.stdout.write("Use the according linstor sub-commands to set/unset options.\n")

    def user_confirm(self, question):
        """
        Ask yes/no questions. Requires the user to answer either "yes" or "no".
        If the input stream closes, it defaults to "no".
        returns: True for "yes", False for "no"
        """
        sys.stdout.write(question + "\n")
        sys.stdout.write("  yes/no: ")
        sys.stdout.flush()
        fn_rc = False
        while True:
            answer = sys.stdin.readline()
            if len(answer) != 0:
                if answer.endswith("\n"):
                    answer = answer[:len(answer) - 1]
                if answer.lower() == "yes":
                    fn_rc = True
                    break
                elif answer.lower() == "no":
                    break
                else:
                    sys.stdout.write("Please answer \"yes\" or \"no\": ")
                    sys.stdout.flush()
            else:
                # end of stream, no more input
                sys.stdout.write("\n")
                break
        return fn_rc


def main():
    try:
        LinStorCLI().run()
    except KeyboardInterrupt:
        sys.stderr.write("\nlinstor: Client exiting (received SIGINT)\n")
        return 1
    return 0


if __name__ == "__main__":
    main()
