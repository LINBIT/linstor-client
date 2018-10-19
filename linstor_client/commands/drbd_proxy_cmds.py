from __future__ import print_function

import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands
from linstor_client.consts import RES_NAME
from linstor_client.utils import namecheck, rangecheck


class DrbdProxyCommands(Commands):
    class Enable(object):
        LONG = "enable"
        SHORT = "e"

    class Disable(object):
        LONG = "disable"
        SHORT = "d"

    def __init__(self):
        super(DrbdProxyCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            self.Enable,
            self.Disable
        ]

        res_conn_parser = parser.add_parser(
            Commands.DRBD_PROXY,
            aliases=["proxy"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="DRBD Proxy subcommands")
        subp = res_conn_parser.add_subparsers(
            title="DRBD Proxy commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # enable proxy
        p_proxy_enable = subp.add_parser(
            self.Enable.LONG,
            aliases=[self.Enable.SHORT],
            description='Enables DRBD Proxy on a resource connection.')
        p_proxy_enable.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_proxy_enable.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        p_proxy_enable.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_completer
        p_proxy_enable.add_argument('-p', '--port', type=rangecheck(1, 65535))
        p_proxy_enable.set_defaults(func=self.enable)

        # disable proxy
        p_proxy_disable = subp.add_parser(
            self.Disable.LONG,
            aliases=[self.Disable.SHORT],
            description='Disables DRBD Proxy on a resource connection.')
        p_proxy_disable.add_argument(
            'node_name_a',
            help="Node name source of the connection.").completer = self.node_completer
        p_proxy_disable.add_argument(
            'node_name_b',
            help="Node name target of the connection.").completer = self.node_completer
        p_proxy_disable.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_completer
        p_proxy_disable.set_defaults(func=self.disable)

        self.check_subcommands(subp, subcmds)

    def enable(self, args):
        replies = self._linstor.drbd_proxy_enable(
            args.resource_name,
            args.node_name_a,
            args.node_name_b,
            args.port
        )
        return self.handle_replies(args, replies)

    def disable(self, args):
        replies = self._linstor.drbd_proxy_disable(
            args.resource_name,
            args.node_name_a,
            args.node_name_b
        )
        return self.handle_replies(args, replies)
