
#include "AlveoHost.h"


// contructor
AlveoHost::AlveoHost(std::string binaryFile, unsigned int num_cu, unsigned int points, std::string krnl_name) : num_cu(num_cu), points(points)
{
    cl_int err;
    //std::vector<cl::Kernel> krnl(num_cu);
    krnl.resize(num_cu);
    // OPENCL HOST CODE AREA START
    std::vector<cl::Device> devices = xcl::get_devices("Xilinx");
    devices.resize(1);
    device = devices[0];
    // Creating Context and Command Queue for selected Device
    OCL_CHECK(err, cl::Context context1(device, NULL, NULL, NULL, &err));

    context = context1;
    //std::vector<std::vector<cl::CommandQueue> > data_queues {PING_PONG_SIZE, std::vector<cl::CommandQueue>(num_cu)};
    //data_queue.resize(
    //data_queues_ptr = &data_queues;

    //std::vector<std::vector<cl::CommandQueue> > k_queues {PING_PONG_SIZE, std::vector<cl::CommandQueue>(num_cu)};
    //k_queues_ptr = &k_queues;

    for (int p = 0; p < PING_PONG_SIZE; p++) {
        data_queues[p].resize(num_cu);
        for (unsigned int i = 0; i < num_cu; i++) {
            OCL_CHECK(err, cl::CommandQueue q(context, device, CL_QUEUE_PROFILING_ENABLE, &err));
            data_queues[p][i] = q;
        }
    }
    for (int p = 0; p < PING_PONG_SIZE; p++) {
        k_queues[p].resize(num_cu);
        for (unsigned int i = 0; i < num_cu; i++) {
            OCL_CHECK(err, cl::CommandQueue q(context, device, CL_QUEUE_PROFILING_ENABLE, &err));
            k_queues[p][i] = q;
        }
    }
    // read_binary_file() command will find the OpenCL binary file created using
    // the V++ compiler load into OpenCL Binary and return pointer to file buffer.
    auto fileBuf = xcl::read_binary_file(binaryFile);
    cl::Program::Binaries bins{{fileBuf.data(), fileBuf.size()}};
    std::cout << "Trying to program device: " << device.getInfo<CL_DEVICE_NAME>() << std::endl;
    cl::Program program(context, {device}, bins, nullptr, &err);
    if (err != CL_SUCCESS) {
        std::cout << "Failed to program device with xclbin file!\n";
        return; // EXIT_FAILURE; // TODO move this out of the constructor
    } else {
        std::cout << "Device: program successful!\n";
        // Creating Kernel object using Compute unit names
        for (unsigned int i = 0; i < num_cu; i++) {
            std::string cu_id = std::to_string(i + 1);
            std::string krnl_name_full = krnl_name + ":{" + krnl_name + "_" + cu_id + "}";
            printf("Creating a kernel [%s] for CU(%d)\n", krnl_name_full.c_str(), i + 1);
            OCL_CHECK(err, krnl[i] = cl::Kernel(program, krnl_name_full.c_str(), &err));
        }
    }

    num_times = floor(CH_SIZE/(std::max(INPUT_SIZE,OUTPUT_SIZE)*sizeof(data_t)));
    num_times = (num_times/4)*4;
    
    num_batches = ceil((double)points/(double)(num_cu*PING_PONG_SIZE*num_times))*PING_PONG_SIZE; // will always be divisible by PING_PONG_SIZE

    std::cout << "POINTS      = " << points << std::endl;
    std::cout << "NUM_CU      = " << num_cu << std::endl;
    std::cout << "NUM_TIMES   = " << num_times << "(per CU)" << std::endl;
    std::cout << "NUM_BATCHES = " << num_batches << std::endl;
}

AlveoHost::~AlveoHost() {
    // TODO
}

void AlveoHost::create_buffers()
{
    // Create empty output buffers
    // Resize the collection of results to hold one set of results for each PP*CU
    source_hbm_results.resize(PING_PONG_SIZE*num_cu);

    // Resize each of the results arrays to fit the full results
    for (unsigned int c = 0; c < PING_PONG_SIZE*num_cu; c++) {
       source_hbm_results[c].resize(OUTPUT_SIZE*num_times);
    }

    std::vector<std::vector<cl_mem_ext_ptr_t> > inBufExt 
            {PING_PONG_SIZE, std::vector<cl_mem_ext_ptr_t>(num_cu)};
    std::vector<std::vector<cl_mem_ext_ptr_t> > outBufExt 
            {PING_PONG_SIZE, std::vector<cl_mem_ext_ptr_t>(num_cu)};

    /*
    std::vector<std::vector<cl::Buffer> > buffer_input 
            {PING_PONG_SIZE, std::vector<cl::Buffer>(num_cu)};
    std::vector<std::vector<cl::Buffer> > buffer_output 
            {PING_PONG_SIZE, std::vector<cl::Buffer>(num_cu)};
    */

    // For Allocating Buffer to specific Global Memory PC, user has to use
    // cl_mem_ext_ptr_t and provide the PCs
    for (int p = 0; p < PING_PONG_SIZE; p++) {
        for (unsigned int i = 0; i < num_cu; i++) {
            inBufExt[p][i].obj = source_full_input.data();
            inBufExt[p][i].param = 0;
            inBufExt[p][i].flags = pc[(i*2*PING_PONG_SIZE) + p]; // 2 for in + out

            outBufExt[p][i].obj = source_hbm_results[i*PING_PONG_SIZE + p].data();
            outBufExt[p][i].param = 0;
            outBufExt[p][i].flags = pc[((i*2+1)*PING_PONG_SIZE) + p]; // 2 for in + out
#ifdef DEBUG
            std::cout << "cu: " << i << " p: " << p << " in pc: " << (i*2*PING_PONG_SIZE) + p << " out pc : " << ((i*2+1)*PING_PONG_SIZE) + p << std::endl;
#endif
        }
    }

    // These commands will allocate memory on the FPGA. The cl::Buffer objects can
    // be used to reference the memory locations on the device.
    // Creating Buffers
    cl_int err;
    for (int p = 0; p < PING_PONG_SIZE; p++) {
        buffer_input[p].resize(num_cu);
        buffer_output[p].resize(num_cu);
        for (unsigned int i = 0; i < num_cu; i++) {
            OCL_CHECK(err, 
                    buffer_input[p][i] = cl::Buffer(context, 
                        CL_MEM_READ_ONLY | CL_MEM_EXT_PTR_XILINX | CL_MEM_USE_HOST_PTR,
                        sizeof(data_t) * (INPUT_SIZE * num_times),
                        &inBufExt[p][i], 
                        &err
                        )
                    );

            OCL_CHECK(err, 
                    buffer_output[p][i] = cl::Buffer(context, 
                        CL_MEM_WRITE_ONLY | CL_MEM_EXT_PTR_XILINX | CL_MEM_USE_HOST_PTR,
                        sizeof(data_t) * (OUTPUT_SIZE * num_times),
                        &outBufExt[p][i], 
                        &err
                        )
                    );
        }
    }
}

void AlveoHost::update_num_times_b(unsigned int b)
{
#ifdef DEBUG
    std::cout << "--executing batch " << (b+1) << "/" << num_batches << std::endl;
    std::cout << "ping: " << ping << std::endl;

#endif
    num_times_b_prev = num_times_b;
    // Calculate remainder num_times for last iteration
    num_times_b = num_times;
    if (b >= (num_batches - PING_PONG_SIZE)) {
        num_times_b = (points - ((num_batches - PING_PONG_SIZE) * num_times * num_cu)) /
            (num_cu * PING_PONG_SIZE);
#ifdef DEBUG
        std::cout << "b: " << b << " num_times_b: " << num_times_b << std::endl;
#endif
    }
}

void AlveoHost::transfer_input_batch(unsigned int ping)
{
    cl_int err;
    for (unsigned int i = 0; i < num_cu; i++) {
        OCL_CHECK(err,
                err = data_queues[ping][i].enqueueMigrateMemObjects({buffer_input[ping][i]}, 0) 
                // 0 means from host
                );
    }    
}

void AlveoHost::transfer_output_batch(unsigned int ping)
{
    cl_int err;
    for (unsigned int i = 0; i < num_cu; i++) {
        OCL_CHECK(err, 
                err = data_queues[ping][i].enqueueMigrateMemObjects({buffer_output[ping][i]},
                    CL_MIGRATE_MEM_OBJECT_HOST
                    )
                );
#ifdef DEBUG
        std::cout << "done: " << num_times_b << std::endl;
#endif
    }
}

void AlveoHost::data_finish(unsigned int ping)
{
    for (unsigned int i = 0; i < num_cu; i++) {
        data_queues[ping][i].finish(); 
    }
}

/*
void AlveoHost::kernel(unsigned int ping)
{
    cl_int err;
    // Setting the k_vadd Arguments
    for (unsigned int i = 0; i < num_cu; i++) {
        OCL_CHECK(err, err = krnl[i].setArg(0, buffer_input[0][i]));
        OCL_CHECK(err, err = krnl[i].setArg(1, buffer_input[1][i]));
        OCL_CHECK(err, err = krnl[i].setArg(2, buffer_output[0][i]));
        OCL_CHECK(err, err = krnl[i].setArg(3, buffer_output[1][i]));
        OCL_CHECK(err, err = krnl[i].setArg(4, num_times_b));
        OCL_CHECK(err, err = krnl[i].setArg(5, ping));

        // Invoking the kernel
        OCL_CHECK(err, err = k_queues[ping][i].enqueueTask(krnl[i]));
    }
}
*/

void AlveoHost::kernel_finish(unsigned int ping)
{
    for (unsigned int i = 0; i < num_cu; i++) {
        k_queues[ping][i].finish(); 
    }
}

