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

def plot_throughput(data):
    epoch = [temp['epoch_ms'] for temp in data]
    subtract_first_index(epoch)
    fig, ax = plt.subplots(figsize=(15,5))
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

                ax.plot(epoch, writes, label = "Writes {}/{}".format(x,y))
                ax.plot(epoch, reads, label = "Reads {}/{}".format(x,y))
    fig.legend()
    # Epoch in seconds
    ms_to_string = lambda time: f"{int(time / 1000 / 60)}:{int(time / 1000) % 60:02d}"
    epoch_formatted = list(map(ms_to_string, epoch))
    ax.set_xlabel("runtime (minute:seconds)")  # add X-axis label
    ax.set_xticks(epoch, epoch_formatted)
    ax.locator_params(tight=True, nbins=10)

    ax.set_ylabel("MiB/s (I/0)")  # add Y-axis label
    label=' | '.join(sys.argv[1].split('/')[-2:])
    ax.set_title(f"Haura - {label}")  # add title
    fig.savefig(f"{sys.argv[1]}/plot.svg")

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
        1: "#009E73",
        2: "#F0E442",
        3: "#0072B2",
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
        group_1 = [n[1] for n in keys[:2000]]
        group_2 = [n[1] for n in keys[2000:2300]]
        group_3 = [n[1] for n in keys[2300:2320]]
    
        # Reshape to matrix and fill with zeros if necessary
        group_1 = np.concatenate((np.array(group_1), np.zeros(2025 - len(group_1)))).reshape((45,45))
        group_2 = np.concatenate((np.array(group_2), np.zeros(324 - len(group_2)))).reshape((18,18))
        group_3 = np.concatenate((np.array(group_3), np.zeros(25 - len(group_3)))).reshape((5,5))
    
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
            im.set_clim(0, num_tier)
            subax.yaxis.set_ticks([])
            subax.xaxis.set_ticks([])
        #divider = make_axes_locatable(subax)
        #cax = divider.append_axes("right", size="5%", pad=0.05) 
        #fig.colorbar(im, cax=cax)
        fmt = matplotlib.ticker.FuncFormatter(lambda x, pos: labels[x])
        ticks = [0, 1, 2, 3]
        fig.colorbar(cm.ScalarMappable(cmap=cmap, norm=mat_col.NoNorm()), format=fmt, ticks=ticks)

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
    ax.plot(mean_group_vals[0], color='#E69F00', label="Seldomly Accessed Group");
    ax.plot(mean_group_vals[1], color='#56B4E9', label="Occassionally Accessed");
    ax.plot(mean_group_vals[2], color='#D55E00', label="Often Accessed");
    # we might want to pick the actual timestamps for this
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Mean object tier")
    ax.set_title("Mean tier of all object groups over time")
    ax.set_ylim((1,3))
    pls_no_cut_off = ax.legend(bbox_to_anchor=(1.0,1.0), loc="upper left")
    fig.savefig(f"{sys.argv[1]}/plot_timestep_means.svg", bbox_extra_artists=(pls_no_cut_off,), bbox_inches='tight')

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


print("reading intiital data")
fs = open(f"{sys.argv[1]}/betree-metrics.jsonl", 'r')
# print("{}".format(data))
data = read_jsonl(fs)
fs.close()

# Plot actions
plot_throughput(data)
#plot_latency(data)
plot_object_distribution()
