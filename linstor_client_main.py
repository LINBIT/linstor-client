#!/usr/bin/env python3
"""
    LINSTOR - management of distributed storage/DRBD9 resources
    Copyright (C) 2013 - 2018  LINBIT HA-Solutions GmbH
    Author: Robert Altnoeder, Roland Kammerer, Rene Peinthor

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
import traceback
import itertools
import getpass

import linstor
import linstor_client.argparse.argparse as argparse
import linstor_client.argcomplete as argcomplete
import linstor_client.utils as utils
from linstor_client.commands import (
    ControllerCommands,
    VolumeDefinitionCommands,
    StoragePoolCommands,
    ResourceDefinitionCommands,
    ResourceGroupCommands,
    VolumeGroupCommands,
    ResourceCommands,
    ResourceConnectionCommands,
    VolumeCommands,
    NodeCommands,
    NodeConnectionCommands,
    SnapshotCommands,
    DrbdProxyCommands,
    MigrateCommands,
    PhysicalStorageCommands,
    ErrorReportCommands,
    ExosCommands,
    AdviceCommands,
    ZshGenerator,
    MiscCommands,
    BackupCommands,
    RemoteCommands,
    FileCommands,
    KeyValueStoreCommands,
    ScheduleCommands,
    Commands,
    DefaultState,
    ArgumentError
)

from linstor_client.consts import (
    GITHASH,
    KEY_LS_CONTROLLERS,
    ENV_OUTPUT_VERSION,
    VERSION,
    ExitCode
)


class StateService(object):
    def __init__(self, linstor_cli):
        self._linstor_cli = linstor_cli
        self._current_state = []

    def enter_state(self, state, verbose):
        already_interactive = bool(self._current_state)
        self._current_state.append(state)
        if not already_interactive:
            return self._linstor_cli.run_interactive(verbose)
        return ExitCode.OK

    def pop_state(self):
        if self._current_state:
            self._current_state.pop()

    def clear_state(self):
        self._current_state = []

    def has_state(self):
        return bool(self._current_state)

    def get_state(self):
        return self._current_state[-1] if self._current_state else DefaultState()


class LinStorCLI(object):
    """
    linstor command line client
    """

    readline_history_file = "~/.config/linstor/client.history"

    def __init__(self):
        self._state_service = StateService(self)
        self._all_commands = None

        self._controller_commands = ControllerCommands()
        self._node_commands = NodeCommands()
        self._node_conn_commands = NodeConnectionCommands()
        self._storage_pool_commands = StoragePoolCommands()
        self._resource_dfn_commands = ResourceDefinitionCommands()
        self._resource_grp_commands = ResourceGroupCommands()
        self._volume_grp_commands = VolumeGroupCommands()
        self._volume_dfn_commands = VolumeDefinitionCommands()
        self._resource_commands = ResourceCommands(self._state_service)
        self._resource_conn_commands = ResourceConnectionCommands()
        self._volume_commands = VolumeCommands()
        self._snapshot_commands = SnapshotCommands()
        self._drbd_proxy_commands = DrbdProxyCommands()
        self._misc_commands = MiscCommands()
        self._physical_storage_commands = PhysicalStorageCommands()
        self._error_report_commands = ErrorReportCommands()
        self._exos_commands = ExosCommands()
        self._advise_commands = AdviceCommands()
        self._backup_commands = BackupCommands()
        self._remote_commands = RemoteCommands()
        self._file_commands = FileCommands()
        self._schedule_commands = ScheduleCommands()
        self._key_value_store_commands = KeyValueStoreCommands()

        self._command_list = [
            self._controller_commands,
            self._node_commands,
            self._node_conn_commands,
            self._resource_dfn_commands,
            self._resource_grp_commands,
            self._volume_grp_commands,
            self._resource_commands,
            self._resource_conn_commands,
            self._volume_commands,
            self._snapshot_commands,
            self._drbd_proxy_commands,
            self._storage_pool_commands,
            self._volume_dfn_commands,
            self._physical_storage_commands,
            self._error_report_commands,
            self._exos_commands,
            self._advise_commands,
            self._backup_commands,
            self._remote_commands,
            self._file_commands,
            self._misc_commands,
            self._schedule_commands,
            self._key_value_store_commands
        ]

        self._zsh_generator = None
        self._parser = self.setup_parser()
        self._all_commands = self.parser_cmds(self._parser)
        self._linstorapi = None  # type: Optional[linstor.Linstor]

    def setup_parser(self):
        parser = argparse.ArgumentParser(prog="linstor")
        """
        ATTENTION! ATTENTION!
        If you add a new global option here, don't forget to update:
        utils.py:filter_new_args
        otherwise drbd options will fail!
        ATTENTION OVER! ATTENTION OVER!
        """
        parser.add_argument('--version', '-v', action='version',
                            version='%(prog)s-client ' + VERSION + '; ' + GITHASH)
        parser.add_argument('--no-color', action="store_true",
                            help='Do not use colors in output. Useful for old terminals/scripting.')
        parser.add_argument('--no-utf8', action="store_true", default=not sys.stdout.isatty(),
                            help='Do not use utf-8 characters in output (i.e., tables).')
        parser.add_argument('--warn-as-error', action="store_true",
                            help='Treat WARN return code as error (i.e., return code > 0).')
        parser.add_argument('--curl',
                            action="store_true",
                            help="Do not execute the action, only output a curl equivalent command.")
        parser.add_argument('--controllers', default='localhost:%d' % linstor.Linstor.REST_PORT,
                            help='Comma separated list of controllers (e.g.: "host1:port,host2:port"). '
                            'If the environment variable %s is set, '
                            'the ones set via this argument get appended.' % KEY_LS_CONTROLLERS)
        parser.add_argument('-m', '--machine-readable', action="store_true")
        parser.add_argument(
            '--output-version',
            choices=['v0', 'v1'],
            default=os.environ.get(ENV_OUTPUT_VERSION, "v1"),
            help="Machine readable output format, default 'v1'. "
                 "Can also be set via environment variable '{env}'".format(env=ENV_OUTPUT_VERSION)
        )
        parser.add_argument('--verbose', '-V', action='store_true')
        parser.add_argument('-t', '--timeout', default=300, type=int,
                            help="Connection/Command timeout value in seconds.")
        parser.add_argument('--disable-config', action="store_true",
                            help="Disable config loading and only use commandline arguments.")
        parser.add_argument('--user', '-u', help="Linstor username to use")
        parser.add_argument('--password', '-P', help="Linstor user password")
        parser.add_argument('--certfile', help="SSL certificate file")
        parser.add_argument('--keyfile', help="SSL key file")
        parser.add_argument('--cafile', help="SSL CA certificate file")
        parser.add_argument(
            '--allow-insecure-auth',
            action='store_true',
            help="Allow password authentication with HTTP"
        )

        subp = parser.add_subparsers(title='subcommands',
                                     description='valid subcommands',
                                     help='Use the list command to print a '
                                     'nicer looking overview of all valid commands')

        # interactive mode
        parser_ia = subp.add_parser(Commands.INTERACTIVE,
                                    description='Start interactive mode')
        parser_ia.set_defaults(func=self.cmd_interactive)

        # help
        p_help = subp.add_parser(Commands.HELP,
                                 description='Print help for a command')
        p_help.add_argument('command', nargs='*')
        p_help.set_defaults(func=self.cmd_help, always_allowed=True)

        # list
        p_list = subp.add_parser(Commands.LIST_COMMANDS, aliases=['commands', 'list'],
                                 description='List available commands')
        p_list.add_argument('-t', '--tree', action="store_true", help="Print a tree view of all commands.")
        p_list.set_defaults(func=self.cmd_list, always_allowed=True)

        # exit
        p_exit = subp.add_parser(Commands.EXIT, aliases=['quit'],
                                 description='Only useful in interactive mode')
        p_exit.set_defaults(func=self.cmd_exit, always_allowed=True)

        for sub_cmd in self._command_list:
            sub_cmd.setup_commands(subp)

        # dm-migrate
        c_dmmigrate = subp.add_parser(
            Commands.DMMIGRATE,
            description='Generate a migration script from drbdmanage to linstor'
        )
        c_dmmigrate.add_argument('ctrlvol', help='json dump generated by "drbdmanage export-ctrlvol"')
        c_dmmigrate.add_argument('script', help='file name of the generated migration shell script')
        c_dmmigrate.set_defaults(func=MigrateCommands.cmd_dmmigrate)

        # zsh completer
        self._zsh_generator = ZshGenerator(subp)
        zsh_compl = subp.add_parser(
            Commands.GEN_ZSH_COMPLETER,
            description='Generate a zsh completion script'
        )
        zsh_compl.set_defaults(func=self._zsh_generator.cmd_completer)

        argcomplete.autocomplete(parser)

        subp.metavar = "{%s}" % ", ".join(sorted(Commands.MainList))

        return parser

    @staticmethod
    def merge_config_arguments(pargs):
        global_entries = linstor.Config.get_section('global')
        for key, val in global_entries.items():
            pargs.insert(0, "--" + key)
            if val:
                pargs.insert(1, val)
        return pargs

    @staticmethod
    def merge_environ_arguments(pargs):
        for key, val in os.environ.items():
            if key.startswith("LS_CLIENT_"):
                arg = key[10:].lower().replace("_", "-")
                pargs.insert(0, "--" + arg)
                if val:
                    pargs.insert(1, val)
        return pargs

    def parse(self, pargs):
        # read global environment options
        pargs = LinStorCLI.merge_environ_arguments(pargs)
        # read global options from config file
        if '--disable-config' not in pargs:
            pargs = LinStorCLI.merge_config_arguments(pargs)
        # very basic way to default into interactive if no options or commands are specified
        # only python 3.4+ argparse supports default subparsers
        if not pargs:
            pargs.append("interactive")
        return self._parser.parse_args(pargs)

    @classmethod
    def _report_linstor_error(cls, le):
        sys.stderr.write("Error: " + le.message + '\n')
        for err in le.all_errors():
            sys.stderr.write(' ' * 2 + err.message + '\n')

    def parse_and_execute(self, pargs, is_interactive=False):
        rc = ExitCode.OK
        try:
            try:
                args = self.parse(pargs)
            except IOError as ex:
                import errno
                if ex.errno == errno.EPIPE:
                    raise SystemExit(1)
                raise

            local_only_cmds = [
                self.cmd_list,
                MigrateCommands.cmd_dmmigrate,
                self._zsh_generator.cmd_completer,
                self.cmd_help
            ]

            # only connect if not already connected or a local only command was executed
            conn_errors = []
            contrl_list = linstor.MultiLinstor.controller_uri_list(
                os.environ.get(KEY_LS_CONTROLLERS, "") + ',' + args.controllers)
            if self._linstorapi is None and args.func not in local_only_cmds:
                username = None
                password = None
                if args.user:
                    username = args.user
                    if args.password:
                        password = args.password
                    else:
                        password = getpass.getpass("Enter Linstor password:")

                for contrl in contrl_list:
                    try:
                        self._linstorapi = linstor.Linstor(
                            contrl,
                            timeout=args.timeout,
                            keep_alive=True,
                            agent_info="Client " + VERSION
                        )
                        self._linstorapi.username = username
                        self._linstorapi.password = password
                        self._linstorapi.certfile = args.certfile
                        self._linstorapi.keyfile = args.keyfile
                        self._linstorapi.cafile = args.cafile
                        self._linstorapi.allow_insecure = args.allow_insecure_auth
                        self._linstorapi.curl = args.curl or (hasattr(args, 'from_file') and args.from_file)
                        for cmd in self._command_list:
                            cmd._linstor = self._linstorapi
                        self._linstorapi.connect()
                        break
                    except linstor.LinstorNetworkError as le:
                        conn_errors.append(le)

            if len(conn_errors) == len(contrl_list):
                for x in conn_errors:
                    self._report_linstor_error(x)
                rc = ExitCode.CONNECTION_ERROR
            else:
                if args.verbose and args.func != self.cmd_interactive:
                    print("Connected to {h}".format(h=self._linstorapi.controller_host()))
                current_state = self._state_service.get_state()
                allowed_states = vars(args).get('allowed_states', [DefaultState])
                always_allowed = vars(args).get('always_allowed', False)
                if always_allowed or current_state.__class__ in allowed_states:
                    rc = args.func(args)
                else:
                    sys.stderr.write("Error: Command not allowed in state '{state.name}'\n".format(state=current_state))
                    rc = ExitCode.ILLEGAL_STATE
        except (ArgumentError, argparse.ArgumentTypeError, linstor.LinstorArgumentError) as ae:
            try:
                self.parse(list(itertools.takewhile(lambda x: not x.startswith('-'), pargs)) + ['-h'])
            except SystemExit:
                pass
            sys.stderr.write(ae.message + '\n')
            return ExitCode.ARGPARSE_ERROR
        except utils.LinstorClientError as lce:
            sys.stderr.write(lce.message + '\n')
            return lce.exit_code
        except linstor.LinstorNetworkError as le:
            self._report_linstor_error(le)
            rc = ExitCode.CONNECTION_ERROR
        except linstor.LinstorTimeoutError as le:
            self._report_linstor_error(le)
            rc = ExitCode.CONNECTION_TIMEOUT
            self._linstorapi.disconnect()
            self._linstorapi = None  # should trigger reconnect in interactive mode
        except linstor.LinstorApiCallError as le:
            rc = self._controller_commands.handle_replies(args, le.all_errors())
        except linstor.LinstorError as le:
            self._report_linstor_error(le)
            rc = ExitCode.UNKNOWN_ERROR
        finally:
            if self._linstorapi and not is_interactive:
                self._linstorapi.disconnect()

        return rc

    @staticmethod
    def parser_cmds(parser):
        # AFAIK there is no other way to get the subcommands out of argparse.
        # This avoids at least to manually keep track of subcommands

        cmds = dict()
        subparsers_actions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
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
                if cmd.startswith("create-") or cmd.startswith("delete-"):
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

    def check_parser_commands(self):

        parser_cmds = LinStorCLI.parser_cmds(self._parser)
        for cmd in parser_cmds:
            mcos = [x for x in cmd if x in Commands.MainList + Commands.Hidden]
            if len(mcos) != 1:
                raise AssertionError("no main command found for group: " + str(cmd))

        all_cmds = [y for x in parser_cmds for y in x]
        for cmd in Commands.MainList + Commands.Hidden:
            if cmd not in all_cmds:
                raise AssertionError("defined command not used in argparse: " + str(cmd))

        return True

    @staticmethod
    def get_commands(parser, with_aliases=True):
        cmds = []
        for cmd in LinStorCLI.parser_cmds(parser):
            cmds.append(cmd[0])
            if with_aliases:
                for al in cmd[1:]:
                    cmds.append(al)
        return cmds

    @staticmethod
    def get_command_aliases(all_commands, cmd):
        return [x for subx in all_commands if cmd in subx for x in subx if cmd not in x]

    @staticmethod
    def gen_cmd_tree(subp):
        cmd_map = {}
        for cmd in subp._name_parser_map:
            argparse_cmd = subp._name_parser_map[cmd]
            new_subp = argparse_cmd._actions[-1]
            if isinstance(new_subp, argparse._SubParsersAction):
                if argparse_cmd.prog in cmd_map:
                    cmd_map[argparse_cmd.prog] =\
                        (cmd_map[argparse_cmd.prog][0] + [cmd], LinStorCLI.gen_cmd_tree(new_subp))
                else:
                    cmd_map[argparse_cmd.prog] = ([cmd], LinStorCLI.gen_cmd_tree(new_subp))
            else:
                if argparse_cmd.prog in cmd_map:
                    cmd_map[argparse_cmd.prog] = (cmd_map[argparse_cmd.prog][0] + [cmd], {})
                else:
                    cmd_map[argparse_cmd.prog] = ([cmd], {})

        return cmd_map

    @staticmethod
    def print_cmd_tree(entry, indent=0):
        for fullcmd in sorted(entry.keys()):
            cmd = fullcmd[fullcmd.rindex(' '):].strip()
            aliases, sub_cmds = entry[fullcmd]
            p_str = cmd
            if len(aliases) > 1:
                p_str += " ({al})".format(al=sorted(aliases, key=len)[0])
            print(" " * indent + "- " + p_str)
            LinStorCLI.print_cmd_tree(sub_cmds, indent + 2)

    def cmd_list(self, args):
        return self.print_cmds(args.tree)

    def print_cmds(self, tree=False):
        sys.stdout.write('Use "help <command>" to get help for a specific command.\n\n')
        sys.stdout.write('Available commands:\n')
        # import pprint
        # pp = pprint.PrettyPrinter()
        # pp.pprint(self._all_commands)

        if tree:
            subp = self._parser._actions[-1]
            assert (isinstance(subp, argparse._SubParsersAction))
            cmd_map = LinStorCLI.gen_cmd_tree(subp)
            LinStorCLI.print_cmd_tree(
                {k: v for k, v in cmd_map.items() if k[k.rindex(' '):].strip() in Commands.MainList}
            )
        else:
            for cmd in sorted(Commands.MainList):
                sys.stdout.write("- " + cmd)
                aliases = LinStorCLI.get_command_aliases(self._all_commands, cmd)
                if aliases:
                    sys.stdout.write(" (%s)" % (", ".join(aliases)))
                sys.stdout.write("\n")

        return 0

    def cmd_interactive(self, args):
        if self._state_service.has_state():
            sys.stderr.write("The client is already running in interactive mode\n")
        else:
            self.print_cmds()
            sys.stdout.write("\n")
            self._state_service.enter_state(DefaultState(), verbose=args.verbose)

    def run_interactive(self, verbose):
        all_cmds = [i for sl in self._all_commands for i in sl]

        # helper function
        def unknown(cmd):
            sys.stdout.write("\n" + "Command \"%s\" not known!\n" % cmd)
            self.print_cmds()

        # helper function
        def parsecatch(cmds_):
            rc = ExitCode.OK

            # remove linstor if cmd started with it
            if cmds_ and cmds_[0] == 'linstor':
                cmds_ = cmds_[1:]

            try:
                cmds_clone = list(cmds_)
                rc = self.parse_and_execute(cmds_, is_interactive=True)
            except SystemExit as se:
                cmd = cmds_clone[0]
                if cmd in [Commands.EXIT, "quit"]:
                    sys.exit(ExitCode.OK)
                elif cmd == "help":
                    if len(cmds_clone) == 1:
                        self.print_cmds()
                        return
                    else:
                        cmd = cmds_clone[1]
                        if cmd not in all_cmds:
                            unknown(cmd)
                elif cmd in all_cmds:
                    if '-h' in cmds_clone or '--help' in cmds:
                        return
                    if se.code == ExitCode.ARGPARSE_ERROR:
                        sys.stderr.write("\nIncorrect syntax. Use 'help {cmd}' for more information:\n".format(cmd=cmd))
                        rc = ExitCode.ARGPARSE_ERROR
                else:
                    unknown(cmd)
                    rc = ExitCode.ARGPARSE_ERROR
            except KeyboardInterrupt:
                pass
            except BaseException:
                traceback.print_exc(file=sys.stderr)

            if rc == ExitCode.CONNECTION_ERROR:
                sys.exit(rc)

            return rc

        # try to load readline
        # if loaded, raw_input makes use of it
        if sys.version_info < (3,):
            my_input = raw_input
        else:
            my_input = input

        abs_readline_hist_path = None
        try:
            import readline
            # seems after importing readline it is not possible to output to sys.stderr
            completer = argcomplete.CompletionFinder(self._parser)
            readline.set_completer_delims("")
            readline.set_completer(completer.rl_complete)
            readline.parse_and_bind("tab: complete")
            abs_readline_hist_path = os.path.expanduser(self.readline_history_file)
            if os.path.exists(abs_readline_hist_path):
                readline.read_history_file(abs_readline_hist_path)
        except ImportError:
            pass

        last_rc = ExitCode.OK
        while self._state_service.has_state():
            try:
                cmds = my_input('{state.prompt}{h} ==> '.format(
                    state=self._state_service.get_state(),
                    h='(' + self._linstorapi.controller_host() + ')' if verbose else ""
                )).strip()

                cmds = [cmd.strip() for cmd in cmds.split()]
                if not cmds:
                    self.print_cmds()
                else:
                    last_rc = parsecatch(cmds)

                if last_rc != ExitCode.OK:
                    while self._state_service.has_state() and self._state_service.get_state().terminate_on_error:
                        self._state_service.pop_state()
            except EOFError:  # raised by ctrl-d
                self._state_service.pop_state()
            except KeyboardInterrupt:  # raised by ctrl-c
                self._state_service.clear_state()
            sys.stdout.write("\n")

        if abs_readline_hist_path:
            try:
                os.makedirs(os.path.dirname(abs_readline_hist_path))
            except OSError:
                pass
            readline.write_history_file(abs_readline_hist_path)

        return last_rc

    def cmd_help(self, args):
        return self.parse_and_execute(args.command + ["-h"])

    def cmd_exit(self, _):
        sys.exit(ExitCode.OK)

    def run(self):
        # TODO(rck): try/except
        rc = self.parse_and_execute(sys.argv[1:])
        sys.exit(rc)

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
