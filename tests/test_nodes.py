import unittest
from .linstor_testcase import LinstorTestCase
from linstor.commands import NodeCommands


class TestNodeCommands(LinstorTestCase):

    def test_create_node(self):
        retcode = self.execute(['create-node', 'node1', '192.168.100.1'])
        self.assertEqual(0, retcode)

        node_list = self.execute_with_maschine_output(['list-nodes'])
        self.assertIsNotNone(node_list)
        self.assertIs(len(node_list), 1)
        node_list = node_list[0]
        self.assertTrue('nodes' in node_list)
        nodes = node_list['nodes']
        self.assertGreater(len(nodes), 0)
        self.assertTrue([n for n in nodes if n['name'] == 'node1'])

        args = self.parse_args(['list-nodes'])  # any valid command, just need the parsed args object
        completer_nodes = NodeCommands.completer('node1', parsed_args=args)
        self.assertTrue('node1' in completer_nodes)

        retcode = self.execute(['delete-node', 'node1'])
        self.assertEqual(0, retcode)


if __name__ == '__main__':
    unittest.main()
