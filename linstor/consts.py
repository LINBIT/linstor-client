#!/usr/bin/env python2
"""
    LINSTOR - management of distributed storage/DRBD9 resources
    Copyright (C) 2013 - 2017  LINBIT HA-Solutions GmbH
    Author: Robert. Altnoeder, Roland Kammerer

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

"""
Global constants for linstor
"""

VERSION = "0.1.9"

try:
    from linstor.consts_githash import GITHASH
except:
    GITHASH = 'GIT-hash: UNKNOWN'

# Default terminal dimensions
# Used by get_terminal_size()
DEFAULT_TERM_WIDTH, DEFAULT_TERM_HEIGHT = 80, 25

NODE_NAME = "node_name"
RES_NAME = "res_name"
SNAPS_NAME = "snaps_name"
STORPOOL_NAME = "storpool_name"

# RFC952 / RFC1035 / RFC1123 host name constraints; do not change
NODE_NAME_MINLEN = 2
NODE_NAME_MAXLEN = 255
NODE_NAME_LABEL_MAXLEN = 63

# linstor object name constraints
RES_NAME_MINLEN = 1
RES_NAME_MAXLEN = 48    # Enough for a UUID string plus prefix
RES_NAME_VALID_CHARS = "_"
RES_NAME_VALID_INNER_CHARS = "_-"
SNAPS_NAME_MINLEN = 1
SNAPS_NAME_MAXLEN = 100
SNAPS_NAME_VALID_CHARS = "_"
SNAPS_NAME_VALID_INNER_CHARS = "_-"
STORPOOL_NAME_MINLEN = 3
STORPOOL_NAME_MAXLEN = 48
STORPOOL_NAME_VALID_CHARS = "_"
STORPOOL_NAME_VALID_INNER_CHARS = "_-"

FILE_GLOBAL_COMMON_CONF = "linstor_global_common.conf"

# boolean expressions
BOOL_TRUE = "true"
BOOL_FALSE = "false"

KEY_LS_CONTROLLERS = 'LS_CONTROLLERS'


class ExitCode(object):
    OK = 0
    UNKNOWN_ERROR = 1
    ARGPARSE_ERROR = 2
    OBJECT_NOT_FOUND = 3
    OPTION_NOT_SUPPORTED = 4
    CONNECTION_ERROR = 20
    CONNECTION_TIMEOUT = 21
    UNEXPECTED_REPLY = 22
    API_ERROR = 10
    NO_SATELLITE_CONNECTION = 11


class Color(object):
    # Do not reorder
    (BLACK,
     DARKRE,
     DARKGREEN,
     BROWN,
     DARKBLUE,
     DARKPINK,
     TEAL,
     GRAY,
     DARKGRAY,
     RED,
     GREEN,
     YELLOW,
     BLUE,
     PINK,
     TURQUOIS,
     WHITE,
     NONE) = [chr(0x1b) + "[%d;%dm" % (i, j) for i in range(2) for j in range(30, 38)] + [chr(0x1b) + "[0m"]
