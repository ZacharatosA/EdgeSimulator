package ForkliftSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.Task;
import com.mechalikh.pureedgesim.taskorchestrator.DefaultOrchestrator;

import java.util.List;
import java.util.Random;

public class ForkliftTaskOrchestratorD2 extends DefaultOrchestrator {
    private final Random random;
    private static final double OFFLOAD_PROBABILITY = 0.5;

    public ForkliftTaskOrchestratorD2(SimulationManager simulationManager) {
        super(simulationManager);
        this.random = new Random();
        this.algorithmName = "FORKLIFT_OFFLOADING_WITH_PROBABILITY";
        ForkliftLogger.initialize(simulationManager);
    }

    @Override
    public void orchestrate(Task task) {
        // Απόφαση για offload με βάση την πιθανότητα
        if (random.nextDouble() < OFFLOAD_PROBABILITY) {
            assignTaskToNearestEdgeServer(task);
        } else {
            assignTaskToLocalDevice(task);
        }
    }
    
    @Override
    public void resultsReturned(Task task) {
        // Καλούμε την υλοποίηση της μητρικής κλάσης
        super.resultsReturned(task);
        
        // Καταγραφή της ολοκλήρωσης του task με τους χρόνους
        ForkliftLogger.getInstance().logTaskCompletion(task);
    }
    
    protected void assignTaskToLocalDevice(Task task) {
        task.setOffloadingDestination(task.getEdgeDevice());
    }
    
    protected void assignTaskToNearestEdgeServer(Task task) {
        // Βρες τον πιο κοντινό edge server
        ComputingNode nearestEdge = findNearestEdgeServer(task.getEdgeDevice());
        
        if (nearestEdge != ComputingNode.NULL) {
            task.setOffloadingDestination(nearestEdge);
        } else {
            // Αν δεν βρεθεί κοντινός server, εκτέλεσε τοπικά
            assignTaskToLocalDevice(task);
        }
    }
    
    protected ComputingNode findNearestEdgeServer(ComputingNode device) {
        double minDistance = Double.MAX_VALUE;
        ComputingNode nearestEdge = ComputingNode.NULL;
        
        List<ComputingNode> edgeServers = simulationManager.getDataCentersManager()
                                         .getComputingNodesGenerator().getEdgeOnlyList();
        
        for (ComputingNode edge : edgeServers) {
            double distance = device.getMobilityModel().distanceTo(edge);
            if (distance < minDistance) {
                minDistance = distance;
                nearestEdge = edge;
            }
        }
        
        return nearestEdge;
    }
} 