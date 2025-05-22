#!/bin/bash

# Ορισμός των παραμέτρων
MIN_DEVICES=100
MAX_DEVICES=100
SIMULATION_TIME=10
OFFLOAD_PERCENTAGES=(0 3 5 9 12 18 20 27 34 45 100)

# Βρόχος για κάθε τιμή ποσοστού
for PERCENTAGE in "${OFFLOAD_PERCENTAGES[@]}"
do
    echo "Εκτέλεση προσομοίωσης με ποσοστό offloading: $PERCENTAGE%"
    
    # Δημιουργία νέου φακέλου εξόδου με το επιθυμητό όνομα
    OUTPUT_FOLDER="${MIN_DEVICES}D_${SIMULATION_TIME}min_${PERCENTAGE}%"
    OUTPUT_PATH="PureEdgeSim/ForkliftSim/forklift_output/"
    mkdir -p "$OUTPUT_PATH"
    
    # Αλλαγή των παραμέτρων στο simulation_parameters.properties
    sed -i "s/min_number_of_edge_devices=.*/min_number_of_edge_devices=$MIN_DEVICES/" PureEdgeSim/ForkliftSim/Forklift_settings/simulation_parameters.properties
    sed -i "s/max_number_of_edge_devices=.*/max_number_of_edge_devices=$MAX_DEVICES/" PureEdgeSim/ForkliftSim/Forklift_settings/simulation_parameters.properties
    sed -i "s/simulation_time=.*/simulation_time=$SIMULATION_TIME/" PureEdgeSim/ForkliftSim/Forklift_settings/simulation_parameters.properties
    
    # Αλλαγή του ποσοστού στο ForkliftTaskOrchestrator.java
    sed -i "s/private static final double OFFLOAD_PERCENTAGE = .*/private static final double OFFLOAD_PERCENTAGE = $PERCENTAGE;/" PureEdgeSim/ForkliftSim/ForkliftTaskOrchestrator.java
    
    # Εκτέλεση του mvn clean install
    echo "Εκτέλεση mvn clean install..."
    mvn clean install
    
    # Εκτέλεση του προγράμματος
    echo "Εκτέλεση προγράμματος..."
    mvn exec:java -Dexec.mainClass="ForkliftSim.ForkliftSimulation"
    
    echo "Η προσομοίωση με ποσοστό $PERCENTAGE% ολοκληρώθηκε!"
    echo "----------------------------------------"
done

echo "Όλες οι προσομοιώσεις ολοκληρώθηκαν!" 