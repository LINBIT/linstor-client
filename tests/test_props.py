from .linstor_testcase import LinstorTestCase
from linstor.sharedconsts import *


class TestProperties(LinstorTestCase):
    NAMESPC_AUX = "aux"

    def find_prop(self, props, key):
        for prop in props:
            self.assertIn('key', prop)
            if key == prop['key']:
                return prop

        self.assertTrue(False, "Property '{key}' not found.".format(key=key))

    def check_prop(self, prop, key, value):
        self.assertEqual(2, len(prop.keys()))
        self.assertIn('key', prop)
        self.assertIn('value', prop)
        self.assertEqual(key, prop['key'])
        self.assertEqual(value, prop['value'])

    def test_set_properties(self):
        # create all object kinds
        cnode_resp = self.execute_with_single_resp(['create-node', 'node1', '192.168.100.1'])
        self.assertTrue(cnode_resp.is_success())

        # create storagepool
        storpool_resps = self.execute_with_resp(['create-storage-pool', 'storage', 'node1', 'lvm', 'lvmpool'])
        self.assertTrue(storpool_resps[0].is_warning())
        self.assertEqual(WARN_NOT_CONNECTED | MASK_STOR_POOL | MASK_CRT, storpool_resps[0].ret_code)
        self.assertTrue(storpool_resps[1].is_success())

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

        # start prop tests
        node_resp = self.execute_with_single_resp(
            ['set-node-prop', 'node1', TestProperties.NAMESPC_AUX + '/test_prop=val']
        )
        self.assertTrue(node_resp.is_success())

        node_props = self.execute_with_machine_output(['get-node-prop', 'node1'])
        self.assertEqual(1, len(node_props))
        node_props = node_props[0]
        self.assertEqual(1, len(node_props))
        prop = self.find_prop(node_props, TestProperties.NAMESPC_AUX + '/test_prop')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/test_prop', 'val')

        node_resp = self.execute_with_single_resp(
            ['set-node-prop', 'node1', TestProperties.NAMESPC_AUX + '/another_prop=value with spaces']
        )
        self.assertTrue(node_resp.is_success())

        node_props = self.execute_with_machine_output(['get-node-prop', 'node1'])
        self.assertEqual(1, len(node_props))
        node_props = node_props[0]
        self.assertEqual(2, len(node_props))
        prop = self.find_prop(node_props, TestProperties.NAMESPC_AUX + '/test_prop')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/test_prop', 'val')

        prop = self.find_prop(node_props, TestProperties.NAMESPC_AUX + '/another_prop')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/another_prop', 'value with spaces')

        # storage pool definition props
        storage_resp = self.execute_with_single_resp(
            ['set-storage-pool-definition-prop', 'DfltStorPool', TestProperties.NAMESPC_AUX + '/stor=lvmcomplex']
        )
        self.assertTrue(storage_resp.is_success())

        storage_props = self.execute_with_machine_output(['get-storage-pool-definition-prop', 'DfltStorPool'])
        self.assertEqual(1, len(storage_props))
        storage_props = storage_props[0]
        self.assertEqual(1, len(storage_props))
        prop = self.find_prop(storage_props, TestProperties.NAMESPC_AUX + '/stor')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/stor', 'lvmcomplex')

        # storage pool props
        storage_props = self.execute_with_machine_output(['get-storage-pool-prop', 'storage', 'node1'])
        self.assertEqual(1, len(storage_props))
        storage_props = storage_props[0]
        self.assertEqual(1, len(storage_props))
        prop = self.find_prop(storage_props, NAMESPC_STORAGE_DRIVER + '/LvmVg')
        self.check_prop(prop, NAMESPC_STORAGE_DRIVER + '/LvmVg', 'lvmpool')

        storage_resp = self.execute_with_resp(
            ['set-storage-pool-prop', 'storage', 'node1', TestProperties.NAMESPC_AUX + '/stor=lvmcomplex']
        )
        self.assertEqual(2, len(storage_resp))
        self.assertTrue(storage_resp[0].is_success())

        storage_props = self.execute_with_machine_output(['get-storage-pool-prop', 'storage', 'node1'])
        self.assertEqual(1, len(storage_props))
        storage_props = storage_props[0]
        self.assertEqual(2, len(storage_props))
        prop = self.find_prop(storage_props, NAMESPC_STORAGE_DRIVER + '/LvmVg')
        self.check_prop(prop, NAMESPC_STORAGE_DRIVER + '/LvmVg', 'lvmpool')

        prop = self.find_prop(storage_props, TestProperties.NAMESPC_AUX + '/stor')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/stor', 'lvmcomplex')

        # resource definition
        storage_resp = self.execute_with_resp(
            ['set-resource-definition-prop', 'rsc1', TestProperties.NAMESPC_AUX + '/user=alexa']
        )
        self.assertEqual(2, len(storage_resp))
        self.assertTrue(storage_resp[0].is_success())

        storage_props = self.execute_with_machine_output(['get-resource-definition-prop', 'rsc1'])
        self.assertEqual(1, len(storage_props))
        storage_props = storage_props[0]
        self.assertEqual(1, len(storage_props))
        prop = self.find_prop(storage_props, TestProperties.NAMESPC_AUX + '/user')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/user', 'alexa')

        # resource
        resource_props = self.execute_with_machine_output(['get-resource-prop', 'rsc1', 'node1'])
        self.assertEqual(1, len(resource_props))
        resource_props = resource_props[0]
        self.assertEqual(1, len(resource_props))
        prop = self.find_prop(resource_props, KEY_STOR_POOL_NAME)
        self.check_prop(prop, KEY_STOR_POOL_NAME, 'storage')

        storage_resp = self.execute_with_resp(
            ['set-resource-prop', 'rsc1', 'node1', TestProperties.NAMESPC_AUX + '/NIC=10.0.0.1']
        )
        self.assertEqual(2, len(storage_resp))
        self.assertTrue(storage_resp[0].is_warning())
        self.assertTrue(storage_resp[1].is_success())

        resource_props = self.execute_with_machine_output(['get-resource-prop', 'rsc1', 'node1'])
        self.assertEqual(1, len(resource_props))
        resource_props = resource_props[0]
        self.assertEqual(2, len(resource_props))
        prop = self.find_prop(resource_props, KEY_STOR_POOL_NAME)
        self.check_prop(prop, KEY_STOR_POOL_NAME, 'storage')
        prop = self.find_prop(resource_props, TestProperties.NAMESPC_AUX + '/NIC')
        self.check_prop(prop, TestProperties.NAMESPC_AUX + '/NIC', '10.0.0.1')
