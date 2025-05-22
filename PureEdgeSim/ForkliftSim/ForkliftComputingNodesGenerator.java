package ForkliftSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.datacentersmanager.DefaultComputingNodesGenerator;
import com.mechalikh.pureedgesim.locationmanager.MobilityModel;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;

public class ForkliftComputingNodesGenerator extends DefaultComputingNodesGenerator {

    public ForkliftComputingNodesGenerator(SimulationManager simulationManager,
            Class<? extends MobilityModel> mobilityModelClass, Class<? extends ComputingNode> computingNodeClass) {
        super(simulationManager, mobilityModelClass, computingNodeClass);
    }

    @Override
    protected void insertEdgeDevice(ComputingNode newDevice) {
        super.insertEdgeDevice(newDevice);
        
        // Αν το mobility model είναι ForkliftMobilityModel, ορίζουμε το ID του forklift
        if (newDevice.getMobilityModel() instanceof ForkliftMobilityModel) {
            ForkliftMobilityModel forkliftModel = (ForkliftMobilityModel) newDevice.getMobilityModel();
            // Το ID του forklift είναι ο δείκτης του στη λίστα mistOnlyList
            forkliftModel.initializeWithId(mistOnlyList.size() - 1);
        }
    }
} 