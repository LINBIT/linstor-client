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
