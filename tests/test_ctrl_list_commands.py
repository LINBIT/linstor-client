import unittest
from .linstor_testcase import LinstorTestCase, LinstorTestCaseWithData


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


class TestListFilters(LinstorTestCaseWithData):
    def test_list_storage_pools(self):
        jout = self.execute_with_machine_output(["list-storage-pools"])
        pools = self.get_list('stor_pools', jout)
        self.assertGreater(len(pools), 0)

        jout = self.execute_with_machine_output(["list-storage-pools", "-n", "fakehost1"])
        pools = self.get_list('stor_pools', jout)
        fakehost1_stor_pools = len(pools)
        self.assertEqual(fakehost1_stor_pools, len([x for x in pools if x['node_name'] == 'fakehost1']))

        jout = self.execute_with_machine_output(["list-storage-pools", "-n", "fakehost2", "-s", "zfsubuntu"])
        pools = self.get_list('stor_pools', jout)
        self.assertEqual(1, len(pools))
        fakehost1_stor_pools = len(pools)
        self.assertEqual(fakehost1_stor_pools, len([x for x in pools if x['node_name'] == 'fakehost2']))

    def test_list_resources(self):
        jout = self.execute_with_machine_output(["list-resources"])
        resources = self.get_list('resources', jout)
        self.assertGreater(len(resources), 0)

        jout = self.execute_with_machine_output(["list-resources", "-n", "fakehost1"])
        resources = self.get_list('resources', jout)
        fakehost1_resources = len(resources)
        self.assertEqual(fakehost1_resources, len([x for x in resources if x['node_name'] == 'fakehost1']))

        jout = self.execute_with_machine_output(["list-resources", "-n", "fakehost1", "-r", "rsc1"])
        resources = self.get_list('resources', jout)
        self.assertEqual(1, len(resources))
        fakehost1_resources = len(resources)
        self.assertEqual(fakehost1_resources,
                         len([x for x in resources if x['node_name'] == 'fakehost1' and x['name'] == 'rsc1']))

    def test_list_volumes(self):
        jout = self.execute_with_machine_output(["list-volumes"])
        resources = self.get_list('resources', jout)
        self.assertGreater(len(resources), 0)

        jout = self.execute_with_machine_output(["list-volumes", "-s", "thinpool"])
        resources = self.get_list('resources', jout)
        self.assertEqual(len(resources),
                         len([x for x in resources if all([y['stor_pool_name'] == 'thinpool' for y in x['vlms']])]))

        jout = self.execute_with_machine_output(["list-volumes", "-s", "thinpool", "-n", "fakehost1"])
        resources = self.get_list('resources', jout)
        self.assertEqual(1, len(resources))

        jout = self.execute_with_machine_output(["list-volumes", "-r", "rsc1"])
        resources = self.get_list('resources', jout)
        self.assertEqual(len(resources),
                         len([x for x in resources if x['name'] == 'rsc1']))


if __name__ == '__main__':
    unittest.main()
