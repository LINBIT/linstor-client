import unittest
import linstor_client


class TestClientCommands(unittest.TestCase):
    def test_main_commands(self):
        cli = linstor_client.LinStorCLI()
        cli.check_parser_commands()


if __name__ == '__main__':
    unittest.main()
