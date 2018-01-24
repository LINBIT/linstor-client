import unittest
from .linstor_testcase import LinstorTestCase
from linstor.sharedconsts import *


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
        self.assertEqual(WARN_NOT_CONNECTED | MASK_STOR_POOL | MASK_CRT, storpool_resps[0].ret_code)
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
        self.assertIn('vlm_minor_nr', vlms[0])

        # delete resource
        rsc_resps = self.execute_with_resp(['delete-resource', 'rsc1', 'node1'])
        self.assertEqual(2, len(rsc_resps))
        warn_resp = rsc_resps[0]
        self.assertTrue(warn_resp.is_warning(), str(warn_resp))
        self.assertEqual(WARN_NOT_CONNECTED | MASK_RSC | MASK_DEL, warn_resp.ret_code)
        self.assertTrue(rsc_resps[1].is_success())


class TestCreateCommands(LinstorTestCase):

    def test_create_storage_pool_dfn(self):
        storpooldfn = self.execute_with_single_resp(['create-storage-pool-definition', 'mystorpool'])
        self.assertTrue(storpooldfn.is_success())
        self.assertEqual(MASK_STOR_POOL_DFN | CREATED, storpooldfn.ret_code)

        storpooldfns = self.execute_with_maschine_output(['list-storage-pool-definition'])
        self.assertEqual(1, len(storpooldfns))
        self.assertIn('stor_pool_dfns', storpooldfns[0])
        storpooldfns = storpooldfns[0]['stor_pool_dfns']
        mystorpool = [spd for spd in storpooldfns if spd['stor_pool_name'] == 'mystorpool']
        self.assertEqual(1, len(mystorpool), "storpool definition 'mystorpool' not found")

        # illegal name is already catched from argparse
        retcode = self.execute(['create-storage-pool-definition', '13394'])
        self.assertEqual(2, retcode)

    def test_create_node(self):
        node = self.execute_with_single_resp(['create-node', 'node1', '195.0.0.1'])
        self.assertTrue(node.is_success())
        self.assertEqual(MASK_NODE | CREATED, node.ret_code)

    def test_create_storage_pool(self):
        node = self.execute_with_single_resp(['create-node', 'storpool.node1', '195.0.0.2'])
        self.assertTrue(node.is_success())
        self.assertEqual(MASK_NODE | CREATED, node.ret_code)

        storpool = self.execute_with_resp(['create-storage-pool', 'storpool', 'storpool.node1', 'lvm', '/dev/drbdpool'])
        no_active = storpool[0]
        storpool = storpool[1]
        self.assertTrue(no_active.is_warning())
        self.assertTrue(storpool.is_success())
        self.assertEqual(MASK_STOR_POOL | CREATED, storpool.ret_code)

    def test_create_storage_pool_missing_node(self):
        storpool = self.execute_with_single_resp(['create-storage-pool', 'storpool', 'nonode', 'lvm', '/dev/drbdpool'])
        self.assertTrue(storpool.is_error())
        self.assertEqual(MASK_STOR_POOL | MASK_CRT | FAIL_NOT_FOUND_NODE, storpool.ret_code)

    def test_create_resource_dfn(self):
        rsc_dfn = self.execute_with_single_resp(['create-resource-definition', 'rsc1'])
        self.assertTrue(rsc_dfn.is_success())

        rsc_dfns = self.execute_with_maschine_output(['list-resource-definition'])
        self.assertEqual(1, len(rsc_dfns))
        self.assertIn('rsc_dfns', rsc_dfns[0])
        rsc_dfns = rsc_dfns[0]['rsc_dfns']
        rsc1 = [spd for spd in rsc_dfns if spd['rsc_name'] == 'rsc1']
        self.assertEqual(1, len(rsc1), "resource definition 'rsc1' not found")

    def test_create_volume_dfn(self):
        rsc_dfn = self.execute_with_single_resp(['create-resource-definition', 'rscvlm'])
        self.assertTrue(rsc_dfn.is_success())

        vlm_dfn = self.execute_with_single_resp(['create-volume-definition', 'rscvlm', '128MiB'])
        self.assertTrue(vlm_dfn.is_success())

    def test_create_volume_dfn_no_res(self):
        vlm_dfn = self.execute_with_single_resp(['create-volume-definition', 'rsc-does-not-exist', '128MiB'])
        self.assertFalse(vlm_dfn.is_success())
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(FAIL_NOT_FOUND_RSC_DFN | MASK_CRT | MASK_VLM_DFN, vlm_dfn.ret_code)


if __name__ == '__main__':
    unittest.main()
