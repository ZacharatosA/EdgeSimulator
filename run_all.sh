#!/bin/bash

# Script for executing the entire workflow of EdgeSimulator
# 1. Run DAVE scripts
# 2. Run d_run_simulation.sh

# Configuration options
RUN_CITY_NETWORK=false  # Set to false to skip the city network creation step

# Colors for messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Current path where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}=== Starting EdgeSimulator workflow ===${NC}"
echo "Current directory: $SCRIPT_DIR"

# Function to execute command with error checking
run_command() {
    echo -e "${YELLOW}=== Executing: $1 ===${NC}"
    if $1; then
        echo -e "${GREEN}√ Successfully completed: $1${NC}"
        return 0
    else
        echo -e "${RED}✗ Error during execution: $1${NC}"
        return 1
    fi
}

# 1. Execute 1_city_network.py
echo -e "\n${YELLOW}Step 1: Creating city network${NC}"
if [ "$RUN_CITY_NETWORK" = true ]; then
    if run_command "python3 DAVE/1_city_network.py"; then
        echo "City network created successfully."
    else
        echo -e "${RED}Error creating city network. Workflow aborted.${NC}"
        exit 1
    fi
else
    echo "Skipping city network creation as RUN_CITY_NETWORK is set to false."
fi

# 2. Execute 2_ProcessNetworkData.py
echo -e "\n${YELLOW}Step 2: Processing network data${NC}"
if run_command "python3 DAVE/2_ProcessNetworkData.py"; then
    echo "Network data processing completed successfully."
else
    echo -e "${RED}Error processing network data. Workflow aborted.${NC}"
    exit 1
fi

# 3. Execute 3_gnb_to_xml.py
echo -e "\n${YELLOW}Step 3: Converting GNB to XML${NC}"
if run_command "python3 DAVE/3_gnb_to_xml.py"; then
    echo "GNB to XML conversion completed successfully."
else
    echo -e "${RED}Error converting GNB to XML. Workflow aborted.${NC}"
    exit 1
fi

# 4. Execute d_run_simulation.sh
echo -e "\n${YELLOW}Step 4: Running simulation${NC}"
cd PureEdgeSim
if run_command "bash d_run_simulation.sh"; then
    cd "$SCRIPT_DIR"  # Return to original directory
    echo "Simulation completed successfully."
else
    cd "$SCRIPT_DIR"  # Return to original directory
    echo -e "${RED}Error during simulation execution.${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== EdgeSimulator workflow completed successfully ===${NC}"
exit 0 