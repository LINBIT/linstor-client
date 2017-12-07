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

VERSION = "0.1"
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
RES_NAME_VALID_INNER_CHARS = "-"
SNAPS_NAME_MINLEN = 1
SNAPS_NAME_MAXLEN = 100
SNAPS_NAME_VALID_CHARS = "_"
SNAPS_NAME_VALID_INNER_CHARS = "-"
STORPOOL_NAME_MINLEN = 3
STORPOOL_NAME_MAXLEN = 48
STORPOOL_NAME_VALID_CHARS = "_"
STORPOOL_NAME_VALID_INNER_CHARS = "-"

FILE_GLOBAL_COMMON_CONF = "linstor_global_common.conf"

# boolean expressions
BOOL_TRUE = "true"
BOOL_FALSE = "false"

KEY_LS_CONTROLLERS = 'LS_CONTROLLERS'
