#!/bin/bash

# Define parameters we want to change
NUM_DEVICES=6
OFFLOAD_PROB=0.5
SIMULATION_TIME=20
# Map and coverage parameters
MAP_LENGTH=2500
MAP_WIDTH=2500
EDGE_DEVICES_RANGE=20
EDGE_DATACENTERS_COVERAGE=800


# Change parameters in simulation_parameters.properties
sed -i "/^min_number_of_edge_devices=/s/min_number_of_edge_devices=.*/min_number_of_edge_devices=$NUM_DEVICES/" DroneSim/Drone_settings/simulation_parameters.properties
sed -i "/^max_number_of_edge_devices=/s/max_number_of_edge_devices=.*/max_number_of_edge_devices=$NUM_DEVICES/" DroneSim/Drone_settings/simulation_parameters.properties
sed -i "/^simulation_time=/s/simulation_time=.*/simulation_time=$SIMULATION_TIME/" DroneSim/Drone_settings/simulation_parameters.properties
# Map and coverage parameters
sed -i "/^length=/s/length=.*/length=$MAP_LENGTH/" DroneSim/Drone_settings/simulation_parameters.properties
sed -i "/^width=/s/width=.*/width=$MAP_WIDTH/" DroneSim/Drone_settings/simulation_parameters.properties
sed -i "/^edge_devices_range=/s/edge_devices_range=.*/edge_devices_range=$EDGE_DEVICES_RANGE/" DroneSim/Drone_settings/simulation_parameters.properties
sed -i "/^edge_datacenters_coverage=/s/edge_datacenters_coverage=.*/edge_datacenters_coverage=$EDGE_DATACENTERS_COVERAGE/" DroneSim/Drone_settings/simulation_parameters.properties


# Change the offload probability in DroneTaskOrchestratorD2.java
sed -i "s/private static final double OFFLOAD_PROBABILITY = .*/private static final double OFFLOAD_PROBABILITY = $OFFLOAD_PROB;/" DroneSim/DroneTaskOrchestratorD2.java

# Execute mvn clean install
echo "Executing mvn clean install..."
mvn clean install

# Execute program
echo "Executing program..."
mvn exec:java -Dexec.mainClass="DroneSim.DroneSimulation"

echo "Simulation completed!" 