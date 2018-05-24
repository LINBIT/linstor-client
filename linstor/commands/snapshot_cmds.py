import linstor.argparse.argparse as argparse

import linstor
from linstor.commands import Commands
from linstor.consts import RES_NAME, SNAPSHOT_NAME, Color
from linstor.sharedconsts import FLAG_SUCCESSFUL, FLAG_FAILED_DEPLOYMENT, FLAG_FAILED_DISCONNECT
from linstor.utils import Output, namecheck


class SnapshotCommands(Commands):
    def __init__(self):
        super(SnapshotCommands, self).__init__()

    def setup_commands(self, parser):
        """

        :param argparse.ArgumentParser parser:
        :return:
        """

        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List
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

        # new-snapshot
        p_new_snapshot = snapshot_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a snapshot of a resource.')
        p_new_snapshot.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for deployment on satellites before returning'
        )
        p_new_snapshot.add_argument(
            'resource_definition_name',
            type=namecheck(RES_NAME),
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_snapshot.add_argument(
            'snapshot_name',
            type=namecheck(SNAPSHOT_NAME),
            help='Name of the snapshot local to the resource definition')
        p_new_snapshot.set_defaults(func=self.create)

        # list snapshot definitions
        p_lsnapshots = snapshot_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description=' Prints a list of all snapshots known to linstor. '
                        'By default, the list is printed as a human readable table.')
        p_lsnapshots.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lsnapshots.set_defaults(func=self.list)

        self.check_subcommands(snapshot_subp, subcmds)

    def create(self, args):
        replies = self._linstor.snapshot_create(args.resource_definition_name, args.snapshot_name, args.async)
        return self.handle_replies(args, replies)

    @classmethod
    def show(cls, args, lstmsg):
        tbl = linstor.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("ResourceName")
        tbl.add_column("SnapshotName")
        tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color))
        for snapshot_dfn in lstmsg.snapshot_dfns:
            if FLAG_FAILED_DEPLOYMENT in snapshot_dfn.snapshot_dfn_flags:
                state_cell = tbl.color_cell("Failed", Color.RED)
            elif FLAG_FAILED_DISCONNECT in snapshot_dfn.snapshot_dfn_flags:
                state_cell = tbl.color_cell("Satellite disconnected", Color.RED)
            elif FLAG_SUCCESSFUL in snapshot_dfn.snapshot_dfn_flags:
                state_cell = tbl.color_cell("Successful", Color.DARKGREEN)
            else:
                state_cell = tbl.color_cell("Incomplete", Color.DARKBLUE)

            tbl.add_row([
                snapshot_dfn.rsc_name,
                snapshot_dfn.snapshot_name,
                state_cell
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.snapshot_dfn_list()

        return self.output_list(args, lstmsg, self.show)
