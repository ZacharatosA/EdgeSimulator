package ForkliftSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.Task;
import com.mechalikh.pureedgesim.taskorchestrator.DefaultOrchestrator;

import java.util.List;

public class ForkliftTaskOrchestrator extends DefaultOrchestrator {
    // Ποσοστό των edge devices που θα κάνουν offload (%)
    private static final double OFFLOAD_PERCENTAGE = 45;
    
    public ForkliftTaskOrchestrator(SimulationManager simulationManager) {
        super(simulationManager);
        this.algorithmName = "FORKLIFT_PERCENTAGE_OFFLOADING";
        ForkliftLogger.initialize(simulationManager);
    }

    @Override
    public void orchestrate(Task task) {
        // Παίρνουμε το edge device που δημιούργησε το task
        ComputingNode device = task.getEdgeDevice();
        
        // Βρίσκουμε το ID του device
        int deviceId = ((ForkliftMobilityModel) device.getMobilityModel()).getDeviceId();
        
        // Παίρνουμε τον πραγματικό αριθμό των edge devices
        int numDevices = simulationManager.getDataCentersManager()
                           .getComputingNodesGenerator().getMistOnlyList().size();
        
        // Υπολογίζουμε το όριο των devices που θα κάνουν offload
        int offloadLimit = (int)(numDevices * (OFFLOAD_PERCENTAGE / 100.0));
        
        // Αν το ID του device είναι μικρότερο από το όριο, κάνει offload
        if (deviceId < offloadLimit) {
            assignTaskToNearestEdgeServer(task);
        } else {
            // Διαφορετικά εκτελεί το task τοπικά
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
        // Βρίσκουμε τον πλησιέστερο edge server
        ComputingNode nearestEdge = findNearestEdgeServer(task.getEdgeDevice());
        
        if (nearestEdge != ComputingNode.NULL) {
            task.setOffloadingDestination(nearestEdge);
        } else {
            // Αν δεν βρεθεί κοντινός server, εκτελεί τοπικά
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