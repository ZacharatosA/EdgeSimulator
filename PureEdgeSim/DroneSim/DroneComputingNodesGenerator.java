package DroneSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.datacentersmanager.DefaultComputingNodesGenerator;
import com.mechalikh.pureedgesim.locationmanager.MobilityModel;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;

public class DroneComputingNodesGenerator extends DefaultComputingNodesGenerator {

    public DroneComputingNodesGenerator(SimulationManager simulationManager,
            Class<? extends MobilityModel> mobilityModelClass, Class<? extends ComputingNode> computingNodeClass) {
        super(simulationManager, mobilityModelClass, computingNodeClass);
    }

    @Override
    protected void insertEdgeDevice(ComputingNode newDevice) {
        super.insertEdgeDevice(newDevice);
        
        // If the mobility model is DroneMobilityModel, set the drone ID
        if (newDevice.getMobilityModel() instanceof DroneMobilityModel) {
            DroneMobilityModel droneModel = (DroneMobilityModel) newDevice.getMobilityModel();
            // The drone ID is its index in the mistOnlyList
            droneModel.initializeWithId(mistOnlyList.size() - 1);
        }
        // Add support for DroneMobilityModel2
        else if (newDevice.getMobilityModel() instanceof DroneMobilityModel2) {
            DroneMobilityModel2 droneModel = (DroneMobilityModel2) newDevice.getMobilityModel();
            // The drone ID is its index in the mistOnlyList
            droneModel.initializeWithId(mistOnlyList.size() - 1);
            
            // Debug print
            System.out.println("Initialized DroneMobilityModel2 with ID: " + (mistOnlyList.size() - 1));
        }
    }
} 