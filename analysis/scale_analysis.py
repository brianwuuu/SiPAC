'''
Topological analysis for maximum network size.
'''
import numpy as np
from gurobipy import *
import matplotlib.pyplot as plt

#mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
xylabel_fontsize=7.4
xyticklabel_fontsize = 6.5
linewidth_arg = 0.9
latex_linewidth_inch = 6.9787
fig_width = 0.45 * latex_linewidth_inch
fig_height = 1.65
legend_fontsize = 6.2
markersize_arg = 4

color_cycle = ['black','red','lime','blue','darkcyan','blueviolet','deeppink']

# Computes the maximum number of nodes we can support given a node degree and a diameter
def compute_moore_bound(node_degree, diameter):
    moore_bound = -1
    if node_degree == 2:
        moore_bound = 2 * diameter + 1
    elif node_degree > 2:
        moore_bound = 1 + node_degree * ((node_degree - 1) ** diameter - 1) / (node_degree - 2)
    return int(moore_bound)

def dragonfly_network_designer(switch_num_uplinks, pod_level_diameter):
    group_size = switch_num_uplinks
    num_groups = group_size + 1
    max_num_servers = num_groups * group_size * switch_num_uplinks
    num_electrical_ports = num_groups * group_size * (2 * switch_num_uplinks)
    return max_num_servers, num_groups, num_electrical_ports, 0

# Returns the maximum system size and requirement on OCS radix
def fully_subscribed_clos_designer(tor_num_uplinks, levels):
    if tor_num_uplinks == 0:
        return 0, 0
    max_num_servers = 2 * (tor_num_uplinks ** levels)
    total_switches = (2 * levels - 1) * tor_num_uplinks ** (levels - 1)
    return max_num_servers, 0, total_switches * tor_num_uplinks * 2, 0

def photonic_bcube_designer(n, k=1):
    max_num_servers = n ** (k+1)
    num_groups = n * k
    num_electrical_ports = 0
    num_ocs_ports = (n ** k * (k + 1)) * k
    return max_num_servers, num_groups, num_electrical_ports, num_ocs_ports

def sip_ml_designer(ocs_downlinks):
    max_num_servers = ocs_downlinks
    num_groups = max_num_servers
    num_electrical_ports = 0
    num_ocs_ports = ocs_downlinks
    return max_num_servers, num_groups, num_electrical_ports, num_ocs_ports


def scalability_analysis():
    num_uplinks = np.arange(4, 65, 2)
    # Clos
    clos_layer3 = [fully_subscribed_clos_designer(x, 3) for x in num_uplinks]
    clos_layer4 = [fully_subscribed_clos_designer(x, 4) for x in num_uplinks]

    # Dragonfly (Canonical)
    dfly_canonical = [dragonfly_network_designer(x, 1) for x in num_uplinks]

    # Dragonfly ring (canonical)
    photonic_bcube_1 = [photonic_bcube_designer(x, 1) for x in num_uplinks]
    photonic_bcube_2 = [photonic_bcube_designer(x, 2) for x in num_uplinks]
    
    # SiP-ML
    sip_ml = [sip_ml_designer(x) for x in num_uplinks]
    
    # Plotting
    # mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
    fig, ax1 = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=200)
    eps_radices = [2 * x for x in num_uplinks]
    # ax1.plot(eps_radices, [x[0] for x in tor_dimension1_diameter2], linestyle='--', linewidth=linewidth_arg, color='darkcyan', marker='+', markerfacecolor='none', markersize=markersize_arg, markevery=4)
    # ax1.plot(eps_radices, [x[0] for x in tor_dimension2_diameter1], linestyle='-.', linewidth=linewidth_arg, color='darkblue', marker='^', markerfacecolor='none', markersize=markersize_arg, markevery=4)
    # ax1.plot(eps_radices, [x[0] for x in mesh_pod], color='lime',  marker='s', markevery=4, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
    # ax1.plot(eps_radices, [x[0] for x in tiered_1to1_pod], color='red', marker='x', markevery=4, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
    # ax1.plot(eps_radices, [x[0] for x in tiered_4to1_pod], color='darkred', marker='d', markevery=4, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
    ax1.plot(eps_radices, [x[0] for x in dfly_canonical], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='orange', marker='h', markerfacecolor='none', markersize=markersize_arg, markevery=1)
    ax1.plot(eps_radices, [x[0] for x in photonic_bcube_1], linewidth=linewidth_arg, color='darkcyan', marker='x', markerfacecolor='none', markersize=markersize_arg)	
    ax1.plot(eps_radices, [x[0] for x in photonic_bcube_2], linewidth=linewidth_arg, color='blue', marker='.', markerfacecolor='none', markersize=markersize_arg)	
    ax1.plot(eps_radices, [x[0] for x in sip_ml], linewidth=linewidth_arg, color='darkblue', marker='d', markerfacecolor='none', markersize=markersize_arg)	
    # ax1.plot(eps_radices, [x[0] for x in clos_layer3], linewidth=linewidth_arg, color='black', linestyle='--')
    # ax1.plot(eps_radices, [x[0] for x in clos_layer4], linewidth=linewidth_arg, color='black')
    
    #ax1.plot(eps_radices, [x[0] for x in tor_dimension1_diameter3], linestyle='--', linewidth=linewidth_arg, color='gray')
    #ax1.plot([x[0] for x in clos_layer4], num_uplinks, linewidth=linewidth_arg)
    ax1.set_ylabel(r"Network size", fontsize=xylabel_fontsize, labelpad=0.7)
    ax1.set_xlabel(r"Switch degree ($k$)", fontsize=xylabel_fontsize, labelpad=0.7)
    ax1.set_xlim(xmin=min(eps_radices), xmax=max(eps_radices))
    #ax1.set_xscale('log',basex=2,nonposx='clip')
    ax1.set_yscale('log',basey=10, nonposy='clip')
    #ax1.set_xlim(xmax=1e7, xmin=1e3)
    # ax1.legend(['TRN-Flat', 'TRN-2D', 'PRN-Mesh', 'PRN-2L (1:1)', 'PRN-2L (4:1)', 'DF', 'FT3', 'FT4'], fontsize=legend_fontsize, ncol=3, loc='lower right', bbox_to_anchor=(1.01,-0.01), labelspacing=0.3, columnspacing=0.5)
    ax1.legend(['DF', "PB-2", "PB-3", "SiP-ML"], fontsize=legend_fontsize, ncol=3, loc='lower right', bbox_to_anchor=(1.01,-0.01), labelspacing=0.3, columnspacing=0.5)
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    plt.subplots_adjust(left=0.14, bottom=0.21, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
    # plt.show()
    plt.savefig("/Users/bwu/Desktop/test.png")


def drawModelSizeTrend():
    years = [2016, 2017.5, 2018.4, 2019.91, 2020.58, 2020.25, 2021.83, 2021.1, 2022]
    model_name = ["ResNet-50","Transformer(Big)","BERT-Large","GPT-2","GPT-3","Megatron-LM","Megatron-T","1T(Switch-C)","DLRM-2022"]
    model_sizes = [2.56e7, 2.13e8, 3.40e8, 1.50e9, 1.75e11, 8.30e9, 5.30e11, 1.57e12, 1.20e13]
    model_sizes_billion = [x / 10e9 for x in model_sizes]

    fig, ax1 = plt.subplots(1, 1, figsize=(4, 2.5), dpi=200)
    ax1.scatter(years, model_sizes_billion, color='black', marker="o", s=markersize_arg)
    for i, (model_size, year) in enumerate(zip(model_sizes_billion, years)):
        if model_name[i] in ["GPT-2", "GPT-3", "1T(Switch-C)", "Megatron-LM"]:
            plt.text(year,1.2*model_size,model_name[i],fontsize="xx-small", horizontalalignment='center')
        elif model_name[i] in ["Transformer(Big)" , "Megatron-T"]:
            plt.text(year,0.4*model_size,model_name[i],fontsize="xx-small", horizontalalignment='center')
        elif model_name[i] in ["ResNet-50"]:
            plt.text(year-0.2,1.2*model_size,model_name[i],fontsize="xx-small", horizontalalignment='left')
        elif model_name[i] in ["DLRM-2022"]:
            plt.text(year-0.2,0.5*model_size,model_name[i],fontsize="xx-small", horizontalalignment='center')
        else:
            plt.text(year,1.2*model_size,model_name[i],fontsize="xx-small", horizontalalignment='left')
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    plt.xlabel("Year", fontsize=6)
    plt.ylabel("# Parameters (in billions)", fontsize=6)
    plt.xlim([2015.5, 2022.7])
    plt.yscale('log',base=10,nonpositive='clip')
    plt.tight_layout()
    # plt.show()
    plt.savefig("/Users/bwu/Desktop/dml_trend.png")

def drawBandwidthTrend():
    # plt.plot(np.unique(x), np.poly1d(np.polyfit(x, y, 1))(np.unique(x)))
    years_1 = [2023, 2020.98, 2018.25, 2016.33, 2015.92, 2015]
    years_2 = [2023, 2022.33, 2018.92, 2017.25, 2015.92, 2015]
    gpu_name = ["A100 80GB SXM", "V100 SXM", "P100 SXM", "M40 PCIE"]
    gpu_bandwidth = [900, 600, 300, 160, 32, 16]
    memory_name = ["80GB HBM2e","32/16 GB HBM2","16 GB CoWoS HBM2","24 GB GDDR5"]
    memory_bandwidth = [2400, 2039, 900, 732, 288, 200]
    nic_name = ["Connectx-7", "Connectx-6", "Connectx-5", "Connectx-4"]
    nic_bandwidth = [75, 50, 25, 12.5, 5, 2.5]

    fig, ax1 = plt.subplots(1, 1, figsize=(4, 2.5), dpi=200)
    ax1.scatter(years_1[1:-1], memory_bandwidth[1:-1], color='darkred', marker="o", s=markersize_arg)
    ax1.scatter(years_1[1:-1], gpu_bandwidth[1:-1], color='darkblue', marker="o", s=markersize_arg)
    ax1.scatter(years_2[1:-1], nic_bandwidth[1:-1], color='chocolate', marker="o", s=markersize_arg)
    
    for i, (bandwidth, year) in enumerate(zip(memory_bandwidth[1:-1], years_1[1:-1])):
        plt.text(year, bandwidth+30, memory_name[i], fontsize="xx-small", horizontalalignment='center', color="darkred", fontweight='bold')
    for i, (bandwidth, year) in enumerate(zip(gpu_bandwidth[1:-1], years_1[1:-1])):
        if i == 2:
            plt.text(year, bandwidth+30, gpu_name[i], fontsize="xx-small", horizontalalignment='left', color="darkblue", fontweight='bold')
        else:    
            plt.text(year, bandwidth+30, gpu_name[i], fontsize="xx-small", horizontalalignment='center', color="darkblue", fontweight='bold')
    for i, (bandwidth, year) in enumerate(zip(nic_bandwidth[1:-1], years_2[1:-1])):
        if i == 0:
            plt.text(year, bandwidth-120, nic_name[i], fontsize="xx-small", horizontalalignment='right', color="chocolate", fontweight='bold')
        else:
            plt.text(year, bandwidth-120, nic_name[i], fontsize="xx-small", horizontalalignment='center', color="chocolate", fontweight='bold')
        
    ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    ax1.grid(b=None, which='major', axis='x', linestyle='-', linewidth=0.5)
    ax1.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.3)
    ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
    ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
    plt.plot(np.unique(years_1), np.poly1d(np.polyfit(years_1, memory_bandwidth, 1))(np.unique(years_1)), color="darkred", linestyle=(0, (1, 1)), linewidth=linewidth_arg)
    plt.plot(np.unique(years_1), np.poly1d(np.polyfit(years_1, gpu_bandwidth, 1))(np.unique(years_1)), color="darkblue", linestyle=(0, (1, 1)), linewidth=linewidth_arg)
    plt.plot(np.unique(years_2), np.poly1d(np.polyfit(years_2, nic_bandwidth, 1))(np.unique(years_2)), color="chocolate", linestyle=(0, (1, 1)), linewidth=linewidth_arg)
    plt.xlabel("Year", fontsize=6)
    plt.ylabel("Bandwidth (GB/s)", fontsize=6)
    plt.xlim([2015.1, 2022.7])
    plt.ylim([-200, 2200])
    # plt.yscale('log',base=10,nonpositive='clip')
    plt.tight_layout()
    # plt.show()
    plt.savefig("/Users/bwu/Desktop/bw_linear.png")

if __name__ == "__main__":
    # scalability_analysis()
    drawModelSizeTrend()
    # drawBandwidthTrend()
    




