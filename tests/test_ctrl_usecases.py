import unittest
from tests import LinstorTestCase
from linstor.sharedconsts import MASK_CRT, MASK_STOR_POOL, CREATED, MASK_NODE, FAIL_NOT_FOUND_NODE, MASK_VLM_DFN
from linstor.sharedconsts import FAIL_NOT_FOUND_RSC_DFN, FAIL_INVLD_VLM_SIZE, MASK_DEL, WARN_NOT_FOUND, MASK_RSC_DFN
from linstor import SizeCalc


class TestUseCases(LinstorTestCase):

    @unittest.skip("used for dumping help")
    def test_help(self):
        objs = [
            'node', 'resource-definition', 'resource',
            'storage-pool', 'volume-definition'
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

    def test_create_node(self):
        node = self.execute_with_resp(['node', 'create', 'nodeCreate1', '195.0.0.1'])
        self.assert_api_succuess(node[0])
        self.assertEqual(MASK_NODE | MASK_CRT | CREATED, node[0].ret_code)

    def test_create_storage_pool_missing_node(self):
        storpool = self.execute_with_single_resp(['storage-pool', 'create', 'lvm', 'storpool', 'nonode', 'drbdpool'])
        self.assertTrue(storpool.is_error())
        self.assertEqual(self.signed_mask(MASK_STOR_POOL | MASK_CRT | FAIL_NOT_FOUND_NODE), storpool.ret_code)

    def test_create_resource_dfn(self):
        rsc_dfn = self.execute_with_single_resp(['resource-definition', 'create', 'rsccreate1'])
        self.assert_api_succuess(rsc_dfn)

        rsc_dfns = self.execute_with_machine_output(['resource-definition', 'list'])
        self.assertEqual(1, len(rsc_dfns))
        self.assertIn('rsc_dfns', rsc_dfns[0])
        rsc_dfns = rsc_dfns[0]['rsc_dfns']
        rsc1 = [spd for spd in rsc_dfns if spd['rsc_name'] == 'rsccreate1']
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
        self.assert_api_succuess(rsc_dfn)

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '128MiB'])
        self.assert_api_succuess(vlm_dfn)
        self.assert_volume_def('rscvlm', 0, None, SizeCalc.convert_round_up(128, SizeCalc.UNIT_MiB, SizeCalc.UNIT_KiB))

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '0'])
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(self.signed_mask(MASK_VLM_DFN | MASK_CRT | FAIL_INVLD_VLM_SIZE), vlm_dfn.ret_code)

        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '--vlmnr', '3', '256Mib'])
        self.assert_api_succuess(vlm_dfn)
        self.assertEqual(MASK_VLM_DFN | MASK_CRT | CREATED, vlm_dfn.ret_code)
        self.assert_volume_def('rscvlm', 3, None, SizeCalc.convert_round_up(256, SizeCalc.UNIT_MiB, SizeCalc.UNIT_KiB))

        with self.assertRaises(SystemExit):
            self.execute_with_single_resp(['volume-definition', 'create', 'rscvlm', '1Gi'])

    def test_create_volume_dfn_no_res(self):
        vlm_dfn = self.execute_with_single_resp(['volume-definition', 'create', 'rsc-does-not-exist', '128MiB'])
        self.assertFalse(vlm_dfn.is_success())
        self.assertTrue(vlm_dfn.is_error())
        self.assertEqual(self.signed_mask(FAIL_NOT_FOUND_RSC_DFN | MASK_CRT | MASK_VLM_DFN), vlm_dfn.ret_code)

    def test_delete_non_existing_rsc_dfn(self):
        rsc_dfn_del = self.execute_with_resp(['resource-definition', 'delete', 'non_existing_rsc_dfn'])
        self.assertGreater(len(rsc_dfn_del), 0)
        rsc_dfn_del_reply = rsc_dfn_del[0]
        self.assertTrue(rsc_dfn_del_reply.is_warning())
        self.assertEqual(self.signed_mask(WARN_NOT_FOUND | MASK_RSC_DFN | MASK_DEL), rsc_dfn_del_reply.ret_code)

    def get_resource_group(self, rsc_grp_name):
        data = self.execute_with_machine_output(['resource-group', 'list'])[0]
        mygrp = [x for x in data if x['name'] == rsc_grp_name][0]
        self.assertTrue(mygrp)
        return mygrp

    def test_resource_groups_replicas_on_same(self):
        grp_name = 'grp_replicas'
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'create', grp_name, '--place-count=2', '--replicas-on-same', 'x', 'y'])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual(['Aux/x', 'Aux/y'], mygrp['select_filter']['replicas_on_same'])

        # noop modify
        rsc_grp = self.execute_with_single_resp(['resource-group', 'modify', grp_name])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual(['Aux/x', 'Aux/y'], mygrp['select_filter']['replicas_on_same'])

        # add more replicas on same
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'modify', grp_name, '--replicas-on-same', 'x', 'y', 'z'])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual(['Aux/x', 'Aux/y', 'Aux/z'], mygrp['select_filter']['replicas_on_same'])

        # remove replicas on same
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'modify', grp_name, '--replicas-on-same='])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertTrue('replicas_on_same' not in mygrp['select_filter'])

        # delete mygrp
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'delete', grp_name])
        self.assertTrue(rsc_grp.is_success())

    def test_resource_groups_layer_list(self):
        grp_name = 'grp_layer_list'
        rsc_grp_res = self.execute_with_resp(
            ['resource-group', 'create', grp_name, '--place-count=2',
             '--storage-pool', 'mypool', '--layer-list', 'storage'])
        self.assert_apis_success(rsc_grp_res)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual('mypool', mygrp['select_filter']['storage_pool'])
        self.assertEqual(['storage'.upper()], mygrp['select_filter']['layer_stack'])

        # noop modify
        rsc_grp_resp = self.execute_with_resp(['resource-group', 'modify', grp_name])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual('mypool', mygrp['select_filter']['storage_pool'])
        self.assertEqual(['storage'.upper()], mygrp['select_filter']['layer_stack'])

        # add layerstack
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'modify', grp_name, '--layer-list', 'drbd,storage'])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual('mypool', mygrp['select_filter']['storage_pool'])
        self.assertEqual(['drbd'.upper(), 'storage'.upper()], mygrp['select_filter']['layer_stack'])

        # remove layerstack
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'modify', grp_name, '--layer-list='])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual('mypool', mygrp['select_filter']['storage_pool'])
        self.assertTrue('layer_stack' not in mygrp['select_filter'])

        # remove storage pool
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'modify', grp_name, '--storage-pool='])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertTrue('storage_pool' not in mygrp['select_filter'])
        self.assertTrue('layer_stack' not in mygrp['select_filter'])

        # delete mygrp
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'delete', grp_name])
        self.assertTrue(rsc_grp.is_success())

    def test_resource_groups_diskless_on_remaining(self):
        grp_name = 'grp_remaining'
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'create', grp_name, '--place-count=4', '--diskless-on-remaining'])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(4, mygrp['select_filter']['place_count'])
        self.assertTrue(mygrp['select_filter']['diskless_on_remaining'])

        # noop modify
        rsc_grp = self.execute_with_single_resp(['resource-group', 'modify', grp_name])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(4, mygrp['select_filter']['place_count'])
        self.assertTrue(mygrp['select_filter']['diskless_on_remaining'])

        # modify diskless on remaining
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'modify', grp_name, '--diskless-on-remaining', 'false'])
        self.assertTrue(rsc_grp.is_success())
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(4, mygrp['select_filter']['place_count'])
        self.assertFalse(mygrp['select_filter']['diskless_on_remaining'])

        # delete mygrp
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'delete', grp_name])
        self.assertTrue(rsc_grp.is_success())

    def test_resource_groups_storage_pools(self):
        grp_name = 'grp_storpool'
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'create', grp_name, '--place-count=2', '--storage-pool', 'xxx', 'yyy'])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual(['xxx', 'yyy'], mygrp['select_filter']['storage_pool_list'])

        # noop modify
        rsc_grp_resp = self.execute_with_resp(['resource-group', 'modify', grp_name])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual(['xxx', 'yyy'], mygrp['select_filter']['storage_pool_list'])

        # modify storagepools
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'modify', grp_name, '--storage-pool', 'xxx'])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertEqual('xxx', mygrp['select_filter']['storage_pool'])
        self.assertEqual(['xxx'], mygrp['select_filter']['storage_pool_list'])

        # modify storagepools
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'modify', grp_name, '--storage-pool', 'xxx', 'yyy', 'zzz'])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertFalse('storage_pool' in mygrp['select_filter'])
        self.assertEqual(['xxx', 'yyy', 'zzz'], mygrp['select_filter']['storage_pool_list'])

        # remove all storage pools
        rsc_grp_resp = self.execute_with_resp(
            ['resource-group', 'modify', grp_name, '--storage-pool='])
        self.assert_apis_success(rsc_grp_resp)
        mygrp = self.get_resource_group(grp_name)
        print(mygrp['select_filter'])
        self.assertEqual(2, mygrp['select_filter']['place_count'])
        self.assertFalse('storage_pool' in mygrp['select_filter'])
        self.assertFalse('storage_pool_list' in mygrp['select_filter'])

        # delete mygrp
        rsc_grp = self.execute_with_single_resp(
            ['resource-group', 'delete', grp_name])
        self.assertTrue(rsc_grp.is_success())


if __name__ == '__main__':
    unittest.main()
