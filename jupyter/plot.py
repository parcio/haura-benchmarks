import json
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
# %matplotlib inline

# Constants
BLOCK_SIZE = 4096
EPOCH_MS=500
SEC_MS=1000

from matplotlib import pyplot as plt

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

data = []

if len(sys.argv) < 2:
    print("Please specify an input run directory. If you already completed benchmarks they can be found under `results/*`.")
    exit(1)

fs = open(f"{sys.argv[1]}/betree-metrics.jsonl", 'r')

line_number = 0
while True:
    line_number += 1
    # Get next line from file
    line = fs.readline()
    # if line is empty
    # end of file is reached
    if not line:
        break
    json_object = json.loads(line)
    data.append(json_object);
    
# print("{}".format(data))
  
fs.close()

df = pd.DataFrame(data)

plot_throughput(data)
plot_latency(data)
