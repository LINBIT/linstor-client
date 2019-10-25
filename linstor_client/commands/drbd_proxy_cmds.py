from __future__ import print_function

from linstor.sharedconsts import VAL_DRBD_PROXY_COMPRESSION_NONE, VAL_DRBD_PROXY_COMPRESSION_ZLIB, \
    VAL_DRBD_PROXY_COMPRESSION_LZMA, VAL_DRBD_PROXY_COMPRESSION_LZ4, VAL_DRBD_PROXY_COMPRESSION_ZSTD
import linstor_client.argparse.argparse as argparse
from linstor_client.commands import Commands, DrbdOptions, ArgumentError
from linstor_client.utils import rangecheck


class DrbdProxyCommands(Commands):
    OBJECT_NAME = 'drbd-proxy'
    OBJECT_NAME_LZMA = 'drbd-proxy-lzma'
    OBJECT_NAME_ZLIB = 'drbd-proxy-zlib'
    OBJECT_NAME_ZSTD = 'drbd-proxy-zstd'

    class Enable(object):
        LONG = "enable"
        SHORT = "e"

    class Disable(object):
        LONG = "disable"
        SHORT = "d"

    class Options(object):
        LONG = "options"
        SHORT = "opt"

    class Compression(object):
        LONG = "compression"
        SHORT = "c"

    class NoCompression(object):
        LONG = "none"
        SHORT = "none"

    class Zlib(object):
        LONG = "zlib"
        SHORT = "zlib"

    class Lzma(object):
        LONG = "lzma"
        SHORT = "lzma"

    class Lz4(object):
        LONG = "lz4"
        SHORT = "lz4"

    class Zstd(object):
        LONG = "zstd"
        SHORT = "zstd"

    def __init__(self):
        super(DrbdProxyCommands, self).__init__()

    def setup_commands(self, parser):
        subcmds = [
            self.Enable,
            self.Disable,
            self.Options,
            self.Compression
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
            type=str,
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
            type=str,
            help='Name of the resource'
        ).completer = self.resource_completer
        p_proxy_disable.set_defaults(func=self.disable)

        # drbd options
        p_drbd_opts = subp.add_parser(
            self.Options.LONG,
            aliases=[self.Options.SHORT],
            description=DrbdOptions.description("resource")
        )
        self._add_resource_name_argument(p_drbd_opts)
        DrbdOptions.add_arguments(p_drbd_opts, self.OBJECT_NAME)
        p_drbd_opts.set_defaults(func=self.set_drbd_opts)

        compression_subcmds = [
            self.NoCompression,
            self.Zlib,
            self.Lzma,
            self.Lz4,
            self.Zstd
        ]

        p_compression = subp.add_parser(
            self.Compression.LONG,
            aliases=[self.Compression.SHORT],
            formatter_class=argparse.RawTextHelpFormatter,
            description='DRBD Proxy compression subcommands. '
                        'Each subcommand overrides any previous compression configuration.'
        )
        compression_subp = p_compression.add_subparsers(
            title="DRBD Proxy compression options",
            metavar="",
            description=Commands.Subcommands.generate_desc(compression_subcmds)
        )

        p_compression_none = compression_subp.add_parser(
            self.NoCompression.LONG,
            aliases=[self.NoCompression.SHORT],
            description='Do not use compression.'
        )
        self._add_resource_name_argument(p_compression_none)
        p_compression_none.set_defaults(func=self.set_compression, compression_type=VAL_DRBD_PROXY_COMPRESSION_NONE)

        p_compression_zlib = compression_subp.add_parser(
            self.Zlib.LONG,
            aliases=[self.Zlib.SHORT],
            description='Use ZLIB compression. Options are reset to those given here.'
        )
        self._add_resource_name_argument(p_compression_zlib)
        DrbdOptions.add_arguments(p_compression_zlib, self.OBJECT_NAME_ZLIB, allow_unset=False)
        p_compression_zlib.set_defaults(func=self.set_compression, compression_type=VAL_DRBD_PROXY_COMPRESSION_ZLIB)

        p_compression_lzma = compression_subp.add_parser(
            self.Lzma.LONG,
            aliases=[self.Lzma.SHORT],
            description='Use LZMA compression. Options are reset to those given here.'
        )
        self._add_resource_name_argument(p_compression_lzma)
        DrbdOptions.add_arguments(p_compression_lzma, self.OBJECT_NAME_LZMA, allow_unset=False)
        p_compression_lzma.set_defaults(func=self.set_compression, compression_type=VAL_DRBD_PROXY_COMPRESSION_LZMA)

        p_compression_lz4 = compression_subp.add_parser(
            self.Lz4.LONG,
            aliases=[self.Lz4.SHORT],
            description='Use LZ4 compression.'
        )
        self._add_resource_name_argument(p_compression_lz4)
        p_compression_lz4.set_defaults(func=self.set_compression, compression_type=VAL_DRBD_PROXY_COMPRESSION_LZ4)

        p_compression_zstd = compression_subp.add_parser(
            self.Zstd.LONG,
            aliases=[self.Zstd.SHORT],
            description='Use ZStandard compression.'
        )
        self._add_resource_name_argument(p_compression_zstd)
        p_compression_zstd.set_defaults(func=self.set_compression, compression_type=VAL_DRBD_PROXY_COMPRESSION_ZSTD)

        self.check_subcommands(compression_subp, compression_subcmds)

        self.check_subcommands(subp, subcmds)

    def _add_resource_name_argument(self, parser):
        parser.add_argument(
            'resource_name',
            type=str,
            help="Resource name"
        ).completer = self.resource_dfn_completer

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

    def set_drbd_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']  # remove resource name key

        mod_props, del_props = DrbdOptions.parse_opts(a, self.OBJECT_NAME)

        replies = self._linstor.drbd_proxy_modify(
            args.resource_name,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)

    def set_compression(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']  # remove resource name key
        del a['compression-type']  # remove compression_type key

        if args.compression_type == VAL_DRBD_PROXY_COMPRESSION_NONE:
            set_props = {}
        elif args.compression_type == VAL_DRBD_PROXY_COMPRESSION_ZLIB:
            set_props, _ = DrbdOptions.parse_opts(a, self.OBJECT_NAME_ZLIB)
        elif args.compression_type == VAL_DRBD_PROXY_COMPRESSION_LZMA:
            set_props, _ = DrbdOptions.parse_opts(a, self.OBJECT_NAME_LZMA)
        elif args.compression_type == VAL_DRBD_PROXY_COMPRESSION_ZSTD:
            set_props, _ = DrbdOptions.parse_opts(a, self.OBJECT_NAME_ZSTD)
        elif args.compression_type == VAL_DRBD_PROXY_COMPRESSION_LZ4:
            set_props = {}
        else:
            raise ArgumentError("Unknown compression type")

        replies = self._linstor.drbd_proxy_modify(
            args.resource_name,
            compression_type=args.compression_type,
            compression_property_dict=set_props
        )
        return self.handle_replies(args, replies)
