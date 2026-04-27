import unittest

from linstor_client.commands.snapshot_cmds import (
    _extract_shipping,
    _format_shipping_cell,
    _shipping_color,
    _worst_shipping_status,
)
from linstor_client.consts import Color


class TestExtractShipping(unittest.TestCase):

    def test_empty_props(self):
        sources, target = _extract_shipping({})
        self.assertEqual([], sources)
        self.assertIsNone(target)

    def test_single_source(self):
        props = {"BackupShipping/Source/r1/ShippingStatus": "Shipping"}
        sources, target = _extract_shipping(props)
        self.assertEqual([("r1", "Shipping")], sources)
        self.assertIsNone(target)

    def test_multi_source(self):
        props = {
            "BackupShipping/Source/r1/ShippingStatus": "Success",
            "BackupShipping/Source/r2/ShippingStatus": "Aborted",
            "BackupShipping/Source/r3/ShippingStatus": "Shipping",
        }
        sources, target = _extract_shipping(props)
        self.assertEqual(
            sorted([("r1", "Success"), ("r2", "Aborted"), ("r3", "Shipping")]),
            sorted(sources),
        )
        self.assertIsNone(target)

    def test_target_with_src_remote(self):
        props = {
            "BackupShipping/Target/ShippingStatus": "Shipping",
            "BackupShipping/Target/BackupSrcRemote": "remote-eu",
        }
        sources, target = _extract_shipping(props)
        self.assertEqual([], sources)
        self.assertEqual(("remote-eu", "Shipping"), target)

    def test_target_without_src_remote(self):
        props = {"BackupShipping/Target/ShippingStatus": "Failed"}
        sources, target = _extract_shipping(props)
        self.assertEqual([], sources)
        self.assertEqual((None, "Failed"), target)

    def test_source_and_target(self):
        props = {
            "BackupShipping/Source/r1/ShippingStatus": "Shipping",
            "BackupShipping/Target/ShippingStatus": "Aborted",
            "BackupShipping/Target/BackupSrcRemote": "remote-eu",
        }
        sources, target = _extract_shipping(props)
        self.assertEqual([("r1", "Shipping")], sources)
        self.assertEqual(("remote-eu", "Aborted"), target)

    def test_ignores_other_keys_in_namespace(self):
        props = {
            "BackupShipping/Source/r1/ShippingStatus": "Success",
            "BackupShipping/Source/r1/SrcNode": "node-a",
            "BackupShipping/Source/r1/BackupStartTimestamp": "12345",
            "BackupShipping/BackupTimeout": "60",
            "Aux/something": "x",
        }
        sources, target = _extract_shipping(props)
        self.assertEqual([("r1", "Success")], sources)
        self.assertIsNone(target)


class TestShippingColor(unittest.TestCase):

    def test_red_values(self):
        self.assertEqual(Color.RED, _shipping_color("Aborted"))
        self.assertEqual(Color.RED, _shipping_color("Failed"))

    def test_yellow_values(self):
        for s in ("Shipping", "Prepare Shipping", "Prepare Abort", "Aborting"):
            self.assertEqual(Color.YELLOW, _shipping_color(s))

    def test_unknown_status_yellow(self):
        self.assertEqual(Color.YELLOW, _shipping_color("SomethingNew"))


class TestWorstShippingStatus(unittest.TestCase):

    def test_in_progress_beats_failed(self):
        self.assertEqual("Shipping", _worst_shipping_status(["Shipping", "Failed"]))

    def test_only_failures_picks_either(self):
        # Aborted and Failed share priority 1 — either is acceptable.
        self.assertIn(_worst_shipping_status(["Aborted", "Failed"]), ("Aborted", "Failed"))

    def test_unknown_treated_as_in_progress(self):
        # unknown maps to priority 0, same as in-progress; with min() it should
        # not lose to Aborted (priority 1).
        self.assertEqual("Mystery", _worst_shipping_status(["Mystery", "Aborted"]))


class TestFormatShippingCell(unittest.TestCase):

    def test_no_shipping_returns_none(self):
        self.assertIsNone(_format_shipping_cell([], None))

    def test_only_success_returns_none(self):
        # All Success entries are filtered out -> caller falls through to "Successful".
        sources = [("r1", "Success"), ("r2", "Success")]
        target = ("remote-eu", "Success")
        self.assertIsNone(_format_shipping_cell(sources, target))

    def test_uploading_metadata_treated_as_success(self):
        # "Uploading Metadata" is an internal intermediate state; it should not
        # be surfaced and should not block the fall-through to "Successful".
        sources = [("r1", "Success"), ("r2", "Uploading Metadata")]
        target = (None, "Uploading Metadata")
        self.assertIsNone(_format_shipping_cell(sources, target))

    def test_single_source_in_progress(self):
        text, color = _format_shipping_cell([("r1", "Shipping")], None)
        self.assertEqual("Ship(r1): Shipping", text)
        self.assertEqual(Color.YELLOW, color)

    def test_single_source_failed(self):
        text, color = _format_shipping_cell([("r1", "Failed")], None)
        self.assertEqual("Ship(r1): Failed", text)
        self.assertEqual(Color.RED, color)

    def test_multi_source_filters_success(self):
        sources = [("r1", "Success"), ("r2", "Aborted"), ("r3", "Shipping")]
        text, color = _format_shipping_cell(sources, None)
        self.assertEqual("Ship(r2): Aborted\nShip(r3): Shipping", text)
        # Worst among visible (Aborted, Shipping) -> in-progress wins -> yellow.
        self.assertEqual(Color.YELLOW, color)

    def test_multi_source_only_failures(self):
        sources = [("r1", "Aborted"), ("r2", "Failed")]
        text, color = _format_shipping_cell(sources, None)
        self.assertEqual("Ship(r1): Aborted\nShip(r2): Failed", text)
        self.assertEqual(Color.RED, color)

    def test_target_with_src_remote(self):
        text, color = _format_shipping_cell([], ("remote-eu", "Shipping"))
        self.assertEqual("Restore(remote-eu): Shipping", text)
        self.assertEqual(Color.YELLOW, color)

    def test_target_without_src_remote(self):
        text, color = _format_shipping_cell([], (None, "Failed"))
        self.assertEqual("Restore: Failed", text)
        self.assertEqual(Color.RED, color)

    def test_target_success_is_filtered(self):
        self.assertIsNone(_format_shipping_cell([], ("remote-eu", "Success")))

    def test_source_and_target_combined_multiline(self):
        sources = [("r1", "Success"), ("r2", "Failed")]
        target = ("remote-eu", "Shipping")
        text, color = _format_shipping_cell(sources, target)
        self.assertEqual(
            "Ship(r2): Failed\nRestore(remote-eu): Shipping",
            text,
        )
        # Failed (red) + Shipping (yellow) -> worst-priority is Shipping -> yellow.
        self.assertEqual(Color.YELLOW, color)

    def test_unknown_status_does_not_crash(self):
        text, color = _format_shipping_cell([("r1", "FutureStatus")], None)
        self.assertEqual("Ship(r1): FutureStatus", text)
        self.assertEqual(Color.YELLOW, color)


if __name__ == "__main__":
    unittest.main()
