import unittest

from linstor_client.commands import ArgumentError
from linstor_client.commands.drbd_setup_cmds import DrbdOptions


class TestDrbdOptionUnits(unittest.TestCase):
    """
    drbd-options must store a value without unit as given, i.e. in the option's default unit,
    the same as set-property does. Values with a unit suffix are converted to the default unit.
    """

    def _parse(self, opt, value, object_name='resource-definition'):
        modify, deletes = DrbdOptions.parse_opts({opt: value}, object_name)
        self.assertEqual([], deletes)
        return modify

    def test_c_max_rate_bare_value(self):
        # default unit KiB/s
        self.assertEqual({'DrbdOptions/PeerDevice/c-max-rate': '4194304'}, self._parse('c-max-rate', '4194304'))
        self.assertEqual({'DrbdOptions/PeerDevice/c-max-rate': '100'}, self._parse('c-max-rate', '100'))

    def test_c_max_rate_suffixed_value(self):
        self.assertEqual({'DrbdOptions/PeerDevice/c-max-rate': '100'}, self._parse('c-max-rate', '100k'))
        self.assertEqual({'DrbdOptions/PeerDevice/c-max-rate': '102400'}, self._parse('c-max-rate', '100M'))
        self.assertEqual({'DrbdOptions/PeerDevice/c-max-rate': '4194304'}, self._parse('c-max-rate', '4G'))

    def test_c_max_rate_out_of_range(self):
        self.assertRaises(ArgumentError, self._parse, 'c-max-rate', '4194305')
        self.assertRaises(ArgumentError, self._parse, 'c-max-rate', '5G')

    def test_c_fill_target_bare_value(self):
        # default unit sectors (512 bytes)
        self.assertEqual({'DrbdOptions/PeerDevice/c-fill-target': '2048'}, self._parse('c-fill-target', '2048'))

    def test_c_fill_target_suffixed_value(self):
        self.assertEqual({'DrbdOptions/PeerDevice/c-fill-target': '2048'}, self._parse('c-fill-target', '1M'))
        self.assertEqual({'DrbdOptions/PeerDevice/c-fill-target': '2'}, self._parse('c-fill-target', '1K'))


if __name__ == '__main__':
    unittest.main()
