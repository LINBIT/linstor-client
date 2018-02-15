from linstor.utils import rangecheck, filter_new_args, namecheck
from linstor.commands import ResourceCommands
from linstor.consts import RES_NAME, ExitCode
from proto.MsgModRsc_pb2 import MsgModRsc
from linstor.drbdsetup_options import drbdoptions_raw
import sys
import pickle


class DrbdOptions(object):
    _options = pickle.loads(drbdoptions_raw.encode())

    def __init__(self):
        self.unsetprefix = 'unset'

    def setup_commands(self, parser):
        sp = parser.add_parser('drbd-options', description=DrbdOptions._options['help'])

        def mybool(x):
            return x.lower() in ('y', 'yes', 't', 'true', 'on')

        for opt in DrbdOptions._options:
            if opt == 'help':
                continue
            if DrbdOptions._options[opt]['type'] == 'handler':
                sp.add_argument('--' + opt, choices=DrbdOptions._options[opt]['handlers'])
            if DrbdOptions._options[opt]['type'] == 'boolean':
                sp.add_argument('--' + opt, type=mybool,
                                help="yes/no (Default: %s)" % (DrbdOptions._options[opt]['default']))
            if DrbdOptions._options[opt]['type'] == 'string':
                sp.add_argument('--' + opt)
            if DrbdOptions._options[opt]['type'] == 'numeric':
                min_ = DrbdOptions._options[opt]['min']
                max_ = DrbdOptions._options[opt]['max']
                default = DrbdOptions._options[opt]['default']
                if "unit" in DrbdOptions._options[opt]:
                    unit = "; Unit: " + DrbdOptions._options[opt]['unit']
                else:
                    unit = ""
                # sp.add_argument('--' + opt, type=rangecheck(min_, max_),
                #                 default=default, help="Range: [%d, %d]; Default: %d" %(min_, max_, default))
                # setting a default sets the option to != None, which makes
                # filterNew relatively complex
                sp.add_argument('--' + opt, type=rangecheck(min_, max_),
                                help="Range: [%d, %d]; Default: %d%s" % (min_, max_, default, unit))
        for opt in DrbdOptions._options:
            if opt == 'help':
                continue
            else:
                sp.add_argument('--%s-%s' % (self.unsetprefix, opt),
                                action='store_true')

        sp.add_argument('--common', action="store_true")
        sp.add_argument(
            '--resource',
            type=namecheck(RES_NAME),
            help='Name of the resource to modify').completer = ResourceCommands.completer
        sp.add_argument(
            '--volume',
            help='Name of the volume to modify').completer = ResourceCommands.completer_volume
        sp.set_defaults(func=self._optioncommand)

        return sp

    def _checkmutex(self, args, names):
        """Checks that only one of the strings in names is in args"""
        target = ""
        for o in names:
            if args.__dict__[o]:
                if target:
                    sys.stderr.write("--%s and --%s are mutually exclusive\n" % (o, target))
                    sys.exit(ExitCode.ARGPARSE_ERROR)
                target = o

        if not target:
            sys.stderr.write("You have to specify (exactly) one of %s\n" % ('--' + ' --'.join(names)))
            sys.exit(ExitCode.ARGPARSE_ERROR)

        return target

    def filterNew(self, args):
        """return a dict containing all non-None args"""
        return filter_new_args(self.unsetprefix, args)

    def _check_target_for_option(self, target, option_name):
        if target == 'common':
            return True

        categories = {
            "resource": ['disk-options', 'peer-device-options', 'resource-options', 'net-options'],
            "volume": ['disk-options', 'peer-device-options']
        }

        if DrbdOptions._options[option_name]['category'] in categories[target]:
            return True

        return False

    def _check_options(self, target, args):
        """
        Checks if all entries in args are valid for the target.

        Keyword arguments:
        target -- option target ('common', 'resource', 'volume')
        args -- dict of options

        Return:
        A tuple (bool, errmsg), if first tuple param is False the errmsg is filled.
        """
        for option_name in args:
            if not self._check_target_for_option(target, option_name):
                return (False, "{opt} not valid for option group {cat}".format(opt=option_name, cat=target))

        return (True, None)

    def _optioncommand(self, args):
        target = self._checkmutex(args, ['common', 'resource', 'volume'])
        a = self.filterNew(args)
        a = {k: a[k] for k in a if k != target}  # remove 'resource', 'volume' arg

        # check if options are valid for target
        valid, errmsg = self._check_options(target, a)
        if not valid:
            print(errmsg)
            sys.exit(ExitCode.ARGPARSE_ERROR)

        if target == 'resource':
            print('TODO set {opts} for resource {rsc}'.format(opts=",".join(a.keys()), rsc=args.resource))
        elif target == 'volume':
            print('TODO set {opts} for volume {vol}'.format(opts=",".join(a.keys()), vol=args.volume))
        else:  # common
            print('TODO set {opts} for common'.format(opts=",".join(a.keys())))
