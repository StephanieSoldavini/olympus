#!/usr/bin/env python3.10
import os
from argparse import ArgumentParser 

import targetplatform.PlatformDescription as PlatformDescription
import application.ApplicationDescription as ApplicationDescription
import olympusopt.Transforms as t
import olympusopt.Analyses as a
import code_generator.CUGen as CUGen

#class OlympusKernel:
#    def __init__(self, name, inputs, outputs):
#        self.name = name
#        self.inputs = inputs
#        self.outputs = outputs

class OlympusContext:
    def __init__(self, sysname, outdir, target, application):
        self.sysname = sysname
        self.outdir = outdir
        self.target = target
        self.application = application
#        self.kernels = []
#    def add_kernel(self, name, inputs, outputs):
#        self.kernels.append(OlympusKernel(name, inputs, outputs))


def main():
    # Defining command line options
    parser = ArgumentParser(description="Olympus: Automatic generation of memory systems")
    parser.add_argument("-p", "--platform", dest="fplatform", required="true",
                      help="Specify the target platform description [json]", metavar="FILE")
    parser.add_argument("-a", "--application", dest="fapplication", required="true",
                      help="Specify the application description [mlir]", metavar="FILE")
    parser.add_argument("-o", "--outdir", dest="fout", required="true",
                      help="Specify the output directory", metavar="PATH")
    parser.add_argument("--no-build", dest="do_build", action="store_false",
                      help="Stop execution before final build step")

    # Parsing command line options
    options = parser.parse_args()
    appname = "omm"

    print("---")
    t.test()
    a.test()
    #print("---")

    # Make sure inputs exist 
    ## Platform info
    ### Parsing platform description
    target = PlatformDescription(options.fplatform, options.fout)
    print(target)

    ## MLIR
    ### Parsing application description
    app = ApplicationDescription(appname, options.fapplication) 

    olympusCtx = OlympusContext(appname, options.fout, target, app)

    print(app)
    print(app.networks)
    for z in app.networks:
        for x in app.networks[z].kernels:
            print(x)
            print("Inputs:")
            for y in x.get_inputs():
                print(y)
            print("Outputs:")
            for y in x.get_outputs():
                print(y)
    ## Kernels - TODO actually this is checked from parsing the MLIR and getting the paths from there

    # Sanitize MLIR input

    # Olympus-opt
    ## Do while X:
    ### Analyses
    ### Transforms

    # Lower to hardware
    ## Create Output locations
    os.makedirs(options.fout+"/src", exist_ok=True)
    os.makedirs(options.fout+"/host", exist_ok=True)
    os.makedirs(options.fout+"/mnem", exist_ok=True)

    ## For each kernel:
    ### Generate PLM (mnemosyne)

    # Generate CU(s?)
    
    cus = CUGen(olympusCtx) 
    


    # Generate driver methods
    #gen_drivers()

    if options.do_build:
        pass
        # Build library
        #build_library() #TODO this makes more sense as a makefile task?

        # Generate bitstream



if __name__ == "__main__":
    main()
