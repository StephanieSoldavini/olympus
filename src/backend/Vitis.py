import os

#import code_generator.code_generator as Code
#import code_generator.cpp_generator as Cpp

from backend.Backend import Backend

class Vitis(Backend):
    toolchain = "2020.1"

    def createBuildFolders(self):
        self.createFolder(os.path.join(self.root,"host"))
        self.createFolder(os.path.join(self.root,"src","hls"))
        self.createFolder(os.path.join(self.root,"src","rtl"))
        self.createFolder(os.path.join(self.root,"scripts"))

    def buildKernel(self, kernel):
        cpp = Code.CodeFile(os.path.join(self.root,"src","hls",'example.cpp'))
        cpp("#include <runtime.h>")
