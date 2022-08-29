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

import subprocess
import sys

from linstor_client.consts import (
    Color,
    ExitCode
)


class Output(object):
    @staticmethod
    def handle_ret(answer, no_color, warn_as_error, outstream=sys.stdout):
        from linstor.sharedconsts import (MASK_ERROR, MASK_WARN, MASK_INFO)

        rc = answer.ret_code
        ret = 0
        message = answer.message
        cause = answer.cause
        correction = answer.correction
        details = answer.details
        if rc & MASK_ERROR == MASK_ERROR:
            ret = ExitCode.API_ERROR
            category = Output.color_str('ERROR:\n', Color.RED, no_color)
        elif rc & MASK_WARN == MASK_WARN:
            if warn_as_error:  # otherwise keep at 0
                ret = ExitCode.API_ERROR
            category = Output.color_str('WARNING:\n', Color.YELLOW, no_color)
        elif rc & MASK_INFO == MASK_INFO:
            category = Output.color_str('INFO:\n', Color.BLUE, no_color)
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

        if answer.error_report_ids:
            outstream.write("Show reports:\n")
            Output.print_with_indent(outstream, 4, "linstor error-reports show " + " ".join(answer.error_report_ids))
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

    @staticmethod
    def utf8(msg):
        # e.g., redirect, then force utf8 encoding (default on py3)
        if sys.stdout.encoding is None:
            msg = msg.encode('utf-8')
        return msg


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


# base range check
def checkrange(v, i, j):
    return i <= v <= j


# "type" used for argparse
def rangecheck(i, j):
    def range(v):
        v = int(v)
        if not checkrange(v, i, j):
            raise LinstorClientError('%d not in range: [%d, %d]' % (v, i, j), exit_code=2)
        return v
    return range


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
        "machine_readable", "disable_config", "timeout",
        "verbose", "output_version", "curl", "allow_insecure_auth",
        "certfile", "keyfile", "cafile"
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
            del (to_filter[k])
    return to_filter


def filter_allowed(to_filter, allowed):
    for k in to_filter.keys():
        if k not in allowed:
            del (to_filter[k])
    return to_filter


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
