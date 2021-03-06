import json
import numpy as np
import matplotlib.pyplot as plt

## Given a long representing the nanoseconds, returns a string of the time.
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

## Given a long representing the bytes, returns a string of the bytes.
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

# Parse JSON file into dictionary object
def parseJSON(filename):
    with open(filename) as json_file: 
        file = json.load(json_file)
    return file

# Given a flow completion time (FCT) file generated by Netbench, extract
# the flow with the longest FCT to be the job completion time (JCT) of the entire job.
def extract_max_fct_from_file(fct_filename):
    print("[ANALYSIS] Reading {}".format(fct_filename))
    job_finish_time = -float('inf')
    with open(fct_filename, 'r') as f:
        for line in f:
            row = line.split(',')
            job_finish_time = max(job_finish_time, float(row[6]))
    return job_finish_time

# Given a flow completion time (FCT) file generated by Netbench, 
# extract the average FCT.
def extract_avg_fct_from_file(fct_filename):
    print("[ANALYSIS] Reading {}".format(fct_filename))
    total_flow_duration, num_flows = 0, 0
    with open(fct_filename, 'r') as f:
        for line in f:
            row = line.split(',')
            total_flow_duration += float(row[7])
            num_flows += 1
    return total_flow_duration / max(1, num_flows)

# Given a list of numerical "data", compute the stats corresopnding to stat "type"
def computeListStat(type:str, data:list):
    if type == "mean":
        return np.mean(data)
    elif type == "99":
        return np.percentile(data, 99, interpolation='nearest')
    elif type == "50":
        return np.percentile(data, 50, interpolation='nearest')

################################################################################################################
#######################################    PLOTTING FUNCTIONS    ###############################################
################################################################################################################
# Plotting related
color_cycle = ['darkcyan', 'lime', 'darkred','deeppink', 'blueviolet',  "silver", 'black']
mark_cycle = ['d', '+', 's', 'x','v','1', 'p', ".", "o", "^", "<", ">", "1", "2", "3", "8", "P"]
line_styles = ["solid", "dotted", "dashed", "dashdot"]
markersize_arg = 4
legend_fontsize = 8.2

# Ploting function for multi-line chart 
def plotMultiLineChart(x, y, path=""):
    print("[ANALYSIS] Plotting multiline chart to " + path)
    plt.figure(figsize=(3,3))
    for i, (parameter, marker_arg) in enumerate(zip(y["data"].keys(), mark_cycle)):
        plt.plot(x["data"], y["data"][parameter], label=parameter, ls=line_styles[i%len(line_styles)], 
                marker=marker_arg, markerfacecolor='none', markersize=markersize_arg)
    plt.xlabel(x["label"])
    plt.ylabel(y["label"])
    if y["log"]:
        plt.yscale('log',base=y["log"],nonpositive='clip')
    if x["log"]:
        plt.xscale('log',base=x["log"],nonpositive='clip')
    plt.grid(b=None, which='major', axis='x', linestyle=':', linewidth=0.7)
    plt.grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.7)
    plt.grid(b=None, which='major', axis='y', linestyle='--',linewidth=0.7)
    plt.grid(b=None, which='minor', axis='y', linestyle='--',linewidth=0.7)
    plt.xticks(x["data"], fontsize=10) # rotation="45"
    plt.tight_layout()
    # plt.legend(ncol=2, bbox_to_anchor= (0.0, 0.6), loc='lower left', fontsize=legend_fontsize) # bbox_to_anchor= (-3.0, 1), loc='lower left'
    # plt.legend(ncol=1, bbox_to_anchor= (-1, 0), loc='lower left', fontsize=legend_fontsize) # bbox_to_anchor= (-3.0, 1), loc='lower left'
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()

# Plotting function for multiple multi-column charts on the same plot.
def plotMultiColBarChartSubplot(x, y, path=""):
    print("[ANALYSIS] Plotting bar chart for " + y["label"] + " vs " + x["label"])
    num_pairs = len(x["data"])
    ind = np.arange(num_pairs)
    width = 0.2
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
        x_ticks_loc = [0.3, 1.3, 2.3, 3.0]
        axs[i].set_xticks(ticks=x_ticks_loc)
        axs[i].set_xticklabels(x["data"], fontsize=15, rotation="20")
        axs[i].grid(b=None, which='major', axis='x', linestyle=':', linewidth=0.7)
        axs[i].grid(b=None, which='minor', axis='x', linestyle=':', linewidth=0.7)
        axs[i].grid(b=None, which='major', axis='y', linestyle='--',linewidth=0.7)
        axs[i].grid(b=None, which='minor', axis='y', linestyle='--',linewidth=0.7)
    fig.axes[-1].legend(bbox_to_anchor= (-3.0, 1), loc='lower left', ncol=4, fontsize="x-large")
    # plt.tight_layout()
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()

# Plotting function for a single multi-column chart
# Accepts data columns with different lengths
def plotMultiColBarChart(x, y, path=""):
    print("[ANALYSIS] Plotting bar chart for " + y["label"] + " vs " + x["label"])
    num_pairs = len(x["data"])
    ind = np.arange(num_pairs)
    width = 0.2
    plt.figure(figsize=(5,3))
    for i, parameter in enumerate(y["data"].keys()):
        plt.bar(ind+i*width, y["data"][parameter], label=parameter, width=width, color=color_cycle[i])
    plt.ylabel(y["label"], fontsize=13)
    x_ticks_loc = [0.3, 1.3, 2.3]
    plt.xticks(x_ticks_loc, x["data"], fontsize=13) 
    plt.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
    plt.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    plt.legend()
    if path: plt.savefig(path, dpi=200)
    else: plt.show()
    plt.close()