import os
import tempfile
import unittest
from unittest import mock

import linstor_client_main
from linstor_client_main import LinStorCLI


class TestRuntimeConf(unittest.TestCase):
    """
    A satellite publishes the controller it is connected to in /run/linstor/linstor-client.conf.
    The client uses that as the source for 'controllers' when no linstor-client.conf provided
    one, so a node running a satellite does not have to be configured by hand.
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.runtime_conf = os.path.join(self.tmp_dir.name, "linstor-client.conf")
        patcher = mock.patch.object(LinStorCLI, 'RUNTIME_CONF_PATH', self.runtime_conf)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_runtime_conf(self, content):
        with open(self.runtime_conf, 'w') as f:
            f.write(content)

    def merge(self, global_entries):
        with mock.patch.object(linstor_client_main.linstor.Config, 'get_section', return_value=global_entries):
            return LinStorCLI.merge_config_arguments([])

    def test_no_file_has_no_controllers(self):
        self.assertIsNone(LinStorCLI.runtime_controllers())

    def test_reads_the_published_controller(self):
        self.write_runtime_conf("[global]\ncontrollers = linstor://10.43.0.7\n")
        self.assertEqual('linstor://10.43.0.7', LinStorCLI.runtime_controllers())

    def test_file_without_controllers_entry(self):
        self.write_runtime_conf("[global]\n")
        self.assertIsNone(LinStorCLI.runtime_controllers())

    def test_malformed_file_is_ignored(self):
        self.write_runtime_conf("this is not a config file\n")
        self.assertIsNone(LinStorCLI.runtime_controllers())

    def test_used_when_the_config_has_no_controllers(self):
        self.write_runtime_conf("[global]\ncontrollers = linstor://10.43.0.7\n")
        self.assertEqual(['--controllers', 'linstor://10.43.0.7'], self.merge({}))

    def test_configured_controllers_win(self):
        self.write_runtime_conf("[global]\ncontrollers = linstor://10.43.0.7\n")
        self.assertEqual(
            ['--controllers', 'linstor://configured'],
            self.merge({'controllers': 'linstor://configured'})
        )

    def test_nothing_published_keeps_the_config_untouched(self):
        self.assertEqual([], self.merge({}))
