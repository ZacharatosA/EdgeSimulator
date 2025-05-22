package DroneSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
//import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.Task;
import com.mechalikh.pureedgesim.taskorchestrator.DefaultOrchestrator;



//import java.util.ArrayList;
import java.util.List;

/**
 * Orchestrator that decides when to execute a task on the drone (far-edge/mist)
 * and when to offload it to the edge server.
 */
public class DroneTaskOrchestrator extends DefaultOrchestrator {
    // Threshold to decide if a task will be executed locally or on the edge server
    private final double TASK_LENGTH_THRESHOLD = 20000;

    public DroneTaskOrchestrator(SimulationManager simulationManager) {
        super(simulationManager);
        this.algorithmName = "DRONE_OFFLOADING"; 
    }

    @Override
    public void orchestrate(Task task) {
        // Assignment based on instruction length
        if (task.getLength() < TASK_LENGTH_THRESHOLD) {
            assignTaskToLocalDevice(task);
        } else {
            assignTaskToNearestEdgeServer(task);
        }
    }
    
    @Override
    public void resultsReturned(Task task) {
        // Call the parent class implementation
        super.resultsReturned(task);
        
        // Log the completion of the task with times
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