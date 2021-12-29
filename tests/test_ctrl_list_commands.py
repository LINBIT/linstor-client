import unittest
from tests import LinstorTestCase


class TestListCommands(LinstorTestCase):

    def test_nodes(self):
        jout = self.execute_with_machine_output(["node", "list"])
        self.assertIsNotNone(jout)

    def test_nodes_text(self):
        text_out = self.execute_with_text_output(["node", "list"])
        self.assertIn("Node", text_out)

    def test_resource_defs(self):
        jout = self.execute_with_machine_output(["resource-definition", "list"])
        self.assertIsNotNone(jout)

    def test_resource_defs_text(self):
        text_out = self.execute_with_text_output(["resource-definition", "list"])
        self.assertIn("ResourceName", text_out)

    def test_resources(self):
        jout = self.execute_with_machine_output(["resource", "list"])
        self.assertIsNotNone(jout)

    def test_resources_text(self):
        text_out = self.execute_with_text_output(["resource", "list"])
        self.assertIn("ResourceName", text_out)

    def test_volume_text(self):
        text_out = self.execute_with_text_output(["resource", "list-volumes"])
        self.assertIn("VolNr", text_out)

    def test_storage_pools(self):
        jout = self.execute_with_machine_output(["storage-pool", "list"])
        self.assertIsNotNone(jout)

    def test_storage_pools_text(self):
        text_out = self.execute_with_text_output(["storage-pool", "list"])
        self.assertIn("StoragePool", text_out)

    def test_volume_definitions(self):
        jout = self.execute_with_machine_output(["volume-definition", "list"])
        self.assertIsNotNone(jout)

    def test_volume_definitions_text(self):
        text_out = self.execute_with_text_output(["volume-definition", "list"])
        self.assertIn("ResourceName", text_out)


if __name__ == '__main__':
    unittest.main()
