import unittest
from tests import LinstorTestCase
import linstor.sharedconsts as apiconsts


class TestNodeCommands(LinstorTestCase):

    def create_node(self, node_name, subip):
        node = self.execute_with_resp(['node', 'create', node_name, '195.0.0.' + str(subip)])
        self.assert_api_succuess(node[0])
        self.assertEqual(apiconsts.MASK_NODE | apiconsts.MASK_CRT | apiconsts.CREATED, node[0].ret_code)

    def test_create_node(self):
        node_name = 'nodeCommands1'
        self.create_node(node_name, 2)

        node_list = self.execute_with_machine_output(['node', 'list'])
        self.assertIsNotNone(node_list)
        self.assertIs(len(node_list), 1)
        node_list = node_list[0]
        self.assertTrue('nodes' in node_list)
        nodes = node_list['nodes']
        self.assertGreater(len(nodes), 0)
        self.assertTrue([n for n in nodes if n['name'] == node_name])

        # args = self.parse_args(['node', 'list'])  # any valid command, just need the parsed args object
        # completer_nodes = NodeCommands.node_completer('node1', parsed_args=args)
        # self.assertTrue('node1' in completer_nodes)

        retcode = self.execute(['node', 'delete', node_name])
        self.assertEqual(0, retcode)

    def find_node(self, nodelist, node_name):
        fnodes = [x for x in nodelist if x['name'] == node_name]
        if fnodes:
            self.assertEqual(1, len(fnodes))
            return fnodes[0]
        return None

    def assert_netinterface(self, netif_data, netif_name, netif_addr):
        self.assertEqual(netif_data['name'], netif_name)
        self.assertEqual(netif_data['address'], netif_addr)

    def assert_netinterfaces(self, node, expected_netifs):
        netifs = self.execute_with_machine_output(['node', 'interface', 'list', node])
        self.assertEqual(1, len(netifs))
        netifs = netifs[0]
        self.assertIn("nodes", netifs)
        nodes = netifs['nodes']
        node = self.find_node(nodes, 'nodenetif')
        self.assertIsNotNone(node)
        self.assertEqual(len(expected_netifs), len(node['net_interfaces']))
        netifs = node['net_interfaces']

        for i in range(0, len(expected_netifs)):
            self.assert_netinterface(netifs[i], expected_netifs[i][0], expected_netifs[i][1])

    def test_add_netif(self):
        self.create_node('nodenetif', 1)

        self.assert_netinterfaces('nodenetif', [("default", '195.0.0.1')])

        netif = self.execute_with_single_resp(['node', 'interface', 'create', 'nodenetif', 'othernic', '10.0.0.1'])
        self.assert_api_succuess(netif)
        self.assertEqual(apiconsts.MASK_NET_IF | apiconsts.MASK_CRT | apiconsts.CREATED, netif.ret_code)

        self.assert_netinterfaces('nodenetif', [("default", '195.0.0.1'), ("othernic", '10.0.0.1')])

        # modify netif
        netif = self.execute_with_single_resp(
            ['node', 'interface', 'modify', 'nodenetif', 'othernic', '--ip', '192.168.0.1']
        )
        self.assert_api_succuess(netif)
        self.assertEqual(apiconsts.MASK_NET_IF | apiconsts.MASK_MOD | apiconsts.MODIFIED, netif.ret_code)

        self.assert_netinterfaces('nodenetif', [("default", '195.0.0.1'), ("othernic", '192.168.0.1')])

        # delete netif
        netif = self.execute_with_single_resp(['node', 'interface', 'delete', 'nodenetif', 'othernic'])
        self.assert_api_succuess(netif)
        self.assertEqual(apiconsts.MASK_NET_IF | apiconsts.MASK_DEL | apiconsts.DELETED, netif.ret_code)

        self.assert_netinterfaces('nodenetif', [("default", '195.0.0.1')])

    def get_nodes(self, args=None):
        cmd = ['node', 'list']
        if args:
            cmd += args
        node_list = self.execute_with_machine_output(cmd)
        self.assertIsNotNone(node_list)
        self.assertIs(len(node_list), 1)
        return node_list[0]['nodes']

    def test_property_filtering(self):
        self.create_node('alpha', 50)
        self.create_node('bravo', 51)
        self.create_node('charly', 52)
        self.create_node('delta', 53)

        node_resp = self.execute_with_resp(['node', 'set-property', 'alpha', '--aux', 'site', 'a'])
        self.assert_apis_success(node_resp)

        node_resp = self.execute_with_resp(['node', 'set-property', 'bravo', '--aux', 'site', 'a'])
        self.assert_apis_success(node_resp)

        node_resp = self.execute_with_resp(['node', 'set-property', 'charly', '--aux', 'site', 'b'])
        self.assert_apis_success(node_resp)

        node_resp = self.execute_with_resp(['node', 'set-property', 'delta', '--aux', 'site', 'b'])
        self.assert_apis_success(node_resp)

        node_resp = self.execute_with_resp(['node', 'set-property', 'delta', '--aux', 'disks', 'fast'])
        self.assert_apis_success(node_resp)

        nodes = self.get_nodes(['--props', 'Aux/site=b', '--props', 'Aux/disks'])
        self.assertEqual(len(nodes), 1, "Only delta node expected")
        self.assertEqual("delta", nodes[0]['name'])

        nodes = self.get_nodes(['--props', 'Aux/site=a'])
        self.assertEqual(len(nodes), 2, "Only alpha, bravo nodes expected")
        self.assertEqual({'alpha', 'bravo'}, {x['name'] for x in nodes})

        # delete nodes
        for node_name in ['alpha', 'bravo', 'charly', 'delta']:
            retcode = self.execute(['node', 'delete', node_name])
            self.assertEqual(0, retcode)


if __name__ == '__main__':
    unittest.main()
