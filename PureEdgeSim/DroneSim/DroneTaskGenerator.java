package DroneSim;

import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Random;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters;
import com.mechalikh.pureedgesim.simulationengine.FutureQueue;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.DefaultTaskGenerator;
import com.mechalikh.pureedgesim.taskgenerator.Task;

public class DroneTaskGenerator extends DefaultTaskGenerator {
    protected Random random;
    // Add variable for print control
    protected boolean print = false;
    private static final int TASKS_PER_SECOND_APP1 = 15;
    private static final int TASKS_APP1_BEFORE_APP2 = 15;
    private int taskCounterApp1 = 0;
    
    public DroneTaskGenerator(SimulationManager simulationManager) {
        super(simulationManager);
        try {
            random = SecureRandom.getInstanceStrong();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
        }
    }
    
    /**
     * Sets whether messages should be printed during task generation
     * 
     * @param print true to print messages, false to avoid printing
     */
    public void setPrintEnabled(boolean print) {
        this.print = print;
    }
    
    @Override
    public FutureQueue<Task> generate() {
        if (simulationManager == null) return taskList;
        
        devicesList.removeIf(dev -> !dev.isGeneratingTasks());
        
        if (devicesList.isEmpty()) {
            if (print) {
                simulationManager.getSimulationLogger().print("Warning: No devices found that generate tasks!");
            }
            return taskList;
        }
        
        ComputingNode drone = devicesList.get(0);
        double simulationTime = SimulationParameters.simulationDuration;
        int totalSeconds = (int) simulationTime;
        
        // For each second of the simulation
        for (int second = 0; second < totalSeconds; second++) {
            // Generate 15 tasks of the first application at regular intervals
            for (int i = 0; i < TASKS_PER_SECOND_APP1; i++) {
                // Calculate exact time with equal intervals within the second
                double taskTime = second + (i * (1.0 / TASKS_PER_SECOND_APP1));
                insertTask(taskTime, 0, drone); // appId 0 for the first application
                taskCounterApp1++;
                
                // If we have generated 15 tasks of the first application
                if (taskCounterApp1 >= TASKS_APP1_BEFORE_APP2) {
                    // Create a task of the second application immediately after
                    insertTask(taskTime + (1.0 / (2 * TASKS_PER_SECOND_APP1)), 1, drone);
                    taskCounterApp1 = 0;
                }
            }
        }
        
        if (print) {
            simulationManager.getSimulationLogger().print("DroneTaskGenerator: Total tasks created: " + taskList.size());
        }
        
        return taskList;
    }
    
    /**
     * Creates and inserts a task into the task list
     */
    protected void insertTask(double time, int appId, ComputingNode device) {
        // Simulation time limit in seconds
        double timeLimit = SimulationParameters.simulationDuration;
        
        // Limit time to the duration of the simulation
        if (time > timeLimit) {
            time = timeLimit - 0.1; // 0.1 seconds before the end
        }
        
        try {
            // Application parameters
            long requestSize = SimulationParameters.applicationList.get(appId).getRequestSize();
            long outputSize = SimulationParameters.applicationList.get(appId).getResultsSize();
            long containerSize = SimulationParameters.applicationList.get(appId).getContainerSizeInBits();
            double maxLatency = SimulationParameters.applicationList.get(appId).getLatency();
            long length = (long) SimulationParameters.applicationList.get(appId).getTaskLength();
            String type = SimulationParameters.applicationList.get(appId).getType();
            
            // Create task
            Task task = createTask(++id)
                    .setType(type)
                    .setFileSizeInBits(requestSize)
                    .setOutputSizeInBits(outputSize)
                    .setContainerSizeInBits(containerSize)
                    .setApplicationID(appId)
                    .setMaxLatency(maxLatency)
                    .setLength(length)
                    .setEdgeDevice(device)
                    .setRegistry(getSimulationManager().getDataCentersManager()
                    .getComputingNodesGenerator().getCloudOnlyList().get(0));
            
            task.setTime(time);
            taskList.add(task);
            
            if (print) {
                simulationManager.getSimulationLogger().deepLog("DroneTaskGenerator: Task " + id + 
                                   ", with execution time " + time + ", (s) appId=" + appId + 
                                   ",  length=" + length + " created.");
            }
            
        } catch (Exception e) {
            if (print) {
                simulationManager.getSimulationLogger().print("DroneTaskGenerator: Error while creating task: " + e.getMessage());
            }
            e.printStackTrace();
        }
    }
} 