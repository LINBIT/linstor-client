from .commands import Commands

_header = """#compdef linstor_client_main.py linstor
#autoload

# ------------------------------------------------------------------------------
# Description
# -----------
#
#  Completion script for linstor-client
#
# ------------------------------------------------------------------------------
# Authors
# -------
#
#  * Rene Peinthor <rene.peinthor@linbit.com>
#
# ------------------------------------------------------------------------------

_linstor() {
  local context curcontext="$curcontext" state line
  typeset -A opt_args

  local ret=1

  _arguments -C '--no-utf8[No UTF8 characters in output]' '--no-color[Do not use color output]' \
    '--machine-readable[Output in json format]' '--version[Show version]' '--disable-config[Disable config loading]' \
    '--help[Show help]' '--timeout[Timeout in seconds]: :()' '--controllers[list of controllers to try]: :()' \
    '1: :_linstor_cmds' \
    '*::arg:->args' \
  && ret=0

  case $state in
    (args)
      curcontext="${curcontext%:*:*}:linstor-cmd-$words[1]:"
      case $line[1] in
"""

_mid = """        *)
          _call_function ret _linstor_cmd_$words[1] && ret=0
          (( ret )) && _message 'no more arguments'
        ;;
      esac
    ;;
  esac
}

(( $+functions[_linstor_cmds] )) ||
_linstor_cmds() {
  local commands; commands=("""

_footer = """  )
  _describe -t commands 'linstor command' commands "$@"
}

_linstor "$@"

# Local Variables:
# mode: Shell-Script
# sh-indentation: 2
# indent-tabs-mode: nil
# sh-basic-offset: 2
# End:
# vim: ft=zsh sw=2 ts=2 et
"""


class ZshGenerator(object):
    def __init__(self, parser):
        self._parser = parser

    def cmd_completer(self, args):
        print(_header)
        for cmd in Commands.MainList:
            print(self.cmd(cmd))
        print(_mid)
        print(self.cmds_list_str())
        print(_footer)

    def describe_cmds(self, cmd, indent=0):
        argparse_cmd = self._parser._name_parser_map[cmd]
        safe_str = cmd.replace('-', '_')
        c = " " * indent + "local {cmd}_cmds;\n".format(cmd=safe_str)
        c += " " * indent + "{cmd}_cmds=(\n".format(cmd=safe_str)
        for action in argparse_cmd._actions:
            subcmds = action.choices if action.choices else []
            for subcmd in subcmds:
                c += " " * indent + "  '{subcmd}:'\n".format(subcmd=subcmd)
        c += " " * indent + ")\n"
        c += " " * indent + "_describe -t {cmd}_cmds '{cmd} cmds' {cmd}_cmds \"$@\" && ret=0\n".format(cmd=safe_str)
        return c

    @classmethod
    def arguments_str(cls, argparse_cmd):
        c = ""
        opts = []
        for action in argparse_cmd._actions:
            if action.option_strings:
                # get longest option string
                optstr = sorted(action.option_strings, key=len, reverse=True)[0]
                helptxt = action.help.replace("'", "''") if action.help else ' '
                helptxt = helptxt.replace(":", "\\:")
                opt_data = [optstr, helptxt]
                if action.choices:
                    opt_data.append("(" + " ".join(action.choices) + ")")
                opts.append("'" + ':'.join(opt_data) + "'")
            else:  # positional
                opt_data = ['', action.dest]
                if action.choices:
                    opt_data.append("(" + " ".join(action.choices) + ")")
                else:
                    opt_data.append("()")
                opts.append("'" + ':'.join(opt_data) + "'")
        if opts:
            c += "_arguments " + " ".join(opts) + " && ret=0\n"
        return c

    def cmd(self, cmd):
        c = "        ({cmd})\n".format(cmd=cmd)
        c += "          case $line[2] in\n"
        # argparse_cmd = self._parser._name_parser_map[cmd]
        # for action in argparse_cmd._actions:
        #     subcmds = action.choices if action.choices else []
        #     for subcmd in subcmds:
        #         c += "            ({subcmd})\n".format(subcmd=subcmd)
        #         c += "              " + self.arguments_str(action.choices[subcmd])
        #         c += "            ;;\n"
        c += "            *)\n"
        c += self.describe_cmds(cmd, indent=14)
        c += "            ;;\n"
        c += "          esac\n"
        # c += self.arguments_str(argparse_cmd)
        c += "        ;;"
        return c

    def cmds_list_str(self):
        tuples = []
        for x in Commands.MainList:
            cmd = self._parser._name_parser_map[x]
            desc = cmd.description if cmd.description else ""
            shortlen = 40
            if desc and len(desc) > shortlen:
                desc = desc[:shortlen - 3] + '...'
            tuples.append((x, desc))
        return "\n    ".join(["'" + x[0] + ':' + x[1] + "'" for x in tuples])
