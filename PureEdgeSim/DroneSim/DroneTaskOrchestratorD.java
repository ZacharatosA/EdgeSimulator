package DroneSim;

import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.Task;
import org.apache.commons.math3.distribution.LogisticDistribution;

import java.util.Random;

public class DroneTaskOrchestratorD extends DroneTaskOrchestrator {
    private final Random random = new Random();
    private final LogisticDistribution offloadDistribution;
    
    // Parameters for the logistic distribution
    private static final double MU = 20000;    // mean value (inflection point)
    private static final double S = 5000;      // scale parameter
    
    public DroneTaskOrchestratorD(SimulationManager simulationManager) {
        super(simulationManager);
        this.algorithmName = "DRONE_OFFLOADING_WITH_DISTRIBUTIONS";
        this.offloadDistribution = new LogisticDistribution(MU, S);
    }

    @Override
    public void orchestrate(Task task) {
        // Calculate offload probability based on task size
        double offloadProbability = offloadDistribution.cumulativeProbability(task.getLength());
        
        // Decision for offload
        if (random.nextDouble() < offloadProbability) {
            assignTaskToNearestEdgeServer(task);
        } else {
            assignTaskToLocalDevice(task);
        }
    }
}