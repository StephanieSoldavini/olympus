#ifdef TIMING
auto sym_end = std::chrono::high_resolution_clock::now();
full_time = std::chrono::duration<double>(sym_end - sym_start);

std::cout << "POINTS          = " << points << std::endl;
std::cout << "NUM_CU          = " << num_cu << std::endl;
std::cout << "NUM_TIMES       = " << num_times << "(per CU)" << std::endl;
std::cout << "NUM_BATCHES     = " << num_batches << std::endl;

std::cout << "KERNEL TIME     = " << kernel_time.count() << " s" << std::endl;
double gflops_k = (((double)points / (1000.0*1000.0*1000.0))*(double)(FLOPS_PER_KERNEL))/kernel_time.count();
std::cout << "GFLOPS (kernel) = " << gflops_k << std::endl;
std::cout << "FULL TIME       = " << full_time.count() << " s" << std::endl;
double gflops = (((double)points / (1000.0*1000.0*1000.0))*(double)(FLOPS_PER_KERNEL))/full_time.count();
std::cout << "GFLOPS (total)  = " << gflops << std::endl;
#endif
