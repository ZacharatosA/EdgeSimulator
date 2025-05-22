#!/bin/bash

# Ορισμός των παραμέτρων
NUM_DEVICES=20
SIMULATION_TIME=10
# Map and coverage parameters
MAP_LENGTH=2500
MAP_WIDTH=2500
EDGE_DEVICES_RANGE=20
EDGE_DATACENTERS_COVERAGE=800
# Πιθανότητες offloading
OFFLOAD_PROBS=(0.03 0.05 0.09 0.12 0.18 0.20 0.27 0.34 0.45 100)

# Βρόχος για κάθε τιμή πιθανότητας
for PROB in "${OFFLOAD_PROBS[@]}"
do
    echo "Εκτέλεση προσομοίωσης με πιθανότητα offloading: $PROB"
    
    # Δημιουργία νέου φακέλου εξόδου με το επιθυμητό όνομα
    OUTPUT_FOLDER="${MIN_DEVICES}D_${SIMULATION_TIME}min_${PROB}%"
    OUTPUT_PATH="DroneSim/Drone_output/"
    mkdir -p "$OUTPUT_PATH"
    
    # Αλλαγή των παραμέτρων στο simulation_parameters.properties
    sed -i "/^min_number_of_edge_devices=/s/min_number_of_edge_devices=.*/min_number_of_edge_devices=$NUM_DEVICES/" DroneSim/Drone_settings/simulation_parameters.properties
    sed -i "/^max_number_of_edge_devices=/s/max_number_of_edge_devices=.*/max_number_of_edge_devices=$NUM_DEVICES/" DroneSim/Drone_settings/simulation_parameters.properties
    sed -i "/^simulation_time=/s/simulation_time=.*/simulation_time=$SIMULATION_TIME/" DroneSim/Drone_settings/simulation_parameters.properties
    # Map and coverage parameters
    sed -i "/^length=/s/length=.*/length=$MAP_LENGTH/" DroneSim/Drone_settings/simulation_parameters.properties
    sed -i "/^width=/s/width=.*/width=$MAP_WIDTH/" DroneSim/Drone_settings/simulation_parameters.properties
    sed -i "/^edge_devices_range=/s/edge_devices_range=.*/edge_devices_range=$EDGE_DEVICES_RANGE/" DroneSim/Drone_settings/simulation_parameters.properties
    sed -i "/^edge_datacenters_coverage=/s/edge_datacenters_coverage=.*/edge_datacenters_coverage=$EDGE_DATACENTERS_COVERAGE/" DroneSim/Drone_settings/simulation_parameters.properties
    
    # Αλλαγή της πιθανότητας στο DroneTaskOrchestratorD2.java
    sed -i "s/private static final double OFFLOAD_PROBABILITY = .*/private static final double OFFLOAD_PROBABILITY = $PROB;/" DroneSim/DroneTaskOrchestratorD2.java
    
    # Εκτέλεση του mvn clean install
    echo "Εκτέλεση mvn clean install..."
    mvn clean install
    
    # Εκτέλεση του προγράμματος
    echo "Εκτέλεση προγράμματος..."
    mvn exec:java -Dexec.mainClass="DroneSim.DroneSimulation"
    
    echo "Η προσομοίωση με πιθανότητα $PROB ολοκληρώθηκε!"
    echo "----------------------------------------"
done

echo "Όλες οι προσομοιώσεις ολοκληρώθηκαν!" 