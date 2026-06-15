#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
    LINSTOR - management of distributed storage/DRBD9 resources
    Copyright (C) 2013 - 2026  LINBIT HA-Solutions GmbH
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
import platform
import io
import shlex
import signal
import subprocess as sp
import traceback
import itertools
import getpass
from contextlib import contextmanager

import linstor
import argparse
try:
    import argcomplete
except ImportError:
    pass

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
    AdviceCommands,
    ZshGenerator,
    EncryptionCommands,
    SosReportCommands,
    SpaceReportingCommands,
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


def _get_pager_cmd():
    """
    Resolve the pager command from environment or fall back to 'less'.
    Returns None if paging should be disabled (empty LINSTOR_PAGER).
    """
    cmd = os.environ.get('LINSTOR_PAGER')
    if cmd is not None:
        return cmd if cmd else None
    cmd = os.environ.get('PAGER')
    if cmd is not None:
        return cmd if cmd else None
    return 'less'


@contextmanager
def setup_pager():
    """
    Context manager that redirects stdout to a pager subprocess.
    Sets LESS=-RFX if not already set so that colors are preserved,
    short output is printed directly, and the screen is not cleared.
    """
    pager_cmd = _get_pager_cmd()
    if pager_cmd is None or not sys.stdout.isatty():
        yield
        return

    # Capture terminal size before stdout becomes a pipe, so that
    # shutil.get_terminal_size() still returns the real width.
    if 'COLUMNS' not in os.environ:
        try:
            columns = os.get_terminal_size(sys.stdout.fileno()).columns
            os.environ['COLUMNS'] = str(columns)
        except (ValueError, OSError):
            pass

    env = os.environ.copy()
    if 'LESS' not in env:
        env['LESS'] = '-RFX'

    old_stdout = sys.stdout

    try:
        proc = sp.Popen(
            shlex.split(pager_cmd),
            stdin=sp.PIPE,
            env=env
        )
    except FileNotFoundError:
        # Pager binary not found — fall back to direct output
        yield
        return

    # Restore default SIGPIPE handling so the process terminates
    # silently when the user quits the pager, instead of raising
    # BrokenPipeError exceptions.
    #
    # No SIGPIPE on Windows:
    if platform.system() != "Windows":
        old_sigpipe = signal.getsignal(signal.SIGPIPE)
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    sys.stdout = io.TextIOWrapper(proc.stdin, encoding=old_stdout.encoding or 'utf-8')
    try:
        yield
    except BrokenPipeError:
        pass
    finally:
        try:
            sys.stdout.flush()
            sys.stdout.close()
        except BrokenPipeError:
            pass
        sys.stdout = old_stdout
        if platform.system() != "Windows":
            signal.signal(signal.SIGPIPE, old_sigpipe)
        proc.wait()


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


class _LazyParserMap(dict):
    """Dict subclass that materializes lazy parsers on __getitem__ access.

    Used as a drop-in replacement for argparse's _name_parser_map/choices dict.
    Lazy entries are stored as callables (factory functions) and replaced with
    real ArgumentParser instances when first accessed by name.
    """

    def __getitem__(self, key):
        value = super(_LazyParserMap, self).__getitem__(key)
        if callable(value):
            value()
            # factory called setup_commands() which called add_parser(),
            # replacing the callable with the real parser
            value = super(_LazyParserMap, self).__getitem__(key)
        return value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def values(self):
        for key in list(super(_LazyParserMap, self).keys()):
            value = super(_LazyParserMap, self).__getitem__(key)
            if callable(value):
                value()
        return super(_LazyParserMap, self).values()

    def items(self):
        for key in list(super(_LazyParserMap, self).keys()):
            value = super(_LazyParserMap, self).__getitem__(key)
            if callable(value):
                value()
        return super(_LazyParserMap, self).items()


class _LazySubParsersAction(argparse._SubParsersAction):
    """SubParsersAction that supports lazy command registration."""

    def __init__(self, *args, **kwargs):
        super(_LazySubParsersAction, self).__init__(*args, **kwargs)
        lazy_map = _LazyParserMap(self._name_parser_map)
        self._name_parser_map = lazy_map
        # choices is used by argparse for validation and help;
        # it must be the same object as _name_parser_map
        self.choices = lazy_map

    def add_parser(self, name, **kwargs):
        # Remove any lazy entry before registering the real parser,
        # so argparse doesn't raise "conflicting subparser"
        existing = dict.get(self._name_parser_map, name)
        if callable(existing):
            aliases = kwargs.get('aliases', ())
            dict.__delitem__(self._name_parser_map, name)
            for alias in aliases:
                if dict.get(self._name_parser_map, alias) is existing:
                    dict.__delitem__(self._name_parser_map, alias)
        return super(_LazySubParsersAction, self).add_parser(name, **kwargs)

    def add_lazy_command(self, name, aliases, description, factory):
        self._name_parser_map[name] = factory
        for alias in aliases:
            self._name_parser_map[alias] = factory
        # Register a pseudo-action so the command appears in --help output
        self._choices_actions.append(
            self._ChoicesPseudoAction(name, aliases, description)
        )


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
        self._encryption_commands = EncryptionCommands()
        self._sos_report_commands = SosReportCommands()
        self._space_reporting_commands = SpaceReportingCommands()
        self._physical_storage_commands = PhysicalStorageCommands()
        self._error_report_commands = ErrorReportCommands()
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
            self._advise_commands,
            self._backup_commands,
            self._remote_commands,
            self._file_commands,
            self._encryption_commands,
            self._sos_report_commands,
            self._space_reporting_commands,
            self._schedule_commands,
            self._key_value_store_commands
        ]

        self._dflt_ctrl = 'localhost:%d' % linstor.Linstor.REST_PORT

        self._zsh_generator = None
        self._parser = self.setup_parser()
        self._all_commands = None
        self._linstorapi = None  # type: Optional[linstor.Linstor]

    @property
    def all_commands(self):
        if self._all_commands is None:
            self._all_commands = self.parser_cmds(self._parser)
        return self._all_commands

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
        parser.add_argument('--no-pager', action="store_true",
                            help='Do not pipe output into a pager.')
        parser.add_argument('--no-utf8', action="store_true", default=False,
                            help='Do not use utf-8 characters in output (i.e., tables).')
        parser.add_argument('--utf8', action="store_false", dest="no_utf8",
                            default=argparse.SUPPRESS,
                            help='Use utf-8 characters in output (i.e., tables). This is the default.')
        parser.add_argument('--warn-as-error', action="store_true",
                            help='Treat WARN return code as error (i.e., return code > 0).')
        parser.add_argument('--curl',
                            action="store_true",
                            help="Do not execute the action, only output a curl equivalent command.")
        parser.add_argument('--controllers', default=self._dflt_ctrl,
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
        parser.add_argument('--auth-token', help="Linstor Controller auth token")
        parser.add_argument(
            '--allow-insecure-auth',
            action='store_true',
            help="Allow password authentication with HTTP"
        )

        subp = parser.add_subparsers(title='subcommands',
                                     description='valid subcommands',
                                     action=_LazySubParsersAction,
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

        # Register all lazy commands. setup_commands() is only called when the
        # subcommand is actually invoked.
        for sub_cmd in self._command_list:
            if sub_cmd._command_name is not None:
                subp.add_lazy_command(
                    sub_cmd._command_name,
                    sub_cmd._command_aliases,
                    sub_cmd._command_description,
                    lambda c=sub_cmd: c.setup_commands(subp)
                )

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

        try:
            argcomplete.autocomplete(parser)
        except NameError:
            pass

        subp.metavar = "{%s}" % ", ".join(sorted(Commands.MainList))

        return parser

    # Per-command config keys that are read directly from the [global] section
    # (e.g. by Commands.add_truncate_args) and must not be injected as global
    # CLI flags here.
    _PER_COMMAND_GLOBAL_KEYS = {'truncate'}

    @staticmethod
    def merge_config_arguments(pargs):
        global_entries = linstor.Config.get_section('global')
        for key, val in global_entries.items():
            if key in LinStorCLI._PER_COMMAND_GLOBAL_KEYS:
                continue
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

            if vars(args).get('func') is None:
                raise ArgumentError("No subcommand specified")

            local_only_cmds = [
                self.cmd_list,
                MigrateCommands.cmd_dmmigrate,
                self._zsh_generator.cmd_completer,
                self.cmd_help
            ]

            # only connect if not already connected or a local only command was executed
            conn_errors = []
            ctrls = []
            if args.controllers != self._dflt_ctrl:
                ctrls.append(args.controllers)
            if os.environ.get(KEY_LS_CONTROLLERS):
                ctrls.append(os.environ.get(KEY_LS_CONTROLLERS))
            if not ctrls:
                ctrls.append(self._dflt_ctrl)
            contrl_list = linstor.MultiLinstor.controller_uri_list(','.join(ctrls))
            if self._linstorapi is None and vars(args).get("func") not in local_only_cmds:
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
                            agent_info="Client " + VERSION,
                            auth_token=args.auth_token,
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
                    use_pager = (
                        not is_interactive
                        and not args.machine_readable
                        and not args.no_pager
                    )
                    if use_pager:
                        with setup_pager():
                            rc = args.func(args)
                    else:
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
                aliases = LinStorCLI.get_command_aliases(self.all_commands, cmd)
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
        all_cmds = [i for sl in self.all_commands for i in sl]

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
        # if loaded, input makes use of it
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
        except (ImportError, NameError):
            pass

        last_rc = ExitCode.OK
        while self._state_service.has_state():
            try:
                cmds = input('{state.prompt}{h} ==> '.format(
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


# This enables colors in legacy windows terminals (cmd/powershell
# pre server 2025):

if platform.system() == "Windows":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except BaseException:
        pass


def main():
    try:
        LinStorCLI().run()
    except KeyboardInterrupt:
        sys.stderr.write("\nlinstor: Client exiting (received SIGINT)\n")
        return 1
    except BrokenPipeError:
        # sys.stderr.write("\nlinstor: Client exiting (received BrokenPipeError)\n")
        return 1
    return 0


if __name__ == "__main__":
    main()
