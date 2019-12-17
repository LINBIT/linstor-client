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
        self.assertIn("VolumeNr", text_out)

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

"""
class TestListFilters(LinstorTestCaseWithData):
    def test_list_storage_pools(self):
        jout = self.execute_with_machine_output(["storage-pool", "list"])
        pools = self.get_list('stor_pools', jout)
        self.assertGreater(len(pools), 0)

        jout = self.execute_with_machine_output(["storage-pool", "list", "-n", "fakehost1"])
        pools = self.get_list('stor_pools', jout)
        fakehost1_stor_pools = len(pools)
        self.assertEqual(fakehost1_stor_pools, len([x for x in pools if x['node_name'] == 'fakehost1']))

        jout = self.execute_with_machine_output(["storage-pool", "list", "-n", "fakehost2", "-s", "zfsubuntu"])
        pools = self.get_list('stor_pools', jout)
        self.assertEqual(1, len(pools))
        fakehost1_stor_pools = len(pools)
        self.assertEqual(fakehost1_stor_pools, len([x for x in pools if x['node_name'] == 'fakehost2']))

    def test_list_resources(self):
        jout = self.execute_with_machine_output(["resource", "list"])
        resources = self.get_list('resources', jout)
        self.assertGreater(len(resources), 0)

        jout = self.execute_with_machine_output(["resource", "list", "-n", "fakehost1"])
        resources = self.get_list('resources', jout)
        fakehost1_resources = len(resources)
        self.assertEqual(fakehost1_resources, len([x for x in resources if x['node_name'] == 'fakehost1']))

        jout = self.execute_with_machine_output(["resource", "list", "-n", "fakehost1", "-r", "rsc1"])
        resources = self.get_list('resources', jout)
        self.assertEqual(1, len(resources))
        fakehost1_resources = len(resources)
        self.assertEqual(fakehost1_resources,
                         len([x for x in resources if x['node_name'] == 'fakehost1' and x['name'] == 'rsc1']))

    def test_list_volumes(self):
        jout = self.execute_with_machine_output(["resource", "list-volumes"])
        resources = self.get_list('resources', jout)
        self.assertGreater(len(resources), 0)

        jout = self.execute_with_machine_output(["resource", "list-volumes", "-s", "thinpool"])
        resources = self.get_list('resources', jout)
        self.assertEqual(len(resources),
                         len([x for x in resources if all([y['stor_pool_name'] == 'thinpool' for y in x['vlms']])]))

        jout = self.execute_with_machine_output(["resource", "list-volumes", "-s", "thinpool", "-n", "fakehost1"])
        resources = self.get_list('resources', jout)
        self.assertEqual(1, len(resources))

        jout = self.execute_with_machine_output(["resource", "list-volumes", "-r", "rsc1"])
        resources = self.get_list('resources', jout)
        self.assertEqual(len(resources),
                         len([x for x in resources if x['name'] == 'rsc1']))

    def test_list_error_reports(self):
        # force an error report
        self.execute(["node", "create", "doesnotexist", "299.299.299.299"])

        error_reports = self.execute_with_machine_output(["error-reports", "list"])
        self.assertGreater(len(error_reports), 0)

        report = error_reports[0]
        report_id = report["filename"][len("ErrorReport-"):-len(".log")]
        error_reports = self.execute_with_machine_output(["error-reports", "show", report_id])
        self.assertEqual(1, len(error_reports))
        error_report = error_reports[0]
        self.assertGreater(len(error_report['text']), 0)


class _FakeArgs(object):
    def __init__(self, addr):
        self.controllers = addr


class TestCompleters(LinstorTestCaseWithData):

    def test_node_completer(self):
        jout = self.execute_with_machine_output(['node', 'list'])
        nodes = self.get_list('nodes', jout)

        linstor_cli = linstor_client_main.LinStorCLI()
        linstor_cli._node_commands.get_linstorapi(parsed_args=_FakeArgs(self.host() + ':' + str(self.port())))
        cmpl_nodes = linstor_cli._node_commands.node_completer("")
        self.assertEqual(len(nodes), len(cmpl_nodes))

        cmpl_nodes = linstor_cli._node_commands.node_completer("fakem")
        self.assertEqual(1, len(cmpl_nodes))

        cmpl_nodes = linstor_cli._node_commands.node_completer("fakeh")
        self.assertEqual(3, len(cmpl_nodes))

    def test_netifs_completer(self):
        jout = self.execute_with_machine_output(['node', 'interface', 'list', 'fakehost1'])
        nodes = self.get_list('nodes', jout)
        netifs = [x for n in nodes if n['name'] == 'fakehost1' for x in n['net_interfaces']]

        linstor_cli = linstor_client_main.LinStorCLI()
        args = _FakeArgs(self.host() + ':' + str(self.port()))
        args.node_name = 'fakehost1'
        linstor_cli._node_commands.get_linstorapi(parsed_args=args)
        cmpl_netifs = linstor_cli._node_commands.netif_completer("", parsed_args=args)
        self.assertEqual(len(netifs), len(cmpl_netifs))

        cmpl_netifs = linstor_cli._node_commands.netif_completer("def", parsed_args=args)
        self.assertEqual(1, len(cmpl_netifs))

    def test_storpool_dfn_completer(self):
        jout = self.execute_with_machine_output(['storage-pool-definition', 'list'])
        stor_pools = self.get_list('stor_pool_dfns', jout)

        linstor_cli = linstor_client_main.LinStorCLI()
        linstor_cli._node_commands.get_linstorapi(parsed_args=_FakeArgs(self.host() + ':' + str(self.port())))
        cmpl_stor_pools = linstor_cli._node_commands.storage_pool_dfn_completer("")
        self.assertEqual(len(stor_pools), len(cmpl_stor_pools))

        cmpl_stor_pools = linstor_cli._node_commands.storage_pool_dfn_completer("zfs")
        self.assertEqual(1, len(cmpl_stor_pools))

    def test_storpool_completer(self):
        jout = self.execute_with_machine_output(['storage-pool-definition', 'list'])
        stor_pools = self.get_list('stor_pool_dfns', jout)

        linstor_cli = linstor_client_main.LinStorCLI()
        linstor_cli._node_commands.get_linstorapi(parsed_args=_FakeArgs(self.host() + ':' + str(self.port())))
        cmpl_stor_pools = linstor_cli._node_commands.storage_pool_completer("")
        self.assertEqual(len(stor_pools), len(cmpl_stor_pools))

        cmpl_stor_pools = linstor_cli._node_commands.storage_pool_completer("zfs")
        self.assertEqual(1, len(cmpl_stor_pools))

    def test_resource_dfn_completer(self):
        jout = self.execute_with_machine_output(['resource-definition', 'list'])
        resources = self.get_list('rsc_dfns', jout)

        linstor_cli = linstor_client_main.LinStorCLI()
        linstor_cli._node_commands.get_linstorapi(parsed_args=_FakeArgs(self.host() + ':' + str(self.port())))
        cmpl_resources = linstor_cli._node_commands.resource_dfn_completer("")
        self.assertEqual(len(resources), len(cmpl_resources))

        cmpl_resources = linstor_cli._node_commands.resource_dfn_completer("rsc-")
        self.assertEqual(1, len(cmpl_resources))

    def test_resource_completer(self):
        jout = self.execute_with_machine_output(['resource-definition', 'list'])
        resources = self.get_list('rsc_dfns', jout)

        linstor_cli = linstor_client_main.LinStorCLI()
        linstor_cli._node_commands.get_linstorapi(parsed_args=_FakeArgs(self.host() + ':' + str(self.port())))
        cmpl_resources = linstor_cli._node_commands.resource_completer("")
        self.assertEqual(len(resources), len(cmpl_resources))
"""

if __name__ == '__main__':
    unittest.main()
