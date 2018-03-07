#!/usr/bin/env python2
"""
    LINSTOR - management of distributed storage/DRBD9 resources
    Copyright (C) 2013 - 2017  LINBIT HA-Solutions GmbH
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
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

# import locale
import linstor.argparse.argparse as argparse
import linstor.argcomplete as argcomplete
import linstor.linstorapi as linstorapi
from linstor.commcontroller import CommController
from linstor.commands import (
    VolumeDefinitionCommands,
    StoragePoolDefinitionCommands,
    StoragePoolCommands,
    ResourceDefinitionCommands,
    ResourceCommands,
    NodeCommands,
    MigrateCommands,
    DrbdOptions,
    ZshGenerator,
    Commands
)

from linstor.consts import (
    GITHASH,
    KEY_LS_CONTROLLERS,
    VERSION,
    ExitCode
)

from linstor import sharedconsts


class LinStorCLI(object):
    """
    linstor command line client
    """

    interactive=False

    def __init__(self):
        self._all_commands = None
        self._colors = True
        self._utf8 = True

        self._node_commands = NodeCommands()
        self._storage_pool_dfn_commands = StoragePoolDefinitionCommands()
        self._storage_pool_commands = StoragePoolCommands()
        self._resource_dfn_commands = ResourceDefinitionCommands()
        self._volume_dfn_commands = VolumeDefinitionCommands()
        self._resource_commands = ResourceCommands()
        self._parser = self.setup_parser()
        self._all_commands = self.parser_cmds(self._parser)
        self._linstorapi = None

    def setup_parser(self):
        parser = argparse.ArgumentParser(prog="linstor")
        parser.add_argument('--version', '-v', action='version',
                            version='%(prog)s ' + VERSION + '; ' + GITHASH)
        parser.add_argument('--no-color', action="store_true",
                            help='Do not use colors in output. Useful for old terminals/scripting.')
        parser.add_argument('--no-utf8', action="store_true",
                            help='Do not use utf-8 characters in output (i.e., tables).')
        parser.add_argument('--warn-as-error', action="store_true",
                            help='Treat WARN return code as error (i.e., return code > 0).')
        parser.add_argument('--controllers', default='localhost:%d' % sharedconsts.DFLT_CTRL_PORT_PLAIN,
                            help='Comma separated list of controllers (e.g.: "host1:port,host2:port"). '
                            'If the environment variable %s is set, '
                            'the ones set via this argument get appended.' % KEY_LS_CONTROLLERS)
        parser.add_argument('-m', '--machine-readable', action="store_true")
        parser.add_argument('-t', '--timeout', default=20, type=int,
                            help="Connection timeout value.")
        parser.add_argument('--disable-config', action="store_true",
                            help="Disable config loading and only use commandline arguments.")

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
        p_help.add_argument('command')
        p_help.set_defaults(func=self.cmd_help)

        # list
        p_list = subp.add_parser(Commands.LIST_COMMANDS, aliases=['commands', 'list'],
                                 description='List available commands')
        p_list.set_defaults(func=self.cmd_list)

        # exit
        p_exit = subp.add_parser(Commands.EXIT, aliases=['quit'],
                                 description='Only useful in interactive mode')
        p_exit.set_defaults(func=self.cmd_exit)

        # add all node commands
        self._node_commands.setup_commands(subp)

        # new-resource definition
        self._resource_dfn_commands.setup_commands(subp)

        # add all resource commands
        self._resource_commands.setup_commands(subp)

        # add all storage pool definition commands
        self._storage_pool_dfn_commands.setup_commands(subp)

        # add all storage pools commands
        self._storage_pool_commands.setup_commands(subp)

        # add all volume definition commands
        self._volume_dfn_commands.setup_commands(subp)

        # controller - get props
        c_ctrl_props = subp.add_parser(Commands.GET_CONTROLLER_PROPS,
                                       aliases=['dspctrlprp'],
                                       description='Print current controller config properties.')
        c_ctrl_props.set_defaults(func=Commands.cmd_print_controller_props)

        #  controller - set props
        c_set_ctrl_props = subp.add_parser(Commands.SET_CONTROLLER_PROP,
                                           aliases=['setctrlprp'],
                                           description='Set a controller config property.')
        Commands.add_parser_keyvalue(c_set_ctrl_props, "controller")
        c_set_ctrl_props.set_defaults(func=Commands.cmd_set_controller_props)

        # shutdown
        c_shutdown = subp.add_parser(
            Commands.SHUTDOWN,
            aliases=['shtdwn'],
            description='Shutdown the linstor controller'
        )
        c_shutdown.set_defaults(func=Commands.cmd_shutdown)

        # dm-migrate
        c_dmmigrate = subp.add_parser(
            Commands.DMMIGRATE,
            description='Generate a migration script from drbdmanage to linstor'
        )
        c_dmmigrate.add_argument('ctrlvol', help='json dump generated by "drbdmanage export-ctrlvol"')
        c_dmmigrate.add_argument('script', help='file name of the generated migration shell script')
        c_dmmigrate.set_defaults(func=MigrateCommands.cmd_dmmigrate)

        # drbd options
        #drbd_options = DrbdOptions()
        #drbd_options.setup_commands(subp)

        # zsh completer
        zsh_generator = ZshGenerator(subp)
        zsh_compl = subp.add_parser(
            Commands.GEN_ZSH_COMPLETER,
            description='Generate a zsh completion script'
        )
        zsh_compl.set_defaults(func=zsh_generator.cmd_completer)

        argcomplete.autocomplete(parser)

        subp.metavar = "{%s}" % ", ".join(Commands.MainList)

        return parser

    @staticmethod
    def read_config(config_file):
        cp = configparser.SafeConfigParser()
        cp.read(config_file)
        config = {}
        for section in cp.sections():
            config[section] = cp.items(section)
        return config

    @staticmethod
    def merge_config_arguments(pargs):
        home_dir = os.path.expanduser("~")
        config_file_name = "linstor-client.conf"
        user_conf = os.path.join(home_dir, ".config", "linstor", config_file_name)
        sys_conf = os.path.join('/etc', 'linstor', config_file_name)

        entries = None
        if os.path.exists(user_conf):
            entries = LinStorCLI.read_config(user_conf)
        elif os.path.exists(sys_conf):
            entries = LinStorCLI.read_config(sys_conf)

        if entries:
            global_entries = entries.get('global', [])
            for key, val in global_entries:
                pargs.insert(0, "--" + key)
                if val:
                    pargs.insert(1, val)
        return pargs

    def parse(self, pargs):
        # read global options from config file
        if '--disable-config' not in pargs:
            pargs = LinStorCLI.merge_config_arguments(pargs)
        return self._parser.parse_args(pargs)

    def parse_and_execute(self, pargs):
        args = self.parse(pargs)
        self._linstorapi = linstorapi.Linstor(CommController.controller_list(args.controllers)[0])
        self._node_commands._linstor = self._linstorapi
        self._storage_pool_dfn_commands._linstor = self._linstorapi
        self._storage_pool_commands._linstor = self._linstorapi
        self._resource_dfn_commands._linstor = self._linstorapi
        self._volume_dfn_commands._linstor = self._linstorapi
        self._resource_commands._linstor = self._linstorapi
        self._linstorapi.connect()
        return args.func(args)

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

    def cmd_list(self, args):
        sys.stdout.write('Use "help <command>" to get help for a specific command.\n\n')
        sys.stdout.write('Available commands:\n')
        # import pprint
        # pp = pprint.PrettyPrinter()
        # pp.pprint(self._all_commands)
        for cmd in Commands.MainList:
            sys.stdout.write("- " + cmd)
            aliases = LinStorCLI.get_command_aliases(self._all_commands, cmd)
            if aliases:
                sys.stdout.write(" (%s)" % (", ".join(aliases)))
            sys.stdout.write("\n")
        return 0

    def cmd_interactive(self, args):
        all_cmds = [i for sl in self._all_commands for i in sl]

        # helper function
        def unknown(cmd):
            sys.stdout.write("\n" + "Command \"%s\" not known!\n" % cmd)
            self.cmd_list(args)

        # helper function
        def parsecatch(cmds_, stoprec=False):
            try:
                self.parse_and_execute(cmds_)
            except SystemExit as se:
                if stoprec:
                    return

                cmd = cmds_[0]
                if cmd in ["exit", "quit"]:
                    sys.exit(ExitCode.OK)
                elif cmd == "help":
                    if len(cmds_) == 1:
                        self.cmd_list(args)
                        return
                    else:
                        cmd = " ".join(cmds_[1:])
                        if cmd not in all_cmds:
                            unknown(cmd)
                elif cmd in all_cmds:
                    if '-h' in cmds_ or '--help' in cmds:
                        return
                    if se.code == ExitCode.ARGPARSE_ERROR:
                        sys.stdout.write("\nIncorrect syntax. Use the command as follows:\n")
                        parsecatch(["help", cmd], stoprec=True)
                else:
                    unknown(cmd)
            except BaseException:
                traceback.print_exc(file=sys.stdout)

        # main part of interactive mode:
        if not LinStorCLI.interactive:
            LinStorCLI.interactive = True

            # try to load readline
            # if loaded, raw_input makes use of it
            if sys.version_info < (3,):
                my_input = raw_input
            else:
                my_input = input

            try:
                import readline
                # seems after importing readline it is not possible to output to sys.stderr
                completer = argcomplete.CompletionFinder(self._parser)
                readline.set_completer_delims("")
                readline.set_completer(completer.rl_complete)
                readline.parse_and_bind("tab: complete")
            except ImportError:
                pass

            self.cmd_list(args)
            while True:
                try:
                    sys.stdout.write("\n")
                    cmds = my_input('LINSTOR ==> ').strip()

                    cmds = [cmd.strip() for cmd in cmds.split()]
                    if not cmds:
                        self.cmd_list(args)
                    else:
                        parsecatch(cmds)
                except (EOFError, KeyboardInterrupt):  # raised by ctrl-d, ctrl-c
                    sys.stdout.write("\n")  # additional newline, makes shell prompt happy
                    break
            LinStorCLI.interactive = False
        else:
            sys.stderr.write("The client is already running in interactive mode\n")


    def cmd_help(self, args):
        return self.parse_and_execute([args.command, "-h"])

    def cmd_exit(self, _):
        sys.exit(ExitCode.OK)

    def run(self):
        # TODO(rck): try/except
        sys.exit(self.parse_and_execute(sys.argv[1:]))

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
