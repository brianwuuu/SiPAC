# SiPAC Evaluation

This repository contains the source codes needed to generate the analysis results for the SiPAC work. Here we describe the two main analysis files:

## Architecture Evaluations

To obtain evaluation results on the component count, run

```
python3 component_count_analysis.py
```

## Simulation Results

To obtain simulation results for the topology-collective combinations, run

```
python3 analysis.py -e <experiment_id> -c <collective_type>
```

where experiment_id =

<ul>
    <li> <em>basic</em>: results for basic collective communication (primitive or allreduce).</li>
    <li> <em>message_size</em>: results for basic collective communication (primitive or allreduce) across different message sizes. </li>
    <li> <em>topology_size</em>: results for basic collective communication (primitive or allreduce) across different topology sizes.</li>
    <li> <em>hybrid_parallel</em>: results for hybrid collective communication across different network bandwidths.</li>
    <li> <em>heatmap</em>: results for generating the traffic heatmaps for different collective communication patterns.</li>
</ul>

and collective_type =

<ul>
    <li> <em>primitive</em>: for primitive collective communication.</li>
    <li> <em>allreduce</em>: for allreduce collective communication. </li>
    <li> <em>hybrid_parallel</em>: for hybrid parallel collective communication.</li>
</ul>
