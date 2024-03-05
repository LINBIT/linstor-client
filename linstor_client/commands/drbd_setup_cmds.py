import linstor_client.argparse.argparse as argparse
from linstor_client.utils import rangecheck, filter_new_args
from linstor.properties import properties
from linstor_client.commands import ArgumentError
from linstor import SizeCalc, LinstorError


def _drbd_options():
    drbd_options = {}
    for object_name, options in properties.items():
        object_drbd_options = {}
        for option in options:
            opt_key = option.get('drbd_option_name')
            if opt_key is None or opt_key in ['help', '_name']:
                continue
            if option['key'].startswith('DrbdOptions/Handlers'):
                opt_key = "handler-" + opt_key
            object_drbd_options[opt_key] = option
        drbd_options[object_name] = object_drbd_options
    return drbd_options


class DrbdOptions(object):
    drbd_options = _drbd_options()

    CLASH_OPTIONS = ["timeout"]

    unsetprefix = 'unset'

    @staticmethod
    def description(_type):
        return "Set DRBD {t} options on the given LINSTOR object. Use --unset-[option_name] to unset.".format(t=_type)

    @staticmethod
    def numeric_symbol(_min, _max, _symbols):
        def foo(x):
            try:
                i = int(x)
                if i not in range(_min, _max):
                    raise ArgumentError("{v} not in range [{min}-{max}].".format(v=i, min=_min, max=_max))
                return i
            except ValueError:
                pass
            if x not in _symbols:
                raise ArgumentError("'{v}' must be one of {s}.".format(v=x, s=_symbols))
            return x

        return foo

    @classmethod
    def unit_str(cls, unit, unit_prefix):
        """

        :param str unit:
        :param str unit_prefix:
        :return: String correctly describing the unit
        """
        if unit_prefix == 'k' and unit == "bytes/second":
            return 'KiB/s'
        return unit

    @classmethod
    def add_arguments(cls, parser, object_name, allow_unset=True):
        for opt_key, option in sorted(cls.drbd_options[object_name].items(), key=lambda k: k[0]):
            if opt_key in cls.CLASH_OPTIONS:
                opt_key = "drbd-" + opt_key
            if option['type'] == 'symbol':
                parser.add_argument('--' + opt_key, choices=option['values'])
            elif option['type'] == 'boolean':
                parser.add_argument(
                    '--' + opt_key,
                    choices=['yes', 'no'],
                    type=str.lower,
                    help="yes/no (Default: %s)" % (option['default'])
                )
            elif option['type'] == 'string':
                parser.add_argument('--' + opt_key)
            elif option['type'] == 'numeric-or-symbol':
                min_ = int(option['min'])
                max_ = int(option['max'])
                parser.add_argument(
                    '--' + opt_key,
                    type=DrbdOptions.numeric_symbol(min_, max_, option['values']),
                    help="Integer between [{min}-{max}] or one of ['{syms}']".format(
                        min=min_,
                        max=max_,
                        syms="','".join(option['values'])
                    )
                )
            elif option['type'] == 'range':
                min_ = option['min']
                max_ = option['max']
                default = option['default']
                unit = ""
                if "unit" in option:
                    unit = "; Unit: " + cls.unit_str(option['unit'], option['unit_prefix'])
                # sp.add_argument('--' + opt, type=rangecheck(min_, max_),
                #                 default=default, help="Range: [%d, %d]; Default: %d" %(min_, max_, default))
                # setting a default sets the option to != None, which makes
                # filterNew relatively complex
                if DrbdOptions._is_byte_unit(option):
                    parser.add_argument(
                        '--' + opt_key,
                        type=str,
                        help="Range: [%d%s, %d%s]; Default: %s%s" % (
                            min_, option.get('unit_prefix', ''),
                            max_, option.get('unit_prefix', ''), str(default), unit)
                    )
                else:
                    parser.add_argument('--' + opt_key, type=rangecheck(min_, max_),
                                        help="Range: [%d, %d]; Default: %s%s" % (min_, max_, str(default), unit))
            else:
                raise LinstorError('Unknown option type ' + option['type'])

            if allow_unset:
                parser.add_argument('--%s-%s' % (cls.unsetprefix, opt_key),
                                    action='store_true',
                                    help=argparse.SUPPRESS)

    @classmethod
    def filter_new(cls, args):
        """return a dict containing all non-None args"""
        return filter_new_args(cls.unsetprefix, args)

    @classmethod
    def _is_byte_unit(cls, option):
        return option.get('unit') in ['bytes', 'bytes/second'] or option['drbd_option_name'] in [
            'al-extents', 'max-io-depth', 'congestion-extents', 'max-buffers'
        ]  # the named options are thought to make sense here, even they are not directly bytes

    @classmethod
    def parse_opts(cls, new_args, object_name):
        modify = {}
        deletes = []
        for arg in new_args:
            is_unset = arg.startswith(cls.unsetprefix)
            value = new_args[arg]
            prop_name = arg[len(cls.unsetprefix) + 1:] if is_unset else arg
            if prop_name.startswith("drbd-") and prop_name[5:] in cls.CLASH_OPTIONS:
                prop_name = prop_name[5:]
            option = cls.drbd_options[object_name][prop_name]

            key = option['key']
            if is_unset:
                deletes.append(key)
            else:
                if DrbdOptions._is_byte_unit(option):
                    unit = SizeCalc.UNIT_B
                    if option.get('unit_prefix') == 'k':
                        unit = SizeCalc.UNIT_KiB
                    elif option.get('unit_prefix') == 's':
                        unit = SizeCalc.UNIT_S
                    value = SizeCalc.auto_convert(value, unit)
                    if option['min'] <= value <= option['max']:
                        value = str(value)
                    else:
                        raise ArgumentError(
                            prop_name + " value {v}{u} is out of range [{mi}-{ma}]".format(
                                v=value,
                                u=SizeCalc.unit_to_str(unit),
                                mi=str(option['min']) + option.get('unit_prefix', ''),
                                ma=str(option['max']) + option.get('unit_prefix', '')))
                modify[key] = str(value)

        return modify, deletes
