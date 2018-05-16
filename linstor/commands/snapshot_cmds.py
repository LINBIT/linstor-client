import linstor.argparse.argparse as argparse

from linstor.commands import Commands
from linstor.consts import RES_NAME, SNAPSHOT_NAME
from linstor.utils import namecheck


class SnapshotCommands(Commands):
    def __init__(self):
        super(SnapshotCommands, self).__init__()

    def setup_commands(self, parser):
        """

        :param argparse.ArgumentParser parser:
        :return:
        """

        subcmds = [
            Commands.Subcommands.Create
        ]

        # Snapshot subcommands
        snapshot_parser = parser.add_parser(
            Commands.SNAPSHOT,
            aliases=["s"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Snapshot subcommands")
        res_subp = snapshot_parser.add_subparsers(
            title="shapshot commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new-snapshot
        p_new_res = res_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Creates a snapshot of a resource.')
        p_new_res.add_argument(
            'resource_definition_name',
            type=namecheck(RES_NAME),
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_res.add_argument(
            'snapshot_name',
            type=namecheck(SNAPSHOT_NAME),
            help='Name of the snapshot local to the resource definition')
        p_new_res.set_defaults(func=self.create)

        self.check_subcommands(res_subp, subcmds)

    def create(self, args):
        replies = self._linstor.snapshot_create(args.resource_definition_name, args.snapshot_name)
        return self.handle_replies(args, replies)
