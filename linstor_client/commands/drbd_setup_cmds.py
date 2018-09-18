import linstor_client.argparse.argparse as argparse
from linstor_client.utils import rangecheck, filter_new_args
from linstor.drbdsetup_options import drbd_options
import linstor.sharedconsts as apiconsts
from linstor import SizeCalc


class DrbdOptions(object):
    _options = drbd_options
    unsetprefix = 'unset'

    _CategoyMap = {
        'new-peer': apiconsts.NAMESPC_DRBD_NET_OPTIONS,
        'disk-options': apiconsts.NAMESPC_DRBD_DISK_OPTIONS,
        'resource-options': apiconsts.NAMESPC_DRBD_RESOURCE_OPTIONS,
        'peer-device-options': apiconsts.NAMESPC_DRBD_PEER_DEVICE_OPTIONS
    }

    @staticmethod
    def description(_type):
        return "Set drbd {t} options.  Use --unset-[option_name] to unset.".format(t=_type)

    @classmethod
    def drbd_options(cls):
        return cls._options

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

    @classmethod
    def add_arguments(cls, parser, option_list):
        assert(len(option_list) > 0)
        options = DrbdOptions._options['options']
        for opt_key in sorted(option_list):
            option = options[opt_key]
            if opt_key in ['help', '_name']:
                continue
            if option['type'] == 'symbol':
                parser.add_argument('--' + opt_key, choices=option['symbols'])
            if option['type'] == 'boolean':
                parser.add_argument(
                    '--' + opt_key,
                    choices=['yes', 'no'],
                    help="yes/no (Default: %s)" % (option['default'])
                )
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
                if 'unit' in option and option['unit'] == 'bytes':
                    parser.add_argument(
                        '--' + opt_key,
                        type=str,
                        help="Range: [%d, %d]; Default: %d%s" % (min_, max_, default, unit)
                    )
                else:
                    parser.add_argument('--' + opt_key, type=rangecheck(min_, max_),
                                        help="Range: [%d, %d]; Default: %d%s" % (min_, max_, default, unit))
        for opt_key in sorted(option_list):
            if opt_key == 'help':
                continue
            else:
                parser.add_argument('--%s-%s' % (cls.unsetprefix, opt_key),
                                    action='store_true',
                                    help=argparse.SUPPRESS)

    @classmethod
    def filter_new(cls, args):
        """return a dict containing all non-None args"""
        return filter_new_args(cls.unsetprefix, args)

    @classmethod
    def parse_opts(cls, new_args):
        modify = {}
        deletes = []
        for arg in new_args:
            value = new_args[arg]
            is_unset = arg.startswith(cls.unsetprefix)
            prop_name = arg[len(cls.unsetprefix) + 1:] if is_unset else arg
            option = cls._options['options'][prop_name]
            category = option['category']

            namespace = cls._CategoyMap[category]
            key = namespace + '/' + prop_name
            if is_unset:
                deletes.append(key)
            else:
                if 'bytes' in option and option['unit'] == 'bytes':
                    value = SizeCalc.auto_convert(value, SizeCalc.UNIT_B)
                    if option['min'] < value < option['max']:
                        value = str(value)
                    else:
                        raise argparse.ArgumentTypeError(
                            prop_name + " value {v} is out of range [{mi}-{ma}]".format(
                                v=value,
                                mi=option['min'],
                                ma=option['max']
                            )
                        )
                modify[key] = str(value)

        return modify, deletes
