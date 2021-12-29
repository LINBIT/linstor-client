import linstor_client.argparse.argparse as argparse

from linstor_client.table import Table, TableHeader
from linstor_client.utils import Output
from linstor_client.commands import Commands

from datetime import datetime


class ErrorReportCommands(Commands):
    def __init__(self):
        super(ErrorReportCommands, self).__init__()

    def setup_commands(self, parser):
        # Error subcommands
        error_subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.Show,
            Commands.Subcommands.Delete
        ]
        error_parser = parser.add_parser(
            Commands.ERROR_REPORTS,
            aliases=["err"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Error report subcommands")

        error_subp = error_parser.add_subparsers(
            title="Error report commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(error_subcmds)
        )

        c_list_error_reports = error_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='List error reports.'
        )
        c_list_error_reports.add_argument('-s', '--since', help='Show errors since n days. e.g. "3days"')
        c_list_error_reports.add_argument('-t', '--to', help='Show errors to specified date. Format YYYY-MM-DD.')
        c_list_error_reports.add_argument(
            '-n',
            '--nodes',
            help='Only show error reports from these nodes.',
            nargs='+'
        )
        c_list_error_reports.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        c_list_error_reports.add_argument(
            '--report-id',
            nargs='+',
            help="Restrict to id's that begin with the given ones."
        )
        c_list_error_reports.add_argument('-f', '--full', action="store_true", help='Show all error info fields')
        c_list_error_reports.set_defaults(func=self.cmd_list_error_reports)

        c_error_report = error_subp.add_parser(
            Commands.Subcommands.Show.LONG,
            aliases=[Commands.Subcommands.Show.SHORT],
            description='Output content of an error report.'
        )
        c_error_report.add_argument("report_id", nargs='+')
        c_error_report.set_defaults(func=self.cmd_error_report)

        c_del_err_report = error_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Delete one or more error reports.'
        )
        c_del_err_report.add_argument("--nodes", nargs="+", help="Only delete error reports from the given nodes")
        c_del_err_report.add_argument(
            "--since", help="Datetime since when to delete error reports. Date format: 2020-08-30 13:40:00")
        c_del_err_report.add_argument(
            "--to", type=str, help="Datetime until to delete error reports. Date format: 2020-08-30 13:40:00")
        c_del_err_report.add_argument("--exception", help="Only delete error reports matching the exception")
        c_del_err_report.add_argument("id", nargs="*", help="Delete error reports matching the given ids")
        c_del_err_report.set_defaults(func=self.cmd_del_error_report)

        self.check_subcommands(error_subp, error_subcmds)

    @classmethod
    def show_error_report_list(cls, args, lstmsg):
        """

        :param args:
        :param list[linstor.responses.ErrorReport] lstmsg:
        :return:
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_header(TableHeader("Id"))
        tbl.add_header(TableHeader("Datetime"))
        tbl.add_header(TableHeader("Node"))
        tbl.add_header(TableHeader("Exception"))
        if args.full:
            tbl.add_header(TableHeader("Location"))
            tbl.add_header(TableHeader("Version"))

        for error in lstmsg:
            msg = error.exception_message \
                if len(error.exception_message) < 60 else error.exception_message[0:57] + '...'
            row = [
                error.id,
                str(error.datetime)[:19],
                (error.module[0] + '|' if error.module else "") + error.node_names,
                error.exception + (": " + msg if msg else "")]
            if args.full:
                row += ["{f}:{l}".format(f=error.origin_file, l=error.origin_line) if error.origin_file else "",
                        error.version]
            tbl.add_row(row)
        tbl.show()

    def cmd_list_error_reports(self, args):
        since = args.since
        since_dt = None
        if since:
            since_dt = self.parse_time_str(since)

        to_dt = None
        if args.to:
            to_dt = datetime.strptime(args.to, '%Y-%m-%d')
            to_dt = to_dt.replace(hour=23, minute=59, second=59)

        lstmsg = self._linstor.error_report_list(nodes=args.nodes, since=since_dt, to=to_dt, ids=args.report_id)
        return self.output_list(args, lstmsg, self.show_error_report_list, single_item=False)

    def show_error_report(self, args, lstmsg):
        for error in lstmsg:
            print(Output.utf8(error.text))

    def cmd_error_report(self, args):
        lstmsg = self._linstor.error_report_list(with_content=True, ids=args.report_id)
        return self.output_list(args, lstmsg, self.show_error_report, single_item=False)

    @classmethod
    def fill_str_part(cls, fill_str, default_str):
        """
        Fill fill_str with missing parts from default_str.

        :param fill_str:
        :param default_str:
        :return:
        """
        return fill_str + default_str[len(fill_str):]

    def cmd_del_error_report(self, args):
        since_dt = None
        to_dt = None

        dt_format = '%Y-%m-%d %H:%M:%S'
        def_dt_str = '0000-00-00 23:59:59'

        if args.since:
            since_str = self.fill_str_part(args.since, def_dt_str)
            since_dt = datetime.strptime(since_str, dt_format)

        if args.to:
            to_str = self.fill_str_part(args.to, def_dt_str)
            to_dt = datetime.strptime(to_str, dt_format)

        replies = self.get_linstorapi().error_report_delete(
            args.nodes,
            since=since_dt,
            to=to_dt,
            exception=args.exception,
            version=None,
            ids=args.id
        )
        return self.handle_replies(args, replies)
