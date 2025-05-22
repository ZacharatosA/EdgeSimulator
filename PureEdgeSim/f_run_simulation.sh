#!/bin/bash

# Ορισμός των παραμέτρων που θέλουμε να αλλάξουμε
MIN_DEVICES=100
MAX_DEVICES=100
OFFLOAD_PERCENTAGE=85
SIMULATION_TIME=10


# Αλλαγή των παραμέτρων στο simulation_parameters.properties
sed -i "s/min_number_of_edge_devices=.*/min_number_of_edge_devices=$MIN_DEVICES/" ForkliftSim/Forklift_settings/simulation_parameters.properties
sed -i "s/max_number_of_edge_devices=.*/max_number_of_edge_devices=$MAX_DEVICES/" ForkliftSim/Forklift_settings/simulation_parameters.properties
sed -i "s/simulation_time=.*/simulation_time=$SIMULATION_TIME/" ForkliftSim/Forklift_settings/simulation_parameters.properties

# Αλλαγή του ποσοστού στο ForkliftTaskOrchestrator.java
sed -i "s/private static final double OFFLOAD_PERCENTAGE = .*/private static final double OFFLOAD_PERCENTAGE = $OFFLOAD_PERCENTAGE;/" ForkliftSim/ForkliftTaskOrchestrator.java

# Εκτέλεση του mvn clean install
echo "Εκτέλεση mvn clean install..."
mvn clean install

# Εκτέλεση του προγράμματος με αυξημένη μνήμη και βελτιστοποιημένες ρυθμίσεις
echo "Εκτέλεση προγράμματος..."
export MAVEN_OPTS="-Xmx8g -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+UseStringDeduplication -XX:+OptimizeStringConcat -XX:+UseCompressedOops -XX:+UseCompressedClassPointers"
mvn exec:java -Dexec.mainClass="ForkliftSim.ForkliftSimulation"

# Έλεγχος αν η προσομοίωση ολοκληρώθηκε επιτυχώς
if [ $? -eq 0 ]; then
    echo "Η προσομοίωση ολοκληρώθηκε επιτυχώς!"
    
    # Βρίσκουμε το τελευταίο φάκελο που δημιουργήθηκε
    LATEST_FOLDER=$(ls -td ForkliftSim/Forklift_output/*/ | head -1)
    LATEST_FOLDER_NAME=$(basename "$LATEST_FOLDER")
    
    # Περιμένουμε λίγο για να εξασφαλιστεί ότι όλα τα αρχεία έχουν γραφτεί
    sleep 10
    
    # Εκτέλεση του LogAnalysis.py
    echo "Εκτέλεση LogAnalysis.py..."
    python3 ForkliftSim/LogAnalysis.py "$LATEST_FOLDER_NAME"
    
    if [ $? -eq 0 ]; then
        echo "Το LogAnalysis.py εκτελέστηκε επιτυχώς!"
    else
        echo "Σφάλμα κατά την εκτέλεση του LogAnalysis.py"
    fi
else
    echo "Η προσομοίωση απέτυχε!"
fi

echo "Η διαδικασία ολοκληρώθηκε!" 