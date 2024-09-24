import unittest
from datetime import datetime, timedelta

import linstor_client_main
from linstor_client.commands import Commands
from linstor_client.utils import LinstorClientError


class TestClientCommands(unittest.TestCase):
    def test_main_commands(self):
        cli = linstor_client_main.LinStorCLI()
        cli.check_parser_commands()

    def _assert_parse_time_str(self, timestr, delta):
        dt_now = datetime.now()
        dt_now = dt_now.replace(microsecond=0)

        dt = Commands.parse_time_str(timestr)
        dt = dt.replace(microsecond=0)
        dt_diff = dt_now - delta
        self.assertEqual(dt_diff, dt)

    def test_parse_time_str(self):
        self._assert_parse_time_str("5d", timedelta(days=5))
        self._assert_parse_time_str("3", timedelta(hours=3))
        self._assert_parse_time_str("3h", timedelta(hours=3))

        self.assertRaises(LinstorClientError, Commands.parse_time_str, "10m")
        self.assertRaises(LinstorClientError, Commands.parse_time_str, "")


if __name__ == '__main__':
    unittest.main()
