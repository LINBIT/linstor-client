import argparse

from linstor_client.table import Table, TableHeader
from linstor_client.utils import Output, LinstorClientError
from linstor_client.commands import Commands
from linstor_client.consts import ExitCode

from datetime import datetime


class ErrorReportCommands(Commands):
    SORT_BY_DEFAULT = 'error_time'
    SORT_ORDER_DEFAULT = 'desc'

    _command_name = Commands.ERROR_REPORTS
    _command_aliases = ["err"]
    _command_description = "Error report subcommands"

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
            self._command_name,
            aliases=self._command_aliases,
            formatter_class=argparse.RawTextHelpFormatter,
            description=self._command_description)

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
        Commands.add_truncate_args(c_list_error_reports)
        c_list_error_reports.add_argument(
            '--report-id',
            nargs='+',
            help="Restrict to id's that begin with the given ones."
        )
        c_list_error_reports.add_argument('-f', '--full', action="store_true", help='Show all error info fields')
        c_list_error_reports.add_argument(
            '--sort-by',
            choices=[
                'error_time', 'node_name', 'module', 'exception', 'exception_message',
                'origin_file', 'filename', 'version', 'peer'
            ],
            default=self.SORT_BY_DEFAULT,
            help='Sort the error reports by the given field (default: %(default)s)'
        )
        c_list_error_reports.add_argument(
            '--sort-order',
            choices=['asc', 'desc'],
            default=self.SORT_ORDER_DEFAULT,
            help='Sort order (default: %(default)s)'
        )
        c_list_error_reports.add_argument(
            '--limit', type=int, help='Maximum number of error reports to show (default: 1000)')
        c_list_error_reports.add_argument('--offset', type=int, help='Number of error reports to skip')
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
            "--since",
            help="Datetime since when to delete error reports. Date format: '2020-08-30 13:40:00' or '5d6h'")
        c_del_err_report.add_argument(
            "--to",
            help="Datetime until to delete error reports. Date format: '2020-08-30 13:40:00' or '5d6h'")
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
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable, truncate=args.truncate)
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

    @classmethod
    def show_error_report_page(cls, args, page):
        """

        :param args:
        :param linstor.responses.ErrorReportPage page:
        :return:
        """
        cls.show_error_report_list(args, page.error_reports)
        shown = len(page.error_reports)
        offset = page.offset if page.offset else 0
        if shown:
            print("Showing {f}-{l} of {t} error reports".format(
                f=offset + 1, l=offset + shown, t=page.total))
        else:
            print("Showing 0 of {t} error reports (offset {o})".format(t=page.total, o=offset))

    def cmd_list_error_reports(self, args):
        since = args.since
        since_dt = None
        if since:
            since_dt = self.parse_time_str(since)

        to_dt = None
        if args.to:
            to_dt = datetime.strptime(args.to, '%Y-%m-%d')
            to_dt = to_dt.replace(hour=23, minute=59, second=59)

        paged = args.limit is not None or args.offset is not None
        sorted_ = args.sort_by != self.SORT_BY_DEFAULT or args.sort_order != self.SORT_ORDER_DEFAULT
        if args.report_id and (paged or sorted_):
            raise LinstorClientError(
                "--report-id cannot be combined with --sort-by/--sort-order/--limit/--offset",
                exit_code=ExitCode.ARGPARSE_ERROR)

        # The paged endpoint (REST-API 1.30.0) sorts the reports of all nodes globally and is used whenever
        # the controller supports it. Report ids are only filtered by the old endpoint. An older controller
        # keeps using the old endpoint, unless sorting or paging was requested explicitly, which it cannot do.
        use_paged = not args.report_id and (paged or sorted_ or not self._linstor.api_version_smaller("1.30.0"))
        if use_paged:
            lstmsg = self._linstor.error_report_list_paged(
                nodes=args.nodes,
                since=since_dt,
                to=to_dt,
                limit=args.limit,
                offset=args.offset,
                sort_by=args.sort_by,
                sort_order=args.sort_order
            )
            if paged:
                return self.output_list(
                    args, lstmsg, self.show_error_report_page, single_item=True, machine_readable_raw=True)
            if not self.check_for_api_replies(lstmsg):
                # without an explicit page the output stays the plain list of reports
                lstmsg = lstmsg[0].error_reports
        else:
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
            try:
                since_dt = self.parse_time_str(args.since)
            except LinstorClientError:
                since_str = self.fill_str_part(args.since, def_dt_str)
                try:
                    since_dt = datetime.strptime(since_str, dt_format)
                except ValueError as ve:
                    raise LinstorClientError("Unable to parse 'since' date: " + str(ve), exit_code=2)

        if args.to:
            try:
                to_dt = self.parse_time_str(args.to)
            except LinstorClientError:
                to_str = self.fill_str_part(args.to, def_dt_str)
                try:
                    to_dt = datetime.strptime(to_str, dt_format)
                except ValueError as ve:
                    raise LinstorClientError("Unable to parse 'to' date: " + str(ve), exit_code=2)

        replies = self.get_linstorapi().error_report_delete(
            args.nodes,
            since=since_dt,
            to=to_dt,
            exception=args.exception,
            version=None,
            ids=args.id
        )
        return self.handle_replies(args, replies)
