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
