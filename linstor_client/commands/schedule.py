from __future__ import print_function

import linstor_client
import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands
from linstor_client import Table
from linstor_client.consts import Color


class ScheduleCommands(Commands):
    _schedule_headers = [
        linstor_client.TableHeader("Name"),
        linstor_client.TableHeader("Full"),
        linstor_client.TableHeader("Incremental"),
        linstor_client.TableHeader("KeepLocal"),
        linstor_client.TableHeader("KeepRemote"),
        linstor_client.TableHeader("OnFailure"),
    ]

    _schedule_by_resource_headers = [
        linstor_client.TableHeader("Resource"),
        linstor_client.TableHeader("Remote"),
        linstor_client.TableHeader("Schedule"),
        linstor_client.TableHeader("Last"),
        linstor_client.TableHeader("Next"),
        linstor_client.TableHeader("Planned Inc"),
        linstor_client.TableHeader("Planned Full"),
        linstor_client.TableHeader("Reason"),
    ]

    _schedule_by_resource_details_headers = [
        linstor_client.TableHeader("Remote"),
        linstor_client.TableHeader("Schedule"),
        linstor_client.TableHeader("Resource-Definition"),
        linstor_client.TableHeader("Resource-Group"),
        linstor_client.TableHeader("Controller"),
    ]

    class ListByResource(object):
        LONG = "list-by-resource"
        SHORT = "lbr"

    class ListByResourceDetails(object):
        LONG = "list-by-resource-details"
        SHORT = "lbd"

    def __init__(self):
        super(ScheduleCommands, self).__init__()

    @classmethod
    def argparse_keep_check(cls, data):
        err_msg = 'Only numbers >= 0 allowed or "all"'
        try:
            value = int(data)

            if value < 0:
                raise argparse.ArgumentTypeError(err_msg)

            return value
        except ValueError:
            if data == "all":
                return -1
            else:
                raise argparse.ArgumentTypeError(err_msg)

    @classmethod
    def argparse_max_retry_check(cls, data):
        err_msg = 'Only numbers >= 0 allowed or "forever"'
        try:
            value = int(data)

            if value < 0:
                raise argparse.ArgumentTypeError(err_msg)

            return value
        except ValueError:
            if data == "forever":
                return -1
            else:
                raise argparse.ArgumentTypeError(err_msg)

    def setup_commands(self, parser):
        subcmds = [
            Commands.Subcommands.List,
            Commands.Subcommands.Create,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Modify,
            ScheduleCommands.ListByResource,
            ScheduleCommands.ListByResourceDetails,
        ]

        sched_parser = parser.add_parser(
            Commands.Subcommands.Schedule.LONG,
            aliases=[Commands.Subcommands.Schedule.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Commands to manage schedules")
        sched_sub = sched_parser.add_subparsers(
            title="Schedule subcommands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # list schedule
        list_sched = sched_sub.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of schedules.')
        list_sched.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        list_sched.set_defaults(func=self.list)

        # list schedule by resources
        list_sched_by_rsc = sched_sub.add_parser(
            ScheduleCommands.ListByResource.LONG,
            aliases=[ScheduleCommands.ListByResource.SHORT],
            description='Prints a list of schedules for resources.')
        list_sched_by_rsc.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        list_sched_by_rsc.add_argument(
            '-r', '--resource',
            type=str,
            help='Filter by list of resource').completer = self.resource_completer
        list_sched_by_rsc.add_argument(
            '-o', '--remote',
            type=str,
            help='Filter by list of remote').completer = self.remote_completer
        list_sched_by_rsc.add_argument(
            '-s', '--schedule',
            type=str,
            help='Filter by list of schedule').completer = self.schedule_completer
        list_sched_by_rsc.add_argument(
            '-a', '--active-only',
            action="store_true",
            help='Filter by list of active only')
        list_sched_by_rsc.set_defaults(func=self.list_by_resource)

        # list schedule resource details
        list_sched_by_rsc_det = sched_sub.add_parser(
            ScheduleCommands.ListByResourceDetails.LONG,
            aliases=[ScheduleCommands.ListByResourceDetails.SHORT],
            description='Prints details of schedules for a resource.')
        list_sched_by_rsc_det.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        list_sched_by_rsc_det.add_argument('resource_name').completer = self.resource_dfn_completer
        list_sched_by_rsc_det.set_defaults(func=self.list_by_resource_details)

        # create schedule
        create_sched = sched_sub.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='''\
Create a schedule.

Cron-Syntax:
  */5 3 2-4 4,5 SAT
   ^  ^  ^   ^   ^
   |  |  |   |   +- Day of Week (Numbers 0-6 (0 == Sunday) or 3 letter abbreviation)
   |  |  |   +----- Month (Numbers 1-12 or 3 letter abbreviation)
   |  |  +--------- Day of Month (1-31)
   |  +------------ Hour (0-23)
   +--------------- Minute (0-59)

The example above reads:
Every 5 minutes past hour 3 on every day between 2 and 4 and on every Saturday in April and May.
''')
        create_sched.add_argument('schedule_name', help='Name of the schedule')
        create_sched.add_argument('full_cron', help='Cron expression to be used for full backups')
        create_sched.add_argument('-i', '--incremental-cron', help='Cron expression to be used for incremental backups')
        create_sched.add_argument('-l', '--keep-local', type=ScheduleCommands.argparse_keep_check,
                                  help='Number(or "all") of snapshots for a full backup to keep local')
        create_sched.add_argument('-r', '--keep-remote', type=ScheduleCommands.argparse_keep_check,
                                  help='Number(or "all") of full backups to keep at the remote')
        create_sched.add_argument('--on-failure', type=str.upper, choices=["RETRY", "SKIP"], help='On failure action')
        create_sched.add_argument('--max-retries',
                                  type=ScheduleCommands.argparse_max_retry_check,
                                  help='How many retries if on-failure is retry, use "forever" for infinity')
        create_sched.set_defaults(func=self.create)

        # modify schedule
        modify_sched = sched_sub.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='''\
Modify a schedule.

Cron-Syntax:
  */5 3 2-4 4,5 SAT
   ^  ^  ^   ^   ^
   |  |  |   |   +- Day of Week (Numbers 0-6 (0 == Sunday) or 3 letter abbreviation)
   |  |  |   +----- Month (Numbers 1-12 or 3 letter abbreviation)
   |  |  +--------- Day of Month (1-31)
   |  +------------ Hour (0-23)
   +--------------- Minute (0-59)

The example above reads:
Every 5 minutes past hour 3 on every day between 2 and 4 and on every Saturday in April and May.
''')

        modify_sched.add_argument('schedule_name', help='Name of the schedule')
        modify_sched.add_argument('-f', '--full-cron', help='Cron expression to be used for full backups')
        modify_sched.add_argument('-i', '--incremental-cron', help='Cron expression to be used for incremental backups')
        modify_sched.add_argument('-l', '--keep-local', type=ScheduleCommands.argparse_keep_check,
                                  help='Number(or "all") of snapshots for a full backup to keep local')
        modify_sched.add_argument('-r', '--keep-remote', type=ScheduleCommands.argparse_keep_check,
                                  help='Number(or "all") of full backups to keep at the remote')
        modify_sched.add_argument('--on-failure', type=str.upper, choices=["RETRY", "SKIP"], help='On failure action')
        modify_sched.add_argument('--max-retries',
                                  type=ScheduleCommands.argparse_max_retry_check,
                                  help='How many retries if on-failure is retry, use "forever" for infinity')
        modify_sched.set_defaults(func=self.modify)

        # delete schedule
        delete_sched = sched_sub.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Delete a schedule.')
        delete_sched.add_argument('schedule_name', help='Name of the schedule').completer = self.schedule_completer
        delete_sched.set_defaults(func=self.delete)

        self.check_subcommands(sched_sub, subcmds)

    def create(self, args):
        replies = self.get_linstorapi().schedule_create(
            schedule_name=args.schedule_name,
            full_cron=args.full_cron,
            keep_local=args.keep_local,
            keep_remote=args.keep_remote,
            on_failure=args.on_failure,
            incremental_cron=args.incremental_cron,
            max_retries=args.max_retries,
        )
        return self.handle_replies(args, replies)

    def modify(self, args):
        replies = self.get_linstorapi().schedule_modify(
            schedule_name=args.schedule_name,
            full_cron=args.full_cron,
            keep_local=args.keep_local,
            keep_remote=args.keep_remote,
            on_failure=args.on_failure,
            incremental_cron=args.incremental_cron,
            max_retries=args.max_retries,
        )
        return self.handle_replies(args, replies)

    def delete(self, args):
        replies = self.get_linstorapi().schedule_delete(schedule_name=args.schedule_name)
        return self.handle_replies(args, replies)

    @classmethod
    def show_schedules(cls, args, lstmsg):
        """

        :param args:
        :param linstor.responses.ScheduleListResponse lstmsg:
        :return:
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._schedule_headers:
            tbl.add_header(hdr)
        for schedule in lstmsg.schedules:
            on_failure = schedule.on_failure
            if schedule.on_failure == "RETRY":
                on_failure += "({r})".format(r=schedule.max_retries if schedule.max_retries is not None else "forever")
            row = [
                schedule.schedule_name,
                schedule.full_cron,
                "" if schedule.inc_cron is None else schedule.inc_cron,
                "all" if schedule.keep_local is None else schedule.keep_local,
                "all" if schedule.keep_remote is None else schedule.keep_remote,
                on_failure
            ]
            tbl.add_row(row)
        tbl.show()

    def list(self, args):
        lstmsg = [self.get_linstorapi().schedule_list()]
        return self.output_list(args, lstmsg, ScheduleCommands.show_schedules, machine_readable_raw=True)

    @classmethod
    def _empty_if_none(cls, value):
        return value if value else ""

    @classmethod
    def _schedule_datetime_str(cls, timestamp, bool_indicator):
        if timestamp:
            return "{dt} ({t})".format(
                dt=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                t="Inc" if bool_indicator else "Full")
        return ""

    @classmethod
    def show_schedules_by_resource(cls, args, lstmsg):
        """

        :param args:
        :param linstor.responses.ScheduleResourceListResponse lstmsg:
        :return:
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._schedule_by_resource_headers:
            tbl.add_header(hdr)
        for schedule in lstmsg.schedule_resources:
            row = [
                schedule.resource_name,
                cls._empty_if_none(schedule.remote_name),
                cls._empty_if_none(schedule.schedule_name),
                cls._schedule_datetime_str(schedule.last_snap_time, schedule.last_snap_inc),
                cls._schedule_datetime_str(schedule.next_exec_time, schedule.next_exec_inc),
                cls._empty_if_none(schedule.next_planned_inc),
                cls._empty_if_none(schedule.next_planned_full),
                cls._empty_if_none(schedule.reason),
            ]
            tbl.add_row(row)
        tbl.show()

    def list_by_resource(self, args):
        lstmsg = self.get_linstorapi().schedule_list_by_resource(
            filter_by_resource=args.resource,
            filter_by_remote=args.remote,
            filter_by_schedule=args.schedule,
            active_only=args.active_only,
        )
        return self.output_list(args, lstmsg, ScheduleCommands.show_schedules_by_resource, machine_readable_raw=True)

    @classmethod
    def _enabled_disabled_str(cls, val, win):
        if val is None:
            return ["", None]
        color_if_win = Color.GREEN if val else Color.RED
        text = "Enabled" if val else "Disabled"
        return [text, color_if_win if win else None]

    @classmethod
    def show_schedules_by_resource_details(cls, args, lstmsg):
        """

        :param args:
        :param linstor.responses.ScheduleResourceDetailsListResponse lstmsg:
        :return:
        """
        tbl = Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in cls._schedule_by_resource_details_headers:
            tbl.add_header(hdr)
        for schedule in lstmsg.schedule_resources:
            rd_win = schedule.resource_definition is not None
            rg_win = not rd_win and schedule.resource_group is not None
            c_win = not rd_win and not rg_win and schedule.controller is not None

            rd_text_color = cls._enabled_disabled_str(schedule.resource_definition, rd_win)
            rg_text_color = cls._enabled_disabled_str(schedule.resource_group, rg_win)
            c_text_color = cls._enabled_disabled_str(schedule.controller, c_win)

            row = [
                schedule.remote_name,
                schedule.schedule_name,
                tbl.color_cell(rd_text_color[0], rd_text_color[1]) if rd_win else rd_text_color[0],
                tbl.color_cell(rg_text_color[0], rg_text_color[1]) if rg_win else rg_text_color[0],
                tbl.color_cell(c_text_color[0], c_text_color[1]) if c_win else c_text_color[0],
            ]
            tbl.add_row(row)
        tbl.show()

    def list_by_resource_details(self, args):
        lstmsg = self.get_linstorapi().schedule_list_by_resource_details(args.resource_name)
        return self.output_list(
            args, lstmsg, ScheduleCommands.show_schedules_by_resource_details, machine_readable_raw=True)
