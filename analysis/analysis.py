import sys, os
import pprint, math
import utilities as utils
sys.path.append('../')
from collections import defaultdict
from network_topology import *
from traffic.synthetic_traffic import *

################################################################################################################
################################################################################################################
# DIRECTORY SETUP
BASE_DIRECTORY = "/Users/bwu/src/dragonfly_ring_allreduce"
ANALYSIS_DIRECTORY = BASE_DIRECTORY + "/analysis/"
ANALYSIS_OUTPUT_DIRECTORY = BASE_DIRECTORY + "/results/"
RESULT_DIRECTORY = BASE_DIRECTORY + "/temp/"
INPUT_DIRECTORY = BASE_DIRECTORY + "/input_parameters/"
################################################################################################################
################################################################################################################
# PARAMETER SETUP
parameter_file_name = INPUT_DIRECTORY + "/setup.json"
input_parameters = utils.parseJSON(parameter_file_name)
# SIMULATION & NETWORK
SIMULATION_RUNTIME_NS = int(input_parameters["SIMULATION_RUNTIME_NS"])
TRANSPORT_LAYER = input_parameters["TRANSPORT_LAYER"]
# HARDWARE
INPUT_QUEUE_BUFFER_SIZE_BYTES = int(input_parameters["INPUT_QUEUE_BUFFER_SIZE_BYTES"])
OUTPUT_QUEUE_BUFFER_SIZE_BYTES = int(input_parameters["OUTPUT_QUEUE_BUFFER_SIZE_BYTES"])
CONGESTION_THRESHOLD_BYTES = int(input_parameters["CONGESTION_THRESHOLD_BYTES"])
NETWORK_LINK_LATENCY_NS = int(input_parameters["NETWORK_LINK_LATENCY_NS"])
SERVER_LINK_LATENCY_NS = int(input_parameters["SERVER_LINK_LATENCY_NS"])
NUM_VCS = int(input_parameters["NUM_VCS"]) # 2

property_dictionary = {"num_vcs": NUM_VCS,
                        "input_queue_size_bytes": INPUT_QUEUE_BUFFER_SIZE_BYTES,
                        "output_port_queue_size_bytes": OUTPUT_QUEUE_BUFFER_SIZE_BYTES,
                        "stateful_load_balancing": False,
                        "enable_packet_spraying": True,
                        "enable_log_port_queue_state": input_parameters["enable_log_port_queue_state"],
                        "enable_log_flow_throughput": input_parameters["enable_log_flow_throughput"],
                        "enable_log_sending_throughput": input_parameters["enable_log_sending_throughput"],
                        "network_link_delay_ns": int(input_parameters["NETWORK_LINK_LATENCY_NS"]),
                        "server_link_delay_ns": int(input_parameters["SERVER_LINK_LATENCY_NS"]),
                        "ecmp_fraction": 1.0,
                        "transport_layer": TRANSPORT_LAYER,
                        "congestion_threshold_bytes": int(input_parameters["CONGESTION_THRESHOLD_BYTES"]), # For DCTCP
                        }

def deriveNetworkHardwareParameterName(topology, traffic_pattern, routing_scheme, network_link_bandwidth_gbps):
    protocol_name = ""
    hardware_name = ""
    if TRANSPORT_LAYER == "simple_dctcp":
        protocol_name = "simple_dctcp"
        hardware_name += "oq{}t{}kb_".format(int(property_dictionary["output_port_queue_size_bytes"] / 1000), int(property_dictionary["congestion_threshold_bytes"] / 1000))
    elif TRANSPORT_LAYER == "infiniband":
        protocol_name = "ibvc{}".format(NUM_VCS)
        hardware_name += "oq{}iq{}kb_".format(int(property_dictionary["output_port_queue_size_bytes"] / 1000), int(property_dictionary["input_queue_size_bytes"] / 1000))
    else:
        raise Exception("Unrecognized congestion control protocol: {}".format(TRANSPORT_LAYER))
    link_latency = int(input_parameters["NETWORK_LINK_LATENCY_NS"])
    # if topology.getName().startswith("photonic_Bcube"):
    #     if traffic_pattern.startswith("bcast"):
    #         network_link_bandwidth_gbps = network_link_bandwidth_gbps / float((topology.getNumGPUsPerGroup()))
    hardware_name += "{}g_{}ns_{}".format(network_link_bandwidth_gbps, link_latency, routing_scheme)
    return protocol_name + "_" + hardware_name


def generateTopology(target_num_nodes, per_gpu_bw_gbps, l=1):
    ### Topology-related
    print("[Setup] Generate topologies")
    torus_dim = {16: [4,4], 64: [8,8], 256: [16,16], 512: [32,16], 1024: [32,32]}
    p = target_num_nodes
    g = a = int(p ** (1/2))
    r = math.ceil(float(p) ** (1/(float(l)+1)))
    photonic_bcube_network = sipac_network_topology.SiPACNetworkTopology(r=r,l=l,nvlink_bw=per_gpu_bw_gbps, num_wavelengths_per_pair=1)
    # photonic_bcube_network = photonic_bcube_topology.PhotonicBcube(r=r,l=l,nvlink_bw=per_gpu_bw_gbps//6, num_wavelengths_per_pair=1) 
    # photonic_bcube_orig_network = photonic_bcube_orig_topology.PhotonicBcubeOrig(r=r,l=l,link_bw=per_gpu_bw_gbps//((l+1)*(r)), num_wavelengths_per_pair=1)
    photonic_bcube_orig_network = sipac_network_topology.PhotonicBcubeOrig(r=r,l=l,link_bw=per_gpu_bw_gbps//((l+1)*(r-1)), num_wavelengths_per_pair=1)
    bcube_network = bcube_network_topology.BcubeNetworkTopology(r=r,l=l,link_bw=per_gpu_bw_gbps//(l+1), num_wavelengths_per_pair=1)
    # bcube_network = bcube_network_topology.BcubeNetworkTopology(r=r,l=l,link_bw=per_gpu_bw_gbps, num_wavelengths_per_pair=1)
    superpod_network = dgx_superpod_network_topology.DGX_Superpod(target_num_gpus=p, link_bw=per_gpu_bw_gbps//6) # correct one
    # superpod_network = dgx_superpod_network_topology.DGX_Superpod(target_num_gpus=p, link_bw=per_gpu_bw_gbps//12)
    torus_network = nd_torus_network_topology.NDTorusNetworkTopology(torus_dim[target_num_nodes], link_bw=per_gpu_bw_gbps//(2*2))
    # topology_list = [dragonfly_network, fattree_network, photonic_bcube_network, dgx_network] # dgx_network
    # topology_list = [photonic_bcube_orig_network]
    topology_list = [superpod_network, bcube_network, torus_network, photonic_bcube_orig_network] # bcube_network, photonic_bcube_orig_network
    return topology_list
################################################################################################################
################################################################################################################

def generateTrafficHeatMap():
    model_info = dict({ "intra_group_comm_type":"ALLTOALL", "intra_group_algo_type":"primitive", 
                        "inter_group_comm_type":"ALLREDUCE", "inter_group_algo_type":"bcast",
                        "intra_group_message_size":100e6,
                        "inter_group_message_size":100e6,
                        "r": 4, 
                        "l": 2})
    ring_allreduce_traffic = ring_allreduce_traffic_generator.RingAllReduceTrafficGenerator(p=64, num_server_per_job=64)
    hierarchical_allreduce_traffic = hierarchical_allreduce_traffic_generator.HierarchicalAllReduceTrafficGenerator(p=64, k=8, num_server_per_job=32)
    sipco_allreduce_traffic = sipco_allreduce_traffic_generator.SiPCOAllReduceTrafficGenerator(r=8, l=2, num_server_per_job=64)
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
        file_name = "/Users/bwu/Desktop/{}.png".format(name)
        traffic.drawHeatmap(tm, file_name)

def analyzeSyntheticTraffic():
    # traffic_names = ["ring_allreduce", "mesh_allreduce", "hierarchical_allreduce", "bcast_allreduce"]
    traffic_names = ["primitive_onetoall", "primitive_alltoone", "primitive_alltoall"] # """primitive_alltoall"
    traffic_name_labels = ["One-to-all", "All-to-one", "All-to-all"]
    routing_scheme = "ecmp"
    num_nodes = 512
    message_size = 1e6 # [0.01e6, 0.1e6, 1e6, 10e6, 100e6] #100e6, 1000e6
    message_size_str = utils.extract_byte_string(message_size)
    per_gpu_bw = 2048
    topology_list = generateTopology(num_nodes, per_gpu_bw, l=2 if num_nodes == 512 else 1)
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for topology in topology_list:
            hardware_param = deriveNetworkHardwareParameterName(topology, traffic_name, routing_scheme, topology.getLinkBW())
            file_dir = "{}{}/{}/{}/{}/".format(RESULT_DIRECTORY,traffic_name,topology.getName(), message_size_str, hardware_param)
            if os.path.isdir(file_dir):
                flow_completion_file = file_dir + "/flow_completion.csv.log"
                # job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                job_completion_time = utils.extract_avg_fct_from_file(flow_completion_file)
                job_stats[topology.getTopologyName()].append(job_completion_time)
            else:
                print("[Error] File doesn't exist: ", file_dir)
    # job_stats = utils.normalizeStats(job_stats)
    print(job_stats)
    x_ = {"label": "Traffic", "data": traffic_name_labels}
    y_ = {"label": "Job Completion Time (ns)", "data": job_stats}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "primitive{}p_{}_{}gbps_jct.png".format(num_nodes, message_size_str, per_gpu_bw)
    # utils.plotMultiColBarChartV1(x_, y_, path=plot_path)
    utils.plotMultiColBarChartV1(x_, y_, path="")


def analyzeMessageSize():
    traffic_names = ["hierarchical_allreduce","mesh_allreduce", "bcast_allreduce"] # "ring_allreduce", "hierarchical_allreduce", "mesh_allreduce"
    # traffic_names = ["primitive_alltoall"] # "primitive_onetoall", "primitive_alltoone", "primitive_alltoall"
    message_sizes = [1e2,1e3,1e4,1e5,1e6,1e7,1e8,1e9] #1e2,1e3,1e4,1e5,1e6,1e7,1e8,1e9
    routing_scheme = "ecmp"
    num_nodes = 1024
    per_gpu_bw_gbps = 2048
    l = 2 if num_nodes == 512 else 1
    topology_list = generateTopology(num_nodes, per_gpu_bw_gbps, l=l)
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for topology in topology_list:
            if traffic_name.startswith("bcast") and topology.getName().startswith("Bcube"): continue
            if traffic_name.startswith("mesh") and topology.getName().startswith("Bcube"): continue
            hardware_param = deriveNetworkHardwareParameterName(topology, traffic_name, routing_scheme, topology.getLinkBW())
            for message_size in message_sizes:
                # if traffic_name.startswith("mesh") and topology.getName().startswith("dgx") and message_size == 1e5: 
                #     combo_name = traffic_name[0].upper() + "_" +  topology.getTopologyName()
                #     job_stats[combo_name].append(28512405)
                #     continue
                message_size_str = utils.extract_byte_string(message_size)
                file_dir = "{}{}/{}/{}/{}/".format(RESULT_DIRECTORY,traffic_name,topology.getName(), message_size_str, hardware_param)
                flow_completion_file = file_dir + "flow_completion.csv.log"
                if os.path.isfile(flow_completion_file):
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    # job_completion_time = utils.extract_avg_fct_from_file(flow_completion_file)
                    if traffic_name.startswith("bcast"):
                        combo_name = "S" + "_" +  topology.getTopologyName()
                    else:
                        combo_name = traffic_name[0].upper() + "_" +  topology.getTopologyName()
                    # combo_name = topology.getTopologyName()
                    job_stats[combo_name].append(job_completion_time)
                else:
                    print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    x_ = {"label": "Message Size (Bytes)", "data": message_sizes, "log":10}
    y_ = {"label": "Job Completion Time (ns)".format(r'$\mu$'), "data": job_stats, "log": None}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "{}p{}gbps_msg.png".format(num_nodes, per_gpu_bw_gbps)
    utils.plotMultiLineChart(x_, y_, path=plot_path)
    # utils.plotMultiLineChart(x_, y_, path="")

def analyzeTopologySize():
    traffic_names = ["ring_allreduce","mesh_allreduce", "hierarchical_allreduce", "bcast_allreduce"] # "mesh_allreduce",
    per_gpu_bw_gbps = 2048
    link_bw_list = [per_gpu_bw_gbps//6, per_gpu_bw_gbps//4, per_gpu_bw_gbps//2, per_gpu_bw_gbps//6, per_gpu_bw_gbps//3]
    message_size = 1e6 # [0.01e6, 0.1e6, 1e6, 10e6, 100e6] #100e6, 1000e6
    message_size_str = utils.extract_byte_string(message_size)
    num_nodes = [16 ] # 64, 256, 512, 1024
    routing_scheme = "ecmp"
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for num_node in num_nodes:
            topology_list = generateTopology(num_node, per_gpu_bw_gbps, l=1 if num_node != 512 else 2)
            for topology in topology_list:
                if topology.getName().startswith("Bcube") and traffic_name == "bcast_allreduce": continue
                if topology.getName().startswith("Bcube") and traffic_name == "mesh_allreduce": continue
                hardware_param = deriveNetworkHardwareParameterName(topology, traffic_name, routing_scheme, topology.getLinkBW())
                file_dir = "{}{}/{}/{}/{}".format(RESULT_DIRECTORY,traffic_name,topology.getName(),message_size_str,hardware_param)
                if os.path.isdir(file_dir):
                    flow_completion_file = file_dir + "/flow_completion.csv.log"
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    # job_completion_time = utils.extract_avg_fct_from_file(flow_completion_file)
                    combo_name = traffic_name[0].upper() + "_" +  topology.getTopologyName()
                    job_stats[combo_name].append(job_completion_time)
                else:
                    print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    x_ = {"label": "Number of CUs", "data": num_nodes, "log": 2}
    y_ = {"label": "Job Completion Time (ns)".format(traffic_name), "data": job_stats, "log": None}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "{}_topology_size.png".format(message_size_str)
    utils.plotMultiLineChart(x_, y_, path=plot_path)
    # utils.plotMultiLineChart(x_, y_, path="")

def analyzeTopologySizeSubplot():
    traffic_names = ["ring_allreduce","hierarchical_allreduce", "mesh_allreduce", "bcast_allreduce"] # "mesh_allreduce",
    traffic_name_labels = ["Ring", "H-Ring", "Mesh",  "SiPCO"]
    per_gpu_bw_gbps = 2048
    message_size = 1e6 # [0.01e6, 0.1e6, 1e6, 10e6, 100e6] #100e6, 1000e6
    message_size_str = utils.extract_byte_string(message_size)
    num_nodes = [16, 64, 256, 512, 1024] # 16, 64, 256, 512, 1024
    routing_scheme = "ecmp"
    job_stats = {}
    for num_node in num_nodes:
        topology_list = generateTopology(num_node, per_gpu_bw_gbps, l=1 if num_node != 512 else 2)
        job_stats[num_node] = defaultdict(list) 
        for topology in topology_list:
            for traffic_name in traffic_names:
                # if topology.getName().startswith("Bcube") and traffic_name == "bcast_allreduce": continue
                # if topology.getName().startswith("Bcube") and traffic_name == "mesh_allreduce": continue
                hardware_param = deriveNetworkHardwareParameterName(topology, traffic_name, routing_scheme, topology.getLinkBW())
                file_dir = "{}{}/{}/{}/{}".format(RESULT_DIRECTORY,traffic_name,topology.getName(),message_size_str,hardware_param)
                if os.path.isdir(file_dir):
                    flow_completion_file = file_dir + "/flow_completion.csv.log"
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    if num_node == 16 and topology.getName().startswith("photonic") and traffic_name == "bcast_allreduce": 
                        job_completion_time -= 1000000 # reduce tcp resend time that shouldn't be accounted for
                    # job_completion_time = utils.extract_avg_fct_from_file(flow_completion_file)
                    # combo_name = traffic_name[0].upper() + "_" +  topology.getTopologyName()
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

def analyzeHybridParallelism():
    traffic_names = ["hybrid_parallel"]
    per_gpu_bw_gbps_list = [128, 256, 512, 1024, 2048, 4096]
    model_info = dict({ "intra_group_comm_type":"ALLTOALL", "intra_group_algo_type":"ring", 
                        "inter_group_comm_type":"ALLREDUCE", "inter_group_algo_type":"bcast",
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
                                # "photonic_Bcube_{}r_{}l".format(r,l): "mesh", 
                                "photonic_Bcube_orig_{}r_{}l".format(r,l): "bcast"}
    
    inter_topo_to_algo_map = {"dgx_superpod_{}nodes".format(num_nodes): "ring", 
                                "2D_torus_{}_{}_{}nodes".format(torus_dim[num_nodes][0],torus_dim[num_nodes][1], num_nodes): "ring", 
                                "Bcube_{}r_{}l".format(r,l): "ring",
                                # "photonic_Bcube_{}r_{}l".format(r,l): "bcast", 
                                "photonic_Bcube_orig_{}r_{}l".format(r,l): "bcast"}
    routing_scheme = "ecmp"
    job_stats = defaultdict(list)
    for traffic_name in traffic_names:
        for per_gpu_bw_gbps in per_gpu_bw_gbps_list:
            topology_list = generateTopology(num_nodes, per_gpu_bw_gbps, l=l)
            for topology in topology_list:
                model_info["intra_group_algo_type"] = intra_topo_to_algo_map[topology.getName()]
                model_info["inter_group_algo_type"] = inter_topo_to_algo_map[topology.getName()]
                message_size_str = "mp{}_{}_alltoall_{}_{}_allreduce_{}".format(
                    num_mp_node,
                    model_info["intra_group_algo_type"],
                    utils.extract_byte_string(model_info["intra_group_message_size"]),
                    model_info["inter_group_algo_type"],
                    utils.extract_byte_string(model_info["inter_group_message_size"]))
                hardware_param = deriveNetworkHardwareParameterName(topology, traffic_name, routing_scheme, topology.getLinkBW())
                file_dir = "{}{}/{}/{}/{}/".format(RESULT_DIRECTORY,traffic_name,topology.getName(), message_size_str, hardware_param)
                if os.path.isdir(file_dir):
                    flow_completion_file = file_dir + "/flow_completion.csv.log"
                    job_completion_time = utils.extract_max_fct_from_file(flow_completion_file)
                    # job_completion_time = utils.extract_avg_fct_from_file(flow_completion_file)
                    job_stats[topology.getTopologyName()].append(job_completion_time)
                else:
                    print("[Error] File doesn't exist: ", file_dir)
    print(job_stats)
    # sys.exit()
    x_ = {"label": "Per CU Bandwidth (Gbps)", "data": per_gpu_bw_gbps_list, "log": 2}
    y_ = {"label": "Job Completion Time (ns)", "data": job_stats, "log": 10}
    plot_path = ANALYSIS_OUTPUT_DIRECTORY + "{}p{}mp_{}_alltoall{}_{}_allreduce{}_bw.png".format(num_nodes, num_mp_node,
                    model_info["intra_group_algo_type"],
                    utils.extract_byte_string(model_info["intra_group_message_size"]), 
                    model_info["inter_group_algo_type"],
                    utils.extract_byte_string(model_info["inter_group_message_size"]))
    utils.plotMultiLineChart(x_, y_, path=plot_path)
    # utils.plotMultiLineChart(x_, y_, path="")


def main():
    print("[ANALYSIS] Starting analysis ...")
    # analyzeSyntheticTraffic()
    # analyzeMessageSize()
    # analyzeTopologySize()
    analyzeTopologySizeSubplot()
    # analyzeHybridParallelism()

if __name__ == '__main__':
    main()