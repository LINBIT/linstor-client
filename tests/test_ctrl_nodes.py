import unittest
from tests import LinstorTestCase
import linstor.sharedconsts as apiconsts


class TestNodeCommands(LinstorTestCase):

    def test_create_node(self):
        node_name = 'nodeCommands1'
        retcode = self.execute(['node', 'create', node_name, '192.168.100.1'])
        self.assertEqual(0, retcode)

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
        node = self.execute_with_resp(['node', 'create', 'nodenetif', '195.0.0.1'])
        self.assert_api_succuess(node[0])
        self.assertEqual(apiconsts.MASK_NODE | apiconsts.MASK_CRT | apiconsts.CREATED, node[0].ret_code)

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

"""
class TestDescribe(LinstorTestCaseWithData):
    def test_describe_node(self):
        nodes = self.execute_with_machine_output(['node', 'describe'])
        self.assertEqual(4, len(nodes))

        nodes = self.execute_with_machine_output(['node', 'describe', 'fakehost1'])
        self.assertEqual(1, len(nodes))

        nodes = self.execute_with_machine_output(['node', 'describe', 'asdofk'])
        self.assertFalse(nodes)

        self.assertNotEqual(0, self.execute(['node', 'describe', 'daskl']))
"""

if __name__ == '__main__':
    unittest.main()
