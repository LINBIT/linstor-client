import unittest
import linstor_client
import sys
from cStringIO import StringIO
import json


class TestListCommands(unittest.TestCase):

    def _get_json_out(self, cmd_args):
        linstor_cli = linstor_client.LinStorCLI()
        backupstd = sys.stdout
        jout = None
        try:
            sys.stdout = StringIO()
            linstor_cli.parse(cmd_args + ["-m"])
        except SystemExit as e:
            self.assertEqual(e.code, 0)
            jout = json.loads(sys.stdout.getvalue())
        finally:
            sys.stdout.close()
            sys.stdout = backupstd
        return jout

    def test_nodes(self):
        jout = self._get_json_out(["list-nodes"])
        self.assertIsNotNone(jout)

    def test_resource_defs(self):
        jout = self._get_json_out(["list-resource-definitions"])
        self.assertIsNotNone(jout)

    def test_resources(self):
        jout = self._get_json_out(["list-resources"])
        self.assertIsNotNone(jout)

    def test_storage_pool_defs(self):
        jout = self._get_json_out(["list-storage-pool-definitions"])
        self.assertIsNotNone(jout)

    def test_storage_pools(self):
        jout = self._get_json_out(["list-storage-pools"])
        self.assertIsNotNone(jout)

    def test_volume_definitions(self):
        jout = self._get_json_out(["list-volume-definitions"])
        self.assertIsNotNone(jout)


if __name__ == '__main__':
    unittest.main()
