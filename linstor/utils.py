#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    linstor - management of distributed DRBD9 resources
    Copyright (C) 2013 - 2017  LINBIT HA-Solutions GmbH
    Author: Robert Altnoeder, Roland Kammerer

    You can use this file under the terms of the GNU Lesser General
    Public License as as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    See <http://www.gnu.org/licenses/>.
"""

import errno
import fcntl
import locale
import operator
import os
import subprocess
import sys

from linstor.consts import (
    DEFAULT_TERM_HEIGHT,
    DEFAULT_TERM_WIDTH,
    NODE_NAME,
    NODE_NAME_LABEL_MAXLEN,
    NODE_NAME_MAXLEN,
    NODE_NAME_MINLEN,
    RES_NAME,
    RES_NAME_MAXLEN,
    RES_NAME_MINLEN,
    RES_NAME_VALID_CHARS,
    RES_NAME_VALID_INNER_CHARS,
    SNAPS_NAME,
    SNAPS_NAME_MAXLEN,
    SNAPS_NAME_MINLEN,
    SNAPS_NAME_VALID_CHARS,
    SNAPS_NAME_VALID_INNER_CHARS,
)


# TODO(rck): still a hack
class SyntaxException(Exception):
    pass


# TODO(rck): move them to consts

# Do not reorder
(COLOR_BLACK,
 COLOR_DARKRE,
 COLOR_DARKGREEN,
 COLOR_BROWN,
 COLOR_DARKBLUE,
 COLOR_DARKPINK,
 COLOR_TEAL,
 COLOR_GRAY,
 COLOR_DARKGRAY,
 COLOR_RED,
 COLOR_GREEN,
 COLOR_YELLOW,
 COLOR_BLUE,
 COLOR_PINK,
 COLOR_TURQUOIS,
 COLOR_WHITE,
 COLOR_NONE) = [chr(0x1b) + "[%d;%dm" % (i, j) for i in range(2) for j in range(30, 38)] + [chr(0x1b) + "[0m"]


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
            term_fd = os.open(os.ctermid(), os.O_RDONLY)
            term_dim = ioctl_GWINSZ(term_fd)
            os.close(term_fd)
        except:
            pass
    try:
        (term_width, term_height) = int(term_dim[1]), int(term_dim[0])
    except:
        term_width = DEFAULT_TERM_WIDTH
        term_height = DEFAULT_TERM_HEIGHT
    return term_width, term_height


class Output(object):
    @staticmethod
    def handle_ret(args, answer):
        outstream = sys.stderr
        from linstor.sharedconsts import (MASK_ERROR, MASK_WARN, MASK_INFO)

        rc = answer.ret_code
        ret = 0
        category = ''
        message = answer.message_format
        cause = answer.cause_format
        correction = answer.correction_format
        details = answer.details_format
        if rc & MASK_ERROR:
            ret = 1
            category = Output.color_str('ERROR:\n', COLOR_RED, args)
        elif rc & MASK_WARN:
            if args[0].warn_as_error:  # otherwise keep at 0
                ret = 1
            category = Output.color_str('WARNING:\n', COLOR_YELLOW, args)
        elif rc & MASK_INFO:
            category = 'INFO: '
        else:  # do not use MASK_SUCCESS
            category = Output.color_str('SUCCESS:\n', COLOR_GREEN, args)

        outstream.write(category)
        have_message = message is not None and len(message) > 0
        have_cause = cause is not None and len(cause) > 0
        have_correction = correction is not None and len(correction) > 0
        have_details = details is not None and len(details) > 0
        if (have_cause or have_correction or have_details) and have_message:
            outstream.write("Description:\n")
        if have_message:
            Output.print_with_indent(outstream, 4, message)
        if have_cause:
            outstream.write("Cause:\n")
            Output.print_with_indent(outstream, 4, cause)
        if have_correction:
            outstream.write("Correction:\n")
            Output.print_with_indent(outstream, 4, correction)
        if have_details:
            outstream.write("Details:\n")
            Output.print_with_indent(outstream, 4, details)
        return ret

    @staticmethod
    def print_with_indent(stream, indent, text):
        spacer = indent * ' '
        offset = 0
        index = 0
        while index < len(text):
            if text[index] == '\n':
                stream.write(spacer)
                stream.write(text[offset:index])
                stream.write('\n')
                offset = index + 1
            index += 1
        if offset < len(text):
            stream.write(spacer)
            stream.write(text[offset:])
            stream.write('\n')

    @staticmethod
    def color_str(string, color, args=None):
        return '%s%s%s' % (Output.color(color, args), string, Output.color(COLOR_NONE, args))

    @staticmethod
    def color(col, args=None):
        if args and args[0].no_color:
            return ''
        else:
            return col

    @staticmethod
    def err(msg):
        Output.bail_out(msg, COLOR_RED, 1)

    @staticmethod
    def bail_out(msg, color, ret):
        sys.stderr.write(Output.color_str(msg, color) + '\n')
        sys.exit(ret)


class Table():
    def __init__(self, colors=True, utf8=False, pastable=False):
        self.r_just = False
        self.got_column = False
        self.got_row = False
        self.groups = []
        self.header = []
        self.table = []
        self.coloroverride = []
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

    def add_column(self, name, color=False, just_col='<', just_txt='<'):
        self.got_column = True
        if self.got_row:
            raise SyntaxException("Not allowed to define columns after rows")
        if just_col == '>':
            if self.r_just:
                raise SyntaxException("Not allowed to use multiple times")
            else:
                self.r_just = True

        self.header.append({
            'name': name,
            'color': color,
            'just_col': just_col,
            'just_txt': just_txt})

    def add_row(self, row, color=False, just_txt='<'):
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
                    if not self.header[idx]['color']:
                        raise SyntaxException("Color tuple for this row not allowed "
                                              "to have colors")
                    else:
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

        # color overhead
        co = len(COLOR_RED) + len(COLOR_NONE)
        co_sum = 0

        hdrnames = [h['name'] for h in self.header]
        if self.groups:
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
            except:
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
        ridx = 0
        self.coloroverride.insert(0, [None] * len(self.header))

        for row in self.table:
            if not row[0]:
                continue
            for idx, col in enumerate(self.header):
                row[idx] = str(row[idx])
                if col['color']:
                    if self.coloroverride[ridx][idx]:
                        color = self.coloroverride[ridx][idx]
                    else:
                        color = col["color"]
                    row[idx] = color + row[idx] + COLOR_NONE
                columnmax[idx] = max(len(row[idx]), columnmax[idx])
            ridx += 1

        for h in self.header:
            if h['color']:
                co_sum += co

        # insert frames
        self.table.insert(0, [None])
        self.table.insert(2, [None])
        self.table.append([None])

        # build format string
        ctbl = {
            'utf8': {
                'tl': '╭',   # top left
                'tr': '╮',   # top right
                'bl': '╰',   # bottom left
                'br': '╯',   # bottom right
                'mr': '╡',   # middle right
                'ml': '╞',   # middle left
                'mdc': '┄',  # middle dotted connector
                'msc': '─',  # middle straight connector
                'pipe': '┊'
            },
            'ascii': {
                'tl': '+',
                'tr': '+',
                'bl': '+',
                'br': '+',
                'mr': '|',
                'ml': '|',
                'mdc': '-',
                'msc': '-',
                'pipe': '|'
            }
        }

        enc = 'ascii'
        try:
            import locale
            if locale.getdefaultlocale()[1].lower() == 'utf-8' and self.utf8:
                enc = 'utf8'
        except:
            pass

        fstr = ctbl[enc]['pipe']
        for idx, col in enumerate(self.header):
            if col['just_col'] == '>':
                space = (maxwidth - sum(columnmax) + co_sum)
                space_and_overhead = space - (len(self.header) * 3) - 2
                if space_and_overhead >= 0:
                    fstr += ' ' * space_and_overhead + ctbl[enc]['pipe']

            fstr += ' {' + str(idx) + ':' + col['just_txt'] + str(columnmax[idx]) + '} ' + ctbl[enc]['pipe']

        try:
            for idx, row in enumerate(self.table):
                if not row[0]:  # print a separator
                    if idx == 0:
                        l, m, r = ctbl[enc]['tl'], ctbl[enc]['msc'], ctbl[enc]['tr']
                    elif idx == len(self.table) - 1:
                        l, m, r = ctbl[enc]['bl'], ctbl[enc]['msc'], ctbl[enc]['br']
                    else:
                        l, m, r = ctbl[enc]['ml'], ctbl[enc]['mdc'], ctbl[enc]['mr']
                    sep = l + m * (sum(columnmax) - co_sum + (3 * len(self.header)) - 1) + r
                    if enc == 'utf8':  # should be save on non utf-8 too...
                        sep = sep.decode('utf-8')

                    if self.r_just and len(sep) < maxwidth:
                        sys.stdout.write(l + m * (maxwidth - 2) + r + "\n")
                    else:
                        sys.stdout.write(sep + "\n")
                else:
                    sys.stdout.write(fstr.format(*row) + "\n")
        except IOError as e:
            if e.errno == errno.EPIPE:
                return
            else:
                raise


# a wrapper for subprocess.check_output
def check_output(*args, **kwargs):
    def _wrapcall_2_6(*args, **kwargs):
        # no check_output in 2.6
        if "stdout" in kwargs:
            raise ValueError("stdout argument not allowed, it will be overridden.")
        process = subprocess.Popen(stdout=subprocess.PIPE, *args, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = args[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output

    try:
        return subprocess.check_output(*args, **kwargs)
    except AttributeError:
        return _wrapcall_2_6(*args, **kwargs)


def ssh_exec(cmdname, ip, name, cmdline, quiet=False, suppress_stderr=False):
    try:
        ssh_base = ["ssh", "-oBatchMode=yes",
                    "-oConnectTimeout=2", "root@" + ip]
        if subprocess.call(ssh_base + ["true"]) == 0:
            sys.stdout.write(
                "\nExecuting %s command using ssh.\n"
                "IMPORTANT: The output you see comes from %s\n"
                "IMPORTANT: Your input is executed on %s\n"
                % (cmdname, name, name)
            )
            ssh_cmd = ssh_base + cmdline
            if quiet:
                ssh_cmd.append("-q")
            if suppress_stderr:
                ssh_cmd.append('2>/dev/null')
            subprocess.check_call(ssh_cmd)
            return True
    except subprocess.CalledProcessError:
        sys.stderr.write("Error: Attempt to execute the %s command remotely"
                         "failed\n" % (cmdname))

    return False


# base range check
def checkrange(v, i, j):
    return i <= v <= j


# "type" used for argparse
def rangecheck(i, j):
    def range(v):
        import argparse.argparse as argparse
        v = int(v)
        if not checkrange(v, i, j):
            raise argparse.ArgumentTypeError('Range: [%d, %d]' % (i, j))
        return v
    return range


def check_name(name, min_length, max_length, valid_chars, valid_inner_chars):
    """
    Check the validity of a string for use as a name for
    objects like nodes or volumes.
    A valid name must match these conditions:
      * must at least be 1 byte long
      * must not be longer than specified by the caller
      * contains a-z, A-Z, 0-9, and the characters allowed
        by the caller only
      * contains at least one alpha character (a-z, A-Z)
      * must not start with a numeric character
      * must not start with a character allowed by the caller as
        an inner character only (valid_inner_chars)
    @param name         the name to check
    @param max_length   the maximum permissible length of the name
    @param valid_chars  list of characters allowed in addition to
                        [a-zA-Z0-9]
    @param valid_inner_chars    list of characters allowed in any
                        position in the name other than the first,
                        in addition to [a-zA-Z0-9] and the characters
                        already specified in valid_chars
    returns a valid string or "" (which can be if-checked)
    """
    checked_name = None
    if min_length is None or max_length is None:
        return ""
    if name is None:
        return ""
    name_b = bytearray(str(name), "utf-8")
    name_len = len(name_b)
    if name_len < min_length or name_len > max_length:
        return ""
    alpha = False
    idx = 0
    while idx < name_len:
        item = name_b[idx]
        if item >= ord('a') and item <= ord('z'):
            alpha = True
        elif item >= ord('A') and item <= ord('Z'):
            alpha = True
        else:
            if (not (item >= ord('0') and item <= ord('9') and idx >= 1)):
                letter = chr(item)
                if (not (letter in valid_chars or (letter in valid_inner_chars and idx >= 1))):
                    # Illegal character in name
                    return ""
        idx += 1
    if not alpha:
        return ""
    checked_name = str(name_b)
    return checked_name


def check_node_name(name):
    """
    RFC952 / RFC1123 internet host name validity check

    @returns Valid host name or ""
    """
    if name is None:
        return ""
    name_b = bytearray(str(name), "utf-8")
    name_len = len(name_b)
    if name_len < NODE_NAME_MINLEN or name_len > NODE_NAME_MAXLEN:
        return ""
    for label in name_b.split("."):
        if len(label) > NODE_NAME_LABEL_MAXLEN:
            return ""
    idx = 0
    while idx < name_len:
        letter = name_b[idx]
        if not ((letter >= ord('a') and letter <= ord('z')) or
                (letter >= ord('A') and letter <= ord('Z')) or
                (letter >= ord('0') and letter <= ord('9'))):
            # special characters allowed depending on position within the string
            if idx == 0 or idx + 1 == name_len:
                return ""
            else:
                if not (letter == ord('.') or letter == ord('-')):
                    return ""
        idx += 1
    checked_name = str(name_b)
    return checked_name


# "type" used for argparse
def namecheck(checktype):
    # Define variables in this scope (Python 3.x compatibility)
    min_length = 0
    max_length = 0
    valid_chars = ""
    valid_inner_chars = ""

    if checktype == RES_NAME:
        min_length = RES_NAME_MINLEN
        max_length = RES_NAME_MAXLEN
        valid_chars = RES_NAME_VALID_CHARS
        valid_inner_chars = RES_NAME_VALID_INNER_CHARS
    elif checktype == SNAPS_NAME:
        min_length = SNAPS_NAME_MINLEN
        max_length = SNAPS_NAME_MAXLEN
        valid_chars = SNAPS_NAME_VALID_CHARS
        valid_inner_chars = SNAPS_NAME_VALID_INNER_CHARS
    else:  # checktype == NODE_NAME, use that as rather arbitrary default
        min_length = NODE_NAME_MINLEN
        max_length = NODE_NAME_MAXLEN

    def check(name):
        import argparse.argparse as argparse
        if checktype == NODE_NAME:
            name = check_node_name(name)
        else:
            name = check_name(name, min_length, max_length, valid_chars, valid_inner_chars)
        if not name:
            raise argparse.ArgumentTypeError('Name: %s not valid' % (name))
        return name
    return check


def get_uname():
    checked_node_name = ""
    try:
        node_name = None
        uname = os.uname()
        if len(uname) >= 2:
            node_name = uname[1]
        checked_node_name = check_node_name(node_name)
    except OSError:
        pass
    return checked_node_name


# mainly used for DrbdSetupOpts()
# but also usefull for 'handlers' subcommand
def filter_new_args(unsetprefix, args):
    new = dict()
    reserved_keys = ["func", "optsobj", "common", "command"]
    for k, v in args.__dict__.iteritems():
        if v is not None and k not in reserved_keys:
            key = k.replace('_', '-')

            # handle --unset
            if key.startswith(unsetprefix) and not v:
                continue

            strv = str(v)
            if strv == 'False':
                strv = 'no'
            if strv == 'True':
                strv = 'yes'

            new[key] = strv

    for k in new.keys():
        if "unset-" + k in new:
            sys.stderr.write('Error: You are not allowed to set and unset'
                             ' an option at the same time!\n')
            return False
    return new


class DrbdSetupOpts():
    def __init__(self, setup_command, dm_command=None):
        import xml.etree.ElementTree as ET
        self.setup_command = setup_command
        self.dm_command = dm_command if dm_command else setup_command
        self.config = {}
        self.unsetprefix = 'unset'
        self.ok = False

        xmlout = ""
        from linstor.setupoptions import (diskoptions, netoptions, peerdeviceoptions, resourceoptions)

        if self.dm_command == "disk-options":
            xmlout = diskoptions
        elif self.dm_command == "net-options":
            xmlout = netoptions
        elif self.dm_command == "peer-device-options":
            xmlout = peerdeviceoptions
        elif self.dm_command == "resource-options":
            xmlout = resourceoptions

        root = ET.fromstring(xmlout)

        for child in root:
            if child.tag == 'summary':
                self.config['help'] = child.text
            elif child.tag == 'argument':
                # ignore them
                pass
            elif child.tag == 'option':
                opt = child.attrib['name']
                self.config[opt] = {'type': child.attrib['type']}
                if child.attrib['name'] == 'set-defaults':
                    continue
                if child.attrib['type'] == 'boolean':
                    self.config[opt]['default'] = child.find('default').text
                if child.attrib['type'] == 'handler':
                    self.config[opt]['handlers'] = [h.text for h in child.findall('handler')]
                elif child.attrib['type'] == 'numeric':
                    for v in ('min', 'max', 'default', 'unit_prefix', 'unit'):
                        val = child.find(v)
                        if val is not None:
                            self.config[opt][v] = val.text
        self.ok = True

    def gen_argparse_subcommand(self, subp):
        sp = subp.add_parser(self.dm_command, description=self.config['help'])

        def mybool(x):
            return x.lower() in ('y', 'yes', 't', 'true', 'on')

        for opt in self.config:
            if opt == 'help':
                continue
            if self.config[opt]['type'] == 'handler':
                sp.add_argument('--' + opt, choices=self.config[opt]['handlers'])
            if self.config[opt]['type'] == 'boolean':
                sp.add_argument('--' + opt, type=mybool,
                                help="yes/no (Default: %s)" % (self.config[opt]['default']))
            if self.config[opt]['type'] == 'string':
                sp.add_argument('--' + opt)
            if self.config[opt]['type'] == 'numeric':
                min_ = int(self.config[opt]['min'])
                max_ = int(self.config[opt]['max'])
                default = int(self.config[opt]['default'])
                if "unit" in self.config[opt]:
                    unit = "; Unit: " + self.config[opt]['unit']
                else:
                    unit = ""
                # sp.add_argument('--' + opt, type=rangecheck(min_, max_),
                #                 default=default, help="Range: [%d, %d]; Default: %d" %(min_, max_, default))
                # setting a default sets the option to != None, which makes
                # filterNew relatively complex
                sp.add_argument('--' + opt, type=rangecheck(min_, max_),
                                help="Range: [%d, %d]; Default: %d%s" % (min_, max_, default, unit))
        for opt in self.config:
            if opt == 'help':
                continue
            else:
                sp.add_argument('--%s-%s' % (self.unsetprefix, opt),
                                action='store_true')

        return sp

    # return a dict containing all non-None args
    def filterNew(self, args):
        return filter_new_args(self.unsetprefix, args)

    # returns True if opt is a valid option and val has the correct type and
    # satisfies the specified check (e.g., a range check)
    def validateCommand(self, opt, val):
        if opt not in self.config:
            return False

        if self.config[opt]['type'] == 'handler':
            return val in self.config[opt]['handlers']
        if self.config[opt]['type'] == 'boolean':
            return isinstance(val, bool)
        if self.config[opt]['type'] == 'string':
            return isinstance(val, str)
        if self.config[opt]['type'] == 'numeric':
            min_ = int(self.config[opt]['min'])
            max_ = int(self.config[opt]['max'])
            return checkrange(val, min_, max_)

    def get_options(self):
        return self.config


def filter_prohibited(to_filter, prohibited):
    for k in prohibited:
        if k in to_filter:
            del(to_filter[k])
    return to_filter


def filter_allowed(to_filter, allowed):
    for k in to_filter.keys():
        if k not in allowed:
            del(to_filter[k])
    return to_filter


def approximate_size_string(size_kiB):
    """
    Produce human readable size information as a string
    """
    units = []
    units.append("kiB")
    units.append("MiB")
    units.append("GiB")
    units.append("TiB")
    units.append("PiB")
    max_index = len(units)

    index = 0
    counter = 1
    magnitude = 1 << 10
    while counter < max_index:
        if size_kiB >= magnitude:
            index = counter
        else:
            break
        magnitude = magnitude << 10
        counter += 1
    magnitude = magnitude >> 10

    size_str = None
    if size_kiB % magnitude != 0:
        size_unit = float(size_kiB) / magnitude
        size_loc = locale.format('%3.2f', size_unit, grouping=True)
        size_str = "%s %s" % (size_loc, units[index])
    else:
        size_unit = size_kiB / magnitude
        size_str = "%d %s" % (size_unit, units[index])

    return size_str


class SizeCalc(object):

    """
    Methods for converting decimal and binary sizes of different magnitudes
    """

    _base_2 = 0x0200
    _base_10 = 0x0A00

    UNIT_B = 0 | _base_2
    UNIT_kiB = 10 | _base_2
    UNIT_MiB = 20 | _base_2
    UNIT_GiB = 30 | _base_2
    UNIT_TiB = 40 | _base_2
    UNIT_PiB = 50 | _base_2
    UNIT_EiB = 60 | _base_2
    UNIT_ZiB = 70 | _base_2
    UNIT_YiB = 80 | _base_2

    UNIT_kB = 3 | _base_10
    UNIT_MB = 6 | _base_10
    UNIT_GB = 9 | _base_10
    UNIT_TB = 12 | _base_10
    UNIT_PB = 15 | _base_10
    UNIT_EB = 18 | _base_10
    UNIT_ZB = 21 | _base_10
    UNIT_YB = 24 | _base_10

    """
    Unit names are lower-case; functions using the lookup table should
    convert the unit name to lower-case to look it up in this table
    """
    UNITS_MAP = {
        "k": UNIT_kiB,
        "m": UNIT_MiB,
        "g": UNIT_GiB,
        "t": UNIT_TiB,
        "p": UNIT_PiB,
        "kb": UNIT_kB,
        "mb": UNIT_MB,
        "gb": UNIT_GB,
        "tb": UNIT_TB,
        "pb": UNIT_PB,
        "kib": UNIT_kiB,
        "mib": UNIT_MiB,
        "gib": UNIT_GiB,
        "tib": UNIT_TiB,
        "pib": UNIT_PiB,
    }

    @classmethod
    def convert(cls, size, unit_in, unit_out):
        """
        Convert a size value into a different scale unit

        Convert a size value specified in the scale unit of unit_in to
        a size value given in the scale unit of unit_out
        (e.g. convert from decimal megabytes to binary gigabytes, ...)

        @param   size: numeric size value
        @param   unit_in: scale unit selector of the size parameter
        @param   unit_out: scale unit selector of the return value
        @return: size value converted to the scale unit of unit_out
                 truncated to an integer value
        """
        fac_in = ((unit_in & 0xffffff00) >> 8) ** (unit_in & 0xff)
        div_out = ((unit_out & 0xffffff00) >> 8) ** (unit_out & 0xff)
        return (size * fac_in // div_out)

    @classmethod
    def convert_round_up(cls, size, unit_in, unit_out):
        """
        Convert a size value into a different scale unit and round up

        Convert a size value specified in the scale unit of unit_in to
        a size value given in the scale unit of unit_out
        (e.g. convert from decimal megabytes to binary gigabytes, ...).
        The result is rounded up so that the returned value always specifies
        a size that is large enough to contain the size supplied to this
        function.
        (e.g., for 100 decimal Megabytes (MB), which equals 100 million bytes,
         returns 97,657 binary kilobytes (kiB), which equals 100 million
         plus 768 bytes and therefore is large enough to contain 100 megabytes)

        @param   size: numeric size value
        @param   unit_in: scale unit selector of the size parameter
        @param   unit_out: scale unit selector of the return value
        @return: size value converted to the scale unit of unit_out
        """
        fac_in = ((unit_in & 0xffffff00) >> 8) ** (unit_in & 0xff)
        div_out = ((unit_out & 0xffffff00) >> 8) ** (unit_out & 0xff)
        byte_sz = size * fac_in
        if byte_sz % div_out != 0:
            result = (byte_sz / div_out) + 1
        else:
            result = byte_sz / div_out
        return result
