import unittest
from linstor_testcase import LinstorTestCase


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
        retcode = self.execute(['create-node', 'node1', '192.168.100.1'])
        self.assertEqual(0, retcode)

        node_list = self.execute_with_maschine_output(['list-nodes'])
        self.assertIsNotNone(node_list)
        self.assertTrue('nodes' in node_list)
        nodes = node_list['nodes']
        self.assertGreater(len(nodes), 0)
        self.assertTrue([n for n in nodes if n['name'] == 'node1'])

        # create storagepool
        retcode = self.execute(['create-storage-pool', 'storage', 'node1', 'lvm', '/dev/lvmpool'])
        self.assertEqual(0, retcode)

        # check
        storagepool_list = self.execute_with_maschine_output(['list-storage-pools'])
        self.assertIsNotNone(storagepool_list)
        self.assertTrue('storPools' in storagepool_list)
        stor_pools = storagepool_list['storPools']
        self.assertEqual(len(stor_pools), 1)
        stor_pool = stor_pools[0]
        self.assertEqual('node1', stor_pool['nodeName'])
        self.assertEqual('LvmDriver', stor_pool['driver'])
        self.assertEqual('storage', stor_pool['storPoolName'])
        self.assertHasProp(stor_pool['props'], 'LvmVg', '/dev/lvmpool')

        # create resource def
        retcode = self.execute(['create-resource-definition', 'rsc1'])
        self.assertEqual(0, retcode)

        # create volume def
        retcode = self.execute(['create-volume-definition', 'rsc1', '1Gib'])
        self.assertEqual(0, retcode)

        # create resource on node1
        retcode = self.execute(['create-resource', '-s', 'storage', 'rsc1', 'node1'])
        self.assertEqual(0, retcode)

        # check resource
        resource_list = self.execute_with_maschine_output(['list-resources'])
        self.assertIsNotNone(resource_list)
        self.assertIn('resources', resource_list)
        resources = resource_list['resources']
        self.assertEqual(len(resources), 1)
        rsc1 = resources[0]
        self.assertEqual(rsc1['name'], 'rsc1')
        self.assertIn('vlms', rsc1)
        vlms = rsc1['vlms']
        self.assertEqual(len(vlms), 1)
        self.assertEqual(vlms[0]['vlmNr'], 0)

    def test_delete_resource(self):
        retcode = self.execute(['delete-resource', 'rsc1', 'node1'])
        self.assertEqual(0, retcode)

        # self.execute(['list-resource', '-m', 'json'])


if __name__ == '__main__':
    unittest.main()
