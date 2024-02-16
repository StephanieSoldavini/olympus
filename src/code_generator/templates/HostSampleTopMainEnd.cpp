    alveo_host.pack_input(inputs);

    alveo_host.create_buffers();
 
    std::cout << "Starting FPGA execution!" << std::endl;

    alveo_host.run();

    std::cout << "FPGA execution completed!" << std::endl;

    unsigned int ping = 0;
    alveo_host.unpack_output(outputs, ping);
    unsigned int checks = alveo_host.num_times_b;
    checks = (checks/4)*4;

#ifdef DEBUG
    std::cout << "checks: " << checks << std::endl;
#endif
    bool match = true;
    unsigned int num_errors = 0;
    for (unsigned int i = 0; i < num_cu; i++) {
       unsigned int err = verify(result_sw_v, result_hw_v[i*PING_PONG_SIZE + (!ping)], checks);
       std::cout << "CU = " << i << " - num errors = " << err << std::endl;
       num_errors += err;
    }
    if (num_errors > 0) match = false;
    std::cout << (match ? "TEST PASSED" : "TEST FAILED") << std::endl;
 
    /*
    std::cout << "POINTS          = " << points << std::endl;
    std::cout << "NUM_CU          = " << num_cu << std::endl;
    std::cout << "NUM_TIMES       = " << alveo_host.num_times << "(per CU)" << std::endl;
    std::cout << "NUM_BATCHES     = " << alveo_host.num_batches << std::endl;

    std::cout << "KERNEL TIME     = " << kernel_time.count() << " s" << std::endl;
    double gflops_k = (((double)points / (1000.0*1000.0*1000.0))*(double)(FLOP_PER_KERNEL))/kernel_time.count();
    std::cout << "GFLOPS (kernel) = " << gflops_k << std::endl; 
    std::cout << "FULL TIME       = " << full_time.count() << " s" << std::endl;
    double gflops = (((double)points / (1000.0*1000.0*1000.0))*(double)(FLOP_PER_KERNEL))/full_time.count();
    std::cout << "GFLOPS (total)  = " << gflops << std::endl; 
    */
    
    return (match ? EXIT_SUCCESS : EXIT_FAILURE);
