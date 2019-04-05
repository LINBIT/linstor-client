import unittest
from .linstor_testcase import LinstorTestCase
from linstor.sharedconsts import *
from linstor import SizeCalc


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
        self.assertEqual(10, retcode)

    def test_create_node(self):
        node = self.execute_with_single_resp(['node', 'create', 'node1', '195.0.0.1'])
        self.assertTrue(node.is_success())
        self.assertEqual(MASK_NODE | MASK_CRT | CREATED, node.ret_code)

    def test_create_storage_pool_missing_node(self):
        storpool = self.execute_with_single_resp(['storage-pool', 'create', 'lvm', 'storpool', 'nonode', 'drbdpool'])
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
        if minornr is not None:
            self.assertEqual(minornr, vlmdfn['vlm_minor'])
        self.assertEqual(size, vlmdfn['vlm_size'])

    def test_create_volume_dfn(self):
        rsc_dfn = self.execute_with_single_resp(['resource-definition', 'create', 'rscvlm'])
        self.assertTrue(rsc_dfn.is_success())

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '128MiB'])
        self.assertTrue(vlm_dfn.is_success())
        self.assert_volume_def('rscvlm', 0, None, SizeCalc.convert_round_up(128, SizeCalc.UNIT_MiB, SizeCalc.UNIT_KiB))

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '0'])
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(MASK_VLM_DFN | MASK_CRT | FAIL_INVLD_VLM_SIZE, vlm_dfn.ret_code)

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '--vlmnr', '3', '256Mib'])
        self.assertTrue(vlm_dfn.is_success())
        self.assertEqual(MASK_VLM_DFN | MASK_CRT | CREATED, vlm_dfn.ret_code)
        self.assert_volume_def('rscvlm', 3, None, SizeCalc.convert_round_up(256, SizeCalc.UNIT_MiB, SizeCalc.UNIT_KiB))

        with self.assertRaises(SystemExit):
            self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '1Gi'])

    def test_create_volume_dfn_no_res(self):
        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rsc-does-not-exist', '128MiB'])
        self.assertFalse(vlm_dfn.is_success())
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(FAIL_NOT_FOUND_RSC_DFN | MASK_CRT | MASK_VLM_DFN, vlm_dfn.ret_code)

    def test_delete_non_existing_rsc_dfn(self):
        rsc_dfn_del = self.execute_with_resp(['resource-definition', 'delete', 'non_existing_rsc_dfn'])
        self.assertGreater(len(rsc_dfn_del), 0)
        rsc_dfn_del_reply = rsc_dfn_del[0]
        self.assertTrue(rsc_dfn_del_reply.is_warning())
        self.assertEqual(WARN_NOT_FOUND | MASK_RSC_DFN | MASK_DEL, rsc_dfn_del_reply.ret_code)


if __name__ == '__main__':
    unittest.main()
