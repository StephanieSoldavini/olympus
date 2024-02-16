#ifndef __ALVEO_HOST_H__
#define __ALVEO_HOST_H__

#define CL_HPP_CL_1_2_DEFAULT_BUILD
#define CL_HPP_TARGET_OPENCL_VERSION 120
#define CL_HPP_MINIMUM_OPENCL_VERSION 120
#define CL_HPP_ENABLE_PROGRAM_CONSTRUCTION_FROM_ARRAY_COMPATIBILITY 1
#define CL_USE_DEPRECATED_OPENCL_1_2_APIS

//OCL_CHECK doesn't work if call has templatized function call
#define OCL_CHECK(error,call)                                       \
    call;                                                           \
    if (error != CL_SUCCESS) {                                      \
      printf("%s:%d Error calling " #call ", error code is: %d\n",  \
              __FILE__,__LINE__, error);                            \
      exit(EXIT_FAILURE);                                           \
    }
#define DATA_SIZE 4 //1048576
#define BUFFER_SIZE 2 //1024
#define XCL_MEM_TOPOLOGY                (1<<31)

// HBM Pseudo-channel(PC) requirements
#define MAX_HBM_PC_COUNT 32
#define PC_NAME(n) n | XCL_MEM_TOPOLOGY

// size of 1 channel: 256 MB
#define CH_SIZE (256*1024*1024)

#include "xcl2.hpp"

#include <vector>
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <algorithm>
#include <CL/cl2.hpp>
#include <cmath>

#include "../src/Kernel.gen.h"

// array type for data in HBM
typedef std::vector<data_t,aligned_allocator<data_t> > data_hbm_vector_t;

// array type for original data types 
// (i.e. used if input/output is double and kernel processes fixedp)
typedef std::vector<data_host_t,aligned_allocator<data_host_t> > data_host_vector_t;

class AlveoHost
{
public:
    // name of xclbin
    //std::string binaryFile;

    // Error code
    //cl_int err;

    // the number of instantiated CUs
    unsigned int num_cu;

    // the number of points to execute
    unsigned int points;

    // number of elements that can fit in the memory space (size of a batch)
    unsigned int num_times;
    
    // number of times to run 
    unsigned int num_batches;

    // number of times for the current batch (smaller for the last batches)
    unsigned int num_times_b;
private:

    // for error checking
    unsigned int num_times_b_prev;

    // the detected FPGA
    cl::Device device;

    // the cl context
    cl::Context context;
    
    // the kernels
    std::vector<cl::Kernel> krnl;

    // queues for data movement
    std::vector<std::vector<cl::CommandQueue> > data_queues
            {PING_PONG_SIZE, std::vector<cl::CommandQueue>()};

    // queues for kernel executions
    std::vector<std::vector<cl::CommandQueue> > k_queues
            {PING_PONG_SIZE, std::vector<cl::CommandQueue>()};

    // input    
    data_hbm_vector_t source_full_input;

    // output
    std::vector<data_hbm_vector_t> source_hbm_results;

    // hbm input buffer
    std::vector<std::vector<cl::Buffer> > buffer_input 
            {PING_PONG_SIZE, std::vector<cl::Buffer>()};

    // hbm output buffer
    std::vector<std::vector<cl::Buffer> > buffer_output 
            {PING_PONG_SIZE, std::vector<cl::Buffer>()};

    const int pc[MAX_HBM_PC_COUNT] = {
        PC_NAME(0),  PC_NAME(1),  PC_NAME(2),  PC_NAME(3),  
        PC_NAME(4),  PC_NAME(5),  PC_NAME(6),  PC_NAME(7),
        PC_NAME(8),  PC_NAME(9),  PC_NAME(10), PC_NAME(11), 
        PC_NAME(12), PC_NAME(13), PC_NAME(14), PC_NAME(15),
        PC_NAME(16), PC_NAME(17), PC_NAME(18), PC_NAME(19), 
        PC_NAME(20), PC_NAME(21), PC_NAME(22), PC_NAME(23),
        PC_NAME(24), PC_NAME(25), PC_NAME(26), PC_NAME(27), 
        PC_NAME(28), PC_NAME(29), PC_NAME(30), PC_NAME(31)
    };

public:
    AlveoHost(std::string binaryFile, unsigned int num_cu, unsigned int points, std::string krnl_name);
    ~AlveoHost();

    void pack_input(std::vector<data_host_vector_t *> inputs);
    void unpack_output(std::vector<std::vector<data_host_vector_t> *> outputs, unsigned int ping);
    void run();
    void create_buffers();
    void transfer_input_batch(unsigned int ping);
    void transfer_output_batch(unsigned int ping);
    void data_finish(unsigned int ping);
    void kernel(unsigned int ping);
    void kernel_finish(unsigned int ping);
    void update_num_times_b(unsigned int b);

    std::vector<cl::Device> get_devices(const std::string& vendor_name) {
        size_t i;
        cl_int err;
        std::vector<cl::Platform> platforms;
        OCL_CHECK(err, err = cl::Platform::get(&platforms));
        cl::Platform platform;
        for (i  = 0 ; i < platforms.size(); i++){
            platform = platforms[i];
            OCL_CHECK(err, std::string platformName = platform.getInfo<CL_PLATFORM_NAME>(&err));
            if (platformName == vendor_name){
                std::cout << "Found Platform" << std::endl;
                std::cout << "Platform Name: " << platformName.c_str() << std::endl;
                break;
            }
        }
        if (i == platforms.size()) {
            std::cout << "Error: Failed to find Xilinx platform" << std::endl;
            exit(EXIT_FAILURE);
        }

        //Getting ACCELERATOR Devices and selecting 1st such device 
        std::vector<cl::Device> devices;
        OCL_CHECK(err, err = platform.getDevices(CL_DEVICE_TYPE_ACCELERATOR, &devices));
        return devices;
    }

    char* read_binary_file(const std::string &xclbin_file_name, unsigned &nb) 
    {
        std::cout << "INFO: Reading " << xclbin_file_name << std::endl;

        if(access(xclbin_file_name.c_str(), R_OK) != 0) {
            printf("ERROR: %s xclbin not available please build\n", xclbin_file_name.c_str());
            exit(EXIT_FAILURE);
        }
        //Loading XCL Bin into char buffer 
        std::cout << "Loading: '" << xclbin_file_name.c_str() << "'\n";
        std::ifstream bin_file(xclbin_file_name.c_str(), std::ifstream::binary);
        bin_file.seekg (0, bin_file.end);
        nb = bin_file.tellg();
        bin_file.seekg (0, bin_file.beg);
        char *buf = new char [nb];
        bin_file.read(buf, nb);
        return buf;
    }
};
#endif /*__ALVEO_HOST_H__*/
