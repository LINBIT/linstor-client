import unittest
from . import test_utils
from . import test_ctrl_list_commands, test_ctrl_nodes, test_ctrl_usecases, test_utils, test_ctrl_props

_controller_tests = [
    "tests.test_ctrl_list_commands",
    "tests.test_ctrl_nodes",
    "tests.test_ctrl_usecases",
    "tests.test_ctrl_props"
]

_std_tests = [
    "tests.test_utils",
    "tests.test_client_commands"
]


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    loaded_tests = loader.loadTestsFromNames(_controller_tests + _std_tests)
    suite.addTest(loaded_tests)
    return suite


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
