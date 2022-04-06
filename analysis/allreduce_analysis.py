'''
Topological analysis for maximum network size.
'''
import numpy as np
from gurobipy import *
import math, sys
import matplotlib as mpl
import matplotlib
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d
import matplotlib.image as img
from matplotlib import cm

# Plotting
xylabel_fontsize=7.4
xyticklabel_fontsize = 6.5
linewidth_arg = 0.9
latex_linewidth_inch = 6.9787
fig_width = 0.6 * latex_linewidth_inch
fig_height = 1.8
legend_fontsize = 6.2
markersize_arg = 4
color_cycle = ['black','red','lime','blue','darkcyan','blueviolet','deeppink']
mark_cycle = ['d', '+', 's', 'x','v','1', 'p', ".", "o", "^", "<", ">", "1", "2", "3", "8", "P"]

def ring_allreduce_time(p, n, alpha, beta):
    latency_term = 2 * (p - 1) * alpha
    bw_term = 2 * (p - 1) * (n // p) * beta
    return latency_term + bw_term

def mesh_allreduce_time(p, n, alpha, beta):
    latency_term = 2 * alpha
    bw_term = 2 * (p - 1) * (n // p) * beta
    return latency_term + bw_term

def hierarchical_ring_allreduce_time(p, k, n, alpha, beta):
    latency_term = (4 * (k - 1) + 2 * (p // k - 1)) * alpha
    bw_term = (4 * (k - 1) + 2 * (p // k - 1)) * (n // k) * beta
    return latency_term + bw_term

def hierarchical_mesh_allreduce_time(p, k, n, alpha, beta):
    latency_term = 4 * alpha
    bw_term = 4 * (n // k) * (k - 1) * beta
    return latency_term + bw_term

def hierarchical_bcast_allreduce_time(p, k, n, L, alpha, beta):
    latency_term = (L+1) * alpha
    bw_term = (L+1) * (k-1) // (L * k) * n * beta
    return latency_term + bw_term

def bcast_assisted_allreduce_time_v1(p, n, alpha, beta):
    # assume canonical where p = k ** 2
    k = p ** (1/2)
    latency_term = 2 * alpha
    # bw_term = 2 * n * beta
    bw_term = (2 * k) * (n // k) * k * beta
    return latency_term + bw_term

def bcast_assisted_allreduce_time_v2(p, k, n, L, alpha, beta):
    # does not assume canonical where p = k ** 2
    # Mesh-based broadcast allreduce
    latency_term = 2 * L * alpha
    bw_term = (2 * L * n // k * k * beta)
    return (latency_term + bw_term)

def bcast_optimized_allreduce(p, k, n, L, alpha, beta):
    # does not assume canonical where p = k ** 2
    # Mesh-based broadcast allreduce
    latency_term = (L+2) * alpha
    bw_term = (L+2) * n // L * beta
    return (latency_term + bw_term)

def allreduce_analysis_network_size():
    alpha = 1e-6 # unit link latency = 1 us
    beta = 1 / (128 * 32e9 / 8) # 128 channels of 32 Gbps
    n = 1e6 # 1 MB message size
    k_list = list(range(2, 34, 2))
    p_list = [x**2 for x in k_list]
    ring_allreduce = [ring_allreduce_time(p, n, alpha, beta) for k, p in zip(k_list, p_list)]
    mesh_allreduce = [ring_allreduce_time(p, n, alpha, beta) for k, p in zip(k_list, p_list)]
    hierarchical_ring_allreduce = [hierarchical_ring_allreduce_time(p, k, n, alpha, beta) for k, p in zip(k_list, p_list)]
    hierarchical_mesh_allreduce = [hierarchical_mesh_allreduce_time(p, k, n, alpha, beta) for k, p in zip(k_list, p_list)]
    hierarchical_bcast_allreduce_2L = [hierarchical_bcast_allreduce_time(p, k, n, 1, alpha, beta) for k, p in zip(k_list, p_list)]
    hierarchical_bcast_allreduce_3L = [hierarchical_bcast_allreduce_time(p, k, n, 2, alpha, beta) for k, p in zip(k_list, p_list)]
    
    # bcast_assisted_allreduce = [bcast_assisted_allreduce_time_v1(p, n, alpha, beta) for k, p in zip(k_list, p_list)]
    # bcast_assisted_allreduce_2L = [bcast_assisted_allreduce_time_v2(p, p**(1/2), n, 2, alpha, beta) for k, p in zip(k_list, p_list)]
    # bcast_assisted_allreduce_3L = [bcast_assisted_allreduce_time_v2(p, p**(1/3), n, 3, alpha, beta) for k, p in zip(k_list, p_list)]
    # bcast_optimized_allreduce_2L = [bcast_optimized_allreduce(p, p**(1/2), n, 2, alpha, beta) for k, p in zip(k_list, p_list)]
    # bcast_optimized_allreduce_2L = [bcast_optimized_allreduce(p, p**(1/3), n, 3, alpha, beta) for k, p in zip(k_list, p_list)]
    
    # Start plotting
    fig, ax1 = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=200)
    ax1.plot(p_list, ring_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='orange', marker='h', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(p_list, mesh_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='blue', marker='x', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(p_list, hierarchical_ring_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='black', marker='+', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(p_list, hierarchical_mesh_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='red', marker='s', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(p_list, hierarchical_bcast_allreduce_2L, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='green', marker='*', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(p_list, hierarchical_bcast_allreduce_3L, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='purple', marker='o', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    
    ax1.set_ylabel(r"Time ($s$)", fontsize=xylabel_fontsize, labelpad=0.7)
    ax1.set_xlabel(r"Number of Nodes ($p$)", fontsize=xylabel_fontsize, labelpad=0.7)
    # ax1.set_xlim(xmin=min(eps_radices), xmax=max(eps_radices))
    # ax1.set_xscale('log',basex=2,nonposx='clip')
    # ax1.set_yscale('log',basey=2, nonposy='clip')
    ax1.legend(['R Allreduce', "M Allreduce", "H-R Allreduce", "H-M Allreduce", "H-B(2L) Allreduce", "H-B(3L) Allreduce"], fontsize=legend_fontsize, ncol=2, loc='upper left', labelspacing=0.3, columnspacing=0.5)
    # ax1.legend(["Hiearchical Ring Allreduce", "BCast Allreduce", "2D-Mesh BCast Allreduce", "3D-Mesh BCast Allreduce", "2D-* BCast Allreduce", "3D-* BCast Allreduce"], fontsize=legend_fontsize, ncol=2, loc='center left', labelspacing=0.3, columnspacing=0.5)
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    plt.subplots_adjust(left=0.14, bottom=0.21, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
    # plt.show()
    plt.savefig("/Users/bwu/Desktop/all_reduce.png")
    
def allreduce_analysis_message_size():
    alpha = 1e-6 # unit link latency = 1 us
    beta = 1 / (128 * 32e9 / 8) # 128 channels of 32 Gbps
    message_sizes = [1e3, 10e3, 100e3, 1e6, 10e6, 100e6] # 1 MB message size
    k = 4
    p = 16
    ring_allreduce = [ring_allreduce_time(p, n, alpha, beta) for n in message_sizes]
    mesh_allreduce = [mesh_allreduce_time(p, n, alpha, beta) for n in message_sizes]
    hierarchical_ring_allreduce = [hierarchical_ring_allreduce_time(p, k, n, alpha, beta) for n in message_sizes]
    hierarchical_mesh_allreduce = [hierarchical_mesh_allreduce_time(p, k, n, alpha, beta) for n in message_sizes]
    hierarchical_bcast_allreduce_2L = [hierarchical_bcast_allreduce_time(p, k, n, 1, alpha, beta) for n in message_sizes]
    hierarchical_bcast_allreduce_3L = [hierarchical_bcast_allreduce_time(p, k, n, 2, alpha, beta) for n in message_sizes]
    bcast_assisted_allreduce = [bcast_assisted_allreduce_time_v1(p, n, alpha, beta) for n in message_sizes]
    bcast_assisted_allreduce_2L = [bcast_assisted_allreduce_time_v2(p, p**(1/2), n, 2, alpha, beta) for n in message_sizes]
    bcast_assisted_allreduce_3L = [bcast_assisted_allreduce_time_v2(p, p**(1/3), n, 3, alpha, beta) for n in message_sizes]
    bcast_optimized_allreduce_2L = [bcast_optimized_allreduce(p, p**(1/2), n, 2, alpha, beta) for n in message_sizes]
    bcast_optimized_allreduce_2L = [bcast_optimized_allreduce(p, p**(1/3), n, 3, alpha, beta) for n in message_sizes]
    
    
    # Start plotting
    fig, ax1 = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=200)
    ax1.plot(message_sizes, ring_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='orange', marker='h', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(message_sizes, mesh_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='black', marker='+', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(message_sizes, hierarchical_ring_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='red', marker='s', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(message_sizes, hierarchical_mesh_allreduce, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='blue', marker='.', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(message_sizes, hierarchical_bcast_allreduce_2L, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='green', marker='*', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(message_sizes, hierarchical_bcast_allreduce_3L, linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='purple', marker='x', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    
    ax1.set_ylabel(r"Time ($s$)", fontsize=xylabel_fontsize, labelpad=0.7)
    ax1.set_xlabel(r"Message Sizes ($B$)", fontsize=xylabel_fontsize, labelpad=0.7)
    # ax1.set_xlim(xmin=min(eps_radices), xmax=max(eps_radices))
    ax1.set_xscale('log',basex=10,nonposx='clip')
    # ax1.set_yscale('log',basey=2, nonposy='clip')
    # ax1.legend(['Ring Allreduce', "Hiearchical Ring Allreduce", "BCast Allreduce", "2D-Mesh BCast Allreduce", "3D-Mesh BCast Allreduce"], fontsize=legend_fontsize, ncol=2, loc='center left', labelspacing=0.3, columnspacing=0.5)
    ax1.legend(['R Allreduce', "M Allreduce", "H-R Allreduce", "H-M Allreduce", "H-B(2L) Allreduce", "H-B(3L) Allreduce"], fontsize=legend_fontsize, ncol=2, loc='center left', labelspacing=0.3, columnspacing=0.5)
    
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    plt.subplots_adjust(left=0.14, bottom=0.21, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
    plt.show()
    # plt.savefig("/Users/bwu/Desktop/message_size.png")

def allreduce_3d_plot():
    # alpha = 10e-6 # unit link latency = 1 us
    beta = 1 / (128 * 32e9 / 8) # 128 channels of 32 Gbps
    # k_list = list(range(2, 34, 2))
    # p_list = [x**2 for x in k_list]

    p = 1024
    message_sizes = [0.125e6, 0.25e6, 0.5e6, 1e6, 2e6, 4e6] # in megabytes
    alpha_list = [0.4e-6, 0.8e-6, 1e-6, 1.5e-6, 2e-6, 5e-6, 8e-6, 10e-6] # in microseconds

    # p, n = np.meshgrid(p_list, message_sizes)
    alpha, n = np.meshgrid(alpha_list, message_sizes)
    
    ring_allreduce = ring_allreduce_time(p, n, alpha, beta)
    hierarchical_ring_allreduce = hierarchical_ring_allreduce_time(p, p**(1/2), n, alpha, beta)
    bcast_assisted_allreduce = bcast_assisted_allreduce_time_v1(p, n, alpha, beta)
    hierarchical_bcast_allreduce_2L = hierarchical_bcast_allreduce_time(p, p**(1/2), n, 1, alpha, beta)
    ring_allreduce_vs_bcast_assisted_allreduce = ring_allreduce / hierarchical_bcast_allreduce_2L
    
    fig = plt.figure()
    ax = plt.axes(projection='3d')
    # ax.plot_surface(p, n, ring_allreduce, rstride=1, cstride=1, cmap='Greys', edgecolor='none')
    # ax.plot_surface(p, n, hierarchical_ring_allreduce, rstride=1, cstride=1, cmap='viridis', edgecolor='none')
    # ax.plot_surface(p, n, bcast_assisted_allreduce, rstride=1, cstride=1, cmap='Purples', edgecolor='none')
    ax.plot_surface(alpha, n, ring_allreduce_vs_bcast_assisted_allreduce, rstride=1, cstride=1, cmap='viridis', edgecolor='none')
    ax.set_xlabel('Per node latency (s)')
    ax.set_ylabel('Message Sizes (Bytes)')
    ax.set_zlabel('Completion Time Ratio')
    # ax.set_xlim(10e-6, 0)
    plt.show()
    # plt.savefig("/Users/bwu/Desktop/network_size_message_size_3d.png")
    
if __name__ == "__main__":
    # allreduce_analysis_network_size()
    allreduce_analysis_message_size()
    # allreduce_3d_plot()
    




