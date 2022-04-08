"""
Analysis script for SiPAC simulations.

Usage:
    1) Run "python3 analysis.py -e <experiment> -c <collective_type>" with the following input argument:
        -e --exp_type=
            1. 'synthetic' traffic experiment
            2. 'message_size' experiment
            3. 'topology_size' experiment
            4. 'hybrid_parallel' experiment
        -c --collective_type=
            1. 'allreduce'
            2. 'primitive'
            3. 'hybrid_parallel'
    e.g. "python3 generate_experiments.py --exp_type=message_size --collective_type=allreduce"
"""

import sys, os, getopt
import pprint, math
import utilities as utils
sys.path.append('../')
from collections import defaultdict
from network_topology import *
from traffic.synthetic_traffic import *

####################################################################################################
# Analysis Parameters 
####################################################################################################

# DIRECTORY SETUP
BASE_DIRECTORY = os.getcwd() + "/../"
ANALYSIS_DIRECTORY = BASE_DIRECTORY + "/analysis/"
ANALYSIS_OUTPUT_DIRECTORY = BASE_DIRECTORY + "/results/"
RESULT_DIRECTORY = BASE_DIRECTORY + "/temp/"
INPUT_DIRECTORY = BASE_DIRECTORY + "/input_parameters/"

# read parameters from file
parameter_file_name = INPUT_DIRECTORY + "/setup.json"
input_parameters = utils.parseJSON(parameter_file_name)

# Derive the hardware/system parameter name that includes information on:
# 1) Transport layer protocol and input/output port buffer size
# 2) Network link bandwidth, network link latency
# 3) Routing scheme
def deriveNetworkHardwareParameterName(routing_scheme, network_link_bandwidth_gbps):
    protocol_name = ""
    hardware_name = ""
    if input_parameters["TRANSPORT_LAYER"] == "simple_dctcp":
        protocol_name = "simple_dctcp"
        hardware_name += "oq{}t{}kb_".format(int(int(input_parameters["OUTPUT_QUEUE_BUFFER_SIZE_BYTES"]) / 1000), int(int(input_parameters["CONGESTION_THRESHOLD_BYTES"]) / 1000))
    elif input_parameters["TRANSPORT_LAYER"] == "infiniband":
        protocol_name = "ibvc{}".format(int(input_parameters["NUM_VCS"]))
        hardware_name += "oq{}iq{}kb_".format(int(int(input_parameters["OUTPUT_QUEUE_BUFFER_SIZE_BYTES"]) / 1000), int(int(input_parameters["CONGESTION_THRESHOLD_BYTES"]) / 1000))
    else:
        raise Exception("Unrecognized congestion control protocol: {}".format(input_parameters["TRANSPORT_LAYER"]))
    hardware_name += "{}g_{}ns_{}".format(network_link_bandwidth_gbps, int(input_parameters["NETWORK_LINK_LATENCY_NS"]), routing_scheme)
    return protocol_name + "_" + hardware_name

# Generate the topologies compared in this work normalized along the per-CU bandwidth
def generateTopology(target_num_nodes, per_cu_bw_gbps, l=1):
    print("[Setup] Generate topologies")
    p = target_num_nodes
    r = math.ceil(float(p) ** (1/(float(l)+1)))
    torus_dim = {16: [4,4], 64: [8,8], 256: [16,16], 512: [32,16], 1024: [32,32]}
    sipac_network_network = sipac_network_topology.SiPACNetworkTopology(r=r,l=l,link_bw=per_cu_bw_gbps//((l+1)*(r-1)), num_wavelengths_per_pair=1)
    bcube_network = bcube_network_topology.BcubeNetworkTopology(r=r,l=l,link_bw=per_cu_bw_gbps//(l+1), num_wavelengths_per_pair=1)
    superpod_network = dgx_superpod_network_topology.DGX_Superpod(target_num_gpus=p, link_bw=per_cu_bw_gbps//6) # each gpu is connected to 6 nvswitches with 2 links each = 12 links
    torus_network = nd_torus_network_topology.NDTorusNetworkTopology(torus_dim[target_num_nodes], link_bw=per_cu_bw_gbps//(2*2))
    topology_list = [superpod_network, torus_network, bcube_network, sipac_network_network]
    return topology_list

# Generate the traffic heatmaps compared in this work for a given topology size of 64 endhosts.
def generateTrafficHeatMap(collective_type):
    model_info = dict({ "intra_group_comm_type":"ALLTOALL", "intra_group_algo_type":"primitive", 
                        "inter_group_comm_type":"ALLREDUCE", "inter_group_algo_type":"bcast",
                        "intra_group_message_size":100e6,
                        "inter_group_message_size":100e6,
                        "r": 8, 
                        "l": 1})
    ring_allreduce_traffic = ring_allreduce_traffic_generator.RingAllReduceTrafficGenerator(p=64, num_server_per_job=64)
    hierarchical_allreduce_traffic = hierarchical_allreduce_traffic_generator.HierarchicalAllReduceTrafficGenerator(p=64, k=8, num_server_per_job=64)
    sipco_allreduce_traffic = sipco_allreduce_traffic_generator.SiPCOAllReduceTrafficGenerator(r=8, l=1, num_server_per_job=64)
    hybrid_parallel_traffic = hybrid_parallel_traffic_generator.HybridParallelTrafficGenerator(p=64, num_mp_nodes=8, model_info=model_info)
    traffics = {
                "ring_allreduce": ring_allreduce_traffic,
                "hierarchical_allreduce": hierarchical_allreduce_traffic,
                "sipco_allreduce_traffic": sipco_allreduce_traffic,
                "hybrid": hybrid_parallel_traffic,
                }
    for name, traffic in traffics.items():
        events = traffic.plan_arrivals(0)
        tm = traffic.generateProbabilityMatrix(events, 64)
        file_name = RESULT_DIRECTORY + "{}.png".format(name)
        traffic.drawHeatmap(tm, file_name)
        
################################################################################################################
################################################################################################################

# Analyze the performance of allreduce or primitive collective on various topology-collective combinations
def analyzeSyntheticTraffic(collective_type):
    if collective_type == "allreduce":
        traffic_names = ["ring_allreduce", "mesh_allreduce", "hierarchical_allreduce", "SiPCO_allreduce"]
        traffic_name_labels = ["Ring", "Mesh", "H-Ring", "SiPCO"]
    elif collective_type == "primitive":
        traffic_names = ["primitive_onetoall", "primitive_alltoone", "primitive_alltoall"]
        traffic_name_labels = ["One-to-all", "All-to-one", "All-to-all"]
    routing_scheme = "ecmp"
    num_nodes = 512
    message_size = 1e6
    message_size_str = utils.extract_byte_string(message_size)
    per_gpu_bw = 2048
    topology_list = generateTopology(num_nodes, per_gpu_bw, l=2 if num_nodes == 512 else 1)
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for topology in topology_list:
            hardware_param = deriveNetworkHardwareParameterName(routing_scheme, topology.getLinkBW())
            file_dir = "{}{}/{}/{}/{}/".format(RESULT_DIRECTORY,traffic_name,topology.getName(), message_size_str, hardware_param)
            if os.path.isdir(file_dir):
                flow_completion_file = file_dir + "/flow_completion.csv.log"
                job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                job_stats[topology.getTopologyName()].append(job_completion_time)
            else:
                print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    x_ = {"label": "Traffic", "data": traffic_name_labels}
    y_ = {"label": "Job Completion Time (ns)", "data": job_stats}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "primitive{}p_{}_{}gbps_jct.png".format(num_nodes, message_size_str, per_gpu_bw)
    utils.plotMultiColBarChart(x_, y_, path="")

# Analyze the performance of different topology-collective combinations across varying message sizes
def analyzeMessageSize(collective_type):
    if collective_type == "allreduce": 
        traffic_names = ["hierarchical_allreduce","mesh_allreduce", "sipco_allreduce"]
    elif collective_type == "primitive":
        traffic_names = ["primitive_alltoall"] # "primitive_onetoall", "primitive_alltoone", "primitive_alltoall"
    message_sizes = [1e2,1e3,1e4,1e5,1e6,1e7,1e8,1e9]
    routing_scheme = "ecmp"
    num_nodes = 1024
    per_cu_bw_gbps = 2048
    l = 2 if num_nodes == 512 else 1
    topology_list = generateTopology(num_nodes, per_cu_bw_gbps, l=l)
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for topology in topology_list:
            if traffic_name.startswith("sipco") and topology.getName().startswith("Bcube"): continue
            if traffic_name.startswith("mesh") and topology.getName().startswith("Bcube"): continue
            hardware_param = deriveNetworkHardwareParameterName(routing_scheme, topology.getLinkBW())
            for message_size in message_sizes:
                message_size_str = utils.extract_byte_string(message_size)
                file_dir = "{}{}/{}/{}/{}/".format(RESULT_DIRECTORY,traffic_name,topology.getName(), message_size_str, hardware_param)
                flow_completion_file = file_dir + "flow_completion.csv.log"
                if os.path.isfile(flow_completion_file):
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    combo_name = traffic_name[0].upper() + "_" +  topology.getTopologyName()
                    job_stats[combo_name].append(job_completion_time)
                else:
                    print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    x_ = {"label": "Message Size (Bytes)", "data": message_sizes, "log":10}
    y_ = {"label": "Job Completion Time (ns)".format(r'$\mu$'), "data": job_stats, "log": None}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "{}p{}gbps_msg.png".format(num_nodes, per_cu_bw_gbps)
    # utils.plotMultiLineChart(x_, y_, path=plot_path)
    utils.plotMultiLineChart(x_, y_, path="")

# Analyze the performance of different topology-collective combinations across varying topology sizes
def analyzeTopologySize(collective_type):
    assert(collective_type == "allreduce")
    traffic_names = ["ring_allreduce","hierarchical_allreduce", "mesh_allreduce", "sipco_allreduce"] # "mesh_allreduce",
    traffic_name_labels = ["Ring", "H-Ring", "Mesh",  "SiPCO"]
    per_cu_bw_gbps = 2048
    message_size = 1e6
    message_size_str = utils.extract_byte_string(message_size)
    num_nodes = [16, 64, 256, 512, 1024]
    routing_scheme = "ecmp"
    job_stats = {}
    for num_node in num_nodes:
        topology_list = generateTopology(num_node, per_cu_bw_gbps, l=1 if num_node != 512 else 2)
        job_stats[num_node] = defaultdict(list) 
        for topology in topology_list:
            for traffic_name in traffic_names:
                hardware_param = deriveNetworkHardwareParameterName(routing_scheme, topology.getLinkBW())
                file_dir = "{}{}/{}/{}/{}".format(RESULT_DIRECTORY,traffic_name,topology.getName(),message_size_str,hardware_param)
                if os.path.isdir(file_dir):
                    flow_completion_file = file_dir + "/flow_completion.csv.log"
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    if num_node == 16 and topology.getName().startswith("sipac") and traffic_name == "sipco_allreduce": 
                        job_completion_time -= 1000000 # reduce tcp resend time that shouldn't be accounted for
                    combo_name = topology.getTopologyName()
                    job_stats[num_node][combo_name].append(job_completion_time)
                else:
                    print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    x_ = {"label": "Number of CUs", "data": traffic_name_labels, "log": None}
    y_ = {"label": "Job Completion Time (ns)".format(traffic_name), "data": job_stats, "log": 10}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "{}_topology_size_subplots1.png".format(message_size_str)
    utils.plotMultiColBarChartSubplot(x_, y_, path="")
    # utils.plotMultiColBarChartSubplot(x_, y_, path=plot_path)

# Analyze the performance of hybrid parallel collectives across varying network bandwidths on different topologies
def analyzeHybridParallel(collective_type):
    assert(collective_type == "hybrid")
    traffic_names = ["hybrid_parallel"]
    per_cu_bw_gbps_list = [128, 256, 512, 1024, 2048, 4096]
    model_info = dict({ "intra_group_comm_type":"ALLTOALL", "intra_group_algo_type":"ring", 
                        "inter_group_comm_type":"ALLREDUCE", "inter_group_algo_type":"sipco",
                        "intra_group_message_size":100e6,
                        "inter_group_message_size":100e6})
    num_nodes = 64
    num_mp_node = 8
    l = 2 if num_nodes == 512 else 1
    r = math.ceil(float(num_nodes) ** (1/(float(l)+1)))
    torus_dim = {16: [4,4], 64: [8,8], 256: [16,16], 512: [32,16], 1024: [32,32]}
    intra_topo_to_algo_map = {"dgx_superpod_{}nodes".format(num_nodes): "mesh", 
                                "2D_torus_{}_{}_{}nodes".format(torus_dim[num_nodes][0],torus_dim[num_nodes][1], num_nodes): "mesh", 
                                "Bcube_{}r_{}l".format(r,l): "mesh",
                                "sipac_{}r_{}l".format(r,l): "sipco"}
    
    inter_topo_to_algo_map = {"dgx_superpod_{}nodes".format(num_nodes): "ring", 
                                "2D_torus_{}_{}_{}nodes".format(torus_dim[num_nodes][0],torus_dim[num_nodes][1], num_nodes): "ring", 
                                "Bcube_{}r_{}l".format(r,l): "ring",
                                "sipac_{}r_{}l".format(r,l): "sipco"}
    routing_scheme = "ecmp"
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for per_cu_bw_gbps in per_cu_bw_gbps_list:
            topology_list = generateTopology(num_nodes, per_cu_bw_gbps, l=l)
            for topology in topology_list:
                model_info["intra_group_algo_type"] = intra_topo_to_algo_map[topology.getName()]
                model_info["inter_group_algo_type"] = inter_topo_to_algo_map[topology.getName()]
                message_size_str = "mp{}_{}_alltoall_{}_{}_allreduce_{}".format(
                    num_mp_node,
                    model_info["intra_group_algo_type"],
                    utils.extract_byte_string(model_info["intra_group_message_size"]),
                    model_info["inter_group_algo_type"],
                    utils.extract_byte_string(model_info["inter_group_message_size"]))
                hardware_param = deriveNetworkHardwareParameterName(routing_scheme, topology.getLinkBW())
                file_dir = "{}{}/{}/{}/{}/".format(RESULT_DIRECTORY,traffic_name,topology.getName(), message_size_str, hardware_param)
                if os.path.isdir(file_dir):
                    flow_completion_file = file_dir + "/flow_completion.csv.log"
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    job_stats[topology.getTopologyName()].append(job_completion_time)
                else:
                    print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    x_ = {"label": "Per CU Bandwidth (Gbps)", "data": per_cu_bw_gbps_list, "log": 2}
    y_ = {"label": "Job Completion Time (ns)", "data": job_stats, "log": 10}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "{}p{}mp_{}_alltoall{}_{}_allreduce{}_bw.png".format(num_nodes, num_mp_node,
                    model_info["intra_group_algo_type"],
                    utils.extract_byte_string(model_info["intra_group_message_size"]), 
                    model_info["inter_group_algo_type"],
                    utils.extract_byte_string(model_info["inter_group_message_size"]))
    # utils.plotMultiLineChart(x_, y_, path=plot_path)
    utils.plotMultiLineChart(x_, y_, path="")

def main():
    print("[ANALYSIS] Starting analysis ...")
    try:
        opts, args = getopt.getopt(sys.argv[1:],"he:c:",["exp=", "collective="])
    except getopt.GetoptError:
        print('python3 analysis.py -e <experiment> -c <collective_type>')
        sys.exit(2)
    exp_type = ""
    collective_type = ""
    for opt, arg in opts:
        if opt == '-h':
            print('python3 analysis.py -e <experiment> -c <collective_type>')
            sys.exit()
        elif opt in ("-e", "--exp"):
            exp_type = arg
        elif opt in ("-c", "--collective"):
            collective_type = arg
    if exp_type == "basic":
        analyzeSyntheticTraffic(collective_type)
    elif exp_type == "message_size":
        analyzeMessageSize(collective_type)
    elif exp_type == "topology_size":
        analyzeTopologySize(collective_type)
    elif exp_type == "hybrid_parallel":
        analyzeHybridParallel(collective_type)
    elif exp_type == "heatmap":
        generateTrafficHeatMap(collective_type)

if __name__ == '__main__':
    main()