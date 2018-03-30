# -*- coding: utf-8 -*-
from __future__ import print_function

class TreeNode:
    SPACE_AND_VBAR = u'   │'
    SPACE = u'    '
    PRE_NODE_CHARS = u'   ├───'
    PRE_LAST_NODE_CHARS = u'   └───'

    def __init__(self, name, description):
        """
        Creates a new TreeNode object

        :param str name: name of the node
        :param str description: description of the node
        """

        self.name = name
        self.description = description
        self.child_list = []

    def print_node(self):
        self.print_node_in_tree("", "", "")

    def print_node_in_tree(self, connector, element_marker, child_prefix):
        if connector:
            print(connector)

        print(element_marker + self.name + ' (' + self.description + ')')

        for child_node in self.child_list[:-1]:
            child_node.print_node_in_tree(
                child_prefix + self.SPACE_AND_VBAR,
                child_prefix + self.PRE_NODE_CHARS,
                child_prefix + self.SPACE_AND_VBAR
            )

        for child_node in self.child_list[-1:]:
            child_node.print_node_in_tree(
                child_prefix + self.SPACE_AND_VBAR,
                child_prefix + self.PRE_LAST_NODE_CHARS,
                child_prefix + self.SPACE
            )

    def add_child(self, child):
        self.child_list.append(child)

    def find_child(self, name):
        for child in self.child_list:
            if child.name == name:
                return child
        return None

    def set_description (self, description):
        self.description = description

    def add_description (self, description):
        self.description += description
