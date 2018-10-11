# -*- coding: utf-8 -*-
import os
import sys
import fcntl
import errno
import operator

from linstor_client.consts import (
    DEFAULT_TERM_HEIGHT,
    DEFAULT_TERM_WIDTH,
    Color
)


# TODO(rck): still a hack
class SyntaxException(Exception):
    pass


def get_terminal_size():
    def ioctl_GWINSZ(term_fd):
        term_dim = None
        try:
            import termios
            import struct
            term_dim = struct.unpack(
                'hh',
                fcntl.ioctl(term_fd, termios.TIOCGWINSZ, '1234')
            )
        except:
            pass
        return term_dim
    # Assign the first value that's not a NoneType
    term_dim = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not term_dim:
        try:
            with os.open(os.ctermid(), os.O_RDONLY) as term_fd:
                term_dim = ioctl_GWINSZ(term_fd)
        except:
            pass
    try:
        (term_width, term_height) = int(term_dim[1]), int(term_dim[0])
    except:
        term_width = DEFAULT_TERM_WIDTH
        term_height = DEFAULT_TERM_HEIGHT
    return term_width, term_height


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
    def __init__(self, colors=True, utf8=False, pastable=False):
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
                row[idx] = text
                if self.colors:
                    coloroverride[idx] = color

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
            assert(isinstance(groups, list))
            self.groups = groups

    def show(self, machine_readable=False, overwrite=False):
        if machine_readable:
            overwrite = False

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
            maxwidth = 110 if term_width > 110 else term_width

        hdrnames = [h['name'] for h in self.header]
        if self.groups and self.table:
            group_bys = [hdrnames.index(g) for g in self.groups if g in hdrnames]
            for row in self.table:
                for idx in group_bys:
                    try:
                        row[idx] = int(row[idx])
                    except ValueError:
                        pass
            orig_table = self.table[:]
            orig_coloroverride = self.coloroverride[:]
            tidx_used = set()
            try:
                from natsort import natsorted
                self.table = natsorted(self.table, key=operator.itemgetter(*group_bys))
            except ImportError:
                self.table.sort(key=operator.itemgetter(*group_bys))

            # restore color overrides after sort
            for oidx, orow in enumerate(orig_table):
                for tidx, trow in enumerate(self.table):
                    if orow == trow and oidx != tidx and tidx not in tidx_used:
                        tidx_used.add(tidx)
                        self.coloroverride[tidx] = orig_coloroverride[oidx]
                        break

            lstlen = len(self.table)
            seps = set()
            for c in range(len(self.header)):
                if c not in group_bys:
                    continue
                cur = self.table[0][c]
                for idx, l in enumerate(self.table):
                    if idx < lstlen - 1:
                        if self.table[idx + 1][c] == cur:
                            if overwrite:
                                self.table[idx + 1][c] = ' '
                        else:
                            cur = self.table[idx + 1][c]
                            seps.add(idx + 1)

            if self.showseps:
                for c, pos in enumerate(sorted(seps)):
                    self.table.insert(c + pos, [None])

        # calc max width per column and set final strings (with color codes)
        self.table.insert(0, [h.replace('_', ' ') for h in hdrnames])
        self.coloroverride.insert(0, [None] * len(self.header))

        # precalculate maximum column width
        for ridx, row in enumerate(self.table):
            if row[0] is None:
                continue
            for idx, col in enumerate(self.header):
                columnmax[idx] = max(len(str(row[idx])), columnmax[idx])

        # insert frames
        self.table.insert(0, [None])
        self.table.insert(2, [None])
        self.table.append([None])

        # build format string
        ctbl = {
            'utf8': {
                'tl': u'╭',   # top left
                'tr': u'╮',   # top right
                'bl': u'╰',   # bottom left
                'br': u'╯',   # bottom right
                'mr': u'╡',   # middle right
                'ml': u'╞',   # middle left
                'mdc': u'┄',  # middle dotted connector
                'msc': u'─',  # middle straight connector
                'pipe': u'┊'
            },
            'ascii': {
                'tl': u'+',
                'tr': u'+',
                'bl': u'+',
                'br': u'+',
                'mr': u'|',
                'ml': u'|',
                'mdc': u'-',
                'msc': u'-',
                'pipe': u'|'
            }
        }

        enc = 'ascii'
        try:
            import locale
            if locale.getdefaultlocale()[1].lower() == 'utf-8' and self.utf8:
                enc = 'utf8'
        except:
            pass

        try:
            data_idx = 0  # index of the actual data table, self.table was inserted with table separators
            for ridx, row in enumerate(self.table):
                if row[0] is None:  # print a separator
                    if ridx == 0:  # top line
                        l, m, r = ctbl[enc]['tl'], ctbl[enc]['msc'], ctbl[enc]['tr']
                    elif ridx == len(self.table) - 1:  # header/body separator
                        l, m, r = ctbl[enc]['bl'], ctbl[enc]['msc'], ctbl[enc]['br']
                    else:  # bottom line
                        l, m, r = ctbl[enc]['ml'], ctbl[enc]['mdc'], ctbl[enc]['mr']
                    sep = l + m * (sum(columnmax) + (3 * len(self.header)) - 1) + r

                    if self.r_just and len(sep) < maxwidth:
                        sys.stdout.write(l + m * (maxwidth - 2) + r + u"\n")
                    else:
                        sys.stdout.write(sep + u"\n")
                else:
                    fstr = ctbl[enc]['pipe']  # prepare the format string per row, this allows colors per cell
                    for idx, col in enumerate(self.header):  # loop columns
                        if col['align_column'] == TableHeader.ALIGN_RIGHT:
                            space = maxwidth - sum(columnmax)
                            space_and_overhead = space - (len(self.header) * 3) - 2
                            if space_and_overhead >= 0:
                                fstr += ' ' * space_and_overhead + ctbl[enc]['pipe']

                        field_format = u'{' + str(idx) + u':' + col['just_txt'] + str(columnmax[idx]) + u'}'

                        fstr += u' '
                        # add color, if set
                        if self.coloroverride[data_idx][idx] or col["color"] and (self._header_colors or data_idx > 0):
                            if self.coloroverride[data_idx][idx]:
                                color = self.coloroverride[data_idx][idx]
                            else:
                                color = col["color"]
                            fstr += color + field_format + Color.NONE
                        else:
                            fstr += field_format
                        fstr += u' ' + ctbl[enc]['pipe']

                    data_idx += 1  # we wrote a data row, so increase the data_idx
                    sys.stdout.write(fstr.format(*row) + u"\n")
        except IOError as e:
            if e.errno == errno.EPIPE:
                return
            else:
                raise e

    def color_cell(self, text, color):
        return (color, text) if self.colors else text
