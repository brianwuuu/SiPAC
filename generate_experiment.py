"""
File generating script for SiPAC simulations.

Usage:
    1) Run "python3 generate_experiments.py" with the following input argument:
        --exp_id=
            1. primitive collective experiment
            2. allreduce collective experiment
            3. hybrid parallel collective experiment
    e.g. "python3 generate_experiments.py --exp_id=1"
"""

import os, sys, getopt
import math
import utilities
from network_topology import *
from traffic.synthetic_traffic import *


####################################################################################################
# Simulation Parameters 
####################################################################################################

# Directory Setup
print("[Setup] Setup directory")
BASE_DIRECTORY = os.getcwd()
WORKING_DIRECTORY = BASE_DIRECTORY + "/temp"
INPUT_DIRECTORY = BASE_DIRECTORY + "/input_parameters"
EXECUTION_DIRECTORY = BASE_DIRECTORY + "/execution"
if not os.path.isdir(WORKING_DIRECTORY): os.mkdir(WORKING_DIRECTORY)
if not os.path.isdir(INPUT_DIRECTORY): os.mkdir(INPUT_DIRECTORY)
if not os.path.isdir(EXECUTION_DIRECTORY): os.mkdir(EXECUTION_DIRECTORY)

# read parameters from file
print("[Setup] Read inputs")
parameter_file_name = INPUT_DIRECTORY + "/setup.json"
input_parameters = utilities.parseJSON(parameter_file_name)

property_dictionary = {"num_vcs": int(input_parameters["NUM_VCS"]),
                        "input_queue_size_bytes": int(input_parameters["INPUT_QUEUE_BUFFER_SIZE_BYTES"]),
                        "output_port_queue_size_bytes": int(input_parameters["OUTPUT_QUEUE_BUFFER_SIZE_BYTES"]),
                        "output_port_ecn_threshold_k_bytes": int(1/5 * int(input_parameters["OUTPUT_QUEUE_BUFFER_SIZE_BYTES"])),
                        "enable_log_port_queue_state": input_parameters["enable_log_port_queue_state"],
                        "enable_log_flow_throughput": input_parameters["enable_log_flow_throughput"],
                        "enable_log_sending_throughput": input_parameters["enable_log_sending_throughput"],
                        "network_link_delay_ns": int(input_parameters["NETWORK_LINK_LATENCY_NS"]),
                        "server_link_delay_ns": int(input_parameters["SERVER_LINK_LATENCY_NS"]),
                        "injection_link_bw_gbps": int(input_parameters["INJECTION_LINK_BW_GBPS"]),
                        "transport_layer": input_parameters["TRANSPORT_LAYER"],
                        "congestion_threshold_bytes": int(input_parameters["CONGESTION_THRESHOLD_BYTES"]),
                        "stateful_load_balancing": False,
                        "enable_packet_spraying": False,
                        }

# Derive the hardware/system parameter name that includes information on:
# 1) Transport layer protocol and input/output port buffer size
# 2) Network link bandwidth, network link latency
# 3) Routing scheme
def deriveNetworkHardwareParameterName(routing_scheme, network_link_bandwidth_gbps):
    protocol_name = ""
    hardware_name = ""
    if input_parameters["TRANSPORT_LAYER"] == "simple_dctcp":
        protocol_name = "simple_dctcp"
        hardware_name += "oq{}t{}kb_".format(int(property_dictionary["output_port_queue_size_bytes"] / 1000), int(property_dictionary["congestion_threshold_bytes"] / 1000))
    elif input_parameters["TRANSPORT_LAYER"] == "infiniband":
        protocol_name = "ibvc{}".format(int(input_parameters["NUM_VCS"]))
        hardware_name += "oq{}iq{}kb_".format(int(property_dictionary["output_port_queue_size_bytes"] / 1000), int(property_dictionary["input_queue_size_bytes"] / 1000))
    else:
        raise Exception("Unrecognized congestion control protocol: {}".format(input_parameters["TRANSPORT_LAYER"]))
    property_dictionary["network_link_bw_gbps"] = network_link_bandwidth_gbps
    hardware_name += "{}g_{}ns_{}".format(network_link_bandwidth_gbps, int(input_parameters["NETWORK_LINK_LATENCY_NS"]), routing_scheme)
    return protocol_name + "_" + hardware_name

# Given the topology, traffic arrival events, traffic type, routing scheme, message (flow) size, and network bandwidth,
# generate the simulation parameter files required to run Netbench.
def createExperimentFiles(topology, traffic_arrival_events, traffic_pattern, routing_scheme, flow_size, network_link_bandwidth_gbps):
    # Set up
    if isinstance(flow_size, float) or isinstance(flow_size, int): flow_size = utilities.extract_byte_string(flow_size)
    # 1) Traffic Directory
    traffic_directory = "{}/{}".format(WORKING_DIRECTORY,traffic_pattern)
    if not os.path.isdir(traffic_directory): os.mkdir(traffic_directory)
    # 2) Network Topology Directory
    topology_directory = traffic_directory + "/" + topology.getName()
    if not os.path.isdir(topology_directory): os.mkdir(topology_directory)
    topology_filename = "{}/initial_topology.topology".format(topology_directory)
    with open(topology_filename, "w+") as f: f.write(topology.generateTopologyFileString())
    routing_path_split_ratio_filename = "{}/initial_wcmp_path_split_weights.txt".format(topology_directory)
    # 4) Flow Size Directory
    flow_size_directory = "{}/{}".format(topology_directory, flow_size)
    if not os.path.isdir(flow_size_directory): os.mkdir(flow_size_directory)
    traffic_flows_arrival_filename = "{}/flow_arrivals.txt".format(flow_size_directory)
    traffic_flows_arrival_string, number_of_flows = topology.generateTrafficEventsString(traffic_arrival_events)
    with open(traffic_flows_arrival_filename, "w+") as f: f.write(traffic_flows_arrival_string)
    # 3) Hardware Parameter Directory
    hardware_parameter_name = deriveNetworkHardwareParameterName(routing_scheme, network_link_bandwidth_gbps)
    hardware_parameter_directory = "{}/{}".format(flow_size_directory, hardware_parameter_name)
    if not os.path.isdir(hardware_parameter_directory): os.mkdir(hardware_parameter_directory)
    link_delay_filename = "{}/link_delay.txt".format(hardware_parameter_directory)
    with open(link_delay_filename, "w+") as f: f.write(topology.generateLinkDelayFileString())
    config_file_string = utilities.write_simulation_configuration_file(hardware_parameter_directory,
                                                                        "",
                                                                        topology_filename, 
                                                                        traffic_flows_arrival_filename, 
                                                                        routing_path_split_ratio_filename,
                                                                        routing_scheme,
                                                                        link_delay_filename,
                                                                        input_parameters["SIMULATION_RUNTIME_NS"],
                                                                        number_of_flows,
                                                                        property_dictionary)
    simulation_config_filename = "{}/simulation_parameters.properties".format(hardware_parameter_directory)
    with open(simulation_config_filename, "w+") as f:
        f.write(config_file_string)
    return simulation_config_filename

# Generate the topologies compared in this work normalized along the per-CU bandwidth
def generateTopology(target_num_nodes, per_cu_bw_gbps, l=1):
    ### Topology-related
    print("[Setup] Generate topologies")
    p = target_num_nodes
    r = math.ceil(float(p) ** (1/(float(l)+1)))
    torus_dim = {16: [4,4], 64: [8,8], 256: [16,16], 512: [32,16], 1024: [32,32]}
    sipac_network = sipac_network_topology.SiPACNetworkTopology(r=r,l=l,link_bw=per_cu_bw_gbps//((l+1)*(r-1)), link_latency=int(input_parameters["NETWORK_LINK_LATENCY_NS"]), num_wavelengths_per_pair=1)
    bcube_network = bcube_network_topology.BcubeNetworkTopology(r=r,l=l,link_bw=per_cu_bw_gbps//(l+1), num_wavelengths_per_pair=1)
    superpod_network = dgx_superpod_network_topology.DGX_Superpod(target_num_gpus=p, link_bw=per_cu_bw_gbps//6) # each gpu is connected to 6 nvswitches with 2 links each = 12 links
    torus_network = nd_torus_network_topology.NDTorusNetworkTopology(torus_dim[target_num_nodes], link_bw=per_cu_bw_gbps//(2*2))
    topology_list = [superpod_network, torus_network, bcube_network, sipac_network]
    return topology_list

# Given a specific topology, generate all-reduce traffic based on different all-reduce algorithms
def generateAllReduceTraffic(topology):
    ### Traffic generators
    print("[Setup] Generate traffic for {}".format(topology.getName()))
    ring_allreduce_traffic = ring_allreduce_traffic_generator.RingAllReduceTrafficGenerator(p=topology.getNumServers(), num_server_per_job=topology.getNumServers())
    mesh_allreduce_traffic = mesh_allreduce_traffic_generator.MeshAllReduceTrafficGenerator(p=topology.getNumServers(), num_server_per_job=topology.getNumServers())
    if topology.getName().startswith("2D"):
        k=int(topology.getNumServers()**(1/2))
        hierarchical_allreduce_traffic = hierarchical_allreduce_traffic_generator.HierarchicalAllReduceTrafficGenerator(p=topology.getNumServers(), k=k, num_server_per_job=topology.getNumServers())
    elif topology.getName().startswith("dgx"):
        k = topology.getNumServers() / 8
        assert(k == int(k))
        hierarchical_allreduce_traffic = hierarchical_allreduce_traffic_generator.HierarchicalAllReduceTrafficGenerator(p=topology.getNumServers(), k=int(k), num_server_per_job=topology.getNumServers())
    elif topology.getName().startswith("sipac") or topology.getName().startswith("Bcube"):
        k = (topology.getR()) ** (topology.getL())
        hierarchical_allreduce_traffic = hierarchical_allreduce_traffic_generator.HierarchicalAllReduceTrafficGenerator(p=topology.getNumServers(), k=int(k), num_server_per_job=topology.getNumServers())
    if topology.getName().startswith("sipac") or topology.getName().startswith("Bcube"):
        sipco_allreduce_traffic = sipco_allreduce_traffic_generator.SiPCOAllReduceTrafficGenerator(r=topology.getR(), l=topology.getL(), num_server_per_job=topology.getNumServers())

    traffic_generators = {
                        "ring_allreduce": ring_allreduce_traffic,
                        "hierarchical_allreduce": hierarchical_allreduce_traffic,
                        "sipco_allreduce": sipco_allreduce_traffic,
                        "mesh_allreduce": mesh_allreduce_traffic,
                        }
    return traffic_generators

# Given a specific topology, generate primitive collectives (one-to-all, all-to-one, all-to-all).
def generatePrimitiveTraffic(topology):
    primitive_alltoall_traffic = primitive_alltoall_traffic_generator.PrimitiveAllToAllTrafficGenerator(p=topology.getNumServers())
    primitive_onetoall_traffic = primitive_onetoall_traffic_generator.PrimitiveOneToAllTrafficGenerator(p=topology.getNumServers(), src_node=0)
    primitive_alltoone_traffic = primitive_alltoone_traffic_generator.PrimitiveAllToOneTrafficGenerator(p=topology.getNumServers(), dst_node=0)
    traffic_generators = {
                        "primitive_onetoall": primitive_onetoall_traffic,
                        "primitive_alltoone": primitive_alltoone_traffic,
                        "primitive_alltoall": primitive_alltoall_traffic,
                        }
    return traffic_generators

# Generate the required files for different types of experiments
def generateExperimentFiles(num_nodes_list, per_cu_bw_gbps_list, flow_size_bytes, traffic_type):
    simulation_config_filenames = []
    for num_nodes in num_nodes_list:
        l = 2 if num_nodes == 512 else 1
        for per_cu_bw_gbps in per_cu_bw_gbps_list:
            topology_list = generateTopology(num_nodes, per_cu_bw_gbps, l=l)
            for topology in topology_list:
                topology.wireNetwork()
                if traffic_type == "primitive": traffic_generators = generatePrimitiveTraffic(topology)
                elif traffic_type == "allreduce": traffic_generators = generateAllReduceTraffic(topology)
                else: raise Exception("Unknown traffic type.")
                for traffic_name, traffic_generator in traffic_generators.items():
                    for flow_size in flow_size_bytes:
                        traffic_arrival_events = traffic_generator.plan_arrivals(flow_size)
                        simulation_config_filename = createExperimentFiles(topology=topology, 
                                                                        traffic_arrival_events=traffic_arrival_events, 
                                                                        traffic_pattern=traffic_name, 
                                                                        routing_scheme="ecmp", 
                                                                        flow_size=flow_size,
                                                                        network_link_bandwidth_gbps=topology.getLinkBW())
                        simulation_config_filenames.append(simulation_config_filename)
    return simulation_config_filenames

# Experiment parameter setup for all-reduce experiments.
def generateAllReduceExperiment():
    print("[Setup] Generate allreduce experiment files")
    flow_size_bytes = [1e2,1e3,1e4,1e5,1e6,1e7,1e8,1e9]
    num_nodes_list = [16, 64, 256, 512, 1024]
    per_cu_bw_gbps_list = [2048]
    simulation_config_filenames = generateExperimentFiles(num_nodes_list, per_cu_bw_gbps_list, flow_size_bytes, "allreduce")
    return simulation_config_filenames

# Experiment parameter setup for primitive collective experiments.
def generatePrimitiveCollectiveExperiment():
    print("[Setup] Generate primitive experiment files")
    flow_size_bytes = [1e2,1e3,1e4,1e5,1e6,1e7,1e8]
    num_nodes_list = [512]
    per_cu_bw_gbps_list = [2048]
    simulation_config_filenames = generateExperimentFiles(num_nodes_list, per_cu_bw_gbps_list, flow_size_bytes, "primitive")
    return simulation_config_filenames

# Experiment parameter setup for hybrid parallel collective experiments.
def generateHybridParallelExperiment():
    ### Variable Parameters
    print("[Setup] Generate hybrid parallel experiment files")
    num_nodes_list = [64] # 16 , 64, 128, 256, 512, 1024
    per_cu_bw_gbps_list = [128, 256, 512, 1024, 2048, 4096] # 25 GBps/link * 2 links/nvswitch * 6 nvswitches * 8 Gbps/GBps = 2400 Gbps --> A100 system per-GPU bw
    num_mp_nodes = [16] # try 64
    torus_dim = {16: [4,4], 64: [8,8], 256: [16,16], 512: [32,16], 1024: [32,32]}
    # Need to setup experiment for this
    model_info = dict({ "intra_group_comm_type":"ALLTOALL", "intra_group_algo_type":"mesh", 
                        "inter_group_comm_type":"ALLREDUCE", "inter_group_algo_type":"sipco",
                        "intra_group_message_size":100e6,
                        "inter_group_message_size":100e6})
    
    intra_topo_to_algo_map = {"dgx_superpod_{}nodes".format(num_nodes): "mesh", 
                                  "2D_torus_{}_{}_{}nodes".format(torus_dim[num_nodes][0],torus_dim[num_nodes][1], num_nodes): "mesh", 
                                  "Bcube_{}r_{}l".format(r,l): "mesh",
                                  "sipac_{}r_{}l".format(r,l): "sipco"}
    inter_topo_to_algo_map = {"dgx_superpod_{}nodes".format(num_nodes): "ring", 
                                  "2D_torus_{}_{}_{}nodes".format(torus_dim[num_nodes][0],torus_dim[num_nodes][1], num_nodes): "ring", 
                                  "Bcube_{}r_{}l".format(r,l): "ring",
                                  "sipac_{}r_{}l".format(r,l): "sipco"}
    ### Simulation Setup
    simulation_config_filenames = []
    for num_nodes in num_nodes_list:
        l = 2 if num_nodes == 512 or num_nodes == 64 else 1
        r = math.ceil(float(num_nodes) ** (1/(float(l)+1)))
        for per_cu_bw_gbps in per_cu_bw_gbps_list:
            topology_list = generateTopology(num_nodes, per_cu_bw_gbps, l=l)
            for topology in topology_list:
                topology.wireNetwork()
                model_info["intra_group_algo_type"] = intra_topo_to_algo_map[topology.getName()]
                model_info["inter_group_algo_type"] = inter_topo_to_algo_map[topology.getName()]
                if topology.getName().startswith("sipac") or topology.getName().startswith("Bcube"):
                    model_info["r"] = topology.getR()
                    model_info["l"] = topology.getL()
                for num_mp_node in num_mp_nodes:
                    hybrid_parallel_traffic = hybrid_parallel_traffic_generator.HybridParallelTrafficGenerator(p=topology.getNumServers(), num_mp_nodes=num_mp_node, model_info=model_info)
                    traffic_arrival_events = hybrid_parallel_traffic.plan_arrivals(0)
                    simulation_config_filename = createExperimentFiles(
                        topology=topology, 
                        traffic_arrival_events=traffic_arrival_events, 
                        traffic_pattern="hybrid_parallel", 
                        routing_scheme="ecmp", 
                        flow_size="mp{}_{}_alltoall_{}_{}_allreduce_{}".format(
                            num_mp_node,
                            model_info["intra_group_algo_type"],
                            utilities.extract_byte_string(model_info["intra_group_message_size"]),
                            model_info["inter_group_algo_type"],
                            utilities.extract_byte_string(model_info["inter_group_message_size"])),
                        network_link_bandwidth_gbps=topology.getLinkBW())
                    simulation_config_filenames.append(simulation_config_filename)
    return simulation_config_filenames

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:],"he:",["exp_id="])
    except getopt.GetoptError:
        print('python3 generate_experiment.py -e <experiment_number>')
        sys.exit(2)
    exp_id = 1
    for opt, arg in opts:
        if opt == '-h':
            print('python3 generate_experiment.py -exp_id <experiment_number>')
            sys.exit()
        elif opt in ("-e", "--exp_id"):
            exp_id = int(arg)
    exp_id_map = {1: "primitive", 2: "allreduce", 3: "hybrid"}
    simulations_config_filenames = []
    if exp_id == 1:
        simulations_config_filenames = generatePrimitiveCollectiveExperiment()
    elif exp_id == 2:
        simulations_config_filenames = generateAllReduceExperiment()
    elif exp_id == 3:
        simulations_config_filenames = generateHybridParallelExperiment()
    else:
        print("Invalid Experiment Number")
    if simulations_config_filenames: utilities.generateBashScript(EXECUTION_DIRECTORY, simulations_config_filenames, exp_id_map[exp_id])