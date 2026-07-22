import unittest
from tests import LinstorTestCase


class TestPropsFilterArgs(LinstorTestCase):
    """
    Regression tests for GitHub issue #520:
    https://github.com/LINBIT/linstor-server/issues/520

    The list commands accept '--props key=value' filters. Multiple filters must be
    combined with AND on the controller, but for that to work the client has to send
    *all* of them. '--props' is declared with nargs='+'; before the fix it lacked
    action=Commands.ExtendAction, so a second '--props' silently overwrote the first
    and only the last filter ever reached the controller. As a result

        linstor rd list --props Aux/propA=1 --props Aux/propB=a

    behaved as if only 'Aux/propB=a' had been given (returning every resource
    definition with propB=a instead of the single one matching both filters).

    These tests only exercise argument parsing (LinstorTestCase.parse_args does not
    talk to a controller), asserting that every '--props' occurrence is accumulated.
    """

    # (command, list-subcommand) pairs for every list command that offers --props
    LIST_COMMANDS = [
        ['node', 'list'],
        ['resource-definition', 'list'],
        ['resource-group', 'list'],
        ['resource', 'list'],
        ['storage-pool', 'list'],
    ]

    def _parse_props(self, base_cmd, extra_args):
        # --disable-config keeps parsing independent of the caller's environment/config
        args = self.parse_args(['--disable-config'] + list(base_cmd) + extra_args)
        return args.props

    def test_repeated_props_accumulate(self):
        # the exact shape from the issue report: two --props with different keys
        for cmd in self.LIST_COMMANDS:
            props = self._parse_props(cmd, ['--props', 'Aux/propA=1', '--props', 'Aux/propB=a'])
            self.assertEqual(
                ['Aux/propA=1', 'Aux/propB=a'],
                props,
                "repeated --props must accumulate for command {0!r}, got {1!r}".format(cmd, props)
            )

    def test_three_repeated_props_accumulate(self):
        for cmd in self.LIST_COMMANDS:
            props = self._parse_props(cmd, ['--props', 'A=1', '--props', 'B=2', '--props', 'C=3'])
            self.assertEqual(['A=1', 'B=2', 'C=3'], props, "command {0!r}".format(cmd))

    def test_single_props_multiple_values_still_works(self):
        # the space-separated single-flag form must keep working (nargs='+')
        for cmd in self.LIST_COMMANDS:
            props = self._parse_props(cmd, ['--props', 'A=1', 'B=2'])
            self.assertEqual(['A=1', 'B=2'], props, "command {0!r}".format(cmd))

    def test_no_props_defaults_to_none(self):
        # when the filter is omitted the api layer must see a falsy value and skip it
        for cmd in self.LIST_COMMANDS:
            self.assertIsNone(self._parse_props(cmd, []), "command {0!r}".format(cmd))


if __name__ == '__main__':
    unittest.main()
