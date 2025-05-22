package DroneSim;

import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Random;
import org.apache.commons.math3.distribution.NormalDistribution;
import org.apache.commons.math3.distribution.ExponentialDistribution;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters;
import com.mechalikh.pureedgesim.simulationengine.FutureQueue;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.DefaultTaskGenerator;
import com.mechalikh.pureedgesim.taskgenerator.Task;

public class DroneTaskGeneratorD extends DefaultTaskGenerator {
    protected Random random;
    private static final int TASKS_PER_SECOND_APP1 = 15;
    private static final int TASKS_APP1_BEFORE_APP2 = 15;
    private int taskCounterApp1 = 0;
    
    // Distributions for task sizes
    private NormalDistribution droneTaskDistribution;     // Normal distribution for drone tasks
    private ExponentialDistribution edgeTaskDistribution; // Exponential distribution for edge tasks
    
    public DroneTaskGeneratorD(SimulationManager simulationManager) {
        super(simulationManager);
        try {
            random = SecureRandom.getInstanceStrong();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
        }
        

        // Initialize distributions
        // For drone tasks: mean 8000 MI, standard deviation 1000 MI
        droneTaskDistribution = new NormalDistribution(8000, 1000);  
        // For edge tasks: mean 110000 MI
        edgeTaskDistribution = new ExponentialDistribution(110000);
    }
    @Override
    public FutureQueue<Task> generate() {
        if (simulationManager == null) return taskList;
        
        devicesList.removeIf(dev -> !dev.isGeneratingTasks());
        
        if (devicesList.isEmpty()) {
            simulationManager.getSimulationLogger().print("Warning - No devices generating tasks found!");
            return taskList;
        }
        
        ComputingNode drone = devicesList.get(0);
        double simulationTime = SimulationParameters.simulationDuration;
        int totalSeconds = (int) simulationTime;
        
        for (int second = 0; second < totalSeconds; second++) {
            for (int i = 0; i < TASKS_PER_SECOND_APP1; i++) {
                double taskTime = second + (i * (1.0 / TASKS_PER_SECOND_APP1));
                
                // Create task with size from normal distribution
                long taskLength = (long) Math.max(1000, droneTaskDistribution.sample());
                insertTask(taskTime, 0, drone, taskLength);
                taskCounterApp1++;
                
                if (taskCounterApp1 >= TASKS_APP1_BEFORE_APP2) {
                    // Create task with size from exponential distribution
                    long edgeTaskLength = (long) Math.max(20000, edgeTaskDistribution.sample());
                    insertTask(taskTime + (1.0 / (2 * TASKS_PER_SECOND_APP1)), 1, drone, edgeTaskLength);
                    taskCounterApp1 = 0;
                }
            }
        }
        
        return taskList;
    }
    
    protected void insertTask(double time, int appId, ComputingNode device, long taskLength) {
        if (time > SimulationParameters.simulationDuration) {
            time = SimulationParameters.simulationDuration - 0.1;
        }
        
        try {
            long requestSize = SimulationParameters.applicationList.get(appId).getRequestSize();
            long outputSize = SimulationParameters.applicationList.get(appId).getResultsSize();
            long containerSize = SimulationParameters.applicationList.get(appId).getContainerSizeInBits();
            double maxLatency = SimulationParameters.applicationList.get(appId).getLatency();
            String type = SimulationParameters.applicationList.get(appId).getType();
            
            Task task = createTask(++id)
                    .setType(type)
                    .setFileSizeInBits(requestSize)
                    .setOutputSizeInBits(outputSize)
                    .setContainerSizeInBits(containerSize)
                    .setApplicationID(appId)
                    .setMaxLatency(maxLatency)
                    .setLength(taskLength)
                    .setEdgeDevice(device)
                    .setRegistry(getSimulationManager().getDataCentersManager()
                    .getComputingNodesGenerator().getCloudOnlyList().get(0));
            
            task.setTime(time);
            taskList.add(task);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
} 