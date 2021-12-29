import unittest
from .linstor_testcase import LinstorTestCase
from . import test_ctrl_list_commands, test_ctrl_nodes, test_ctrl_usecases
from . import test_ctrl_props, test_drbd_options

_controller_tests = [
    "tests.test_ctrl_list_commands",
    "tests.test_ctrl_nodes",
    "tests.test_ctrl_usecases",
    "tests.test_ctrl_props",
    "tests.test_drbd_options"
]

_std_tests = [
    "tests.test_client_commands",
    "tests.test_tables"
]


def load_all():
    suite = unittest.TestSuite()
    loaded_tests = unittest.defaultTestLoader.loadTestsFromNames(_controller_tests + _std_tests)
    suite.addTest(loaded_tests)
    return suite


def test_without_controller():
    suite = unittest.TestSuite()
    loaded_tests = unittest.defaultTestLoader.loadTestsFromNames(_std_tests)
    suite.addTest(loaded_tests)
    return suite
