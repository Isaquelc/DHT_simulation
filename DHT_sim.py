"""
This is an implementation of a simulation of a distributated hash table, inspired by the chord algorithm
Author: Isaque Lopes Campello
"""

import base64
import textwrap
import hashlib
from pathlib import Path
import numpy as np
import shutil
import os


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

        # each node has it's own memory, simulated by a list of list (to deal with collisions)
        # for simulation purposes, we will store only the paths in the memory, 
        # and the actual data in local folders
        self.memory = [[] for bucket in range(256)]

        # in order to keep track of what are the current smallest and largest nodes, 
        # each node will have a "first" property, set to true only if it meets certain conditions
        # and will be updated as the node joins the network
        self.first = True

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
        
        # upon joining a network, each node will have a directory, if it doesn't already exist
        # this is where the data will be actually stored,
        # the memory list will store the paths 
        Path(self.name).mkdir(parents=True, exist_ok=True)

        # be responsible for correct data 
        # check which data from it's right neightbour this node should take over
        network_files = []
        for bucket in self.neighbours[1].memory:
            if bucket: # if the list is not empty
                for item in bucket:
                    key = item[0]
                    name = item[1].rpartition("/")[-1]
                    if (key <= self.id) or (self.first and key > self.neighbours[0].id):
                        network_files.append(name)
                        position = key % 256
                        # add item to this node's memory
                        self.memory[position].append((key, f"{self.name}/{name}.txt"))
                        # remove item from neighbour's memory
                        bucket.remove(item)

        # transfer files from right neighbour's directory
        for file in os.listdir(self.neighbours[1].name):
            filename = os.fsdecode(file)
            if filename in network_files:
                # copy file to this node's directory
                shutil.copy2(f"{self.neighbours[1].name}/{filename}", self.name)
                # remove file from neighbour's directory
                os.remove(f"{self.neighbours[1].name}/{filename}")

        return None

    def leave_network(self):
        """
        When a node wishes to leave the network, this functions is called,
        and the node updates it's neighbours' neighbour list
        """
        # list of files the current node was hosting for the network
        # we will filter out files the node might have donwloaded fully (leeched) from the network
        network_files = []

        if self.neighbours == [self, self]:
            print("Node already outside network")
            # delete this node's directory should it exist
            shutil.rmtree(f"{self.name}")
            return None
        else:
            # transfer path information to right neighbour
            for bucket in self.memory:
                if bucket: # if the list is not empty
                    for item in bucket:
                        key = item[0]
                        name = item[1].rpartition("/")[-1]
                        network_files.append(name)
                        position = key % 256
                        self.neighbours[1].memory[position].append((key, f"{self.neighbours[1].name}/{name}"))
            # transfer files to right neighbour's directory
            for file in os.listdir(self.name):
                filename = os.fsdecode(file)
                if filename in network_files:
                    shutil.copy2(f"{self.name}/{filename}", self.neighbours[1].name)
            
            # should this node be the first one, then it's right neighbour becomes the first
            if self.first:
                self.neighbours[1].first = True

            # update neighbours
            self.neighbours[0].neighbours[1] = self.neighbours[1]
            self.neighbours[1].neighbours[0] = self.neighbours[0]
            self.neighbours = [self, self]
            self.first = True
        
        # delete this node's directory
        shutil.rmtree(f"{self.name}")

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
            position = key % 256
            self.memory[position].append((key, f"{self.name}/{name}.txt"))
        # elif self.first and (key > self.neighbours[0].id or key < self.id):
        #     self.memory.append((key, value))
        elif key > self.id:
            self.neighbours[1].store_val(key, value, name)
        
        else:
            self.neighbours[0].store_val(key, value, name)

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
        
        return None

    def fetch_val(self, key):
        """
        searches the peers until it finds the one responsible for the key,
        and then returns the value associated with the key to the current node
        """

        position = key % 256
        node = self
        
        while node.first == False:
            if key > node.id:
                node = node.neighbours[1]
            if key < node.neighbours[0].id:
                node = node.neighbours[0]
            else:
                for item in node.memory[position]:
                    if item[0] == key:
                        path = item[1]
                        return path
        if node.first:
            for item in node.memory[position]:
                    if item[0] == key:
                        path = item[1]
                        return path
        else:
            print("ERROR: could not find requested item")
            return None

    def leech(self, video_name, n_parts):
        """
        Takes as input a video name and the number of parts of the video, 
        and retrieves all the parts, joins them, and downloads the video to 
        the current nodes' directory
        """
        text = ""
        for i in range(n_parts):
            name = f"{video_name}_{i}"
            key = hash_func(name)
            path = self.fetch_val(key)
            with open(path) as text_file:
                text += text_file.read()
        with open(f"{self.name}/{video_name}.mp4", "wb+") as videoFile:
            videoFile.write(base64.b64decode(text.encode("UTF-8")))
        
        return None