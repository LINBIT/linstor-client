import linstor.argparse.argparse as argparse
from linstor.utils import rangecheck, filter_new_args, namecheck
from linstor.commands import Commands
from linstor.consts import RES_NAME, ExitCode
from linstor.drbdsetup_options import drbd_options
import linstor.sharedconsts as apiconsts


class DrbdOptions(Commands):
    _options = drbd_options

    _CategoyMap = {
        'net-options': apiconsts.NAMESPC_DRBD_NET_OPTIONS,
        'disk-options': apiconsts.NAMESPC_DRBD_DISK_OPTIONS,
        'resource-options': apiconsts.NAMESPC_DRBD_RESOURCE_OPTIONS,
        'peer-device-options': apiconsts.NAMESPC_DRBD_PEER_DEVICE_OPTIONS
    }

    def __init__(self):
        super(DrbdOptions, self).__init__()
        self.unsetprefix = 'unset'

    @staticmethod
    def numeric_symbol(_min, _max, _symbols):
        def foo(x):
            try:
                i = int(x)
                if i not in range(_min, _max):
                    raise argparse.ArgumentTypeError("{v} not in range [{min}-{max}].".format(v=i, min=_min, max=_max))
                return i
            except ValueError as va:
                pass
            if x not in _symbols:
                raise argparse.ArgumentTypeError("'{v}' must be one of {s}.".format(v=x, s=_symbols))
            return x

        return foo

    def add_arguments(self, parser, option_list):

        def mybool(x):
            return x.lower() in ('y', 'yes', 't', 'true', 'on')

        options = DrbdOptions._options['options']
        for opt_key in option_list:
            option = options[opt_key]
            if opt_key in ['help', '_name']:
                continue
            if option['type'] == 'symbol':
                parser.add_argument('--' + opt_key, choices=option['symbols'])
            if option['type'] == 'boolean':
                parser.add_argument('--' + opt_key, type=mybool, help="yes/no (Default: %s)" % (option['default']))
            if option['type'] == 'string':
                parser.add_argument('--' + opt_key)
            if option['type'] == 'numeric-or-symbol':
                min_ = int(option['min'])
                max_ = int(option['max'])
                parser.add_argument(
                    '--' + opt_key,
                    type=DrbdOptions.numeric_symbol(min_, max_, option['symbols']),
                    help="Integer between [{min}-{max}] or one of ['{syms}']".format(
                        min=min_,
                        max=max_,
                        syms="','".join(option['symbols'])
                    )
                )
            if option['type'] == 'numeric':
                min_ = option['min']
                max_ = option['max']
                default = option['default']
                if "unit" in option:
                    unit = "; Unit: " + option['unit']
                else:
                    unit = ""
                # sp.add_argument('--' + opt, type=rangecheck(min_, max_),
                #                 default=default, help="Range: [%d, %d]; Default: %d" %(min_, max_, default))
                # setting a default sets the option to != None, which makes
                # filterNew relatively complex
                parser.add_argument('--' + opt_key, type=rangecheck(min_, max_),
                                    help="Range: [%d, %d]; Default: %d%s" % (min_, max_, default, unit))
        for opt_key in option_list:
            if opt_key == 'help':
                continue
            else:
                parser.add_argument('--%s-%s' % (self.unsetprefix, opt_key),
                                    action='store_true')

    def setup_commands(self, parser):
        common = parser.add_parser('drbd-options', description="Set common drbd options.")
        resource_cmd = parser.add_parser('drbd-resource-options', description="Set drbd resource options.")
        resource_cmd.add_argument(
            'resource',
            type=namecheck(RES_NAME),
            help="Resource name").completer = self.resource_completer

        volume_cmd = parser.add_parser('drbd-volume-options', description="Set drbd volume options.")
        volume_cmd.add_argument(
            'resource',
            type=namecheck(RES_NAME),
            help="Resource name").completer = self.resource_completer
        volume_cmd.add_argument(
            'volume_nr',
            type=int,
            help="Volume number"
        )

        options = DrbdOptions._options['options']
        self.add_arguments(common, options.keys())
        self.add_arguments(resource_cmd, [x for x in options if x in DrbdOptions._options['filters']['resource']])
        self.add_arguments(volume_cmd, [x for x in options if x in DrbdOptions._options['filters']['volume']])

        common.set_defaults(func=self._option_common)
        resource_cmd.set_defaults(func=self._option_resource)
        volume_cmd.set_defaults(func=self._option_volume)

        return True

    def filter_new(self, args):
        """return a dict containing all non-None args"""
        return filter_new_args(self.unsetprefix, args)

    def _parse_opts(self, new_args):
        modify = {}
        deletes = []
        for arg in new_args:
            is_unset = arg.startswith(self.unsetprefix)
            prop_name = arg[len(self.unsetprefix) + 1:] if is_unset else arg
            category = self._options['options'][prop_name]['category']

            namespace = self._CategoyMap[category]
            key = namespace + '/' + prop_name
            if is_unset:
                deletes.append(key)
            else:
                modify[key] = new_args[arg]

        return modify, deletes

    def _option_common(self, args):
        a = self.filter_new(args)

        mod_props, del_props = self._parse_opts(a)

        replies = []
        for prop, val in mod_props.items():
            replies.extend(self._linstor.controller_set_prop(prop, val))

        for delkey in del_props:
            replies.extend(self._linstor.controller_del_prop(delkey))

        return self.handle_replies(args, replies)

    def _option_resource(self, args):
        a = self.filter_new(args)
        del a['resource']  # remove resource name key

        mod_props, del_props = self._parse_opts(a)

        replies = self._linstor.resource_dfn_modify(
            args.resource,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)

    def _option_volume(self, args):
        a = self.filter_new(args)
        del a['resource']  # remove volume name key
        del a['volume-nr']

        mod_props, del_props = self._parse_opts(a)

        replies = self._linstor.volume_dfn_modify(
            args.resource,
            args.volume_nr,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)
