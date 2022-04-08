# Netbench Simulation Input Parameters

## Description

The input parameters for the simulations are specified in the `setup.json` file. These fields are set to be constant for the duration of the simulation modeled by these parameters, unless otherwise specified.

<ul>
    <li>SIMULATION_RUNTIME_NS: the duration (in nanosecond) for which the simulation is run. </li>
    <li>TRANSPORT_LAYER: the transport layer protocol used by the Netbench simulator. Options include TCP, DCTCP, Infiniband (still in progress, currently only contains link-level backpressure flow control). </li>
    <li>INPUT_QUEUE_BUFFER_SIZE_BYTES: The buffer size (in bytes) of each input queue buffer. This only needs to be specified when using the Infiniband transport protocol.</li>
    <li>OUTPUT_QUEUE_BUFFER_SIZE_BYTES: The buffer size (in bytes) of each output queue buffer. </li>
    <li>CONGESTION_THRESHOLD_BYTES: The threshold size (in bytes) of the buffer for triggering congestion avoidance in TCP/DCTCP.</li>
    <li>NETWORK_LINK_LATENCY_NS: The network link latency (in nanoseconds). </li>
    <li>SERVER_LINK_LATENCY_NS: The server link latency (in nanoseconds). This only applies to the switched topologies and do not apply for the CU-centric topologies.</li>
    <li>INJECTION_LINK_BW_GBPS: The injection bandwidth (in Gbps). </li>
    <li>NUM_VCS: Number of virtual channels for deadlock avoidance.</li>
    <li>enable_log_port_queue_state: For enabling the logging of port queue states. Default to False. </li>
    <li>enable_log_flow_throughput: For enabling the logging of flow throughput. Default to False.</li>
    <li>enable_log_sending_throughput: For enabling the logging of sending throughput. Default to False. </li>
</ul>
