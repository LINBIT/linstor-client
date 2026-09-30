import unittest

from linstor.responses import ResourceState
from linstor_client.commands import Commands
from linstor_client.consts import Color


class TestUsage(unittest.TestCase):

    def test_unknown(self):
        self.assertEqual(("", None), Commands.get_usage(None, 0))
        self.assertEqual(("", None), Commands.get_usage(ResourceState({}), 0))

    def test_in_use(self):
        state = ResourceState({"in_use": True, "open": True})
        self.assertEqual(("InUse", Color.GREEN), Commands.get_usage(state, 1))
        self.assertEqual(("InUse", Color.YELLOW), Commands.get_usage(state, 2))

    def test_open_while_secondary(self):
        self.assertEqual(("Open", Color.YELLOW), Commands.get_usage(ResourceState({"in_use": False, "open": True}), 0))

    def test_old_python_linstor_without_open(self):
        class OldResourceState(object):
            in_use = False

        self.assertEqual(("Unused", None), Commands.get_usage(OldResourceState(), 0))

    def test_unused(self):
        self.assertEqual(("Unused", None), Commands.get_usage(ResourceState({"in_use": False, "open": False}), 0))
        # older controllers do not report open
        self.assertEqual(("Unused", None), Commands.get_usage(ResourceState({"in_use": False}), 0))
