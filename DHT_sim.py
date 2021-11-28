"""
This is an implementation of a simulation of a distributated hash table, inspired by the chord algorithm
Author: Isaque Lopes Campello
"""

import base64
import textwrap
import hashlib
from pathlib import Path
import numpy as np


def hash_func(name):
    return int(hashlib.sha256(name.encode("UTF-8")).hexdigest(), 16)

class node:

    def __init__(self, name):

        # each node has it's own unique name (simualtes it's ip address and/or port)
        self.name = name

        # each node has it's own unique id, which is a 256 bit integer
        self.id = hash_func(name)
    
        # each node knows two other nodes, it's neighours
        # this list will be updated as nodes join or leave the network
        self.neighbours = [self, self]

        # each node has it's own memory, simulated by a list
        # for simulation purposes, we will store only the paths in the memory, 
        # and the actual data in local folders
        self.memory = []

        # in order to keep track of what are the current smallest and largest nodes, 
        # each node will have a "first" property, set to true only if it meets certain conditions
        # and will be updated as the node joins the network
        self.first = True

        # upon creation, each node will have a directory, if it doesn't already exist
        # this is where the data will be actually stored,
        # the memory list will store the paths 
        Path(name).mkdir(parents=True, exist_ok=True)

    def join_network(self, node):
        """
        function that adds current node to the network based on another node,
        which needs to already be in the network.
        We use the convention for the neighbours being [left, right],
        and add the current node to the left of the input node.
        We forward the current node to the correct place in the network it should be added,
        based on it's id.
        """
        # in case the current node is already in network
        if self.neighbours != [self, self]:
            print("node already in the network")
            return None
        # in case there is no existing network
        elif node.neighbours == [node, node]:
            self.neighbours = [node, node]
            node.neighbours = [self, self]
            # update who is the first node
            if self.id > node.id:
                self.first = False
            else:
                node.first = False
        # add into existing network
        elif node.first == False:
            if self.id > node.id:
                self.join_network(node.neighbours[1])
            elif self.id < node.neighbours[0].id:
                self.join_network(node.neighbours[0])
            else:
                self.neighbours[0] = node.neighbours[0]
                self.neighbours[1] = node
                node.neighbours[0].neighbours[1] = self
                node.neighbours[0] = self
                self.first = False
        
        elif node.first:
            if self.id > node.id:
                self.neighbours[0] = node.neighbours[0]
                self.neighbours[1] = node
                node.neighbours[0].neighbours[1] = self
                node.neighbours[0] = self
                self.first = False
            elif self.id < node.id:
                self.neighbours[0] = node.neighbours[0]
                self.neighbours[1] = node
                node.neighbours[0].neighbours[1] = self
                node.neighbours[0] = self
                node.first = False    
        return None

    def leave_network(self):
        """
        When a node wishes to leave the network, this functions is called,
        and the node updates it's neighbours' neighbour list
        """
        if self.neighbours == [self, self]:
            print("Node already outside network")
            return None
        else:
            self.neighbours[0].neighbours[1] = self.neighbours[1]
            self.neighbours[1].neighbours[0] = self.neighbours[0]
            self.neighbours = [self, self]

    def store_val(self, key, value, name):
        """
        Stores the value with the corresponding key if this node is responsible for the key,
        else calls this function for the next closest node
        """
        if (self.neighbours[0].id < key <= self.id) or (self.first and (key > self.neighbours[0].id or key < self.id)):
            # store the file in storage
            with open(f"{self.name}/{name}.txt", "w") as text_file:
                text_file.write(value)
            # add path to memory
            self.memory.append((key, name))
        # elif self.first and (key > self.neighbours[0].id or key < self.id):
        #     self.memory.append((key, value))
        elif key > self.id:
            self.neighbours[1].store_val(key, value, name)
        
        else:
            self.neighbours[0].store_val(key, value, name)

    def fetch_val(self, key):
        """
        searches the peers until it finds the one responsible for the key,
        and then returns the value associated with the key to the current node
        """
        node = self
        if self.first == False:
            if key > node.id:
                node = node.neighbours[1]
            if key < node.neighbours[0].id:
                node = node.neighbours[0]
            else:
                # TODO
                # download data
                pass
        elif node.first:
            # TODO
            # download data
            pass

    def seed(self, video_path, video_name, n_parts):
        """
        Takes as input a path to a video file and an integer n_parts, 
        the node will then encode the file in base64, separate it into n_parts parts, 
        and store each part in the corresponding node according to the hash key generated
        """
        # opens video file and encodes it in base64
        with open(video_path, "rb") as videoFile:
            video_text = base64.b64encode(videoFile.read()).decode("UTF-8")
        # get size of each part for splitting
        n_parts = round(len(video_text) / n_parts)
        # split it into n equal parts
        video_parts = textwrap.wrap(video_text, n_parts)

        for i, part in enumerate(video_parts):
            name = f"{video_name}_{i}"
            key = hash_func(name)
            self.store_val(key, part, name)


# Create network
a = node("a")
b = node("b")
c = node("c")
d = node("d")
e = node("e")

b.join_network(a)
c.join_network(a)
d.join_network(a)
e.join_network(a)

for node in [a, b, c, d, e]:
    print(f"{node.name} id: {node.id}, neighbours: {node.neighbours[0].name}, {node.neighbours[1].name}, first: {node.first}")

# test file
test_file = "this is a test file"
test_file_key = hash_func(test_file)
print(f"key = {test_file_key}, value:{test_file}")

# test file 2
test_file_2 = "this is a different test file"
test_file_key_2 = hash_func(test_file_2)
print(f"key = {test_file_key_2}, value:{test_file_2}")

b.store_val(test_file_key, test_file, "test_file")
b.store_val(test_file_key_2, test_file_2, "test_file_2")

a.seed("/mnt/c/Users/isaqu/Documents/UFABC_temp/AED2_projeto/videos/David_&_Goliath_animation.mp4", "David_&_Goliath_animation", 5)

for node in [a, b, c, d, e]:
    print(f"{node.name} memory : {node.memory}")
