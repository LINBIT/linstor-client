import unittest
from .linstor_testcase import LinstorTestCase


class TestListCommands(LinstorTestCase):

    def test_nodes(self):
        jout = self.execute_with_maschine_output(["list-nodes"])
        self.assertIsNotNone(jout)

    def test_resource_defs(self):
        jout = self.execute_with_maschine_output(["list-resource-definitions"])
        self.assertIsNotNone(jout)

    def test_resources(self):
        jout = self.execute_with_maschine_output(["list-resources"])
        self.assertIsNotNone(jout)

    def test_storage_pool_defs(self):
        jout = self.execute_with_maschine_output(["list-storage-pool-definitions"])
        self.assertIsNotNone(jout)

    def test_storage_pools(self):
        jout = self.execute_with_maschine_output(["list-storage-pools"])
        self.assertIsNotNone(jout)

    def test_volume_definitions(self):
        jout = self.execute_with_maschine_output(["list-volume-definitions"])
        self.assertIsNotNone(jout)


if __name__ == '__main__':
    unittest.main()
