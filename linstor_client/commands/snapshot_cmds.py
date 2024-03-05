import linstor_client.argparse.argparse as argparse

import linstor_client
from linstor_client.commands import Commands
from linstor_client.consts import Color
from linstor.sharedconsts import FLAG_DELETE, FLAG_SUCCESSFUL, FLAG_FAILED_DEPLOYMENT, FLAG_FAILED_DISCONNECT
from linstor.sharedconsts import FLAG_BACKUP, FLAG_SHIPPING, FLAG_BACKUP_TARGET, FLAG_BACKUP_SOURCE
from linstor_client.utils import Output
from linstor import SizeCalc, consts
from linstor_client.commands.backup_cmds import BackupCommands


class SnapshotCommands(Commands):
    _shipping_headers = [
        linstor_client.TableHeader("ResName"),
        linstor_client.TableHeader("SnapName"),
        linstor_client.TableHeader("FromNode"),
        linstor_client.TableHeader("ToNode"),
        linstor_client.TableHeader("Status", Color.DARKGREEN, alignment_text=linstor_client.TableHeader.ALIGN_RIGHT)
    ]

    class CreateMulti(object):
        LONG = "create-multiple"
        SHORT = "cm"

    def __init__(self):
        super(SnapshotCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.Create,
            SnapshotCommands.CreateMulti,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Rollback,
            Commands.Subcommands.Resource,
            Commands.Subcommands.VolumeDefinition,
            Commands.Subcommands.Ship,
            Commands.Subcommands.ShipList
        ]

        # Snapshot subcommands
        snapshot_parser = parser.add_parser(
            Commands.SNAPSHOT,
            aliases=["s"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Snapshot subcommands")
        snapshot_subp = snapshot_parser.add_subparsers(
            title="shapshot commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new snapshot
        p_new_snapshot = snapshot_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a snapshot of a resource.')
        p_new_snapshot.add_argument(
            '--async',
            action='store_true',
            help='Deprecated, kept for compatibility'
        )
        p_new_snapshot.add_argument(
            'node_name',
            type=str,
            nargs='*',
            help='Names of the nodes where the snapshot should be created. '
                 'If none are given, the snapshot will be taken on all nodes '
                 'where the given resource is present.'
        ).completer = self.node_completer
        p_new_snapshot.add_argument(
            'resource_definition_name',
            type=str,
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_snapshot.add_argument(
            'snapshot_name',
            type=str,
            help='Name of the snapshot local to the resource definition')
        p_new_snapshot.set_defaults(func=self.create)

        # new multisnapshot
        p_new_multi_snapshot = snapshot_subp.add_parser(
            SnapshotCommands.CreateMulti.LONG,
            aliases=[SnapshotCommands.CreateMulti.SHORT],
            description='Creates snapshots of multiple resources.')
        p_new_multi_snapshot.add_argument(
            '--node_names', '-n',
            type=str,
            nargs='*',
            help='Names of the nodes where the snapshots should be created. '
                 'If none are given, the snapshot will be taken on all nodes '
                 'where the given resources are present.'
        ).completer = self.node_completer
        p_new_multi_snapshot.add_argument(
            '--resource_names', '-r',
            type=str,
            required=True,
            nargs='+',
            help='Name of the resource definitions').completer = self.resource_dfn_completer
        p_new_multi_snapshot.add_argument(
            'snapshot_name',
            type=str,
            help='Name of the snapshot local to the resource definition')
        p_new_multi_snapshot.set_defaults(func=self.create_multi)

        # delete snapshot
        p_delete_snapshot = snapshot_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Deletes a snapshot.')
        p_delete_snapshot.add_argument(
            'resource_definition_name',
            type=str,
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_delete_snapshot.add_argument(
            'snapshot_name',
            type=str,
            help='Name of the snapshot local to the resource definition')
        p_delete_snapshot.add_argument(
            '-n', '--nodes',
            type=str,
            nargs='+',
            help='Only delete the snapshot from the given nodes. Default: Delete given snapshot from all nodes')
        p_delete_snapshot.set_defaults(func=self.delete)

        p_ship = snapshot_subp.add_parser(
            Commands.Subcommands.Ship.LONG,
            aliases=[Commands.Subcommands.Ship.SHORT],
            description='Ship a snapshot to another node.')
        p_ship.add_argument(
            '--from-node',
            required=True,
            type=str,
            help='Source node name').completer = self.node_completer
        p_ship.add_argument(
            '--to-node',
            required=True,
            type=str,
            help='Destination node name').completer = self.node_completer
        p_ship.add_argument(
            '--resource',
            required=True,
            type=str,
            help='Name of the resource to ship').completer = self.resource_dfn_completer
        p_ship.set_defaults(func=self.ship)

        p_ship_list = snapshot_subp.add_parser(
            Commands.Subcommands.ShipList.LONG,
            aliases=[Commands.Subcommands.ShipList.SHORT],
            description='Shows an overview list of snapshot shippings.')
        p_ship_list.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_ship_list.add_argument(
            '-r', '--resources',
            nargs='+',
            type=str,
            help='Filter by list of resources').completer = self.resource_completer
        p_ship_list.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=str,
            help='Filter by list of nodes').completer = self.node_completer
        p_ship_list.add_argument(
            '-s', '--snapshots',
            nargs='+',
            type=str,
            help='Filter by list of snapshots').completer = self.node_completer
        p_ship_list.add_argument(
            '--status',
            nargs='+',
            choices=[x.value.lower() for x in consts.SnapshotShipStatus],
            type=str.lower,
            help='Filter by list of statuses').completer = self.node_completer
        p_ship_list.set_defaults(func=self.shiplist)

        # roll back to snapshot
        p_rollback_snapshot = snapshot_subp.add_parser(
            Commands.Subcommands.Rollback.LONG,
            aliases=[Commands.Subcommands.Rollback.SHORT],
            description='Rolls resource data back to snapshot state. '
                        'The resource must not be in use. '
                        'The snapshot will not be removed and can be used for subsequent rollbacks. '
                        'Only the most recent snapshot may be used; '
                        'to roll back to an earlier snapshot, the intermediate snapshots must first be deleted.')
        p_rollback_snapshot.add_argument(
            'resource_definition_name',
            type=str,
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_rollback_snapshot.add_argument(
            'snapshot_name',
            type=str,
            help='Name of the snapshot local to the resource definition')
        p_rollback_snapshot.set_defaults(func=self.rollback)

        # list snapshot definitions
        p_lsnapshots = snapshot_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all snapshots known to LINSTOR. '
                        'By default, the list is printed as a human readable table.')
        p_lsnapshots.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lsnapshots.add_argument(
            '-r', '--resources',
            nargs='+',
            type=str,
            help='Filter by list of resources').completer = self.resource_completer
        p_lsnapshots.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=str,
            help='Filter by list of nodes').completer = self.node_completer
        p_lsnapshots.set_defaults(func=self.list)

        # volume definition commands
        volume_definition_subcmds = [
            Commands.Subcommands.Restore
        ]

        volume_definition_parser = snapshot_subp.add_parser(
            Commands.Subcommands.VolumeDefinition.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[Commands.Subcommands.VolumeDefinition.SHORT],
            description="%s subcommands" % Commands.Subcommands.VolumeDefinition.LONG)

        volume_definition_subp = volume_definition_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.VolumeDefinition.LONG,
            metavar="",
            description=Commands.Subcommands.generate_desc(volume_definition_subcmds))

        # restore resource from snapshot
        p_restore_volume_definition = volume_definition_subp.add_parser(
            Commands.Subcommands.Restore.LONG,
            aliases=[Commands.Subcommands.Restore.SHORT],
            description='Creates a volume definition (or definitions) by restoring a snapshot of a specified source '
            'resource to a specified target resource. '
            'Only the basic structure of the volume definition is restored, that is, volume numbers and sizes. '
            'Additional aspects of the source volume definition, such as DRBD options or LINSTOR object properties, '
            'are not restored.')
        p_restore_volume_definition.add_argument(
            '--from-resource', '--fr',
            required=True,
            type=str,
            help='Name of the resource definition containing the snapshot').completer = self.resource_dfn_completer
        p_restore_volume_definition.add_argument(
            '--from-snapshot', '--fs',
            required=True,
            type=str,
            help='Name of the snapshot to restore from')
        p_restore_volume_definition.add_argument(
            '--to-resource', '--tr',
            required=True,
            type=str,
            help='Name of the resource definition in which to create the volume definitions'
        ).completer = self.resource_dfn_completer
        p_restore_volume_definition.set_defaults(func=self.restore_volume_definition)

        # resource commands
        resource_subcmds = [
            Commands.Subcommands.Restore
        ]

        resource_parser = snapshot_subp.add_parser(
            Commands.Subcommands.Resource.LONG,
            formatter_class=argparse.RawTextHelpFormatter,
            aliases=[Commands.Subcommands.Resource.SHORT],
            description="%s subcommands" % Commands.Subcommands.Resource.LONG)

        resource_subp = resource_parser.add_subparsers(
            title="%s subcommands" % Commands.Subcommands.Resource.LONG,
            metavar="",
            description=Commands.Subcommands.generate_desc(resource_subcmds))

        # restore resource from snapshot
        p_restore_snapshot = resource_subp.add_parser(
            Commands.Subcommands.Restore.LONG,
            aliases=[Commands.Subcommands.Restore.SHORT],
            description='Restores a snapshot on a node (or nodes). '
                        'Creates a new resource initialized with the data from a given snapshot. '
                        'The volume definitions of the target resource must match those from the snapshot.')
        p_restore_snapshot.add_argument(
            'node_name',
            type=str,
            nargs='*',
            help='Names of the nodes where the snapshot should be restored. '
                 'If none are given, resources will be created on all nodes where the snapshot is present.'
        ).completer = self.node_completer
        p_restore_snapshot.add_argument(
            '--from-resource', '--fr',
            required=True,
            type=str,
            help='Name of the resource definition containing the snapshot').completer = self.resource_dfn_completer
        p_restore_snapshot.add_argument(
            '--from-snapshot', '--fs',
            required=True,
            type=str,
            help='Name of the snapshot to restore from')
        p_restore_snapshot.add_argument(
            '--to-resource', '--tr',
            required=True,
            type=str,
            help='Name of the resource definition in which to create the resource from this snapshot'
        ).completer = self.resource_dfn_completer
        p_restore_snapshot.add_argument(
            "--storpool-rename",
            nargs='*',
            help="Rename storage pool names. Format: oldname=newname",
            action=BackupCommands._KeyValue)
        p_restore_snapshot.set_defaults(func=self.restore)

        self.check_subcommands(snapshot_subp, subcmds)

    def create(self, args):
        async_flag = vars(args)["async"]
        replies = self._linstor.snapshot_create(
            args.node_name, args.resource_definition_name, args.snapshot_name, async_flag)
        return self.handle_replies(args, replies)

    def create_multi(self, args):
        replies = self._linstor.snapshot_create_multi(
            args.node_names, args.resource_names, args.snapshot_name)
        return self.handle_replies(args, replies)

    def restore_volume_definition(self, args):
        replies = self._linstor.snapshot_volume_definition_restore(
            args.from_resource, args.from_snapshot, args.to_resource)
        return self.handle_replies(args, replies)

    def restore(self, args):
        replies = self._linstor.snapshot_resource_restore(
            args.node_name, args.from_resource, args.from_snapshot, args.to_resource, args.storpool_rename)
        return self.handle_replies(args, replies)

    def delete(self, args):
        replies = self._linstor.snapshot_delete(args.resource_definition_name, args.snapshot_name, args.nodes)
        return self.handle_replies(args, replies)

    def rollback(self, args):
        replies = self._linstor.snapshot_rollback(args.resource_definition_name, args.snapshot_name)
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("ResourceName")
        tbl.add_column("SnapshotName")
        tbl.add_column("NodeNames")
        tbl.add_column("Volumes")
        tbl.add_column("CreatedOn")
        tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color))
        for snapshot_dfn in lstmsg.snapshots:
            if FLAG_DELETE in snapshot_dfn.flags:
                state_cell = tbl.color_cell("DELETING", Color.RED)
            elif FLAG_FAILED_DEPLOYMENT in snapshot_dfn.flags:
                state_cell = tbl.color_cell("Failed", Color.RED)
            elif FLAG_FAILED_DISCONNECT in snapshot_dfn.flags:
                state_cell = tbl.color_cell("Satellite disconnected", Color.RED)
            elif FLAG_SUCCESSFUL in snapshot_dfn.flags:
                in_backup_restore = False
                in_backup_create = False
                if FLAG_BACKUP in snapshot_dfn.flags and FLAG_SHIPPING in snapshot_dfn.flags:
                    for snap in snapshot_dfn.snapshots:
                        in_backup_create |= FLAG_BACKUP_SOURCE in snap.flags
                        in_backup_restore |= FLAG_BACKUP_TARGET in snap.flags
                if in_backup_create:
                    state_cell = tbl.color_cell("Shipping", Color.YELLOW)
                elif in_backup_restore:
                    state_cell = tbl.color_cell("Restoring", Color.YELLOW)
                else:
                    sub_state = ""
                    # take the first non empty and non "completed" state
                    for snapshot in snapshot_dfn.snapshots:
                        for snapshot_volume in snapshot.snapshot_volumes:
                            if snapshot_volume.state and snapshot_volume.state != "completed":
                                sub_state = snapshot_volume.state
                                break
                        if sub_state:
                            break

                    state_text = "Successful"
                    if sub_state:
                        state_text += " (" + sub_state + ")"
                    state_cell = tbl.color_cell(state_text, Color.DARKGREEN)
            else:
                state_cell = tbl.color_cell("Incomplete", Color.DARKBLUE)

            snapshot_date = ""
            if snapshot_dfn.snapshots and snapshot_dfn.snapshots[0].create_datetime:
                snapshot_date = str(snapshot_dfn.snapshots[0].create_datetime)[:19]

            tbl.add_row([
                snapshot_dfn.resource_name,
                snapshot_dfn.name,
                ", ".join([node_name for node_name in snapshot_dfn.nodes]),
                ", ".join([
                    str(snapshot_vlm_dfn.number) + ": " + SizeCalc.approximate_size_string(snapshot_vlm_dfn.size)
                    for snapshot_vlm_dfn in snapshot_dfn.snapshot_volume_definitions]),
                snapshot_date,
                state_cell
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.snapshot_dfn_list(filter_by_nodes=args.nodes, filter_by_resources=args.resources)

        return self.output_list(args, lstmsg, self.show)

    def ship(self, args):
        replies = self.get_linstorapi().snapshot_ship(
            rsc_name=args.resource,
            from_node=args.from_node,
            to_node=args.to_node)
        return self.handle_replies(args, replies)

    def show_ship_list(self, args, shipping_resp):
        """

        :param args:
        :param shipping_resp: ShippingResponse
        :return:
        """
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_headers(self._shipping_headers)
        for shipping in shipping_resp.shippings:
            tbl.add_row([
                shipping.snapshot_dfn.resource_name,
                shipping.snapshot_dfn.snapshot_name,
                shipping.from_node_name,
                shipping.to_node_name,
                tbl.color_cell(shipping.status.value,
                               None if shipping.status == consts.SnapshotShipStatus.COMPLETE else Color.YELLOW)
            ])
        tbl.show()

    def shiplist(self, args):
        lstmsg = self.get_linstorapi().snapshot_shipping_list(
            filter_by_nodes=args.nodes,
            filter_by_resources=args.resources,
            filter_by_snapshots=args.snapshots,
            filter_by_status=args.status)
        return self.output_list(args, lstmsg, self.show_ship_list)
