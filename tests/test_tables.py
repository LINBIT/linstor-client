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
