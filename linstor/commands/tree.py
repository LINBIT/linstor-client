# -*- coding: utf-8 -*-
from __future__ import print_function
from linstor.consts import Color


class TreeNode:
    DTBL = {
        'utf8': {
            'svb': u'   │',    # space and vertical bar
            'spc': u'    ',    # space
            'pnc': u'   ├───',  # pre node characters
            'plnc': u'   └───'  # pre last node characters
        },
        'ascii': {
            'svb': '   |',
            'spc': '    ',
            'pnc': '   |---',
            'plnc': '   +---'
        }
    }

    NODE = 0
    STORAGE_POOL = 1
    RESOURCE = 2
    VOLUME = 3

    WITH_COLOR = 0
    NO_COLOR = 3

    COLORTBL = {
        NODE:Color.RED,
        STORAGE_POOL:Color.WHITE,
        RESOURCE:Color.BLUE,
        VOLUME:Color.NONE
    }

    def __init__(self, name, description):
        """
        Creates a new TreeNode object

        :param str name: name of the node
        :param str description: description of the node
        """

        self.name = name
        self.description = description
        self.child_list = []

    def print_node(self, no_utf8, no_color):

        enc = 'ascii'
        try:
            import locale
            if (locale.getdefaultlocale()[1].lower() == 'utf-8') and (not no_utf8):
                enc = 'utf8'
        except ImportError:
            pass

        if no_color:
            self.print_node_in_tree("", "", "", enc, self.NO_COLOR)
        else:
            self.print_node_in_tree("", "", "", enc, self.WITH_COLOR)
          

    def print_node_in_tree(self, connector, element_marker, child_prefix, enc, level):
        if connector:
            print(connector)

        print(element_marker + self.COLORTBL[level] + self.name + Color.NONE + ' (' + self.description + ')')
 
        if level < self.VOLUME:
            level += 1

        for child_node in self.child_list[:-1]:
            child_node.print_node_in_tree(
                child_prefix + self.DTBL[enc]['svb'],
                child_prefix + self.DTBL[enc]['pnc'],
                child_prefix + self.DTBL[enc]['svb'],
                enc,
                level
            )

        for child_node in self.child_list[-1:]:
            child_node.print_node_in_tree(
                child_prefix + self.DTBL[enc]['svb'],
                child_prefix + self.DTBL[enc]['plnc'],
                child_prefix + self.DTBL[enc]['spc'],
                enc,
                level
            )

    def add_child(self, child):
        self.child_list.append(child)

    def find_child(self, name):
        for child in self.child_list:
            if child.name == name:
                return child
        return None

    def set_description(self, description):
        self.description = description

    def add_description(self, description):
        self.description += description
