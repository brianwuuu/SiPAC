import os
import json
import numpy as np
import matplotlib.pyplot as plt

INFINITY = 1E11

def parseJSON(filename):
    # print("*** Parsing JSON file from " + filename)
    with open(filename) as json_file: 
        file = json.load(json_file)
    return file

def extract_timing_string(nanoseconds):
    if nanoseconds < 1000:
        # nanoseconds regime
        entry = nanoseconds
        return "{}ns".format(entry)
    elif nanoseconds >= 1000 and nanoseconds < 1000000:
        # microseconds regime
        entry = nanoseconds / 1000
        return "{}us".format(entry)
    elif nanoseconds >= 1000000 and nanoseconds < 1000000000:
        # milliseconds regime
        entry = nanoseconds / 1000000
        return "{}ms".format(entry)
    else:
        # seconds regime
        entry = nanoseconds / 1000000000
        return "{}s".format(entry)

def extract_byte_string(size_bytes):
    entry = None
    if size_bytes < 1000:
        entry = "{}B".format(size_bytes)
    elif size_bytes >= 1000 and size_bytes < 1000000:
        entry = "{}KB".format(size_bytes // 1000)
    elif size_bytes >= 1000000 and size_bytes < 1000000000:
        entry = "{}MB".format(size_bytes // 1000000)
    elif size_bytes >= 1000000000:
        entry = "{}GB".format(size_bytes // 1000000000)
    if entry: return entry
    else: raise Exception("Byte size out of range")

def extract_max_fct_from_file(fct_filename):
    print("[ANALYSIS] Reading {}".format(fct_filename))
    job_finish_time = -float('inf')
    with open(fct_filename, 'r') as f:
        for line in f:
            row = line.split(',')
            job_finish_time = max(job_finish_time, float(row[6]))
    return job_finish_time

def extract_avg_fct_from_file(fct_filename):
    print("[ANALYSIS] Reading {}".format(fct_filename))
    total_flow_duration, num_flows = 0, 0
    with open(fct_filename, 'r') as f:
        for line in f:
            row = line.split(',')
            total_flow_duration += float(row[7])
            num_flows += 1
    return total_flow_duration / max(1, num_flows)

def computeListStat(type:str, data:list):
    if type == "mean":
        return np.mean(data)
    elif type == "99":
        return np.percentile(data, 99, interpolation='nearest')
    elif type == "50":
        return np.percentile(data, 50, interpolation='nearest')

def normalizeStats(stats, norm_factor=1):
    max_val = 0
    for value_list in stats.values():
        for value in value_list: max_val = max(max_val, value)
    for key, value_list in stats.items():
        new_value_list = [val/max_val*norm_factor for val in value_list]
        stats[key] = new_value_list
    return stats

################################################################################################################
####################################    PLOTTING FUNCTIONS    ##################################################
################################################################################################################
# Plotting related
# color_cycle = ['black','red','lime','blue','darkcyan','blueviolet','deeppink']
color_cycle = ['darkcyan', 'lime', 'darkred','deeppink', 'blueviolet',  "silver", 'black']
mark_cycle = ['d', '+', 's', 'x','v','1', 'p', ".", "o", "^", "<", ">", "1", "2", "3", "8", "P"]
line_styles = ["solid", "dotted", "dashed", "dashdot"]
markersize_arg = 4
xylabel_fontsize=7.4
xyticklabel_fontsize = 6.5
linewidth_arg = 1
legend_fontsize = 8.2

def plotMultiLineChart(x, y, path=""):
    print("[ANALYSIS] Plotting multiline chart to " + path)
    # plt.figure(figsize=(6,3))
    plt.figure(figsize=(3,3)) # message size
    for i, (parameter, marker_arg) in enumerate(zip(y["data"].keys(), mark_cycle)):
        plt.plot(x["data"], y["data"][parameter], label=parameter, ls=line_styles[i%len(line_styles)], 
                marker=marker_arg, markerfacecolor='none', markersize=markersize_arg) # color=color_cycle[i], linewidth=linewidth_arg
    plt.xlabel(x["label"])
    plt.ylabel(y["label"])
    # plt.ylim([-0.1e8, 5e8]) # message size
    if y["log"]:
        plt.yscale('log',base=y["log"],nonpositive='clip')
    if x["log"]:
        plt.xscale('log',base=x["log"],nonpositive='clip')
    plt.grid(b=None, which='major', axis='x', linestyle=':', linewidth=0.7)
    plt.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.7)
    plt.grid(b=None, which='major', axis='y', linestyle='--',linewidth=0.7)
    plt.grid(b=None, which='minor', axis='y', linestyle='--',linewidth=0.7)
    # plt.title(y["label"] + " vs " + x["label"])
    plt.xticks(x["data"], fontsize=10) # rotation="45"
    plt.tight_layout()
    # plt.legend(ncol=2, bbox_to_anchor= (0.0, 0.6), loc='lower left', fontsize=legend_fontsize) # bbox_to_anchor= (-3.0, 1), loc='lower left'
    # plt.legend(ncol=1, bbox_to_anchor= (-1, 0), loc='lower left', fontsize=legend_fontsize) # bbox_to_anchor= (-3.0, 1), loc='lower left'
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()

def plotMultiLineChartDifferentLength(x, y, log=False, path=""):
    print("[ANALYSIS] Plotting multiline chart to " + path)
    fig, ax = plt.subplots()
    max_x = 0
    for parameter, marker_arg in zip(y["data"].keys(), mark_cycle):
        ax.plot(x["data"][parameter], (np.log10(y["data"][parameter]) if log else y["data"][parameter]), label=parameter, marker=marker_arg)
        max_x = max(max_x, max(x["data"][parameter]))
    plt.xlabel(x["label"])
    plt.ylabel(("Log " if log else "" )+ y["label"])
    plt.title(y["label"] + " vs " + x["label"])
    plt.xticks(np.arange(0,max_x,int(max_x/10)), fontsize=8) # rotation="45"
    plt.yticks(np.arange(0,140,10), fontsize=5)
    ax.legend(loc="upper center", ncol=5, shadow=True, fontsize='x-small')
    fig.set_size_inches(10, 5)
    # if path and not os.path.isfile(path): plt.savefig(path)
    # else: plt.show()
    plt.savefig(path)
    plt.close()

def plotLineChart(x, y, log=False, path=""):
    print("[ANALYSIS] Plotting line chart to" + path)
    plt.plot(x["data"], [np.log10(x) for x in y["data"].values()] if log else y["data"].values(), marker="p")
    plt.xlabel(x["label"])
    plt.ylabel("Log " if log else "" + y["label"])
    plt.title(y["label"] + " vs " + x["label"], fontsize=12)
    plt.xticks(x["data"], fontsize=6) # rotation="45"
    if path and not os.path.isfile(path): plt.savefig(path)
    else: plt.show()
    plt.close()

def plotMultiColBarChart(x, y, path=""):
    print("[ANALYSIS] Plotting bar chart for " + y["label"] + " vs " + x["label"])
    num_pairs = len(x["data"])
    ind = np.arange(num_pairs)
    width = 0.2
    plt.figure(figsize=(5,3))
    for i, parameter in enumerate(y["data"].keys()):
        if len(y["data"][parameter]) != len(ind):
            plt.bar(ind[:len(y["data"][parameter])]+i*width, y["data"][parameter], label=parameter, width=width, color=color_cycle[i])
        else:
            length = len(y["data"][parameter])
            plt.bar(list(ind[:length-1]+i*width) + list(ind[length-1:]), y["data"][parameter], label=parameter, width=width, color=color_cycle[i])
    # plt.xlabel(x["label"], fontsize='small')
    plt.ylabel(y["label"], fontsize='small')
    if y["log"]:
        plt.yscale('log',base=y["log"],nonpositive='clip')
    if x["log"]:
        plt.xscale('log',base=x["log"],nonpositive='clip')
    plt.grid(b=None, which='major', axis='x', linestyle=':', linewidth=0.7)
    plt.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.7)
    plt.grid(b=None, which='major', axis='y', linestyle='--',linewidth=0.7)
    plt.grid(b=None, which='minor', axis='y', linestyle='--',linewidth=0.7)
    x_ticks_loc = [0.3, 1.3, 2.3, 3.0] # ind+(len(y["data"].keys())*width)/4 # [0.3, 1.3, 2]
    plt.xticks(x_ticks_loc, x["data"], fontsize=6) # rotation="45"
    # plt.legend(ncol=4) # bbox_to_anchor=(0, , 1, 1), mode="expand",
    plt.tight_layout()
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()

def plotMultiColBarChartSubplot(x, y, path=""):
    print("[ANALYSIS] Plotting bar chart for " + y["label"] + " vs " + x["label"])
    num_pairs = len(x["data"])
    ind = np.arange(num_pairs)
    width = 0.2
    # fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(1, 5)
    plotfont = {'fontname':'Times'}
    fig, axs = plt.subplots(1,len(y["data"].keys()),figsize=(22,6))
    for i, param in enumerate(y["data"].keys()):
        for j, parameter in enumerate(y["data"][param].keys()):
            if len(y["data"][param][parameter]) != len(ind):
                axs[i].bar(ind[:len(y["data"][param][parameter])]+j*width, y["data"][param][parameter], label=parameter, width=width, color=color_cycle[j])
            else:
                length = len(y["data"][param][parameter])
                axs[i].bar(list(ind[:length-1]+j*width) + list(ind[length-1:]+j//3*width), y["data"][param][parameter], label=parameter, width=width, color=color_cycle[j])
        axs[i].set_title("{} CUs".format(param), y=0.9, fontsize=16, **plotfont)
        if i == 0:
            axs[i].set_ylabel(y["label"], fontsize=16, **plotfont)
        if y["log"]:
            axs[i].set_yscale('log',base=y["log"],nonpositive='clip')
        if x["log"]:
            axs[i].set_xscale('log',base=x["log"],nonpositive='clip')
        x_ticks_loc = [0.3, 1.3, 2.3, 3.0] # ind+(len(y["data"].keys())*width)/4 # [0.3, 1.3, 2]
        axs[i].set_xticks(ticks=x_ticks_loc) # rotation="45"
        axs[i].set_xticklabels(x["data"], fontsize=15, rotation="20")
        # axs[i].set_yticklabels(axs[i].get_yticks(), fontsize=15)
        
        axs[i].grid(b=None, which='major', axis='x', linestyle=':', linewidth=0.7)
        axs[i].grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.7)
        axs[i].grid(b=None, which='major', axis='y', linestyle='--',linewidth=0.7)
        axs[i].grid(b=None, which='minor', axis='y', linestyle='--',linewidth=0.7)
        # if i == len(y["data"].keys()) - 1:
        #     axs[i].legend(loc='lower left', bbox_to_anchor= (0.0, 1.01), ncol=4, borderaxespad=0, frameon=False)
    # lines, labels = fig.axes[-1].get_legend_handles_labels()
    fig.axes[-1].legend(bbox_to_anchor= (-3.0, 1), loc='lower left', ncol=4, fontsize="x-large")
    # plt.tight_layout()
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()

def plotMultiColBarChartV1(x, y, path=""):
    print("[ANALYSIS] Plotting bar chart for " + y["label"] + " vs " + x["label"])
    num_pairs = len(x["data"])
    ind = np.arange(num_pairs)
    width = 0.2
    plt.figure(figsize=(5,3))
    for i, parameter in enumerate(y["data"].keys()):
        plt.bar(ind+i*width, y["data"][parameter], label=parameter, width=width, color=color_cycle[i])
    # plt.xlabel(x["label"])
    plt.ylabel(y["label"], fontsize=13)
    # plt.title(y["label"] + " vs " + x["label"])
    x_ticks_loc = [0.3, 1.3, 2.3]
    plt.xticks(x_ticks_loc, x["data"], fontsize=13) # rotation="45"
    # plt.xticks(ind+(len(y["data"].keys())*width)/4, x["data"], fontsize=6) # rotation="45"
    plt.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    plt.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    plt.legend()
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()