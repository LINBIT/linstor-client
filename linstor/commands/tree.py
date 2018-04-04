# -*- coding: utf-8 -*-
from __future__ import print_function


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

    def __init__(self, name, description):
        """
        Creates a new TreeNode object

        :param str name: name of the node
        :param str description: description of the node
        """

        self.name = name
        self.description = description
        self.child_list = []

    def print_node(self, no_utf8):

        enc = 'ascii'
        try:
            import locale
            if (locale.getdefaultlocale()[1].lower() == 'utf-8') and (not no_utf8):
                enc = 'utf8'
        except ImportError:
            pass

        self.print_node_in_tree("", "", "", enc)

    def print_node_in_tree(self, connector, element_marker, child_prefix, enc):
        if connector:
            print(connector)

        print(element_marker + self.name + ' (' + self.description + ')')

        for child_node in self.child_list[:-1]:
            child_node.print_node_in_tree(
                child_prefix + self.DTBL[enc]['svb'],
                child_prefix + self.DTBL[enc]['pnc'],
                child_prefix + self.DTBL[enc]['svb'],
                enc
            )

        for child_node in self.child_list[-1:]:
            child_node.print_node_in_tree(
                child_prefix + self.DTBL[enc]['svb'],
                child_prefix + self.DTBL[enc]['plnc'],
                child_prefix + self.DTBL[enc]['spc'],
                enc
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
