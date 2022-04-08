# Silicon Photonic Accelerated Compute Cluster (SiPAC)

This repository contains the source codes needed to reproduce results for the SiPAC architecture evaluation.

## Getting Started

### Software Dependencies

#### 1. Netbench (https://github.com/brianwuuu/netbench)

The origina1l Netbench simulator can be found in (https://github.com/ndal-eth/netbench). We have modified Netbench to include functionalities that enable the accurate evaluation of the SiPAC architecture. Please follow the steps in building Netbench.

#### 2. Python 3

Python dependencies: numpy, math, matplotlib.

## Installation

```bash
git clone https://github.com/brianwuuu/SiPAC.git
```

## Directory Overview.

Here is an overview of each directory. For more detailed descriptions, please read the README in each sub-directory.

<ol>
    <li><strong>analysis</strong></li>
    This directory contains scripts used to generate the analysis results.
    <li><strong>input_parameters</strong></li>
    This directory contains files that are read as input when generating simulation parameters for Netbench.
    <li><strong>network_topologies</strong></li>
    This directory contains files in which various topology models are defined.
    <li><strong>traffic</strong></li>
    This directory contains files in which the traffic patterns for various collective operation communication are modeled.
</ol>

## Simulation Setup

Before setting up the simulations, first set the environment variable $NETBENCH_HOME to point to the directory where Netbench is located. One option is to use

```
export NETBENCH_HOME={netbench_directory}.
```

The root directory contains the main sript (generate_experiment.py) to generate the necessary experiment files for running the Netbench simulations in our experiments. To use this script, run

```
python3 generate_experiments.py -e <exp_id>
```

where exp_id =

<ol>
    <li> Experiment for primitive collective communication.</li>
    <li> Experiment for allreduce collective communication. </li>
    <li> Experiment for hybrid parallel collective communication.</li>
</ol>

The network parameters can be modified using the JSON file provided in the input_parameter directory. Users can also manually change the experiment setting in this script by modifying the setup in each experiment function.

## Running Netbench Simulations

The `generate_experiment.py` file outputs the necessary parameter files needed by Netbench to run the simulations. To run the actual simulations, navigate to the `execution` directory where the bash files containing the execution commands are located. Run

```
./automated_execution_<experiment_name>.sh
```

where **experiment_name** corresponds to the name of the experiments as described in the Simulation Setup section.

To run the experiments in the background, one can also use

```
nohup ./automated_execution_<experiment_name>.sh > ../logs/<experiment_name> 2>&1 &
```

where `logs` is the directory containing the running output of the Netbench simulation.

## Contributing

For major changes or concerns, please open an issue for discussion.
