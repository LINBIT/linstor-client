import errno
import operator
import locale
import shutil
from linstor_client.consts import (
    DEFAULT_TERM_HEIGHT,
    DEFAULT_TERM_WIDTH,
    MIN_COLUMN_WIDTH,
    Color
)


# TODO(rck): still a hack
class SyntaxException(Exception):
    pass


def get_terminal_size():
    size = shutil.get_terminal_size(fallback=(DEFAULT_TERM_WIDTH, DEFAULT_TERM_HEIGHT))
    return size.columns, size.lines


class TableHeader(object):
    ALIGN_LEFT = '<'
    ALIGN_RIGHT = '>'

    def __init__(self, name, color=None, align_column=ALIGN_LEFT, alignment_text=ALIGN_LEFT):
        """
        Creates a new TableHeader object.

        :param str name:
        :param str color: color to use for this column
        :param str align_column:
        :param str alignment_text:
        """
        self._name = name
        self._color = color
        self._align_column = align_column
        self._alignment_text = alignment_text

    @property
    def name(self):
        return self._name

    @property
    def color(self):
        return self._color

    @property
    def column_alignment(self):
        return self._align_column

    @property
    def text_alignment(self):
        return self._alignment_text


class Table(object):
    def __init__(self, colors=True, utf8=False, pastable=False, truncate=False):
        self.r_just = False
        self.got_column = False
        self.got_row = False
        self.groups = []
        self.header = []
        self.table = []
        self.coloroverride = []
        self._header_colors = False
        self.view = None
        self.showseps = False
        self.maxwidth = 0  # if 0, determine terminal width automatically
        if pastable:
            self.colors = False
            self.utf8 = False
            self.maxwidth = 78
        else:
            self.colors = colors
            self.utf8 = utf8
        self.truncate = truncate

    def add_column(self, name, color=None, align_column=TableHeader.ALIGN_LEFT, just_txt=TableHeader.ALIGN_LEFT):
        self.got_column = True
        if self.got_row:
            raise SyntaxException("Not allowed to define columns after rows")
        if align_column == TableHeader.ALIGN_RIGHT:
            if self.r_just:
                raise SyntaxException("Can not right align column more than once")
            else:
                self.r_just = True

        if not self.colors:
            color = None

        self.header.append({
            'name': name,
            'color': color,
            'align_column': align_column,
            'just_txt': just_txt})

    def header_name(self, index):
        return self.header[index]['name']

    def add_header(self, header):
        """
        Adds a table header
        :param TableHeader header:
        :return:
        """
        return self.add_column(header.name, header.color, header.column_alignment, header.text_alignment)

    def add_headers(self, headers):
        """
        Adds a list of table headers.
        :param list[TableHeader] headers: list of table headers
        :return:
        """
        for hdr in headers:
            self.add_header(hdr)

    @classmethod
    def to_unicode(cls, t):
        if isinstance(t, str):
            return t
        return str(t)

    def add_row(self, row):
        self.got_row = True
        if not self.got_column:
            raise SyntaxException("Not allowed to define rows before columns")
        if len(row) != len(self.header):
            raise SyntaxException("Row len does not match headers")

        coloroverride = [None] * len(row)
        for idx, c in enumerate(row[:]):
            if isinstance(c, tuple):
                color, text = c
                row[idx] = self.to_unicode(text)
                if self.colors:
                    coloroverride[idx] = color
            else:
                row[idx] = self.to_unicode(row[idx])

        self.table.append(row)
        self.coloroverride.append(coloroverride)

    def add_separator(self):
        self.table.append([None])

    def set_show_separators(self, val=False):
        self.showseps = val

    def set_view(self, columns):
        self.view = columns

    def set_groupby(self, groups):
        if groups:
            assert (isinstance(groups, list))
            self.groups = groups

    @classmethod
    def _determine_column_width(cls, column_text):
        """
        Returns the longest line in the column_text.

        :param str column_text: column text
        :return: Lenght of the longest line in the text
        :rtype: int
        """
        maxline = 0
        for line in str(column_text).splitlines():
            maxline = max(len(line), maxline)
        return maxline

    def _shrink_columns(self, columnmax, maxwidth):
        """
        Shrink column widths proportionally to fit within maxwidth.

        Columns at or below their floor (max of MIN_COLUMN_WIDTH and header label length)
        are left untouched. Remaining space is distributed proportionally among
        oversized columns. If even floor-width columns exceed maxwidth, returns
        columnmax unchanged (no truncation possible).

        :param list[int] columnmax: current maximum width per column
        :param int maxwidth: target maximum table width
        :return: adjusted column widths
        :rtype: list[int]
        """
        num_columns = len(columnmax)
        overhead = 3 * num_columns + 1
        available = maxwidth - overhead

        if sum(columnmax) <= available:
            return columnmax

        # compute floor per column
        floors = []
        for idx, col in enumerate(self.header):
            header_len = len(col['name'].replace('_', ' '))
            floors.append(max(MIN_COLUMN_WIDTH, header_len))

        # if even floors don't fit, skip truncation
        if sum(floors) > available:
            return columnmax

        # separate locked (at/below floor) from shrinkable columns
        locked_total = 0
        shrinkable_indices = []
        shrinkable_total = 0
        for idx, width in enumerate(columnmax):
            if width <= floors[idx]:
                locked_total += width
            else:
                shrinkable_indices.append(idx)
                shrinkable_total += width

        remaining = available - locked_total
        result = list(columnmax)

        if not shrinkable_indices or remaining <= 0:
            return columnmax

        # distribute remaining space proportionally among shrinkable columns
        allocated = 0
        for i, idx in enumerate(shrinkable_indices):
            if i == len(shrinkable_indices) - 1:
                # last column gets whatever is left to avoid rounding drift
                result[idx] = remaining - allocated
            else:
                share = int(remaining * columnmax[idx] / shrinkable_total)
                result[idx] = max(floors[idx], share)
                allocated += result[idx]

        return result

    @classmethod
    def _truncate_cell(cls, text, max_width, utf8=False):
        """
        Truncate text to fit within max_width, appending an ellipsis if truncated.

        :param str text: cell text (single line)
        :param int max_width: maximum allowed width
        :param bool utf8: if True use unicode ellipsis, else use '...'
        :return: truncated text
        :rtype: str
        """
        if len(text) <= max_width:
            return text
        if utf8:
            return text[:max_width - 1] + '\u2026'
        else:
            if max_width < 3:
                return text[:max_width]
            return text[:max_width - 3] + '...'

    @classmethod
    def _str_print(cls, output):
        """
        Print and return output with attached new line.

        :param str output:
        :return: output + '\n'
        :rtype: str
        """
        print(output)
        return output + '\n'

    @classmethod
    def _row_expand(cls, row):
        """
        Expands a row with columns e.g.:
        ["column1_line1\ncolumn1_line2", "column2_line1", "column3_line1\ncolumn3_line2\ncolumn3_line3"]

        to the following format:
        [
            ["column1_line1", "column2_line1", "column3_line1"],
            ["column1_line2", "", "column3_line2"],
            ["", "", "column3_line3"]
        ]
        :param list[str] row:
        :return:
        :rtype: list[list[str]]
        """
        max_rows = 1

        # pre calculate table dimensions
        for column in row:
            max_rows = max(str(column).count('\n') + 1, max_rows)

        if max_rows == 1:  # small optimization
            return [row]

        multirow = [[""] * len(row) for x in range(max_rows)]  # create a pre filled table

        for cidx, column in enumerate(row):
            lines = str(column).splitlines()
            for idx, line in enumerate(lines):
                multirow[idx][cidx] = line

        return multirow

    def show(self, row_separator=True):
        output_table_str = ''
        # no view set, use all headers
        if not self.view:
            self.view = [h['name'] for h in self.header]

        if self.groups:
            self.view += [g for g in self.groups if g not in self.view]

        pcnt = 0
        for idx, c in enumerate(self.header[:]):
            if c['name'] not in self.view:
                pidx = idx - pcnt
                pcnt += 1
                self.header.pop(pidx)
                for row in self.table:
                    row.pop(pidx)
                for row in self.coloroverride:
                    row.pop(pidx)

        columnmax = [0] * len(self.header)
        if self.maxwidth:
            maxwidth = self.maxwidth
        else:
            term_width, _ = get_terminal_size()
            maxwidth = term_width

        hdrnames = [h['name'] for h in self.header]
        if self.groups and self.table:
            low_hdrnames = [h.lower() for h in hdrnames]
            group_bys = [low_hdrnames.index(g.lower()) for g in self.groups if g.lower() in low_hdrnames]
            for idx, row in enumerate(self.table):
                row += [idx]  # add table index for remap coloroverrides later
            orig_coloroverride = self.coloroverride[:]
            try:
                from natsort import natsorted
                self.table = natsorted(self.table, key=operator.itemgetter(*group_bys))
            except ImportError:
                self.table.sort(key=operator.itemgetter(*group_bys))

            # restore color overrides after sort
            for idx, row in enumerate(self.table):
                self.coloroverride[idx] = orig_coloroverride[row[-1]]
                # maybe remove the additional table index column, but it doesn't do harm

            lstlen = len(self.table)
            seps = set()
            for c in range(len(self.header)):
                if c not in group_bys:
                    continue
                cur = self.table[0][c]
                for idx, l in enumerate(self.table):
                    if idx < lstlen - 1:
                        if self.table[idx + 1][c] != cur:
                            cur = self.table[idx + 1][c]
                            seps.add(idx + 1)

            if self.showseps:
                for c, pos in enumerate(sorted(seps)):
                    self.table.insert(c + pos, [None])

        # calc max width per column and set final strings (with color codes)
        self.table.insert(0, [h.replace('_', ' ') for h in hdrnames])
        self.coloroverride.insert(0, [None] * len(self.header))

        # precalculate maximum column width
        multi_line_row = False
        for ridx, row in enumerate(self.table):
            if row[0] is None:
                continue
            for idx, col in enumerate(self.header):
                if not multi_line_row:
                    multi_line_row = str(row[idx]).find("\n") >= 0
                columnmax[idx] = max(self._determine_column_width(row[idx]), columnmax[idx])

        if self.truncate:
            columnmax = self._shrink_columns(columnmax, maxwidth)

        # insert frames
        self.table.insert(0, [None])
        self.table.insert(2, [None])
        self.table.append([None])

        # build format string
        ctbl = {
            'utf8': {
                'tl': u'╭',    # top left
                'tr': u'╮',    # top right
                'bl': u'╰',    # bottom left
                'br': u'╯',    # bottom right
                'mr': u'╡',    # middle right
                'ml': u'╞',    # middle left
                'mrsl': u'┤',  # middle right single line
                'mlsl': u'├',  # middle left single line
                'mdc': u'╌',   # middle dotted connector
                'msc': u'─',   # middle straight connector
                'pipe': u'│',
                'hr': u'═'
            },
            'ascii': {
                'tl': u'+',
                'tr': u'+',
                'bl': u'+',
                'br': u'+',
                'mr': u'|',
                'ml': u'|',
                'mrsl': u'|',
                'mlsl': u'|',
                'mdc': u'-',
                'msc': u'-',
                'pipe': u'|',
                'hr': u'='
            }
        }

        enc = 'ascii'
        if self.utf8:
            locales = locale.getdefaultlocale()
            if len(locales) > 1 and locales[1] and isinstance(locales[1], str) and locales[1].lower() == 'utf-8':
                enc = 'utf8'

        try:
            data_idx = 0  # index of the actual data table, self.table was inserted with table separators
            space = maxwidth - sum(columnmax)
            header_size = len(self.header)
            table_size = len(self.table)
            for ridx, row in enumerate(self.table):
                if row[0] is None:  # print a separator
                    if ridx == 0:  # top line
                        l, m, r = ctbl[enc]['tl'], ctbl[enc]['msc'], ctbl[enc]['tr']
                    elif ridx == table_size - 1:  # bottom line
                        l, m, r = ctbl[enc]['bl'], ctbl[enc]['msc'], ctbl[enc]['br']
                    elif ridx == 2:
                        l, m, r = ctbl[enc]['ml'], ctbl[enc]['hr'], ctbl[enc]['mr']
                    else:  # mid separators
                        l, m, r = ctbl[enc]['mlsl'], ctbl[enc]['mdc'], ctbl[enc]['mrsl']
                    row_sep = l + m * (sum(columnmax) + (3 * header_size) - 1) + r

                    if self.r_just and len(row_sep) < maxwidth:
                        output_table_str += self._str_print(l + m * (maxwidth - 2) + r)
                    else:
                        output_table_str += self._str_print(row_sep)
                else:
                    fstr = ctbl[enc]['pipe']  # prepare the format string per row, this allows colors per cell
                    for idx, col in enumerate(self.header):  # loop columns
                        if col['align_column'] == TableHeader.ALIGN_RIGHT:
                            space_and_overhead = space - (header_size * 3) - 2
                            if space_and_overhead >= 0:
                                fstr += u' ' * space_and_overhead + ctbl[enc]['pipe']

                        field_format = u'{' + str(idx) + u':' + col['just_txt'] + str(columnmax[idx]) + u'}'

                        fstr += u' '
                        # add color, if set
                        if self.coloroverride[data_idx][idx] or col['color'] and (self._header_colors or data_idx > 0):
                            if self.coloroverride[data_idx][idx]:
                                color = self.coloroverride[data_idx][idx]
                            else:
                                color = col['color']
                            fstr += color + field_format + Color.NONE
                        else:
                            fstr += field_format
                        fstr += u' ' + ctbl[enc]['pipe']

                    data_idx += 1  # we wrote a data row, so increase the data_idx
                    # split rows into row lines (for multiline support)
                    for singlerow in self._row_expand(row):
                        if self.truncate:
                            for i in range(len(columnmax)):
                                singlerow[i] = self._truncate_cell(singlerow[i], columnmax[i], self.utf8)
                        output_table_str += self._str_print(fstr.format(*singlerow))

                    # if multiline rows and not disabled draw row separators between real rows
                    if 2 < ridx < table_size - 2:
                        if multi_line_row and row_separator:
                            row_sep = ctbl[enc]['mlsl'] + ctbl[enc]['mdc']\
                                * (sum(columnmax) + (3 * header_size) - 1) + ctbl[enc]['mrsl']
                            output_table_str += self._str_print(row_sep)
            return output_table_str
        except IOError as e:
            if e.errno == errno.EPIPE:
                return
            else:
                raise e

    def color_cell(self, text, color):
        return (color, text) if self.colors else text
