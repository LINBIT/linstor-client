from tests import LinstorTestCase
import linstor.sharedconsts as apiconsts


class TestListFilters(LinstorTestCase):
    def get_resource_dfn_properties(self, rsc_dfn_name):
        resourcedef_props = self.execute_with_machine_output(['resource-definition', 'list-properties', rsc_dfn_name])
        self.assertEqual(1, len(resourcedef_props))
        return resourcedef_props[0]

    def get_volume_dfn_properties(self, rsc_dfn_name, vlm_nr):
        volumedef_props = self.execute_with_machine_output(
            ['volume-definition', 'list-properties', rsc_dfn_name, vlm_nr]
        )
        self.assertEqual(1, len(volumedef_props))
        return volumedef_props[0]

    def get_resource_conn_properties(self, node_a, node_b, rsc_name):
        res_con_props = self.execute_with_machine_output(
            ['resource-connection', 'list-properties', node_a, node_b, rsc_name]
        )
        self.assertEqual(1, len(res_con_props))
        return res_con_props[0]

    def test_resource_protocol(self):
        """symbolic option test"""
        rsc_name = "resource-protocol"

        self.execute(['resource-definition', 'create', rsc_name])

        resp = self.execute_with_resp(['resource-definition', 'drbd-options', '--protocol', 'A', rsc_name])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_RSC_DFN, resp_upd.ret_code)

        resourcedef_props = self.get_resource_dfn_properties(rsc_name)
        self.find_and_check_prop(resourcedef_props, apiconsts.NAMESPC_DRBD_NET_OPTIONS + '/protocol', 'A')

        resp = self.execute_with_resp(['resource-definition', 'drbd-options', '--protocol', 'C', rsc_name])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_RSC_DFN, resp_upd.ret_code)

        resourcedef_props = self.get_resource_dfn_properties(rsc_name)
        self.find_and_check_prop(resourcedef_props, apiconsts.NAMESPC_DRBD_NET_OPTIONS + '/protocol', 'C')

        self.execute(['resource-definition', 'delete', rsc_name])

    def test_resource_mdflushes(self):
        """Boolean option test"""
        rsc_name = "resource-mdflushes"
        self.execute(['resource-definition', 'create', rsc_name])

        resp = self.execute_with_resp(['resource-definition', 'drbd-options', '--md-flushes', 'no', rsc_name])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_RSC_DFN, resp_upd.ret_code)

        resourcedef_props = self.get_resource_dfn_properties(rsc_name)
        self.find_and_check_prop(resourcedef_props, apiconsts.NAMESPC_DRBD_DISK_OPTIONS + '/md-flushes', 'no')

        resp = self.execute_with_resp(['resource-definition', 'drbd-options', '--md-flushes', 'yes', rsc_name])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_RSC_DFN, resp_upd.ret_code)

        resourcedef_props = self.get_resource_dfn_properties(rsc_name)
        self.find_and_check_prop(resourcedef_props, apiconsts.NAMESPC_DRBD_DISK_OPTIONS + '/md-flushes', 'yes')

        self.execute(['resource-definition', 'delete', rsc_name])

    def test_resource_disktimeout(self):
        """Numeric option test"""
        rsc_name = "resource-mdflushes"
        self.execute(['resource-definition', 'create', rsc_name])

        resp = self.execute_with_resp(['resource-definition', 'drbd-options', '--disk-timeout', '5000', rsc_name])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_RSC_DFN, resp_upd.ret_code)

        resourcedef_props = self.get_resource_dfn_properties(rsc_name)
        self.find_and_check_prop(resourcedef_props, apiconsts.NAMESPC_DRBD_DISK_OPTIONS + '/disk-timeout', '5000')

        resp = self.execute_with_resp(['resource-definition', 'drbd-options', '--disk-timeout', '0', rsc_name])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_RSC_DFN, resp_upd.ret_code)

        resourcedef_props = self.get_resource_dfn_properties(rsc_name)
        self.find_and_check_prop(resourcedef_props, apiconsts.NAMESPC_DRBD_DISK_OPTIONS + '/disk-timeout', '0')

        self.execute(['resource-definition', 'delete', rsc_name])

    def test_volume_on_io_error(self):
        rsc_name = "resource-volume-io-error"
        self.execute(['resource-definition', 'create', rsc_name])
        self.execute(['volume-definition', 'create', rsc_name, "20M"])

        resp = self.execute_with_resp(['volume-definition', 'drbd-options', '--on-io-error', 'detach', rsc_name, '0'])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_VLM_DFN, resp_upd.ret_code)

        volumedef_props = self.get_volume_dfn_properties(rsc_name, '0')
        self.find_and_check_prop(volumedef_props, apiconsts.NAMESPC_DRBD_DISK_OPTIONS + '/on-io-error', 'detach')

        resp = self.execute_with_resp(['volume-definition', 'drbd-options', '--on-io-error', 'pass_on', rsc_name, '0'])
        self.assertGreater(len(resp), 1)
        resp_upd = resp[1]
        self.assertEqual(apiconsts.MODIFIED | apiconsts.MASK_MOD | apiconsts.MASK_VLM_DFN, resp_upd.ret_code)

        volumedef_props = self.get_volume_dfn_properties(rsc_name, '0')
        self.find_and_check_prop(volumedef_props, apiconsts.NAMESPC_DRBD_DISK_OPTIONS + '/on-io-error', 'pass_on')

        self.execute(['resource-definition', 'delete', rsc_name])
