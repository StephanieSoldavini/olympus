#ifdef TIMING
std::chrono::duration<double> full_time(0);
std::chrono::duration<double> kernel_time(0);

auto sym_start = std::chrono::high_resolution_clock::now();
#endif

const unsigned int ping = 0;

for (unsigned int b = 0; b < num_batches; b++)
{
    update_num_times_b(b);

    // Copy first batch of input data to Device Global Memory PING (0)
    transfer_input_batch(ping);

    // Data in copy done (0)
    data_finish(ping);

#ifdef TIMING
    auto kernel_start = std::chrono::high_resolution_clock::now();
#endif

    kernel(ping);

    // Kernel done on PING
    kernel_finish(ping);

#ifdef TIMING
    auto kernel_end = std::chrono::high_resolution_clock::now();
    kernel_time += std::chrono::duration<double>(kernel_end - kernel_start);
#endif


    // Data out copy PING
    transfer_output_batch(ping);

    // Data out copy done
    data_finish(ping);

#ifdef DEBUG
    unpack_output(outputs);

    for (unsigned int i = 0; i < num_cu; i++) {
        std::cout << "!ping: " << !ping << std::endl;
        unsigned int err = verify(source_sw_results, source_host_results[i], checks);
        std::cout << "CU = " << i << " - num errors = " << err << std::endl;
        num_errors += err;
    }
#endif

}

