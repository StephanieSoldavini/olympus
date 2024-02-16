import json
import os

import backend
import backend.Backend as Backend

class PlatformNode:
    name = None
    type = None

    def __init__(self, node_desc, fout):
        self.name = node_desc["name"]
        self.type = node_desc["type"]
        self.gen = backend.backendGenerator(self.type, os.path.join(fout,self.name))

    def __str__(self):
        return f"{self.name}: {self.type}"

class PlatformDescription:
    name = None
    nodes = []

    def __init__(self, json_file, fout):
        try:
            with open(json_file, 'r') as f:
                platform = json.load(f)
        except IOError:
            print(f'Platform file "{json_file}" does not exist.')
            exit(1)
        if "platform" not in platform: Exception("Invalid platform description")
        self.name = platform["platform"]["name"]
        for n in platform["platform"]["nodes"]:
            self.nodes.append(PlatformNode(n, fout))

    #def print(self):
    #    print(".:: Platform name:",self.name,"::.")
    #    print("Number of nodes =",len(self.nodes))
    #    for n in self.nodes:
    #        print(" - ", end='')
    #        n.print()
    def __str__(self):
        buf = F""".:: Platform name: {self.name} ::.
        Number of nodes = {len(self.nodes)}"""
        for n in self.nodes:
            buf += '\n'
            buf += " - "
            buf += str(n)
        return buf


