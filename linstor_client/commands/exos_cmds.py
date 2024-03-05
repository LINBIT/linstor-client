import getpass
import json

import linstor_client
import linstor_client.argparse.argparse as argparse

from linstor_client.commands import Commands
from linstor_client.consts import Color, ExitCode


class ExosCommands(Commands):

    _exos_enclosure_headers = [
        linstor_client.TableHeader("Enclosure"),
        linstor_client.TableHeader("Ctrl A IP"),
        linstor_client.TableHeader("Ctrl B IP"),
        linstor_client.TableHeader("Health"),
        linstor_client.TableHeader("Health Reason")
    ]

    _exos_map_headers = [
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Enclosure"),
        linstor_client.TableHeader("Connected Ports")
    ]

    _exos_defaults_headers = [
        linstor_client.TableHeader("Property"),
        linstor_client.TableHeader("Value")
    ]

    def __init__(self):
        super(ExosCommands, self).__init__()

    class GetDefaults:
        LONG = 'get-defaults'

    class SetDefaults:
        LONG = 'set-defaults'

    class Events:
        LONG = 'events'
        SHORT = 'e'

    class Exec:
        LONG = 'exec'

    class Map:
        LONG = 'map'

    def setup_commands(self, parser):
        # Exos subcommands
        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.Delete,
            Commands.Subcommands.Modify,
            ExosCommands.SetDefaults,
            ExosCommands.GetDefaults,
            ExosCommands.Events,
            ExosCommands.Map,
            ExosCommands.Exec,
        ]

        exos_parser = parser.add_parser(
            Commands.EXOS,
            formatter_class=argparse.RawTextHelpFormatter,
            description='Exos subcommands'
        )

        exos_subp = exos_parser.add_subparsers(
            title='Exos commands',
            metavar='',
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # get defaults
        p_get_dflts = exos_subp.add_parser(
            ExosCommands.GetDefaults.LONG,
            description='Lists the default configuration.')
        p_get_dflts.add_argument(
            '-p',
            '--pastable',
            action="store_true",
            help='Generate pastable output')
        p_get_dflts.set_defaults(func=self.get_dflts)

        # set defaults
        p_set_dftls = exos_subp.add_parser(
            ExosCommands.SetDefaults.LONG,
            description='Sets the default configuration for all enclosures.'
        )
        p_set_dftls.add_argument(
            '--username', type=str, help='Default username')
        p_set_dftls.add_argument(
            '--username-env',
            type=str,
            help='Default environment variable containing the username')
        p_set_dftls.add_argument(
            '--password',
            type=str,
            nargs='?',
            help='Default password',
            action='store',
            const='')
        p_set_dftls.add_argument(
            '--password-env',
            type=str,
            help='Default environment variable containing the password')
        p_set_dftls.add_argument(
            '--unset-username',
            action='store_true',
            help='Unsets the default username')
        p_set_dftls.add_argument(
            '--unset-username-env',
            action='store_true',
            help='Unsets the default username-env')
        p_set_dftls.add_argument(
            '--unset-password-env',
            action='store_true',
            help='Unsets the default password-env')
        p_set_dftls.add_argument(
            '--unset-password',
            action='store_true',
            help='Unsets the default password')
        p_set_dftls.set_defaults(func=self.set_dflts)

        # create enclosure
        p_new_encl = exos_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Create a new Exos enclosure.'
        )
        self._add_create_mod_args(p_new_encl, True)
        p_new_encl.set_defaults(func=self.create_encl)

        # modify enclosure
        p_mod_encl = exos_subp.add_parser(
            Commands.Subcommands.Modify.LONG,
            aliases=[Commands.Subcommands.Modify.SHORT],
            description='Modifies the specified Exos enclosure.'
        )
        self._add_create_mod_args(p_mod_encl, False)
        p_mod_encl.set_defaults(func=self.modify_encl)

        # delete enclosure
        p_del_encl = exos_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Deletes the specified Exos enclosure.'
        )
        p_del_encl.add_argument(
            'name',
            help='Name of the enclosure',
            type=str
        )
        p_del_encl.set_defaults(func=self.delete_encl)

        # list enclosures
        p_list_encl = exos_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Lists the Exos enclosures known to LINSTOR.'
        )
        p_list_encl.add_argument(
            '--nocache',
            help='Force recaching',
            action='store_true'
        )
        p_list_encl.add_argument(
            '-p', '--pastable',
            action='store_true',
            help='Generate pastable output')
        p_list_encl.set_defaults(func=self.list_encl)

        # list enclosure events
        p_events_encl = exos_subp.add_parser(
            ExosCommands.Events.LONG,
            aliases=[ExosCommands.Events.SHORT],
            description='Lists events from the controllers in the specified Exos enclosure.'
        )
        p_events_encl.add_argument(
            'name',
            help='Name of the enclosure',
            type=str
        )
        p_events_encl.add_argument(
            '--count',
            help="Fetch the last X events (default 20)",
            type=int
        )
        p_events_encl.set_defaults(func=self.list_encl_events)

        # exec
        p_exec = exos_subp.add_parser(
            ExosCommands.Exec.LONG,
            description="Pass Exos API command(s) to the specified Exos enclosure."
        )
        p_exec.add_argument(
            'name',
            help='Name of the enclosure',
            type=str
        )
        p_exec.add_argument(
            'exos_cmd',
            nargs='+',
            type=str
        )
        p_exec.set_defaults(func=self.exos_exec)

        # map
        p_map = exos_subp.add_parser(
            ExosCommands.Map.LONG,
            description='Lists to which Exos controller.ports each LINSTOR \
                 node is connected.')
        p_map.add_argument('-p', '--pastable', action="store_true",
                           help='Generate pastable output')
        p_map.set_defaults(func=self.exos_map)

        self.check_subcommands(exos_subp, subcmds)

    def _add_create_mod_args(self, sub_parser, create=True):
        sub_parser.add_argument(
            'name',
            help='Name of the enclosure',
            type=str
        )
        sub_parser.add_argument(
            'ctrl_a_ip' if create else '--ctrl-a-ip',
            help='IP address of the first Exos controller',
            # nargs = 1 if create else '?',
            type=str
        )
        sub_parser.add_argument(
            'ctrl_b_ip' if create else '--ctrl-b-ip',
            help='IP address of the second Exos controller',
            nargs='?' if create else 1,
            type=str
        )
        sub_parser.add_argument(
            '--username',
            help='Username for this Exos enclosure',
            type=str
        )
        sub_parser.add_argument(
            '--username-env',
            help='Environment variable containing the username for this Exos \
                enclosure',
            type=str
        )
        sub_parser.add_argument(
            '--password',
            help='Password for this Exos enclosure',
            nargs='?',
            type=str
        )
        sub_parser.add_argument(
            '--password-env',
            help='Environment variable containing the username for this Exos \
                enclosure',
            type=str
        )

    def get_dflts(self, args):
        exos_dflt = self.get_linstorapi().exos_get_defaults()
        return self.output_list(args, exos_dflt, self.show_exos_dflts)

    @classmethod
    def show_exos_dflts(cls, args, exos_dflts):
        tbl = linstor_client.Table(
            utf8=not args.no_utf8,
            colors=not args.no_color,
            pastable=args.pastable)

        header = list(cls._exos_defaults_headers)
        for hdr in header:
            tbl.add_header(hdr)

        # tbl.set_groupby([tbl.header_name(0)])

        tbl.add_row(cls._get_row("Username", exos_dflts.username))
        tbl.add_row(cls._get_row("UsernameEnv", exos_dflts.username_env))
        tbl.add_row(cls._get_row("Password", exos_dflts.password))
        tbl.add_row(cls._get_row("PasswordEnv", exos_dflts.password_env))

        tbl.show()

    @classmethod
    def _get_row(cls, key, value):
        return [key, value if value else '-- Not set --']

    def set_dflts(self, args):
        unset = []
        if args.unset_username:
            unset += ["username"]
        if args.unset_username_env:
            unset += ["usernameEnv"]
        if args.unset_password:
            unset += ["password"]
        if args.unset_password_env:
            unset += ["passwordEnv"]

        replies = self.get_linstorapi().exos_set_defaults(
            args.username,
            args.username_env,
            self._get_password(args),
            args.password_env,
            unset
        )
        return self.handle_replies(args, replies)

    def create_encl(self, args):
        replies = self.get_linstorapi().exos_enclosure_create(
            args.name,
            args.ctrl_a_ip,
            args.ctrl_b_ip if args.ctrl_b_ip else None,
            args.username,
            args.username_env,
            self._get_password(args),
            args.password_env
        )
        return self.handle_replies(args, replies)

    def modify_encl(self, args):
        replies = self.get_linstorapi().exos_enclosure_modify(
            args.name,
            args.ctrl_a_ip,
            args.ctrl_b_ip if args.ctrl_b_ip else None,
            args.username,
            args.username_env,
            self._get_password(args),
            args.password_env
        )
        return self.handle_replies(args, replies)

    def delete_encl(self, args):
        replies = self.get_linstorapi().exos_enclosure_delete(args.name)
        return self.handle_replies(args, replies)

    def list_encl(self, args):
        list_msg = self.get_linstorapi().exos_list_enclosures(args.nocache)
        return self.output_list(args, list_msg, self.show_enclosures)

    @classmethod
    def show_enclosures(cls, args, list_msg):
        tbl = linstor_client.Table(
            utf8=not args.no_utf8,
            colors=not args.no_color,
            pastable=args.pastable)

        header = list(cls._exos_enclosure_headers)
        for hdr in header:
            tbl.add_header(hdr)

        tbl.set_groupby([tbl.header_name(0)])

        health_colors_dict = {
            "OK": Color.GREEN
        }

        for encl in list_msg.exos_enclosures:
            if encl.health in health_colors_dict:
                health_color = health_colors_dict[encl.health]
            else:
                health_color = Color.RED

            row = [
                encl.name,
                encl.ctrl_a_ip if encl.ctrl_a_ip else "-",
                encl.ctrl_b_ip if encl.ctrl_b_ip else "-",
                tbl.color_cell(encl.health, health_color),
                encl.health_reason if encl.health_reason else ""
            ]
            tbl.add_row(row)
        tbl.show()

    def list_encl_events(self, args):
        list_msg = self.get_linstorapi().exos_enclosure_events(
            args.name,
            args.count)
        return self.output_list(args, list_msg, self.show_events)

    @classmethod
    def show_events(cls, args, list_msg):
        for i, event in enumerate(list_msg.exos_events):
            if i > 0:
                print("------")
            print("{}, {}, {}".format(event.severity,
                                      event.event_id,
                                      event.time_stamp))
            print("Message: {}".format(event.message))
            if event.additional_information != "None.":
                print("Additional information: {}".format(
                    event.additional_information))
            if event.recommended_action != "- No action is required.":
                print("Recommended Action: {}".format(
                    event.recommended_action))

    def exos_exec(self, args):
        replies = self.get_linstorapi().exos_exec(args.name, args.exos_cmd)
        if replies:
            print(json.dumps(replies[0].data_v1))
        return ExitCode.OK

    def exos_map(self, args):
        list_msg = self.get_linstorapi().exos_map()
        return self.output_list(args, list_msg, self.show_map)

    @classmethod
    def show_map(cls, args, list_msg):
        tbl = linstor_client.Table(
            utf8=not args.no_utf8,
            colors=not args.no_color,
            pastable=args.pastable)

        header = list(cls._exos_map_headers)
        for hdr in header:
            tbl.add_header(hdr)

        tbl.set_groupby([tbl.header_name(0)])

        for con_map in list_msg.exos_connections:
            row = [
                con_map.node_name,
                con_map.enclosure_name,
                ", ".join(con_map.connections)
            ]
            tbl.add_row(row)
        tbl.show()

    def _get_password(self, args):
        if args.password is None:
            return None
        elif args.password:
            return args.password
        else:
            return getpass.getpass("Password: ")
