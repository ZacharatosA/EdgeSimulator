# PureEdgeSim KPIs Explanation

| KPI | Explanation |
|-----|-------------|
| **Task Execution Metrics** | |
| Total tasks execution time | The total time spent executing all tasks (in seconds) |
| Average task execution time | The average time taken to execute a single task (in seconds) |
| Total waiting time | The total time tasks spent waiting before execution started (in seconds) |
| Average task waiting time | The average time each task spent waiting before execution (in seconds) |
| Tasks successfully executed | Percentage of tasks that were successfully executed out of all sent tasks |
| **Task Failure Metrics** | |
| Not executed due to resource unavailability | Percentage of tasks that failed because there were no resources available |
| Executed but failed due to high delay | Percentage of tasks that were executed but failed because they took too long |
| Tasks execution results not returned due to devices death | Percentage of tasks whose results were lost because the device ran out of battery |
| Tasks execution results not returned due to devices mobility | Percentage of tasks whose results were lost because devices moved out of range |
| **Task Distribution Metrics** | |
| Tasks executed on Cloud | Number of tasks executed in the Cloud and how many succeeded |
| Tasks executed on Edge | Number of tasks executed on Edge servers and how many succeeded |
| Tasks executed on Mist (Drone) | Number of tasks executed locally on devices/drones and how many succeeded |
| **Network Metrics** | |
| Network usage | Total time spent transferring data across all networks (in seconds) |
| WAN usage | Time spent using Wide Area Network and percentage of total usage |
| MAN usage | Time spent using Metropolitan Area Network and percentage of total usage |
| LAN usage | Time spent using Local Area Network and percentage of total usage |
| Total traffic | The total amount of data transferred across all networks (in MBytes) |
| Average transfer speed | The average data transfer speed across all networks (in Mbps) |
| **Resource Utilization Metrics** | |
| Average CPU utilization | The average CPU usage across all computing nodes (as a percentage) |
| Average CPU utilization per level | The average CPU usage broken down by Cloud, Edge, and Mist/Drone levels |
| **Energy Metrics** | |
| Energy consumption | Total energy used by all systems in the simulation (in Watt-hours) |
| Average energy per data center/device | Average energy consumed per computing node (in Watt-hours) |
| Average energy per task | Average energy consumed to process each task (in Watt-hours) |
| Energy consumption per level | Energy used by Cloud, Edge, and Mist/Drone levels (in Watt-hours) |
| Static vs Dynamic energy consumption | Breakdown of energy used when idle (static) vs. when processing (dynamic) |
| Energy consumption per network | Energy used by different network types (WAN, MAN, LAN) |
| Energy consumption per technology | Energy used by different connection technologies (WiFi, Cellular, Ethernet) |
| **Device Health Metrics** | |
| Dead edge devices due to battery drain | Number of devices that ran out of battery during simulation |
| Average remaining power | Average remaining battery power in devices that are still operational |
| **Simulation Parameters** | |
| Simulation time | Duration of the simulation (in minutes) |
| Number of Edge Devices | Number of edge devices used in the simulation |
| Offload Probability | Probability that a task will be offloaded instead of processed locally |
| Map dimensions | Size of the simulation area (length × width in meters) |
| Edge devices range | Maximum distance at which devices can connect to each other (in meters) |
| Edge datacenters coverage | Range of coverage for edge data centers (in meters) | 