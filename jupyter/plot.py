#! /bin/env python
import json
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.cm as cm
import matplotlib.colors as mat_col
import matplotlib
    
# Constants
BLOCK_SIZE = 4096
EPOCH_MS=500
SEC_MS=1000


# For color reference of "Wong" color scheme see:
# https://davidmathlogic.com/colorblind/#%23000000-%23E69F00-%2356B4E9-%23009E73-%23F0E442-%230072B2-%23D55E00-%23CC79A7
GREEN='#009E73'
YELLOW='#F0E442'
BLUE='#0072B2'
LIGHT_BLUE='#56B4E9'
RED='#D55E00'
ORANGE='#E69F00'

def subtract_last_index(array):
    last_val = 0
    for index, value in enumerate(array):
        array[index] = value - last_val
        last_val = value
    array[0] = 0

def subtract_first_index(array):
    first_val = array[0]
    for index, value in enumerate(array):
        array[index] = value -first_val

def num_to_name(tier):
    match tier:
        case 0:
            return 'Fastest'
        case 1:
            return 'Fast'
        case 2:
            return 'Slow'
        case 3:
            return 'Slowest'
        case _:
            return '???'

def plot_throughput(data):
    epoch = [temp['epoch_ms'] for temp in data]
    subtract_first_index(epoch)
    fig, axs = plt.subplots(4, 1, figsize=(16,8))
    colors=[GREEN, YELLOW, BLUE, RED]
    markers=['o', '^', '']
    for x in range(4):
        for y in range(4):
            writes = np.array([])
            reads = np.array([])
            for temp in data:
                if x >= len(temp['storage']['tiers']) or y >= len(temp['storage']['tiers'][x]['vdevs']):
                    continue

                writes = np.append(writes, temp['storage']['tiers'][x]['vdevs'][y]['written'])
                reads = np.append(reads, temp['storage']['tiers'][x]['vdevs'][y]['read'])

            if len(writes) > 0:
                subtract_last_index(writes)
                subtract_last_index(reads)

                # convert to MiB from Blocks
                # NOTE: We assume here a block size of 4096 bytes as this is the default haura block size
                # if you change this you'll need to modify this here too.
                writes = writes * BLOCK_SIZE / 1024 / 1024 * (SEC_MS / EPOCH_MS)
                reads = reads * BLOCK_SIZE / 1024 / 1024 * (SEC_MS / EPOCH_MS)
                axs[x].plot(epoch, reads, label = 'Read', linestyle='dotted', color=GREEN)
                axs[x].plot(epoch, writes, label = 'Written', color=BLUE)

            ms_to_string = lambda time: f"{int(time / 1000 / 60)}:{int(time / 1000) % 60:02d}"
            epoch_formatted = list(map(ms_to_string, epoch))
            axs[x].set_xlabel("runtime (minute:seconds)")  # add X-axis label
            axs[x].set_xticks(epoch, epoch_formatted)
            axs[x].locator_params(tight=True, nbins=10)

            axs[x].set_ylabel(f"{num_to_name(x)}\nMiB/s (I/0)")  # add Y-axis label
            label=' | '.join(sys.argv[1].split('/')[-2:])
    fig.legend(loc="center right")
    # Epoch in seconds
    fig.suptitle(f"Haura - {label}", y=0.98)  # add title
    fig.savefig(f"{sys.argv[1]}/plot_write.svg")
    for x in range(4):
        lines = axs[x].get_lines()
        if len(lines) > 0:
            lines[0].set_linestyle('solid')
            lines[0].zorder = 2.0
            lines[1].set_linestyle('dotted')
            lines[1].zorder = 2.1
    fig.legend(loc="center right")
    fig.savefig(f"{sys.argv[1]}/plot_read.svg")

def plot_latency(data):
    epoch = [temp['epoch_ms'] for temp in data]
    subtract_first_index(epoch)
    fig, ax = plt.subplots(figsize=(15,5))
    for x in range(4):
        for y in range(4):
            lat = np.array([])
            for temp in data:
                if x >= len(temp['storage']['tiers']) or y >= len(temp['storage']['tiers'][x]['vdevs']):
                    continue

                lat = np.append(lat, temp['storage']['tiers'][x]['vdevs'][y]['read_latency'])

            if len(lat) > 0:
                lat = lat / 100000
                lat.astype(int)
                lat = np.array([np.nan if elem == 0 else elem for elem in lat])


                ax.plot(epoch, lat, label = "Average Latency {}/{}".format(x,y))
    fig.legend()
    # Epoch in seconds
    ms_to_string = lambda time: f"{int(time / 1000 / 60)}:{int(time / 1000) % 60:02d}"
    epoch_formatted = list(map(ms_to_string, epoch))
    ax.set_xlabel("runtime (minute:seconds)")  # add X-axis label
    ax.set_xticks(epoch, epoch_formatted)
    ax.locator_params(tight=True, nbins=10)
    ax.set_ylabel("Read Latency in ms")  # add Y-axis label
    label=' | '.join(sys.argv[1].split('/')[-2:])
    ax.set_title(f"Haura - {label}")  # add title
    fig.savefig(f"{sys.argv[1]}/plot_latency.svg")

# Access string subslice and first tuple member
def sort_by_o_id(key):
    return int(key[0][2:])

def plot_object_distribution():
    fs = open(f"{sys.argv[1]}/tier_state.jsonl", 'r')
    data = read_jsonl(fs)
    fs.close()
    colors = {
        0: "white",
        1: GREEN,
        2: YELLOW,
        3: BLUE,
    }    
    cmap = mat_col.ListedColormap([colors[x] for x in colors.keys()])
    labels = np.array(["Not present", "Fastest", "Fast", "Slow"])
    num_ts = 0
    # three groups fixed
    mean_group_vals = [[], [], []]
    for current_timestep in data:
        # Read all names and order
        # Iterate over each tier and add keys to known keys
        keys = []  # Vec<(key, num_tier)>
        num_tier = 1
        for tier in current_timestep:
            for object in tier["files"]:
                keys.append((object, num_tier))
            num_tier += 1
    
        keys.sort(key=sort_by_o_id)
    
        # old boundaries update when needed
        # seldom accessed 1-2000 (45x45)
        # barely accessed 2001-2300 (18x18)
        # often accessed 2301-2320 (5x5)
        group_1 = [n[1] for n in keys[:4030]]
        group_2 = [n[1] for n in keys[4030:4678]]
        group_3 = [n[1] for n in keys[4678:4728]]

        # Reshape to matrix and fill with zeros if necessary
        group_1 = np.concatenate((np.array(group_1), np.zeros(4096 - len(group_1)))).reshape((64,64))
        group_2 = np.concatenate((np.array(group_2), np.zeros(676 - len(group_2)))).reshape((26,26))
        group_3 = np.concatenate((np.array(group_3), np.zeros(64 - len(group_3)))).reshape((8,8))
    
        num_group = 0
        fig, axs = plt.subplots(1, 4, figsize=(20,5))
        for group in [group_1, group_2, group_3]:
            subax = axs[num_group]
            mean = group[group > 0].mean()
            mean_group_vals[num_group].append(mean)
            subax.set_title(f"Object mean level: {mean}")
            subax.tick_params(color="white")
            num_group += 1
            im = subax.imshow(group, cmap=cmap)
            im.set_clim(0, 3)
            subax.yaxis.set_ticks([])
            subax.xaxis.set_ticks([])
        #divider = make_axes_locatable(subax)
        #cax = divider.append_axes("right", size="5%", pad=0.05) 
        #fig.colorbar(im, cax=cax)
        fmt = matplotlib.ticker.FuncFormatter(lambda x, pos: labels[x])
        ticks = [0, 1, 2, 3]
        fig.colorbar(cm.ScalarMappable(cmap=cmap, norm=mat_col.NoNorm()), format=fmt, ticks=ticks)

        # Plot response times if available
        if 'reqs' in current_timestep[0]:
            times = []
            num_tiers = 0
            for tier in current_timestep:
                num_tiers += 1
                resp_times = 0;
                total = 0;
                for o_id in tier["reqs"]:
                    resps = tier["reqs"][f"{o_id}"]
                    size = tier["files"][f"{o_id}"][1]
                    for resp in resps:
                        total += 1
                        resp_times += resp["response_time"]["nanos"] / size
                if total != 0:
                    times.append(resp_times / total)
                else:
                    times.append(0)
            x_ticks = np.arange(0, num_tiers)
            width = 0.35
            # convert from nanos to millis
            axs[3].bar(x_ticks, np.array(times) / 1000000, width, label='Access latency', hatch=['.', '+', '/'], color='white', edgecolor='black')
            axs[3].set_title('Mean access latency for timestep')
            axs[3].set_ylabel('Mean latency in ms')
            #axs[3].set_ylim(0, 100)
            axs[3].set_xticks(x_ticks, labels=["Fastest", "Fast", "Slow"])

        fig.savefig(f"{sys.argv[1]}/plot_timestep_{num_ts:0>3}.png")
        matplotlib.pyplot.close(fig)
        num_ts += 1

    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(mean_group_vals[0], color=ORANGE, label="Seldomly Accessed Group", marker="o", markevery=10);
    ax.plot(mean_group_vals[1], color=LIGHT_BLUE, label="Occassionally Accessed", marker="s", markevery=10);
    ax.plot(mean_group_vals[2], color=RED, label="Often Accessed", marker="^", markevery=10);
    # we might want to pick the actual timestamps for this
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Mean object tier")
    ax.set_title("Mean tier of all object groups over time")
    ax.set_ylim((1,3))
    pls_no_cut_off = ax.legend(bbox_to_anchor=(1.0,1.0), loc="upper left")
    fig.savefig(f"{sys.argv[1]}/plot_timestep_means.svg", bbox_extra_artists=(pls_no_cut_off,), bbox_inches='tight')

def plot_tier_usage(data):
    fig, axs = plt.subplots(4, 1, figsize=(9,13))

    # 0 - 3; Fastest - Slowest
    free = [[], [], [], []]
    total = [[], [], [], []]
    # Map each timestep to an individual
    for ts in data:
        tier = 0
        for stat in ts["usage"]:
            free[tier].append(stat["free"])
            total[tier].append(stat["total"])
            tier += 1

    tier = 0
    for fr in free:
        axs[tier].plot((np.array(total[tier]) - np.array(fr)) * 4096 / 1024 / 1024 / 1024, label="Used", marker="o", markevery=200, color=BLUE)
        axs[tier].plot(np.array(total[tier]) * 4096 / 1024 / 1024 / 1024, label="Total", marker="^", markevery=200, color=GREEN)
        axs[tier].set_ylim(bottom=0)
        axs[tier].legend(loc="upper center")
        axs[tier].set_ylabel(f"{num_to_name(tier)}\nCapacity in GiB")
        tier += 1

    fig.savefig(f"{sys.argv[1]}/tier_usage.svg")

# TODO: Adjust bucket sizes
def size_buckets(byte):
    if byte <= 64000:
        return 64000
    elif byte <= 256000:
        return 256000
    elif byte <= 1000000:
        return 1000000
    elif byte <= 4000000:
        return 4000000
    else:
        return 1000000000

def bytes_to_lexical(byte):
    if byte >= 1000000:
        return f"{byte/1000/1000}MB"
    return f"{byte/1000}KB"

def plot_filesystem_test():
    dat = pd.read_csv(f"{sys.argv[1]}/filesystem_measurements.csv")
    # groups
    fig, axs = plt.subplots(2,3, figsize=(15,5))
    min_read = 99999999999999999
    min_write = 99999999999999999
    max_read = 0
    max_write = 0
    for n in range(3):
        sizes = dat[dat['group'] == n]['size'].to_numpy()
        reads = {}
        reads_raw = dat[dat['group'] == n]['read_latency_ns'].to_numpy()
        writes = {}
        writes_raw = dat[dat['group'] == n]['write_latency_ns'].to_numpy()
        for (idx, size) in enumerate(sizes):
            if size_buckets(size) not in reads:
                reads[size_buckets(size)] = []
            reads[size_buckets(size)].append(reads_raw[idx])
            if size_buckets(size) not in writes:
                writes[size_buckets(size)] = []
            writes[size_buckets(size)].append(writes_raw[idx])

        sorted_sizes = list(reads)
        sorted_sizes.sort()
        labels = []
        reads_plot = []
        writes_plot = []
        for size in sorted_sizes:
            labels.append(bytes_to_lexical(size))
            a = np.array(reads[size]) / 1000
            min_read = min(min_read, a.min())
            max_read = max(max_read, a.max())
            reads_plot.append(a)
            b = np.array(writes[size]) / 1000
            min_write = min(min_write, b.min())
            max_write = max(max_write, b.max())
            writes_plot.append(b)
        axs[0][n].boxplot(reads_plot, vert=True, labels=labels)
        axs[0][n].set_yscale('log')
        match n:
            case 0:
                axs[0][n].set_title("Seldomly Accessed")
            case 1:
                axs[0][n].set_title("Occassionally Accessed")
            case 2:
                axs[0][n].set_title("Often Accessed")
        axs[0][n].set_ylabel("Read latency (μs)")
        axs[1][n].boxplot(writes_plot, vert=True, labels=labels)
        axs[1][n].set_yscale('log')
        axs[1][n].set_ylabel("Write latency (μs)")

    for n in range(3):
        axs[0][n].set_ylim(min(min_read, min_write),max_read + 10000000)
        axs[1][n].set_ylim(min(min_read, min_write),max_write + 10000000)

    fig.savefig(f"{sys.argv[1]}/filesystem_comp.svg")


def read_jsonl(file):
    data = []
    while True:
        # Get next line from file
        line = file.readline()
        # if line is empty
        # end of file is reached
        if not line:
            break
        json_object = json.loads(line)
        data.append(json_object);
    return data

if len(sys.argv) < 2:
    print("Please specify an input run directory. If you already completed benchmarks they can be found under `results/*`.")
    exit(1)


fs = open(f"{sys.argv[1]}/betree-metrics.jsonl", 'r')
# print("{}".format(data))
data = read_jsonl(fs)
fs.close()

# Plot actions
plot_throughput(data)
plot_tier_usage(data)
#plot_latency(data)
plot_object_distribution()
plot_filesystem_test()
