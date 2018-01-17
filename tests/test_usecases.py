import unittest
from .linstor_testcase import LinstorTestCase
from linstor.sharedconsts import RC_RSC_DEL_WARN_NOT_CONNECTED, RC_STOR_POOL_CRT_WARN_NOT_CONNECTED


class TestUseCases(LinstorTestCase):

    @unittest.skip("used for dumping help")
    def test_help(self):
        objs = [
            'node', 'resource-definition', 'resource',
            'storage-pool', 'storage-pool-definition', 'volume-definition'
        ]

        create_cmds = ['create-' + x for x in objs]
        delete_cmds = ['delete-' + x for x in objs]
        list_cmds = ['list-' + x for x in objs]
        for cmd in create_cmds + delete_cmds + list_cmds + ['get-node-properties']:
            print("")
            print('-' * 120)
            print('-- ' + cmd)
            print('-' * 120)
            self.assertEqual(0, self.execute([cmd, '--help']))

    def test_create_volume(self):
        cnode_resp = self.execute_with_single_resp(['create-node', 'node1', '192.168.100.1'])
        self.assertTrue(cnode_resp.is_success())

        node_list = self.execute_with_maschine_output(['list-nodes'])
        self.assertIsNotNone(node_list)
        self.assertIs(len(node_list), 1)
        node_list = node_list[0]
        self.assertTrue('nodes' in node_list)
        nodes = node_list['nodes']
        self.assertGreater(len(nodes), 0)
        self.assertTrue([n for n in nodes if n['name'] == 'node1'])

        # create storagepool
        storpool_resps = self.execute_with_resp(['create-storage-pool', 'storage', 'node1', 'lvm', '/dev/lvmpool'])
        self.assertTrue(storpool_resps[0].is_warning())
        self.assertEqual(RC_STOR_POOL_CRT_WARN_NOT_CONNECTED, storpool_resps[0].ret_code)
        self.assertTrue(storpool_resps[1].is_success())

        # check
        storagepool_list = self.execute_with_maschine_output(['list-storage-pools'])
        self.assertIsNotNone(storagepool_list)
        self.assertIs(len(storagepool_list), 1)
        storagepool_list = storagepool_list[0]
        self.assertIn('stor_pools', storagepool_list)
        stor_pools = storagepool_list['stor_pools']
        self.assertEqual(len(stor_pools), 1)
        stor_pool = stor_pools[0]
        self.assertEqual('node1', stor_pool['node_name'])
        self.assertEqual('LvmDriver', stor_pool['driver'])
        self.assertEqual('storage', stor_pool['stor_pool_name'])
        self.assertHasProp(stor_pool['props'], 'LvmVg', '/dev/lvmpool')

        # create resource def
        rsc_dfn_resp = self.execute_with_single_resp(['create-resource-definition', 'rsc1'])
        self.assertTrue(rsc_dfn_resp.is_success())

        # create volume def
        vlm_dfn_resp = self.execute_with_single_resp(['create-volume-definition', 'rsc1', '1Gib'])
        self.assertTrue(vlm_dfn_resp.is_success())

        # create resource on node1
        rsc_resps = self.execute_with_resp(['create-resource', '-s', 'storage', 'rsc1', 'node1'])
        self.assertEqual(3, len(rsc_resps))
        self.assertTrue(rsc_resps[0].is_warning())  # satellite not reachable
        self.assertTrue(rsc_resps[1].is_success())  # resource created
        self.assertTrue(rsc_resps[2].is_success())  # volume created

        # check resource
        resource_list = self.execute_with_maschine_output(['list-resources'])
        self.assertIsNotNone(resource_list)
        self.assertIs(len(resource_list), 1)
        resource_list = resource_list[0]
        self.assertIn('resources', resource_list)
        resources = resource_list['resources']
        self.assertEqual(len(resources), 1)
        rsc1 = resources[0]
        self.assertEqual(rsc1['name'], 'rsc1')
        self.assertIn('vlms', rsc1)
        vlms = rsc1['vlms']
        self.assertEqual(len(vlms), 1)
        self.assertEqual(vlms[0]['vlm_nr'], 0)

        # delete resource
        rsc_resps = self.execute_with_resp(['delete-resource', 'rsc1', 'node1'])
        self.assertEqual(2, len(rsc_resps))
        warn_resp = rsc_resps[0]
        self.assertTrue(warn_resp.is_warning(), str(warn_resp))
        self.assertEqual(RC_RSC_DEL_WARN_NOT_CONNECTED, warn_resp.ret_code)
        self.assertTrue(rsc_resps[1].is_success())


if __name__ == '__main__':
    unittest.main()
