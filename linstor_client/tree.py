# -*- coding: utf-8 -*-
from __future__ import print_function
from linstor_client.consts import Color
import locale


class TreeFormatter:
    TREE_DRAWING_TABLE = {
        'utf8': {
            'connector_continue': u'   │',
            'connector_end': u'    ',
            'child_marker_continue': u'   ├───',
            'child_marker_end': u'   └───'
        },
        'ascii': {
            'connector_continue': '   |',
            'connector_end': '    ',
            'child_marker_continue': '   |---',
            'child_marker_end': '   +---'
        }
    }

    def __init__(self, no_utf8, no_color):
        enc = 'ascii'
        if not no_utf8:
            locales = locale.getdefaultlocale()
            if len(locales) > 1 and locales[1] and isinstance(locales[1], str) and locales[1].lower() == 'utf-8':
                enc = 'utf8'

        self.tree_drawing_strings = TreeFormatter.TREE_DRAWING_TABLE[enc]
        self.no_color = no_color

    def apply_color(self, text, color):
        return text if self.no_color else color + text + Color.NONE

    def get_drawing_string(self, key):
        return self.tree_drawing_strings[key]


class TreeNode:
    def __init__(self, name, description, color):
        """
        Creates a new TreeNode object

        :param str name: name of the node
        :param str description: description of the node
        :param color: color for the node name
        """

        self.name = name
        self.description = description
        self.color = color
        self.child_list = []

    def print_node(self, no_utf8, no_color):
        self.print_node_in_tree("", "", "", TreeFormatter(no_utf8, no_color))

    def print_node_in_tree(self, connector, element_marker, child_prefix, formatter):
        if connector:
            print(connector)

        print(element_marker + formatter.apply_color(self.name, self.color) + ' (' + self.description + ')')

        for child_node in self.child_list[:-1]:
            child_node.print_node_in_tree(
                child_prefix + formatter.get_drawing_string('connector_continue'),
                child_prefix + formatter.get_drawing_string('child_marker_continue'),
                child_prefix + formatter.get_drawing_string('connector_continue'),
                formatter
            )

        for child_node in self.child_list[-1:]:
            child_node.print_node_in_tree(
                child_prefix + formatter.get_drawing_string('connector_continue'),
                child_prefix + formatter.get_drawing_string('child_marker_end'),
                child_prefix + formatter.get_drawing_string('connector_end'),
                formatter
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

    def to_data(self):
        return {
            'name': self.name,
            'description': self.description,
            'children': [x.to_data() for x in self.child_list]
        }

    def __repr__(self):
        return "TreeNode({n}, {d})".format(n=self.name, d=self.description)
