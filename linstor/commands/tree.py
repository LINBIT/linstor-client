# -*- coding: utf-8 -*-
from __future__ import print_function

class TreeNode:
    SPACE_AND_VBAR = (u'   ' + u'│')
    SPACE = u'    '
    PRE_NODE_CHARS = u'   ├───'
    PRE_LAST_NODE_CHARS = u'   └───'
    LEVEL_ZERO = 0

    """
        arguments: 
        name: name of the node
        description: description of the node
        level: at which level is the node in the tree, i.e. root is level 0
        child_list: children of this node in the tree
    """
    def __init__(self, name, description, level, end_reached_bitmap, child_list):
        self.name = name
        self.description = description
        self.level = level
        self.end_reached_bitmap = end_reached_bitmap
        self.child_list = child_list

    def print_node(self):

        # The following loop draws a padding line, which is to increase space between branches
        for index,  x in enumerate(self.end_reached_bitmap):
            if self.level == self.LEVEL_ZERO:
                continue
            else:
                index += 1
            if index == self.level:
                print (self.SPACE_AND_VBAR, end=""),
                continue
            else:
                if x:
                    print (self.SPACE, end=""),
                else:
                    print (self.SPACE_AND_VBAR, end=""),
        print(' ')

        for index,  x in enumerate(self.end_reached_bitmap):
            if self.level == self.LEVEL_ZERO:
                continue
            else:
                index += 1
            if index == self.level:
                if x:
                    print(self.PRE_LAST_NODE_CHARS, end=""),
                else:
                    print(self.PRE_NODE_CHARS, end=""),
            else:
                if x:
                    print (self.SPACE, end=""),
                else:
                    print (self.SPACE_AND_VBAR, end=""),

                
        if self.name:
            print  (self.name + ' (' + self.description + ')')

        for y in self.child_list:
            y.print_node()

    def add_child(self, child):
        self.child_list.append(child)

    def find_child(self, name):
        for child in self.child_list:
            if child.name == name:
                return child
        return None

    def set_end_reached_bitmap(self, end_reached_bitmap):
        self.end_reached_bitmap = end_reached_bitmap

    def set_description (self, description):
        self.description = description

    def add_description (self, description):
        self.description += description

    # each node has a bit map on wether the previous levels of nodes are the last nodes,
    # this function recursively builds the bit map of a tree
    def build_end_reached_bitmap(self, my_bitmap):
        self.set_end_reached_bitmap (my_bitmap)

        level = len(my_bitmap)

        if my_bitmap == []:
            child_bitmap = [False]
        else:
            child_bitmap = list(my_bitmap)
            child_bitmap.append(False)
            
        if self.child_list == []:
            return None
            
        for index, node in enumerate(self.child_list):
            
            if index == (len(self.child_list)-1):
                child_bitmap = list(child_bitmap)
                child_bitmap[level] = True

            node.build_end_reached_bitmap(child_bitmap)



