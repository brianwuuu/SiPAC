import os, stat, json

## Given a long representing the nanoseconds, returns a string of the time.
def extract_timing_string(nanoseconds):
    if nanoseconds < 1000:
        # nanoseconds
        entry = nanoseconds
        return "{}ns".format(entry)
    elif nanoseconds >= 1000 and nanoseconds < 1000000:
        # microseconds
        entry = nanoseconds / 1000
        return "{}us".format(entry)
    elif nanoseconds >= 1000000 and nanoseconds < 1000000000:
        # milliseconds
        entry = nanoseconds / 1000000
        return "{}ms".format(entry)
    else:
        # seconds
        entry = nanoseconds / 1000000000
        return "{}s".format(entry)

## Given a long representing the bytes, returns a string of the bytes.
def extract_byte_string(size_bytes):
    entry = None
    if size_bytes < 1000:
        # byte
        entry = "{}B".format(size_bytes)
    elif size_bytes >= 1000 and size_bytes < 1000000:
        # kilo-byte
        entry = "{}KB".format(size_bytes // 1000)
    elif size_bytes >= 1000000 and size_bytes < 1000000000:
        # mega-byte
        entry = "{}MB".format(size_bytes // 1000000)
    elif size_bytes >= 1000000000:
        # giga-byte
        entry = "{}GB".format(size_bytes // 1000000000)
    if entry: return entry
    else: raise Exception("Byte size out of range")

# Parse JSON file into dictionary object
def parseJSON(filename):
    with open(filename) as json_file: 
        json_dict = json.load(json_file)
    return json_dict

# Generate the bash script used to run simulations in Netbench
def generateBashScript(exec_dir, netbench_config_files_list, exp_name=""):
    # Construct the string builder
    directory_change_command = "cd $NETBENCH_HOME\n\n"
    netbench_execution_prefix = "java -jar -ea NetBench.jar "
    str_builder = directory_change_command
    for i in range(len(netbench_config_files_list)):
        str_builder += (netbench_execution_prefix + netbench_config_files_list[i] + "\n")
    # Write the script to the .sh file
    file_name = "/automated_execution_{}.sh".format(exp_name)
    with open(exec_dir + file_name, "w+") as f:
        f.write(str_builder)
    print("[Setup] Generate bash script to {}".format(file_name))
    st = os.stat(exec_dir + file_name)
    os.chmod(exec_dir + file_name, st.st_mode | stat.S_IEXEC)
    return

# Given simulation parameters and network parameters, generate a string to be
# written to the simulation parameter file
def write_simulation_configuration_file(output_base_dir,
                                        output_subdir,
                                        initial_topology_filename, 
                                        traffic_arrivals_filename, 
                                        routing_scheme,
                                        link_delay_filename, 
                                        simulation_runtime_ns,
                                        number_of_flows,
                                        network_property_dictionary):
    # Topology file
    str_builder = "# Topology\n"
    str_builder += "scenario_topology_file={}\n".format(initial_topology_filename)
    str_builder += "\n"
    # Run info 
    str_builder += "# Run Info\n"
    str_builder += "run_folder_name={}\n".format(output_subdir)
    str_builder += "run_folder_base_dir={}\n".format(output_base_dir)
    str_builder += "run_time_ns={}\n".format(simulation_runtime_ns)
    str_builder += "finish_when_first_flows_finish={}\n".format(number_of_flows)
    str_builder += "enable_smooth_rtt=true\n"
    str_builder += "seed=8278897294\n"
    if "check_link_bidirectionality" in network_property_dictionary and not network_property_dictionary["check_link_bidirectionality"]:
        str_builder += "check_link_bidirectionality=false\n"
    str_builder += "\n"

    # Network device
    str_builder += "# Network Device\n"
    str_builder += "transport_layer={}\n".format(network_property_dictionary["transport_layer"])
    
    if routing_scheme == "ksp":
        str_builder += "network_device=source_routing_switch\n"
        str_builder += "network_device_routing=k_shortest_paths\n"
        str_builder += "k_for_k_shortest_paths={}\n".format(2)
    elif routing_scheme == "ecmp":
        str_builder += "network_device=ecmp_switch\n"
        str_builder += "network_device_routing=ecmp\n"
    else:
        print("Unsupported routing")
        assert(False)

    str_builder += "link_delay_filename={}\n".format(link_delay_filename)
    str_builder += "network_device_intermediary=identity\n"
    str_builder += "\n"

    # Link & output port
    str_builder += "# Link & output port\n"
    if network_property_dictionary["transport_layer"] == "infiniband":
        str_builder += "output_port=simple_infiniband_output_port\n"
    else:
        str_builder += "output_port=ecn_tail_drop\n"
    str_builder += "output_port_max_queue_size_bytes={}\n".format(network_property_dictionary["output_port_queue_size_bytes"])
    str_builder += "output_port_ecn_threshold_k_bytes={}\n".format(network_property_dictionary["output_port_ecn_threshold_k_bytes"])
    str_builder += "link=perfect_simple_different_delay_bandwidth\n"
    str_builder += "link_delay_ns={}\n".format(network_property_dictionary["network_link_delay_ns"])
    str_builder += "server_link_delay_ns={}\n".format(network_property_dictionary["server_link_delay_ns"])
    str_builder += "link_bandwidth_bit_per_ns={}\n".format(network_property_dictionary["network_link_bw_gbps"])
    str_builder += "injection_link_bandwidth_bit_per_ns={}\n".format(network_property_dictionary["injection_link_bw_gbps"])
    str_builder += "\n"

    #Traffic
    str_builder += "# Traffic\n"
    str_builder += "traffic=traffic_arrivals_file_auto\n"
    str_builder += "traffic_arrivals_filename={}\n".format(traffic_arrivals_filename)
    return str_builder 