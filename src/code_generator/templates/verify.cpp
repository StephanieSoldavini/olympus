// Function for verifying results
unsigned int verify(data_host_vector_t& source_sw_results, data_host_vector_t&  source_hw_results, unsigned int num_times) 
{
    unsigned int num_errors = 0;
    for (unsigned int t = 0; t < num_times; t++) 
    {
	    for (size_t i = 0; i < OUTPUT_SIZE; i++) 
	    {
		    if (source_hw_results[t*OUTPUT_SIZE+i] != source_sw_results[i]) 
		    {
#ifdef FULL_DEBUG
			    //std::cout << "Error: Result mismatch in Operation" << std::endl;
			    std::cout << "Error: i = " << i << " CPU result = " << source_sw_results[i]
				    << " Device result = " << source_hw_results[t*OUTPUT_SIZE+i] << std::endl;
#endif
                num_errors++;
		    }
	    }
    }
    return num_errors;
}

