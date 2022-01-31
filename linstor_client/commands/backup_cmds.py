from __future__ import print_function

from datetime import datetime

import getpass

from linstor import SizeCalc
import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands
from linstor_client import Table
from linstor_client.consts import Color


class BackupCommands(Commands):

    class Info(object):
        LONG = "info"
        SHORT = "i"

    class Ship(object):
        LONG = "ship"
        SHORT = "s"

    class DeleteById(object):
        LONG = "id"
        SHORT = "id"

    class DeleteByFilter(object):
        LONG = "filter"
        SHORT = "f"

    class DeleteAll(object):
        LONG = "all"
        SHORT = "a"

    class DeleteS3Key(object):
        LONG = "s3key"
        SHORT = "s3"

    _backup_headers = [
        linstor_client.TableHeader("Backup Name(ID)"),
        linstor_client.TableHeader("Finished at"),
        linstor_client.TableHeader("Based On"),
        linstor_client.TableHeader("Status")
    ]
    _backup_other_headers = [
        linstor_client.TableHeader("S3 Key"),
    ]

    def __init__(self):
        super(BackupCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.Create,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Abort,
            Commands.Subcommands.Restore,
            BackupCommands.Ship,
            BackupCommands.Info
        ]

        bkp_parser = parser.add_parser(
            Commands.BACKUP,
            aliases=['b'],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Commands to manage Backups")
        bkp_sub = bkp_parser.add_subparsers(
            title="Backup subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # list backup
        p_lbackups = bkp_sub.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of backups.')
        p_lbackups.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lbackups.add_argument(
            '-r', '--resource',
            help='Only show backups for given resource')
        p_lbackups.add_argument(
            '-s', '--snapshot',
            help='Only show backups with the given snapshot name')
        p_lbackups.add_argument(
            'remote_name',
            help='Remote name to show backups for')
        p_lbackups.add_argument(
            '-o', '--others',
            action="store_true",
            help='Only show s3 objects that are unknown to Linstor')
        p_lbackups.set_defaults(func=self.list_backups)

        # create backup
        p_crtbak = bkp_sub.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description="Create a new remote backup.")
        self._add_remote(p_crtbak)
        p_crtbak.add_argument(
            "-f", "--full",
            action="store_true",
            help="Create a full backup")
        p_crtbak.add_argument(
            "-n", "--node",
            help="Node to prefer to upload backup")
        p_crtbak.add_argument(
            "-s", "--snapshot",
            help="Name of the local snapshot to create")
        p_crtbak.add_argument(
            "resource",
            help="Resource used for the backup"
        ).completer = self.resource_completer
        p_crtbak.set_defaults(func=self.create)

        # delete backup
        subcmd_delete = [
            BackupCommands.DeleteById,
            BackupCommands.DeleteByFilter,
            BackupCommands.DeleteAll,
            BackupCommands.DeleteS3Key]
        p_delbak = bkp_sub.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Delete backup(s) from a remote")
        p_delbak_subp = p_delbak.add_subparsers(
            title="Delete backup commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmd_delete))

        p_delbak_id = p_delbak_subp.add_parser(
            BackupCommands.DeleteById.LONG,
            aliases=[BackupCommands.DeleteById.SHORT],
            description="Delete a remote backup by ID")
        self._add_remote(p_delbak_id)
        p_delbak_id.add_argument(
            "id",
            type=str,
            help="ID of the backup to delete")
        p_delbak_id.add_argument(
            "--prefix",
            action="store_true",
            help="Use the ID as a prefix instead of full match")
        p_delbak_id.set_defaults(func=self.del_by_id)

        p_delbak_filter = p_delbak_subp.add_parser(
            BackupCommands.DeleteByFilter.LONG,
            aliases=[BackupCommands.DeleteByFilter.SHORT],
            description="Delete a remote backup by resource name, uploader node name or older than specifc time")
        self._add_remote(p_delbak_filter)
        p_delbak_filter.add_argument(
            "-t", "--time",
            type=str,
            help="Delete backups older than specified time. Expected format is YYYYMMDD_HHMMSS")
        p_delbak_filter.add_argument(
            "-r", "--resource",
            type=str,
            help="Delete backups matching the given resource name")
        p_delbak_filter.add_argument(
            "-n", "--node",
            type=str,
            help="Delete backups uploaded by the given node name")
        p_delbak_filter.set_defaults(func=self.del_by_filter)

        p_delbak_all = p_delbak_subp.add_parser(
            BackupCommands.DeleteAll.LONG,
            aliases=[BackupCommands.DeleteAll.SHORT],
            description="Delete all Linstor backups of the given remote. Will NOT delete non-Linstor S3 objects")
        self._add_remote(p_delbak_all)
        p_delbak_all.add_argument(
            "-c", "--cluster",
            action="store_true",
            help="Only delete Linstor backups created by the local cluster")
        p_delbak_all.set_defaults(func=self.del_all)

        p_delbak_s3 = p_delbak_subp.add_parser(
            BackupCommands.DeleteS3Key.LONG,
            aliases=[BackupCommands.DeleteS3Key.SHORT],
            description="Delete a given S3 object. Use this option to delete non-Linstor S3 objects")
        self._add_remote(p_delbak_s3)
        p_delbak_s3.add_argument(
            "s3key",
            type=str,
            help="S3 key to delete")
        self._add_cascading(p_delbak_id, p_delbak_filter)
        self._add_dry_run(p_delbak_id, p_delbak_filter, p_delbak_all, p_delbak_s3)
        p_delbak_s3.set_defaults(func=self.del_s3)

        # restore backup
        p_rstbak = bkp_sub.add_parser(
            Commands.Subcommands.Restore.LONG,
            aliases=[Commands.Subcommands.Restore.SHORT],
            description="Restore a backup. Either --id OR --resource must be used (not both)")
        self._add_remote(p_rstbak)
        p_rstbak.add_argument(
            "target_node",
            help="Target node to restore"
        ).completer = self.node_completer
        p_rstbak.add_argument(
            "target_resource",
            help="Target resource name to restore into")
        p_rstbak.add_argument(
            "-r", "--resource",
            help="Restore the latest backup of the given resource")
        p_rstbak.add_argument(
            "-s", "--snapshot",
            help="Restore the latest backup with the given snapshot name")
        p_rstbak.add_argument(
            "--id",
            help="Specific backup to restore")
        p_rstbak.add_argument(
            "--passphrase",
            type=str,
            nargs='?',
            action='store',
            help="The passphrase of the uploader cluster. Required if the resource to restore has a LUKS layer",
            const='')
        p_rstbak.add_argument(
            "--storpool-rename",
            nargs='*',
            help="Rename storage pool names. Format: $oldname=$newname",
            action=BackupCommands._KeyValue)
        p_rstbak.add_argument(
            "--download-only",
            action='store_true',
            help="Only download backups"
        )
        p_rstbak.set_defaults(func=self.restore)

        # abort backup
        p_crtabort = bkp_sub.add_parser(
            Commands.Subcommands.Abort.LONG,
            aliases=[Commands.Subcommands.Abort.SHORT],
            description="Aborts a backup. If neither --create nor --restore is given, both will be aborted (if any in "
                        "progress)")
        self._add_remote(p_crtabort)
        p_crtabort.add_argument(
            "resource",
            help="The resource to abort")
        p_crtabort.add_argument(
            "-r", "--restore",
            action="store_true",
            help="Only abort a restoration of the given resource")
        p_crtabort.add_argument(
            "-c", "--create",
            action="store_true",
            help="Only abort a creation of the given resource")
        p_crtabort.set_defaults(func=self.abort)

        # ship backup
        p_shipbak = bkp_sub.add_parser(
            BackupCommands.Ship.LONG,
            aliases=[BackupCommands.Ship.SHORT],
            description="Ships a backup to another Linstor cluster")
        self._add_remote(p_shipbak)
        p_shipbak.add_argument(
            "source_resource",
            help="The local resource name to ship")
        p_shipbak.add_argument(
            "target_resource",
            help="The resource name on the target Linstor cluster")
        p_shipbak.add_argument(
            "--source-node",
            help="Prefer the given node to send the backup")
        p_shipbak.add_argument(
            "--target-node",
            help="Specify which node in the target Linstor cluster should receive the backup")
        p_shipbak.add_argument(
            "--target-net-if",
            help="Specify on which Linstor network interface the target node should listen")
        p_shipbak.add_argument(
            "--target-storage-pool",
            help="Specify in which target storage pool the backup should be received")
        p_shipbak.add_argument(
            "--download-only",
            action='store_true',
            help="Only download backups"
        )
        # TODO: add stor_pool_renaming
        p_shipbak.set_defaults(func=self.ship)

        # restore backup
        p_infobak = bkp_sub.add_parser(
            BackupCommands.Info.LONG,
            aliases=[BackupCommands.Info.SHORT],
            description="Retrieve information about a given backup. Either --id OR --resource must be used (not both)."
                        " Option --storpool-rename must be used in combination with --target-node")
        self._add_remote(p_infobak)
        p_infobak.add_argument(
            "-r", "--resource",
            help="Get info about the latest backup of the given resource")
        p_infobak.add_argument(
            "-s", "--snapshot",
            help="Get info about the last backup with this snapshot name")
        p_infobak.add_argument(
            "--id",
            help="Get info about the given backup to restore")
        p_infobak.add_argument(
            "-n", "--target_node",
            help="Target node to calculate remaining free space"
        ).completer = self.node_completer
        p_infobak.add_argument(
            "--storpool-rename",
            nargs='*',
            help="Rename storage pool names. Format: $oldname=$newname",
            action=BackupCommands._KeyValue)
        p_infobak.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_infobak.set_defaults(func=self.info)

        self.check_subcommands(p_delbak_subp, subcmd_delete)
        self.check_subcommands(bkp_sub, subcmds)

    def _add_remote(self, parser):
        parser.add_argument(
            "remote",
            help="Remote used for deletion of backup(s)"
        ).completer = self.remote_completer

    @classmethod
    def _add_cascading(cls, *parsers):
        for p in parsers:
            p.add_argument(
                "--cascade", "--cascading",
                action="store_true",
                help="Also delete backups depending on selected backups"
            )

    @classmethod
    def _add_dry_run(cls, *parsers):
        for p in parsers:
            p.add_argument(
                "--dry-run", "--dryrun",
                action="store_true",
                help="Does not delete anything, only shows what would be deleted"
            )

    @classmethod
    def show_backups(cls, args, lstmsg):
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        if args.others:
            for hdr in cls._backup_other_headers:
                tbl.add_header(hdr)

            for entry in lstmsg.other.files:
                tbl.add_row([entry])
        else:
            backup_hdr = list(cls._backup_headers)
            for hdr in backup_hdr:
                tbl.add_header(hdr)

            for backup in lstmsg.linstor:
                # row = [backup.id, backup.origin_rsc_name, backup.start_time]
                row = [backup.id]
                if backup.finished_timestamp:
                    row += [datetime.fromtimestamp(int(backup.finished_timestamp / 1000))]
                else:
                    row += [""]
                row += [backup.based_on[0:-5] if backup.based_on else ""]

                status_text = "Success"
                status_color = Color.GREEN
                if backup.shipping:
                    status_text = "Shipping"
                    status_color = Color.YELLOW
                elif not backup.restorable:
                    status_text = "Not restorable"
                    status_color = Color.RED

                row += [tbl.color_cell(status_text, status_color)]

                tbl.add_row(row)

        tbl.show()

    def list_backups(self, args):
        lstmsg = self.get_linstorapi().backup_list(
            remote_name=args.remote_name,
            resource_name=args.resource,
            snap_name=args.snapshot
        )
        return self.output_list(args, lstmsg, BackupCommands.show_backups, machine_readable_raw=True)

    def create(self, args):
        replies = self.get_linstorapi().backup_create(
            remote_name=args.remote,
            resource_name=args.resource,
            incremental=not args.full,
            node_name=args.node,
            snap_name=args.snapshot
        )
        return self.handle_replies(args, replies)

    def del_by_id(self, args):
        replies = self.get_linstorapi().backup_delete(
            args.remote,
            bak_id=args.id if not args.prefix else None,
            bak_id_prefix=args.id if args.prefix else None,
            cascade=args.cascade,
            dryrun=args.dry_run
        )
        return self.handle_replies(args, replies)

    def del_by_filter(self, args):
        if not args.time and not args.resource and not args.node:
            args.parser.error("At least one of --time, --resource or --node has to be used")
            # raise LinstorArgumentError("At least one of --time, --resource or --node has to be used")

        replies = self.get_linstorapi().backup_delete(
            args.remote,
            timestamp=args.time,
            resource_name=args.resource,
            node_name=args.node,
            cascade=args.cascade,
            dryrun=args.dry_run
        )
        return self.handle_replies(args, replies)

    def del_all(self, args):
        replies = self.get_linstorapi().backup_delete(
            args.remote,
            all_linstor=True if not args.cluster else None,
            all_local_cluster=True if args.cluster else None,
            dryrun=args.dry_run
        )
        return self.handle_replies(args, replies)

    def del_s3(self, args):
        replies = self.get_linstorapi().backup_delete(
            args.remote,
            s3_key=args.s3key,
            dryrun=args.dry_run
        )
        return self.handle_replies(args, replies)

    def restore(self, args):
        replies = self.get_linstorapi().backup_restore(
            args.remote,
            args.target_node,
            args.target_resource,
            resource_name=args.resource,
            bak_id=args.id,
            passphrase=self._get_passphrase(args, "Origin clusters passphrase: "),
            stor_pool_map=args.storpool_rename,
            download_only=args.download_only,
            snap_name=args.snapshot,
        )
        return self.handle_replies(args, replies)

    def abort(self, args):
        replies = self.get_linstorapi().backup_abort(
            args.remote,
            args.resource,
            restore=args.restore,
            create=args.create)
        return self.handle_replies(args, replies)

    def ship(self, args):
        replies = self.get_linstorapi().backup_ship(
            args.remote,
            args.source_resource,
            args.target_resource,
            src_node=args.source_node,
            dst_node=args.target_node,
            dst_net_if=args.target_net_if,
            dst_stor_pool=args.target_storage_pool,
            download_only=args.download_only)
        return self.handle_replies(args, replies)

    @classmethod
    def _get_passphrase(cls, args, message):
        if args.passphrase is None:
            return None
        elif args.passphrase:
            return args.passphrase
        else:
            return getpass.getpass(message)

    def info(self, args):
        lstmsg = self.get_linstorapi().backup_info(
            args.remote,
            resource_name=args.resource,
            bak_id=args.id,
            target_node=args.target_node,
            stor_pool_map=args.storpool_rename,
            snap_name=args.snapshot,
        )
        return self.output_list(args, lstmsg, BackupCommands.show_backups_info, machine_readable_raw=True)

    @classmethod
    def show_backups_info(cls, args, lstmsg):
        rsc_tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        rsc_tbl.add_column("Resource")
        rsc_tbl.add_column("Full Backup")
        rsc_tbl.add_column("Latest Backup")
        rsc_tbl.add_column("Backup Count")
        rsc_tbl.add_column("Download Size")
        rsc_tbl.add_column("Allocated Size")

        # table will only have a single row
        row = [lstmsg.rsc, lstmsg.full, lstmsg.latest, lstmsg.count]
        row += [SizeCalc.approximate_size_string(lstmsg.dl_size),
                SizeCalc.approximate_size_string(lstmsg.alloc_size)]
        rsc_tbl.add_row(row)
        rsc_tbl.show()

        stor_pool_tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)

        stor_pool_tbl.add_column("Origin StorPool (Type)")
        if args.target_node:
            stor_pool_tbl.add_column("Target Pool")
            stor_pool_tbl.add_column("Remaining Free Space")
        stor_pool_tbl.add_column("Volume to Download")
        stor_pool_tbl.add_column("Type")
        stor_pool_tbl.add_column("Download Size")
        stor_pool_tbl.add_column("Allocated Size")
        stor_pool_tbl.add_column("Usable Size")

        for stor_pool in lstmsg.storpools:
            row = [stor_pool.name + " (" + stor_pool.provider_kind + ")"]
            if args.target_node:
                row += [stor_pool.target_name, ]
                if stor_pool.remaining_space < 0:
                    row += [stor_pool_tbl.color_cell(
                        "-" + SizeCalc.approximate_size_string(-stor_pool.remaining_space), Color.RED)]
                else:
                    row += [SizeCalc.approximate_size_string(stor_pool.remaining_space)]

            vlm_to_dl_cell = []
            type_cell = []
            dl_size_cell = []
            alloc_size_cell = []
            usable_size_cell = []
            for volume in stor_pool.volumes:
                vlm_to_dl_cell += [volume.name if volume.name else "-"]
                type_cell += [volume.layer_type]
                dl_size_cell += [SizeCalc.approximate_size_string(volume.dl_size) if volume.dl_size else "-"]
                alloc_size_cell += [SizeCalc.approximate_size_string(volume.alloc_size) if volume.alloc_size else "-"]
                usable_size_cell += [SizeCalc.approximate_size_string(volume.usable_size)
                                     if volume.usable_size else "-"]
            row += ["\n".join(vlm_to_dl_cell), "\n".join(type_cell), "\n".join(dl_size_cell),
                    "\n".join(alloc_size_cell), "\n".join(usable_size_cell)]
            stor_pool_tbl.add_row(row)

        stor_pool_tbl.show()

    # create a keyvalue class
    class _KeyValue(argparse.Action):

        # Constructor calling
        def __call__(
                self,
                parser,
                namespace,
                values,
                option_string=None):
            setattr(namespace, self.dest, dict())

            for value in values:
                # split it into key and value
                key, value = value.split('=')
                # assign into dictionary
                getattr(namespace, self.dest)[key] = value
