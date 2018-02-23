import unittest
from .linstor_testcase import LinstorTestCase


class TestListCommands(LinstorTestCase):

    def test_nodes(self):
        jout = self.execute_with_machine_output(["list-nodes"])
        self.assertIsNotNone(jout)

    def test_nodes_text(self):
        text_out = self.execute_with_text_output(["list-nodes"])
        self.assertIn("Node", text_out)

    def test_resource_defs(self):
        jout = self.execute_with_machine_output(["list-resource-definitions"])
        self.assertIsNotNone(jout)

    def test_resource_defs_text(self):
        text_out = self.execute_with_text_output(["list-resource-definitions"])
        self.assertIn("ResourceName", text_out)

    def test_resources(self):
        jout = self.execute_with_machine_output(["list-resources"])
        self.assertIsNotNone(jout)

    def test_resources_text(self):
        text_out = self.execute_with_text_output(["list-resources"])
        self.assertIn("ResourceName", text_out)

    def test_storage_pool_defs(self):
        jout = self.execute_with_machine_output(["list-storage-pool-definitions"])
        self.assertIsNotNone(jout)

    def test_storage_pool_defs_text(self):
        text_out = self.execute_with_text_output(["list-storage-pool-definitions"])
        self.assertIn("StoragePool", text_out)

    def test_storage_pools(self):
        jout = self.execute_with_machine_output(["list-storage-pools"])
        self.assertIsNotNone(jout)

    def test_storage_pools_text(self):
        text_out = self.execute_with_text_output(["list-storage-pools"])
        self.assertIn("StoragePool", text_out)

    def test_volume_definitions(self):
        jout = self.execute_with_machine_output(["list-volume-definitions"])
        self.assertIsNotNone(jout)

    def test_volume_definitions_text(self):
        text_out = self.execute_with_text_output(["list-volume-definitions"])
        self.assertIn("ResourceName", text_out)


if __name__ == '__main__':
    unittest.main()
