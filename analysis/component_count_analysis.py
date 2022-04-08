'''
Analysis script for SiPAC cost comparison.

Usage:
    1) Run "python3 cost_analysis.py"
'''

import sys
sys.path.append('../')
import math, pprint
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from network_topology import *

# Initialize all the topologies to be compared
# Canonical Dragonfly: g = a + 1, h = 1 as described in https://link.springer.com/chapter/10.1007/978-3-319-67630-2_5
# Fully subscribed 3-level Fat-tree: number of endpoints = r ^ 3 / 4 where r is the switch radix
# SuperPod: DGX A-100 nodes interconneted in a 2-layer fat-tree as described in https://www.nvidia.com/en-us/data-center/dgx-superpod/
# 2D-Torus: number of endpoints = num_nodes_in_col * num_nodes_in_row
# BCube with EPS: number of endpoints = r ^ (l+1)
# SiPAC with WSS: number of endpoints = r ^ (l+1)
def initializeNetwork(topology_size):
    p = topology_size
    l_range = [1,2]
    dgx_superpod_network = dgx_superpod_network_topology.DGX_Superpod(target_num_gpus=p, link_bw=100)
    networks = [dgx_superpod_network]
    # multiple for loop for plotting purpose
    for l in l_range:
        r = math.ceil(p ** (1/(l+1)))
        if l == 1: 
            torus_network = nd_torus_network_topology.NDTorusNetworkTopology([r]*(l+1), link_bw=100)
            networks.append(torus_network)
        bcube_network = bcube_network_topology.BcubeNetworkTopology(r=r,l=l,link_bw=100, num_wavelengths_per_pair=1)
        sipac_network = sipac_network_topology.SiPACNetworkTopology(r=r,l=l,link_bw=100)
        networks.append(bcube_network)
        networks.append(sipac_network)
    df_size_map = {16:12, 64:80, 128:150, 256:252, 512:576, 1024:900, 2048:1872}
    df_size = {12:[3,2,2], 80:[5,4,4], 150:[6,5,5], 252:[7,6,6], 576:[9,8,8], 900:[10,9,9], 1872:[13,12,12]}
    dragonfly_network = dragonfly_network_topology.Dragonfly(G=df_size[df_size_map[p]][0], A=df_size[df_size_map[p]][1], h=1, link_bw=100, concentration=df_size[df_size_map[p]][2])
    networks.append(dragonfly_network)
    ft_size_map = {16:16, 64:64, 128:128, 256:250, 512:686, 1024:1024, 2048:2000}
    ft_size = {16:4, 64:8, 128:8, 250:10, 686:14, 1024:16, 2000:20}
    fattree_network = fattree_customized_network_topology.FatTreeCustomizedNetworkTopology(eps_radix=ft_size[ft_size_map[p]],target_num_servers=ft_size_map[p],link_bw=100,num_layers=3,oversubscription_ratio=(1,1)) # (1,1) corresponds to full bisection
    networks.append(fattree_network)
    return networks

# Compute the link, transceiver and switch count for the topologies listed above
def componentCountAnalysis():
    # Parameter
    topology_sizes = [16, 64, 128, 256, 512, 1024, 2048]
    ft_topology_sizes = [16, 64, 128, 250, 686, 1024, 2000]
    df_topology_sizes = [12, 80, 150, 252, 576, 900, 1872]
    sipac_2L_topology_sizes = []
    sipac_3L_topology_sizes = []
    network_names = ["DGX-SuperPod", "2D-Torus","BCube(L=2)", "SiPAC(L=2)", "BCube(L=3)", "SiPAC(L=3)", "Dragonfly", "Fat-tree"]
    link_count_stats = {}
    transceiver_count_stats = {}
    switch_count_stats = {}
    # Set up
    for topology_size in topology_sizes:
        networks = initializeNetwork(topology_size)
        for network, name in zip(networks, network_names):
            if name not in link_count_stats.keys(): link_count_stats[name] = []
            if name not in transceiver_count_stats.keys(): transceiver_count_stats[name] = []
            if name not in switch_count_stats.keys(): switch_count_stats[name] = []
            if name in ["BCube(L=2)"]: sipac_2L_topology_sizes.append(network.getR()**(network.getL()+1))
            if name in ["BCube(L=3)"]: sipac_3L_topology_sizes.append(network.getR()**(network.getL()+1))
            network.wireNetwork()
            num_links = network.getNumLinks()
            num_transceivers = network.getNumTransceivers()
            num_switches = network.getNumSwitches()
            transceiver_count_stats[name].append(num_transceivers)
            link_count_stats[name].append(num_links)
            switch_count_stats[name].append(num_switches)
    # Plotting
    print("[Analysis] Plotting link count.")
    xyticklabel_fontsize = 16
    linewidth_arg = 2
    markersize_arg = 3
    color_cycle = ['darkcyan', 'lime', 'darkred','deeppink', 'blueviolet', 'black', "orange", 'red',"green"]
    mark_cycle = ['d', '+', 's', 'x','v','p',  "o", "^",'1',  "<", ">", "1", "2", "3", "8", "P"]
    fig, (ax1,ax2,ax3) = plt.subplots(1, 3, figsize=(10,4))
    for i, network_name in enumerate(network_names):
        if network_name == "Dragonfly":
            ax1.plot(df_topology_sizes, link_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax2.plot(df_topology_sizes, transceiver_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax3.plot(df_topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
        elif network_name == "Fat-tree":
            ax1.plot(ft_topology_sizes, link_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax2.plot(ft_topology_sizes, transceiver_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax3.plot(ft_topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
        elif network_name in ["BCube(L=2)", "SiPAC(L=2)"]:
            ax1.plot(sipac_2L_topology_sizes, link_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax2.plot(sipac_2L_topology_sizes, transceiver_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax3.plot(sipac_2L_topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
        elif network_name in ["BCube(L=3)", "SiPAC(L=3)"]:
            ax1.plot(sipac_3L_topology_sizes, link_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax2.plot(sipac_3L_topology_sizes, transceiver_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax3.plot(sipac_3L_topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
        else:
            ax1.plot(topology_sizes, link_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax2.plot(topology_sizes, transceiver_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
            ax3.plot(topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
    
    # Plot setup
    ax1.set_ylabel(r"Link Count", fontsize=12)
    ax1.set_xlabel(r"Topology Size", fontsize=12, labelpad=0.7)
    ax1.set_yscale('log',base=10, nonpositive='clip')
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    
    ax2.set_ylabel(r"Transceiver Count", fontsize=13)
    ax2.set_xlabel(r"Topology Size", fontsize=13, labelpad=0.7)
    ax2.set_yscale('log',base=10, nonpositive='clip')
    ax2.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax2.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax2.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax2.tick_params(axis="x", labelsize=xyticklabel_fontsize)

    ax3.set_ylabel(r"Switch Count", fontsize=12)
    ax3.set_xlabel(r"Topology Size", fontsize=12, labelpad=0.7)
    ax3.set_yscale('log',base=10, nonpositive='clip')
    ax3.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax3.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax3.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax3.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax3.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax3.tick_params(axis="x", labelsize=xyticklabel_fontsize)

    ax2.legend(network_names, fontsize=12, loc='lower left', bbox_to_anchor=(-1.2, 1.01), ncol=4, borderaxespad=0)
    plt.show()
    return

if __name__ == "__main__":
    componentCountAnalysis()




