import unittest
import linstor_client
import sys
from cStringIO import StringIO
import json


class LinstorTestCase(unittest.TestCase):

    def execute(self, cmd_args):
        linstor_cli = linstor_client.LinStorCLI()

        try:
            return linstor_cli.parse_and_execute(cmd_args)
        except SystemExit as e:
            return e.code

    def parse_args(self, cmd_args):
        linstor_cli = linstor_client.LinStorCLI()

        return linstor_cli.parse(cmd_args)

    def execute_with_maschine_output(self, cmd_args):
        """
        Execute the given cmd_args command and adds the machine readable flag.
        Returns the parsed json output.
        """
        linstor_cli = linstor_client.LinStorCLI()
        backupstd = sys.stdout
        jout = None
        try:
            sys.stdout = StringIO()
            retcode = linstor_cli.parse_and_execute(cmd_args + ["-m"])
        except SystemExit as e:
            retcode = e.code
        finally:
            self.assertEqual(retcode, 0)
            jout = json.loads(sys.stdout.getvalue())
            sys.stdout.close()
            sys.stdout = backupstd
        return jout
