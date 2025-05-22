package DroneSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.Task;
import com.mechalikh.pureedgesim.taskorchestrator.DefaultOrchestrator;

import java.util.List;
import java.util.Random;

public class DroneTaskOrchestratorD2 extends DefaultOrchestrator {
    private final Random random;
    private static final double OFFLOAD_PROBABILITY = 0.5;

    public DroneTaskOrchestratorD2(SimulationManager simulationManager) {
        super(simulationManager);
        this.random = new Random();
        this.algorithmName = "DRONE_OFFLOADING_WITH_PROBABILITY";
        DroneLogger.initialize(simulationManager);
    }

    @Override
    public void orchestrate(Task task) {
        // Decision to offload based on probability
        if (random.nextDouble() < OFFLOAD_PROBABILITY) {
            assignTaskToNearestEdgeServer(task);
        } else {
            assignTaskToLocalDevice(task);
        }
    }
    
    @Override
    public void resultsReturned(Task task) {
        // Call parent class implementation
        super.resultsReturned(task);
        
        // Log task completion with times
        DroneLogger.getInstance().logTaskCompletion(task);
    }
    
    protected void assignTaskToLocalDevice(Task task) {
        task.setOffloadingDestination(task.getEdgeDevice());
    }
    
    protected void assignTaskToNearestEdgeServer(Task task) {
        // Find the nearest edge server
        ComputingNode nearestEdge = findNearestEdgeServer(task.getEdgeDevice());
        
        if (nearestEdge != ComputingNode.NULL) {
            task.setOffloadingDestination(nearestEdge);
        } else {
            // If no close server is found, execute locally
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