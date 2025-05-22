package DroneSim;

import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Random;
import org.apache.commons.math3.distribution.NormalDistribution;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters;
import com.mechalikh.pureedgesim.simulationengine.FutureQueue;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.DefaultTaskGenerator;
import com.mechalikh.pureedgesim.taskgenerator.Task;

public class DroneTaskGeneratorD2 extends DefaultTaskGenerator {
    protected Random random;
    private static final int TASKS_PER_SECOND = 15; // 15 tasks per second
    private final NormalDistribution taskLengthDistribution;
    private final NormalDistribution requestSizeDistribution;
    
    // Parameters for normal distribution of task length
    private static final double MEAN_TASK_LENGTH = 1722.4; // MI for 53.7ms execution
    private static final double STD_DEV = 96.2; // Standard deviation for ~3ms variation
    
    // Parameters for normal distribution of request size
    private static final double MEAN_REQUEST_SIZE = 118; // 118KB
    private static final double REQUEST_SIZE_STD_DEV = 63; // 63KB
    
    public DroneTaskGeneratorD2(SimulationManager simulationManager) {
        super(simulationManager);
        try {
            random = SecureRandom.getInstanceStrong();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
        }
        
        // Initialize normal distributions
        taskLengthDistribution = new NormalDistribution(MEAN_TASK_LENGTH, STD_DEV);
        requestSizeDistribution = new NormalDistribution(MEAN_REQUEST_SIZE, REQUEST_SIZE_STD_DEV);
    }
    
    @Override
    public FutureQueue<Task> generate() {
        if (simulationManager == null) return taskList;
        
        devicesList.removeIf(dev -> !dev.isGeneratingTasks());
        
        if (devicesList.isEmpty()) {
            simulationManager.getSimulationLogger().print("Warning: No devices found that generate tasks!");
            return taskList;
        }
        
        double simulationTime = SimulationParameters.simulationDuration;
        int totalSeconds = (int) simulationTime;
        
        // For each device (drone)
        for (ComputingNode drone : devicesList) {
            // For each second of the simulation
            for (int second = 0; second < totalSeconds; second++) {
                // Generate 15 tasks per second
                for (int i = 0; i < TASKS_PER_SECOND; i++) {
                    // Calculate exact time with equal intervals within the second
                    double taskTime = second + (i * (1.0 / TASKS_PER_SECOND));
                    
                    // Create task with size from normal distribution
                    long taskLength = (long) Math.max(1000, taskLengthDistribution.sample());
                    long requestSize = (long) Math.max(1, requestSizeDistribution.sample()); // Minimum 1KB
                    insertTask(taskTime, 0, drone, taskLength, requestSize * 8192); // Convert to bits
                }
            }
        }
        
        return taskList;
    }
    
    protected void insertTask(double time, int appId, ComputingNode device, long taskLength, long requestSize) {
        if (time > SimulationParameters.simulationDuration) {
            time = SimulationParameters.simulationDuration - 0.1;
        }
        
        try {
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