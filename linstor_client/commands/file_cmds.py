from __future__ import print_function

import base64
import os
import sys
import tempfile
from subprocess import call

import linstor

import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands


class FileCommands(Commands):
    _file_headers = [
        linstor_client.TableHeader("Path"),
    ]

    def __init__(self):
        super(FileCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.Show,
            Commands.Subcommands.Modify,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Deploy,
            Commands.Subcommands.Undeploy,
        ]

        # Resource subcommands
        file_parser = parser.add_parser(
            Commands.FILE,
            aliases=["f"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="File subcommands")
        file_subp = file_parser.add_subparsers(
            title="file commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        p_file_list = file_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Lists all files in the cluster.')
        p_file_list.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output.')
        p_file_list.set_defaults(func=self.list)

        p_file_show = file_subp.add_parser(
            Commands.Subcommands.Show.LONG,
            aliases=[Commands.Subcommands.Show.SHORT],
            description='Show a single file, including its content.')
        p_file_show.add_argument(
            'file_name',
            type=str,
            help='Name of the file to show')
        p_file_show.set_defaults(func=self.show)

        p_file_modify = file_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modify the contents of a file.')
        p_file_modify.add_argument(
            'file_name',
            type=str,
            help='Name of the file to modify')
        p_file_modify.set_defaults(func=self.modify)

        p_file_delete = file_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Delete a file.')
        p_file_delete.add_argument(
            'file_name',
            type=str,
            help='Name of the file to delete')
        p_file_delete.set_defaults(func=self.delete)

        p_file_deploy = file_subp.add_parser(
            Commands.Subcommands.Deploy.LONG,
            aliases=[Commands.Subcommands.Deploy.SHORT],
            description='Deploy a file with a resource definition.')
        p_file_deploy.add_argument(
            'file_name',
            type=str,
            help='Name of the file to deploy')
        p_file_deploy.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource definition to deploy the file with')
        p_file_deploy.set_defaults(func=self.deploy)

        p_file_undeploy = file_subp.add_parser(
            Commands.Subcommands.Undeploy.LONG,
            aliases=[Commands.Subcommands.Undeploy.SHORT],
            description='Undeploy a file from a resource definition.')
        p_file_undeploy.add_argument(
            'file_name',
            type=str,
            help='Name of the file to undeploy')
        p_file_undeploy.add_argument(
            'resource_name',
            type=str,
            help='Name of the resource definition to undeploy the file from')
        p_file_undeploy.set_defaults(func=self.undeploy)

        self.check_subcommands(file_subp, subcmds)

    def list(self, args):
        lstmsg = self._linstor.file_list()
        return self.output_list(args, lstmsg, self.show_table)

    def show(self, args):
        showmsg = self._linstor.file_show(args.file_name)
        print(base64.b64decode(showmsg.files.content).decode(), end="")

    def modify(self, args):
        if sys.stdin.isatty():
            editor = os.environ.get('EDITOR', 'nano')
            try:
                showmsg = self._linstor.file_show(args.file_name)
                initial_content = base64.b64decode(showmsg.files.content).decode()
            except linstor.LinstorApiCallError:
                # file does not exist yet
                initial_content = ""

            with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
                tf.write(initial_content.encode())
                tf.flush()
                call([editor, tf.name])
                tf.seek(0)
                input_str = tf.read()
        else:
            input_str = sys.stdin.read().encode()
        replies = self._linstor.file_modify(args.file_name, input_str)
        self.handle_replies(args, replies)

    def delete(self, args):
        replies = self._linstor.file_delete(args.file_name)
        self.handle_replies(args, replies)

    def deploy(self, args):
        replies = self._linstor.file_deploy(args.file_name, args.resource_name)
        self.handle_replies(args, replies)

    def undeploy(self, args):
        replies = self._linstor.file_undeploy(args.file_name, args.resource_name)
        self.handle_replies(args, replies)

    def show_table(self, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in FileCommands._file_headers:
            tbl.add_header(hdr)

        for file in lstmsg.files:
            tbl.add_row([file.path])

        tbl.show()
