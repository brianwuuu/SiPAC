'''
Component count analysis for a given topology size.
'''
import sys
sys.path.append('../')
import math, pprint
import utilities as utils
import matplotlib as mpl
import matplotlib
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from network_topology import *
from collections import defaultdict

xylabel_fontsize=5.4
xyticklabel_fontsize = 16  # 6.5
linewidth_arg = 2
latex_linewidth_inch = 7.9787
fig_width = 0.45 * latex_linewidth_inch
fig_height = 1.85
legend_fontsize = 11
markersize_arg = 3

color_cycle = ['darkcyan', 'lime', 'darkred','deeppink', 'blueviolet', 'black', "orange", 'red',"green"] # ['black','red','lime','blue','darkcyan','blueviolet','deeppink',"orange","green"]
mark_cycle = ['d', '+', 's', 'x','v','p',  "o", "^",'1',  "<", ">", "1", "2", "3", "8", "P"]

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
        photonic_bcube_network = sipac_network_topology.PhotonicBcubeOrig(r=r,l=l,link_bw=100)
        networks.append(bcube_network)
        networks.append(photonic_bcube_network)
    df_size_map = {16:12, 64:80, 128:150, 256:252, 512:576, 1024:900, 2048:1872}
    df_size = {12:[3,2,2], 80:[5,4,4], 150:[6,5,5], 252:[7,6,6], 576:[9,8,8], 900:[10,9,9], 1872:[13,12,12]}
    dragonfly_network = dragonfly_network_topology.Dragonfly(G=df_size[df_size_map[p]][0], A=df_size[df_size_map[p]][1], h=1, link_bw=100, concentration=df_size[df_size_map[p]][2])
    networks.append(dragonfly_network)
    ft_size_map = {16:16, 64:64, 128:128, 256:250, 512:686, 1024:1024, 2048:2000}
    ft_size = {16:4, 64:8, 128:8, 250:10, 686:14, 1024:16, 2000:20}
    fattree_network = fattree_customized_network_topology.FatTreeCustomizedNetworkTopology(eps_radix=ft_size[ft_size_map[p]],target_num_servers=ft_size_map[p],link_bw=100,num_layers=3,oversubscription_ratio=(1,1)) # (1,1) corresponds to full bisection
    networks.append(fattree_network)
    return networks

def link_count_analysis():
    # Parameter
    topology_sizes = [16, 64, 128, 256, 512, 1024, 2048] #  32, 64, 128, 256, 512, 1024
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
    print(link_count_stats)
    print(transceiver_count_stats)
    print(switch_count_stats)
    # Plotting
    print("[Analysis] Plotting link count.")
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
    
    # print(transceiver_count_stats)
    # print(link_count_stats)
    # sys.exit()
    # Plot setup
    # ax1.set_ylabel(r"Link Count", fontsize=12)
    # ax1.set_xlabel(r"Topology Size", fontsize=12, labelpad=0.7)
    # ax1.set_title("Link Count", y=1, fontsize=16)
    ax1.set_yscale('log',base=10, nonpositive='clip')
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    
    # ax2.set_ylabel(r"Transceiver Count", fontsize=13)
    # ax2.set_title("Transceiver Count", y=1, fontsize=16)
    # ax2.set_xlabel(r"Topology Size", fontsize=13, labelpad=0.7)
    ax2.set_yscale('log',base=10, nonpositive='clip')
    ax2.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax2.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax2.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax2.tick_params(axis="x", labelsize=xyticklabel_fontsize)

    # ax3.set_ylabel(r"Switch Count", fontsize=12)
    # ax3.set_title("Switch Count", y=1, fontsize=13)
    # ax3.set_xlabel(r"Topology Size", fontsize=12, labelpad=0.7)
    ax3.set_yscale('log',base=10, nonpositive='clip')
    ax3.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax3.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax3.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax3.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax3.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax3.tick_params(axis="x", labelsize=xyticklabel_fontsize)

    # ax2.legend(network_names, fontsize=legend_fontsize, loc='lower left', bbox_to_anchor=(-1.2, 1.01), ncol=4, borderaxespad=0) # labelspacing=0.3, columnspacing=0.5, fancybox=False, shadow=True
    # plt.tight_layout()
    plt.show()
    # plt.savefig("/Users/bwu/Desktop/switch_transceiver_link_count.png", dpi=300)
    return

def transceiver_count_analysis():
    topology_sizes = [16, 128, 256, 512, 1024] #  32, 64, 128, 256, 512, 1024
    network_names = ["DGX-SuperPod", "2D-Torus","3D-Torus", "BCube-2L", "BCube-3L", "SiPAC-2L", "SiPAC-3L"]
    transceiver_count_stats = {}
    # Set up
    for topology_size in topology_sizes:
        networks = initializeNetwork(topology_size)
        for network, name in zip(networks, network_names):
            if name not in transceiver_count_stats.keys(): transceiver_count_stats[name] = []
            network.wireNetwork()
            num_transceivers = network.getNumTransceivers()
            transceiver_count_stats[name].append(num_transceivers)
    # Plotting
    print("[Analysis] Plotting transceiver count.")
    fig, ax2 = plt.subplots(1, 1, figsize=(2, 2), dpi=200)
    print(transceiver_count_stats)
    for i, network_name in enumerate(network_names):
        ax2.plot(topology_sizes, transceiver_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
    # Plot setup
    ax2.set_ylabel(r"Number of Transceivers in Topology", fontsize=xylabel_fontsize, labelpad=0.7)
    ax2.set_xlabel(r"Topology Size", fontsize=xylabel_fontsize, labelpad=0.7)
    ax2.set_xlim(xmin=min(topology_sizes)-16, xmax=max(topology_sizes)+100)
    # ax1.set_xscale('log',basex=10,nonposx='clip')
    ax2.set_yscale('log',base=10, nonpositive='clip')
    # ax1.set_xlim(xmax=1e7, xmin=1e3)
    # ax2.legend(network_names, fontsize=legend_fontsize, loc='upper right', bbox_to_anchor=(1.0, 0.35), ncol=2, labelspacing=0.3, columnspacing=0.5, fancybox=False, shadow=False)
    # ax1.legend(network_names, fontsize=legend_fontsize, ncol=3, loc='lower right', bbox_to_anchor=(1.01,-0.01), labelspacing=0.3, columnspacing=0.5)
    ax2.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax2.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax2.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax2.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    # plt.subplots_adjust(left=0.14, bottom=0.21, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
    plt.tight_layout()
    # plt.show()
    plt.savefig("/Users/bwu/Desktop/transceiver_count.png")
    return

def switch_count_analysis():
    topology_sizes = [16, 64, 128, 256, 512, 1024, 2048] #  32, 64, 128, 256, 512, 1024
    ft_topology_sizes = [16, 64, 128, 250, 686, 1024, 2000]
    df_topology_sizes = [12, 80, 150, 252, 576, 900, 1872]
    network_names = ["DGX-SuperPod", "2D-Torus","BCube(L=2)", "SiPAC(L=2)", "BCube(L=3)", "SiPAC(L=3)", "Dragonfly", "Fat-tree"]
    switch_count_stats = {}
    # Set up
    for topology_size in topology_sizes:
        networks = initializeNetwork(topology_size)
        for network, name in zip(networks, network_names):
            if name not in switch_count_stats.keys(): switch_count_stats[name] = []
            network.wireNetwork()
            num_transceivers = network.getNumSwitches()
            switch_count_stats[name].append(num_transceivers)
    # Plotting
    print("[Analysis] Plotting switch count.")
    fig, ax2 = plt.subplots(1, 1, figsize=(6, 3), dpi=200)
    print(switch_count_stats)
    for i, network_name in enumerate(network_names):
        if network_name == "Dragonfly":
            ax2.plot(df_topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
        elif network_name == "Fat-tree":
            ax2.plot(ft_topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
        else:
            ax2.plot(topology_sizes, switch_count_stats[network_name], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color=color_cycle[i], marker=mark_cycle[i], markerfacecolor='none', markersize=markersize_arg, markevery=1)
    # Plot setup
    ax2.set_ylabel(r"Number of Switches in Topology", fontsize=xylabel_fontsize, labelpad=0.7)
    ax2.set_xlabel(r"Topology Size", fontsize=xylabel_fontsize, labelpad=0.7)
    ax2.set_xlim(xmin=min(topology_sizes)-16, xmax=max(topology_sizes)+100)
    # ax1.set_xscale('log',basex=10,nonposx='clip')
    ax2.set_yscale('log', base=10, nonpositive='clip')
    # ax1.set_xlim(xmax=1e7, xmin=1e3)
    ax2.legend(network_names)
    # ax2.legend(network_names, fontsize=legend_fontsize, loc='upper right', bbox_to_anchor=(1.0, 0.35), ncol=2, labelspacing=0.3, columnspacing=0.5, fancybox=False, shadow=False)
    # ax1.legend(network_names, fontsize=legend_fontsize, ncol=3, loc='lower right', bbox_to_anchor=(1.01,-0.01), labelspacing=0.3, columnspacing=0.5)
    ax2.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax2.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax2.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax2.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax2.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    # plt.subplots_adjust(left=0.14, bottom=0.21, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
    plt.tight_layout()
    plt.show()
    # plt.savefig("/Users/bwu/Desktop/switch_count.png")
    return

def electrical_port_count_analysis():
    # number of tranceivers
    return

if __name__ == "__main__":
    link_count_analysis()
    # transceiver_count_analysis()
    # switch_count_analysis()




