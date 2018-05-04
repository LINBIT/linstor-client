import unittest
from .linstor_testcase import LinstorTestCase
from linstor.sharedconsts import *
from linstor.utils import SizeCalc


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
        cnode_resp = self.execute_with_single_resp(['node', 'create', 'node1', '192.168.100.1'])
        self.assertTrue(cnode_resp.is_success())

        node_list = self.execute_with_machine_output(['node', 'list'])
        self.assertIsNotNone(node_list)
        self.assertIs(len(node_list), 1)
        node_list = node_list[0]
        self.assertTrue('nodes' in node_list)
        nodes = node_list['nodes']
        self.assertGreater(len(nodes), 0)
        self.assertTrue([n for n in nodes if n['name'] == 'node1'])

        # create storagepool
        storpool_resps = self.execute_with_resp(['storage-pool', 'create', 'storage', 'node1', 'lvm', 'lvmpool'])
        self.assertTrue(storpool_resps[0].is_warning())
        self.assertEqual(WARN_NOT_CONNECTED | MASK_STOR_POOL | MASK_CRT, storpool_resps[0].ret_code)
        self.assertTrue(storpool_resps[1].is_success())

        # check
        storagepool_list = self.execute_with_machine_output(['storage-pool', 'list'])
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
        self.assertHasProp(stor_pool['props'], NAMESPC_STORAGE_DRIVER + '/LvmVg', 'lvmpool')

        # create resource def
        rsc_dfn_resp = self.execute_with_single_resp(['resource-definition', 'create', 'rsc1'])
        self.assertTrue(rsc_dfn_resp.is_success())

        # create volume def
        vlm_dfn_resp = self.execute_with_single_resp(['volume-definition', 'create', 'rsc1', '1Gib'])
        self.assertTrue(vlm_dfn_resp.is_success())

        # create resource on node1
        rsc_resps = self.execute_with_resp(['resource', 'create', '--async', '-s', 'storage', 'rsc1', 'node1'])
        self.assertEqual(3, len(rsc_resps))
        self.assertTrue(rsc_resps[0].is_warning())  # satellite not reachable
        self.assertTrue(rsc_resps[1].is_success())  # resource created
        self.assertTrue(rsc_resps[2].is_success())  # volume created

        # check resource
        resource_list = self.execute_with_machine_output(['resource', 'list'])
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
        rsc_resps = self.execute_with_resp(['resource', 'delete', 'rsc1', 'node1'])
        self.assertEqual(2, len(rsc_resps))
        warn_resp = rsc_resps[0]
        self.assertTrue(warn_resp.is_warning(), str(warn_resp))
        self.assertEqual(WARN_NOT_CONNECTED | MASK_RSC | MASK_DEL, warn_resp.ret_code)
        self.assertTrue(rsc_resps[1].is_success())


class TestCreateCommands(LinstorTestCase):

    def test_create_storage_pool_dfn(self):
        storpooldfn = self.execute_with_single_resp(['storage-pool-definition', 'create', 'mystorpool'])
        self.assertTrue(storpooldfn.is_success())
        self.assertEqual(MASK_STOR_POOL_DFN | MASK_CRT | CREATED, storpooldfn.ret_code)

        storpooldfns = self.execute_with_machine_output(['storage-pool-definition', 'list'])
        self.assertEqual(1, len(storpooldfns))
        self.assertIn('stor_pool_dfns', storpooldfns[0])
        storpooldfns = storpooldfns[0]['stor_pool_dfns']
        mystorpool = [spd for spd in storpooldfns if spd['stor_pool_name'] == 'mystorpool']
        self.assertEqual(1, len(mystorpool), "storpool definition 'mystorpool' not found")

        # illegal name is already catched from argparse
        retcode = self.execute(['storage-pool-definition', 'create', '13394'])
        self.assertEqual(2, retcode)

    def test_create_node(self):
        node = self.execute_with_single_resp(['node', 'create', 'node1', '195.0.0.1'])
        self.assertTrue(node.is_success())
        self.assertEqual(MASK_NODE | MASK_CRT | CREATED, node.ret_code)

    def test_create_storage_pool(self):
        node = self.execute_with_single_resp(['node', 'create', 'storpool.node1', '195.0.0.2'])
        self.assertTrue(node.is_success())
        self.assertEqual(MASK_NODE | MASK_CRT | CREATED, node.ret_code)

        storpool = self.execute_with_resp(['storage-pool', 'create', 'storpool', 'storpool.node1', 'lvm', 'drbdpool'])
        no_active = storpool[0]
        storpool = storpool[1]
        self.assertTrue(no_active.is_warning())
        self.assertTrue(storpool.is_success())
        self.assertEqual(MASK_STOR_POOL | MASK_CRT | CREATED, storpool.ret_code)

        stor_pools = self.execute_with_machine_output(['storage-pool', 'list'])
        self.assertEqual(1, len(stor_pools))
        stor_pools = stor_pools[0]
        self.assertIn('stor_pools', stor_pools)
        stor_pools = stor_pools['stor_pools']
        stor_pool = [sp for sp in stor_pools if sp['stor_pool_name'] == 'storpool']
        self.assertEqual(1, len(stor_pool), "created storpool 'storpool' not in list")

    def test_create_storage_pool_missing_node(self):
        storpool = self.execute_with_single_resp(['storage-pool', 'create', 'storpool', 'nonode', 'lvm', 'drbdpool'])
        self.assertTrue(storpool.is_error())
        self.assertEqual(MASK_STOR_POOL | MASK_CRT | FAIL_NOT_FOUND_NODE, storpool.ret_code)

    def test_create_delete_storage_pool_dfn(self):
        storpooldf = self.execute_with_single_resp(['storage-pool-definition', 'create', 'teststorpooldf'])
        self.assertTrue(storpooldf.is_success())
        self.assertEqual(MASK_STOR_POOL_DFN | MASK_CRT | CREATED, storpooldf.ret_code)

        storpooldf = self.execute_with_single_resp(['storage-pool-definition', 'delete', 'teststorpooldf'])
        self.assertTrue(storpooldf.is_success())
        self.assertEqual(MASK_STOR_POOL_DFN | MASK_DEL | DELETED, storpooldf.ret_code)

    def test_create_resource_dfn(self):
        rsc_dfn = self.execute_with_single_resp(['resource-definition', 'create', 'rsc1'])
        self.assertTrue(rsc_dfn.is_success())

        rsc_dfns = self.execute_with_machine_output(['resource-definition', 'list'])
        self.assertEqual(1, len(rsc_dfns))
        self.assertIn('rsc_dfns', rsc_dfns[0])
        rsc_dfns = rsc_dfns[0]['rsc_dfns']
        rsc1 = [spd for spd in rsc_dfns if spd['rsc_name'] == 'rsc1']
        self.assertEqual(1, len(rsc1), "resource definition 'rsc1' not found")

    def assert_volume_def(self, rsc_name, vlmnr, minornr, size):
        rscdfs = self.execute_with_machine_output(['volume-definition', 'list'])
        self.assertEqual(1, len(rscdfs))
        rscdfs = rscdfs[0]
        self.assertIn('rsc_dfns', rscdfs)
        rscdfs = rscdfs['rsc_dfns']
        rsc = [x for x in rscdfs if x['rsc_name'] == rsc_name]
        self.assertEqual(1, len(rsc))
        rsc = rsc[0]
        self.assertIn('vlm_dfns', rsc)
        vlmdfns = rsc['vlm_dfns']
        vlmdfn = [x for x in vlmdfns if x['vlm_nr'] == vlmnr]
        self.assertEqual(1, len(vlmdfn), "volume definition not found")
        vlmdfn = vlmdfn[0]
        self.assertEqual(minornr, vlmdfn['vlm_minor'])
        self.assertEqual(size, vlmdfn['vlm_size'])

    def test_create_volume_dfn(self):
        rsc_dfn = self.execute_with_single_resp(['resource-definition', 'create', 'rscvlm'])
        self.assertTrue(rsc_dfn.is_success())

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '128MiB'])
        self.assertTrue(vlm_dfn.is_success())
        self.assert_volume_def('rscvlm', 0, 1000, SizeCalc.convert_round_up(128, SizeCalc.UNIT_MiB, SizeCalc.UNIT_kiB))

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '0'])
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(MASK_VLM_DFN | MASK_CRT | FAIL_INVLD_VLM_SIZE, vlm_dfn.ret_code)

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '--vlmnr', '3', '256Mib'])
        self.assertTrue(vlm_dfn.is_success())
        self.assertEqual(MASK_VLM_DFN | MASK_CRT | CREATED, vlm_dfn.ret_code)
        self.assert_volume_def('rscvlm', 3, 1002, SizeCalc.convert_round_up(256, SizeCalc.UNIT_MiB, SizeCalc.UNIT_kiB))

        with self.assertRaises(SystemExit):
            self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '1Gi'])

    def test_create_volume_dfn_no_res(self):
        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rsc-does-not-exist', '128MiB'])
        self.assertFalse(vlm_dfn.is_success())
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(FAIL_NOT_FOUND_RSC_DFN | MASK_CRT | MASK_VLM_DFN, vlm_dfn.ret_code)


if __name__ == '__main__':
    unittest.main()
