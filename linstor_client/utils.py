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

import locale
import os
import subprocess
import sys
from collections import OrderedDict

from linstor_client.consts import (
    NODE_NAME,
    NODE_NAME_LABEL_MAXLEN,
    NODE_NAME_MAXLEN,
    NODE_NAME_MINLEN,
    RES_NAME,
    RES_NAME_MAXLEN,
    RES_NAME_MINLEN,
    RES_NAME_VALID_CHARS,
    RES_NAME_VALID_INNER_CHARS,
    SNAPSHOT_NAME,
    SNAPSHOT_NAME_MAXLEN,
    SNAPSHOT_NAME_MINLEN,
    SNAPSHOT_NAME_VALID_CHARS,
    SNAPSHOT_NAME_VALID_INNER_CHARS,
    STORPOOL_NAME,
    STORPOOL_NAME_MAXLEN,
    STORPOOL_NAME_MINLEN,
    STORPOOL_NAME_VALID_CHARS,
    STORPOOL_NAME_VALID_INNER_CHARS,
    Color,
    ExitCode
)


class Output(object):
    @staticmethod
    def handle_ret(answer, no_color, warn_as_error, outstream=sys.stdout):
        from linstor.sharedconsts import (MASK_ERROR, MASK_WARN, MASK_INFO)

        rc = answer.ret_code
        ret = 0
        message = answer.message_format
        cause = answer.cause_format
        correction = answer.correction_format
        details = answer.details_format
        if rc & MASK_ERROR == MASK_ERROR:
            ret = ExitCode.API_ERROR
            category = Output.color_str('ERROR:\n', Color.RED, no_color)
        elif rc & MASK_WARN == MASK_WARN:
            if warn_as_error:  # otherwise keep at 0
                ret = ExitCode.API_ERROR
            category = Output.color_str('WARNING:\n', Color.YELLOW, no_color)
        elif rc & MASK_INFO == MASK_INFO:
            category = 'INFO: '
        else:  # do not use MASK_SUCCESS
            category = Output.color_str('SUCCESS:\n', Color.GREEN, no_color)

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
    def color_str(string, color, no_color):
        return '%s%s%s' % (Output.color(color, no_color), string, Output.color(Color.NONE, no_color))

    @staticmethod
    def color(col, no_color):
        if no_color:
            return ''
        else:
            return col

    @staticmethod
    def err(msg, no_color):
        Output.bail_out(msg, Color.RED, 1, no_color)

    @staticmethod
    def bail_out(msg, color, ret, no_color):
        sys.stderr.write(Output.color_str(msg, color, no_color) + '\n')
        sys.exit(ret)


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
        import linstor_client.argparse.argparse as argparse
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
    checked_name = name_b.decode("utf-8")
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
    for label in name_b.split(".".encode("utf-8")):
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
    checked_name = name_b.decode("utf-8")
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
    elif checktype == SNAPSHOT_NAME:
        min_length = SNAPSHOT_NAME_MINLEN
        max_length = SNAPSHOT_NAME_MAXLEN
        valid_chars = SNAPSHOT_NAME_VALID_CHARS
        valid_inner_chars = SNAPSHOT_NAME_VALID_INNER_CHARS
    elif checktype == STORPOOL_NAME:
        min_length = STORPOOL_NAME_MINLEN
        max_length = STORPOOL_NAME_MAXLEN
        valid_chars = STORPOOL_NAME_VALID_CHARS
        valid_inner_chars = STORPOOL_NAME_VALID_INNER_CHARS
    else:  # checktype == NODE_NAME, use that as rather arbitrary default
        min_length = NODE_NAME_MINLEN
        max_length = NODE_NAME_MAXLEN

    def check(name):
        import linstor_client.argparse.argparse as argparse
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


def ip_completer(where):
    def completer(prefix, parsed_args, **kwargs):
        import socket
        opt = where
        if opt == "name":
            name = parsed_args.name
        elif opt == "peer_ip":
            name = parsed_args.peer_ip
        else:
            return ""

        ip = socket.gethostbyname(name)
        ip = [ip]
        return ip
    return completer


# mainly used for DrbdSetupOpts()
# but also usefull for 'handlers' subcommand
def filter_new_args(unsetprefix, args):
    new = dict()
    reserved_keys = [
        "func", "optsobj", "common", "command",
        "controllers", "warn_as_error", "no_utf8", "no_color",
        "machine_readable", "disable_config", "timeout"
    ]
    for k, v in args.__dict__.items():
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


class SizeCalc(object):

    """
    Methods for converting decimal and binary sizes of different magnitudes
    """

    _base_2 = 0x0200
    _base_10 = 0x0A00

    UNIT_B = 0 | _base_2
    UNIT_KiB = 10 | _base_2
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
    Unit keys are lower-case; functions using the lookup table should
    convert the unit name to lower-case to look it up in this table
    """
    UNITS_MAP = OrderedDict([(unit_str.lower(), (unit_str, unit)) for unit_str, unit in [
        ('K', UNIT_KiB),
        ('kB', UNIT_kB),
        ('KiB', UNIT_KiB),
        ('M', UNIT_MiB),
        ('MB', UNIT_MB),
        ('MiB', UNIT_MiB),
        ('G', UNIT_GiB),
        ('GB', UNIT_GB),
        ('GiB', UNIT_GiB),
        ('T', UNIT_TiB),
        ('TB', UNIT_TB),
        ('TiB', UNIT_TiB),
        ('P', UNIT_PiB),
        ('PB', UNIT_PB),
        ('PiB', UNIT_PiB),
    ]])

    UNITS_LIST_STR = ', '.join([unit_str for unit_str, _ in UNITS_MAP.values()])

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
        return int(result)

    @classmethod
    def approximate_size_string(cls, size_kib):
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
            if size_kib >= magnitude:
                index = counter
            else:
                break
            magnitude = magnitude << 10
            counter += 1
        magnitude = magnitude >> 10

        size_str = None
        if size_kib % magnitude != 0:
            size_unit = float(size_kib) / magnitude
            size_loc = locale.format('%3.2f', size_unit, grouping=True)
            size_str = "%s %s" % (size_loc, units[index])
        else:
            size_unit = size_kib / magnitude
            size_str = "%d %s" % (size_unit, units[index])

        return size_str


class LinstorClientError(Exception):
    """
    Linstor exception with a message and exit code information
    """
    def __init__(self, msg, exit_code):
        self._msg = msg
        self._exit_code = exit_code

    @property
    def exit_code(self):
        return self._exit_code

    @property
    def message(self):
        return self._msg

    def __str__(self):
        return "Error: {msg}".format(msg=self._msg)

    def __repr__(self):
        return "LinstorError('{msg}', {ec})".format(msg=self._msg, ec=self._exit_code)
