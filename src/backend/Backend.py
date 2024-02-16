import os

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Backend:
    toolchain = None
    root = None

    def createFolder(self, folder):
        if not os.path.exists(folder): os.makedirs(folder)

    def __init__(self, target_root):
        self.root = target_root
        self.createFolder(self.root)

    def createBuildFolders(self):
        pass

    def createBuildFiles(self):
        pass

    def createRunScripts(self):
        pass

    def buildKernel(self, kernel):
        pass

    def buildGen(self):
        print(f"{bcolors.BOLD}"+self.toolchain+f"{bcolors.ENDC}")
        print(f"{bcolors.UNDERLINE}Generating build folders{bcolors.ENDC}")
        self.createBuildFolders()
        print(f"{bcolors.UNDERLINE}Generating build files{bcolors.ENDC}")
        self.createBuildFiles()
        print(f"{bcolors.UNDERLINE}Generating run scripts{bcolors.ENDC}")
        self.createRunScripts()
