import unittest
from linstor_client import TableHeader, Table
from linstor_client.consts import Color


class TestUtils(unittest.TestCase):

    @unittest.skip("jenkins is not happy about the color codes")
    def test_cell_color(self):
        tbl = Table(colors=True, utf8=False)
        tbl.add_header(TableHeader("FirstName"))
        tbl.add_header(TableHeader("LastName"))
        tbl.add_header(TableHeader("Age"))
        tbl.add_header(TableHeader("Comment"))

        tbl.add_row(["Max", "Mustermann", tbl.color_cell("62", Color.RED), ""])
        tbl.add_row(["Heinrich", "Mueller", "29", ""])
        tbl.show()

    def test_row_expand(self):
        multirow = Table._row_expand(
            [
                "column1_line1\ncolumn1_line2",
                "column2_line1",
                "column3_line1\ncolumn3_line2\ncolumn3_line3"
            ]
        )
        self.assertListEqual(
            [
                ["column1_line1", "column2_line1", "column3_line1"],
                ["column1_line2", "", "column3_line2"],
                ["", "", "column3_line3"]
            ],
            multirow
        )

    def test_multiline_colums(self):
        tbl = Table()
        tbl.add_header(TableHeader("id"))
        tbl.add_header(TableHeader("description"))
        tbl.add_header(TableHeader("text"))

        tbl.add_row([
            "0",
            "In a land far far away in a time long long ago\nThere were 3 pigs with 3 wigs and a chair to despair\n"
            "in a house with no mouse.",
            "PlaceCount: 2\nDisklessOnRemaining: True\nStoragePool: DfltStorPool\nLayerList: storage,drbd"]
        )
        table_out = tbl.show()

        self.assertEqual(
            """+---------------------------------------------------------------------------------------+
| id | description                                          | text                      |
|=======================================================================================|
| 0  | In a land far far away in a time long long ago       | PlaceCount: 2             |
|    | There were 3 pigs with 3 wigs and a chair to despair | DisklessOnRemaining: True |
|    | in a house with no mouse.                            | StoragePool: DfltStorPool |
|    |                                                      | LayerList: storage,drbd   |
+---------------------------------------------------------------------------------------+
""",
            table_out
        )

        tbl = Table()
        tbl.add_header(TableHeader("id"))
        tbl.add_header(TableHeader("vlmgroups"))
        tbl.add_header(TableHeader("text"))
        tbl.add_header(TableHeader("description"))

        tbl.add_row([
            "DfltRscGrp",
            "",
            "",
            ""
        ])
        tbl.add_row([
            "testrg",
            "0",
            "PlaceCount: 2\nStoragePool: DfltStorPool",
            "bla"
        ])

        table_out = tbl.show()

        self.assertEqual(
            """+------------------------------------------------------------------+
| id         | vlmgroups | text                      | description |
|==================================================================|
| DfltRscGrp |           |                           |             |
|------------------------------------------------------------------|
| testrg     | 0         | PlaceCount: 2             | bla         |
|            |           | StoragePool: DfltStorPool |             |
+------------------------------------------------------------------+
""",
            table_out
        )

    def test_groupby_single_column(self):
        """Test sorting by a single column."""
        tbl = Table(utf8=False)
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Category"))
        tbl.add_header(TableHeader("Value"))

        # Add rows in unsorted order
        tbl.add_row(["Charlie", "B", "30"])
        tbl.add_row(["Alice", "A", "10"])
        tbl.add_row(["Bob", "A", "20"])

        tbl.set_groupby(["Name"])
        table_out = tbl.show()

        # Rows should be sorted alphabetically by Name
        # No separators between rows since each Name is unique (each is its own group)
        self.assertEqual(
            """+----------------------------+
| Name    | Category | Value |
|============================|
| Alice   | A        | 10    |
| Bob     | A        | 20    |
| Charlie | B        | 30    |
+----------------------------+
""",
            table_out
        )

    def test_groupby_multiple_columns(self):
        """Test sorting by multiple columns."""
        tbl = Table(utf8=False)
        tbl.add_header(TableHeader("Category"))
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))

        # Add rows in unsorted order
        tbl.add_row(["B", "Zoe", "50"])
        tbl.add_row(["A", "Charlie", "30"])
        tbl.add_row(["A", "Alice", "10"])
        tbl.add_row(["B", "Bob", "40"])
        tbl.add_row(["A", "Bob", "20"])

        tbl.set_groupby(["Category", "Name"])
        table_out = tbl.show()

        # Rows should be sorted by Category first, then by Name
        # Separator appears when Category changes (between A and B groups)
        self.assertEqual(
            """+----------------------------+
| Category | Name    | Value |
|============================|
| A        | Alice   | 10    |
| A        | Bob     | 20    |
| A        | Charlie | 30    |
| B        | Bob     | 40    |
| B        | Zoe     | 50    |
+----------------------------+
""",
            table_out
        )

    def test_groupby_with_numeric_values(self):
        """Test numeric sorting - requires natsort, otherwise sorts lexicographically."""
        tbl = Table(utf8=False)
        tbl.add_header(TableHeader("Id"))
        tbl.add_header(TableHeader("Name"))

        # Add rows with numeric IDs in unsorted order
        tbl.add_row(["2", "Two"])
        tbl.add_row(["10", "Ten"])
        tbl.add_row(["1", "One"])

        tbl.set_groupby(["Id"])
        table_out = tbl.show()

        try:
            import natsort  # noqa: F401
            # With natsort: sorted numerically (1, 2, 10)
            expected = """+-----------+
| Id | Name |
|===========|
| 1  | One  |
| 2  | Two  |
| 10 | Ten  |
+-----------+
"""
        except ImportError:
            # Without natsort: sorted lexicographically (1, 10, 2)
            expected = """+-----------+
| Id | Name |
|===========|
| 1  | One  |
| 10 | Ten  |
| 2  | Two  |
+-----------+
"""

        self.assertEqual(expected, table_out)

    def test_groupby_case_insensitive(self):
        """Test that groupby column names are case-insensitive."""
        tbl = Table(utf8=False)
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))

        tbl.add_row(["Bob", "20"])
        tbl.add_row(["Alice", "10"])

        # Use lowercase column name
        tbl.set_groupby(["name"])
        table_out = tbl.show()

        # Should still sort correctly
        self.assertEqual(
            """+---------------+
| Name  | Value |
|===============|
| Alice | 10    |
| Bob   | 20    |
+---------------+
""",
            table_out
        )

    def test_shrink_columns_no_shrink_needed(self):
        """Table fits within maxwidth - no shrinking."""
        tbl = Table(utf8=False, truncate=True)
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))
        # overhead = 3 * 2 + 1 = 7
        # columnmax = [10, 10], sum = 20, total = 27
        columnmax = [10, 10]
        result = tbl._shrink_columns(columnmax, maxwidth=40)
        self.assertEqual([10, 10], result)

    def test_shrink_columns_proportional(self):
        """Two equally wide columns should be shrunk equally."""
        tbl = Table(utf8=False, truncate=True)
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))
        # overhead = 3 * 2 + 1 = 7
        # columnmax = [50, 50], sum = 100, total = 107
        # available content = 80 - 7 = 73
        # both columns above floor (10), both shrinkable
        # each gets 73 * 50/100 = 36.5 -> 36 and 37
        columnmax = [50, 50]
        result = tbl._shrink_columns(columnmax, maxwidth=80)
        self.assertEqual(73, sum(result))
        # both should be within 1 of each other (rounding)
        self.assertTrue(abs(result[0] - result[1]) <= 1)

    def test_shrink_columns_small_untouched(self):
        """Small columns at or below floor should not be shrunk."""
        tbl = Table(utf8=False, truncate=True)
        tbl.add_header(TableHeader("Id"))
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Description"))
        # overhead = 3 * 3 + 1 = 10
        # columnmax = [5, 50, 40], sum = 95, total = 105
        # available content = 80 - 10 = 70
        # Id (5) is below floor (10), but its actual width is 5 so lock at 5
        # remaining available = 70 - 5 = 65 for Name(50) + Description(40)
        # Name: 65 * 50/90 = 36.1 -> 36
        # Description: 65 * 40/90 = 28.9 -> 29
        columnmax = [5, 50, 40]
        result = tbl._shrink_columns(columnmax, maxwidth=80)
        self.assertEqual(5, result[0])  # small column untouched
        self.assertEqual(70, sum(result))  # total fits available

    def test_shrink_columns_respects_header_floor(self):
        """Column floor should be at least the header label length."""
        tbl = Table(utf8=False, truncate=True)
        tbl.add_header(TableHeader("ResourceName"))  # 12 chars > MIN_COLUMN_WIDTH(10)
        tbl.add_header(TableHeader("State"))          # 5 chars < MIN_COLUMN_WIDTH(10)
        # The floor for ResourceName should be 12 (header length)
        # The floor for State should be 10 (MIN_COLUMN_WIDTH)
        columnmax = [60, 60]
        result = tbl._shrink_columns(columnmax, maxwidth=50)
        self.assertTrue(result[0] >= 12, f"ResourceName column {result[0]} below header length 12")
        self.assertTrue(result[1] >= 10, f"State column {result[1]} below MIN_COLUMN_WIDTH 10")

    def test_shrink_columns_too_narrow_skips(self):
        """If terminal is too narrow for even floor-width columns, skip truncation."""
        tbl = Table(utf8=False, truncate=True)
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))
        tbl.add_header(TableHeader("Description"))
        # overhead = 3 * 3 + 1 = 10
        # floor per column = 10, total floors = 30, 30 + 10 = 40 > maxwidth of 30
        columnmax = [50, 50, 50]
        result = tbl._shrink_columns(columnmax, maxwidth=30)
        self.assertEqual([50, 50, 50], result)  # unchanged, skip truncation

    def test_truncation_basic(self):
        """Table with truncation enabled should fit within maxwidth."""
        tbl = Table(utf8=False, truncate=True)
        tbl.maxwidth = 40
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Description"))

        tbl.add_row(["short", "This is a very long description that exceeds width"])
        table_out = tbl.show()

        # every line should fit within maxwidth
        for line in table_out.strip().splitlines():
            self.assertLessEqual(len(line), 40, f"Line too long: {repr(line)}")

    def test_truncation_ellipsis_ascii(self):
        """Truncated cells should end with '...' in ascii mode."""
        tbl = Table(utf8=False, truncate=True)
        tbl.maxwidth = 40
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))

        tbl.add_row(["a_very_long_name_that_will_be_truncated", "also_a_very_long_value_here_too_yes"])
        table_out = tbl.show()

        # find the data row (skip header, separators)
        data_lines = [line for line in table_out.strip().splitlines() if '...' in line]
        self.assertTrue(len(data_lines) > 0, "Expected at least one line with '...' ellipsis")

    def test_truncation_ellipsis_utf8(self):
        """Truncated cells should end with unicode ellipsis in utf8 mode."""
        tbl = Table(utf8=True, truncate=True)
        tbl.maxwidth = 40
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Value"))

        tbl.add_row(["a_very_long_name_that_will_be_truncated", "also_a_very_long_value_here_too_yes"])
        table_out = tbl.show()

        data_lines = [line for line in table_out.strip().splitlines()
                      if '\u2026' in line or '...' in line]
        self.assertTrue(len(data_lines) > 0, "Expected at least one line with ellipsis")

    def test_truncation_disabled(self):
        """With truncate=False, table should render at full width as before."""
        tbl = Table(utf8=False, truncate=False)
        tbl.maxwidth = 40
        tbl.add_header(TableHeader("Name"))
        tbl.add_header(TableHeader("Description"))

        tbl.add_row(["short", "This is a very long description that exceeds width"])
        table_out = tbl.show()

        # at least one line should exceed maxwidth (no truncation)
        max_line = max(len(line) for line in table_out.strip().splitlines())
        self.assertGreater(max_line, 40)

    def test_truncation_multiline(self):
        """Multiline cells should have each line truncated independently."""
        tbl = Table(utf8=False, truncate=True)
        tbl.maxwidth = 45
        tbl.add_header(TableHeader("Id"))
        tbl.add_header(TableHeader("Text"))

        tbl.add_row(["1", "first_very_long_line_that_needs_truncation\nsecond_very_long_line_also_needs_truncation"])
        table_out = tbl.show()

        for line in table_out.strip().splitlines():
            self.assertLessEqual(len(line), 45, f"Line too long: {repr(line)}")

    def test_truncation_equal_columns(self):
        """Two equally wide columns should be truncated to roughly equal widths."""
        tbl = Table(utf8=False, truncate=True)
        tbl.maxwidth = 50
        tbl.add_header(TableHeader("ColumnA"))
        tbl.add_header(TableHeader("ColumnB"))

        long_a = "a" * 60
        long_b = "b" * 60
        tbl.add_row([long_a, long_b])
        table_out = tbl.show()

        # find the data row
        for line in table_out.strip().splitlines():
            if 'aaa' in line and 'bbb' in line:
                # extract the two cell contents (between pipes)
                parts = line.split('|')
                # parts[0] is empty (before first pipe), parts[1] is col A, parts[2] is col B
                col_a = parts[1].strip()
                col_b = parts[2].strip()
                self.assertTrue(abs(len(col_a) - len(col_b)) <= 1,
                                f"Columns not equally truncated: {len(col_a)} vs {len(col_b)}")
                break
