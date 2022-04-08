# Netbench Simulation Input Parameters

## Description

The input parameters for the simulations are specified in the `setup.json` file. These fields are set to be constant for the duration of the simulation modeled by these parameters, unless otherwise specified.

<ul>
    <li><em>SIMULATION_RUNTIME_NS</em>: the duration (in nanoseconds) for which the simulation is run. </li>
    <li><em>TRANSPORT_LAYER</em>: the transport layer protocol used by the Netbench simulator. Options include TCP, DCTCP, Infiniband (still in progress, currently only contains link-level backpressure flow control). </li>
    <li><em>INPUT_QUEUE_BUFFER_SIZE_BYTES</em>: The buffer size (in bytes) of each input queue buffer. This only needs to be specified when using the Infiniband transport protocol.</li>
    <li><em>OUTPUT_QUEUE_BUFFER_SIZE_BYTES</em>: The buffer size (in bytes) of each output queue buffer. </li>
    <li><em>CONGESTION_THRESHOLD_BYTES</em>: The threshold size (in bytes) of the buffer for triggering congestion avoidance in TCP/DCTCP.</li>
    <li><em>NETWORK_LINK_LATENCY_NS</em>: The network link latency (in nanoseconds). </li>
    <li><em>SERVER_LINK_LATENCY_NS</em>: The server link latency (in nanoseconds). This only applies to the switched topologies and do not apply for the CU-centric topologies.</li>
    <li><em>INJECTION_LINK_BW_GBPS</em>: The injection bandwidth (in Gbps). </li>
    <li><em>NUM_VCS</em>: Number of virtual channels for deadlock avoidance. This is used for the Infiniband Transport Protocol. </li>
    <li><em>enable_log_port_queue_state</em>: For enabling the logging of port queue states. Default to False. </li>
    <li><em>enable_log_flow_throughput</em>: For enabling the logging of flow throughput. Default to False.</li>
    <li><em>enable_log_sending_throughput</em>: For enabling the logging of sending throughput. Default to False. </li>
</ul>
