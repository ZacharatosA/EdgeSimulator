package DroneSim;

//import java.util.ArrayList;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.locationmanager.Location;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters;
import com.mechalikh.pureedgesim.simulationmanager.SimLog;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.taskgenerator.Task;

/**
 * Class for logging data related to the drone and its tasks.
 * Uses the Singleton pattern to ensure a single instance throughout the system.
 */
public class DroneLogger {
    private static DroneLogger instance;
    private SimulationManager simulationManager;
    @SuppressWarnings("unused")
    private SimLog simulationLogger;
    
    // Έλεγχος εκτύπωσης στο τερματικό
    private static boolean PRINT_TO_TERMINAL = false; 
    
    // Maps for storing information per drone
    private Map<Integer, Location> droneLocations = new HashMap<>();
    
    // Map for position history per drone
    private Map<Integer, List<Location>> positionHistoryMap = new HashMap<>();
    
    // Store task information per second
    private boolean edgeDatacentersInfoPrinted = false;
    
    // Adding new fields
    private List<String> csvRecords = new ArrayList<>();
    private static final String CSV_HEADER = "Time,DroneX,DroneY,DroneID,TaskID,AppType,TaskLength,ExecutionLocation,WaitingTime,ExecutionTime,NetworkTime,TotalTime,Status,CPUUsage (%)";
    
    // Private constructor for Singleton pattern
    private DroneLogger() {
    }
    
    /**
     * Initializes the logger with the simulation manager
     */
    public static DroneLogger initialize(SimulationManager simulationManager) {
        if (instance == null) {
            instance = new DroneLogger();
        }
        instance.simulationManager = simulationManager;
        instance.simulationLogger = simulationManager.getSimulationLogger();
        
        // Print edge datacenters information during initialization
        instance.printEdgeDatacentersInfo();
        
        return instance;
    }
    
    /**
     * Returns the logger instance
     */
    public static DroneLogger getInstance() {
        if (instance == null) {
            instance = new DroneLogger();
        }
        return instance;
    }
    
    /**
     * Enables or disables terminal printing
     */
    public static void setPrintToTerminal(boolean enabled) {
        PRINT_TO_TERMINAL = enabled;
    }
    
    /**
     * Returns the current status of terminal printing
     */
    public static boolean isPrintingToTerminal() {
        return PRINT_TO_TERMINAL;
    }
    
    /**
     * Prints information about edge datacenters.
     */
    public void printEdgeDatacentersInfo() {
        if (edgeDatacentersInfoPrinted || simulationManager == null) {
            return;
        }
        
        List<ComputingNode> edgeDatacenters = simulationManager.getDataCentersManager()
                .getComputingNodesGenerator().getEdgeOnlyList();
        
        simulationManager.getSimulationLogger().printWithoutTime("===== EDGE DATACENTERS =====");
        for (ComputingNode node : edgeDatacenters) {
            simulationManager.getSimulationLogger().printWithoutTime(
                    "%s - Location: (%.1f, %.1f) - Resources: %.0f cores, %.0f MIPS, %.0f RAM, %.0f Storage",
                    node.getName(),
                    node.getMobilityModel().getCurrentLocation().getXPos(),
                    node.getMobilityModel().getCurrentLocation().getYPos(),
                    node.getNumberOfCPUCores(),
                    node.getMipsPerCore(),
                    node.getAvailableRam(),
                    node.getAvailableStorage()
            );
        }
        
        edgeDatacentersInfoPrinted = true;
    }
    
    /**
     * Logs the current position of the drone with ID
     */
    public void logDronePosition(int droneId, double time, Location position) {
        // Store position in the map
        droneLocations.put(droneId, new Location(position.getXPos(), position.getYPos()));
        
        // Add to position history
        positionHistoryMap.computeIfAbsent(droneId, k -> new ArrayList<>())
                         .add(new Location(position.getXPos(), position.getYPos()));
    }
    
    // Add new method for printing with specific time formatting
    private void printWithCustomTime(String message) {
        if (simulationManager == null) return;
        
        double time = simulationManager.getSimulation().clock();
        String formattedTime = String.format("%.4f", time);
        
        // Add date and time with correct formatting
        String fullMessage = String.format("%s - simulation time %s (s) : %s",
            new java.text.SimpleDateFormat("yyyy/MM/dd HH:mm:ss").format(new java.util.Date()),
            formattedTime,
            message);
        
        // Έλεγχος αν πρέπει να γίνει εκτύπωση στο τερματικό
        if (PRINT_TO_TERMINAL) {
            simulationManager.getSimulationLogger().printWithoutTime(fullMessage);
        } else {
            // Εγγραφή μόνο στο αρχείο log χωρίς εκτύπωση στο τερματικό
            try {
                String logFileName = simulationManager.getSimulationLogger().getFileName(".txt");
                try (BufferedWriter writer = new BufferedWriter(new FileWriter(logFileName, true))) {
                    writer.write(fullMessage);
                    writer.newLine();
                }
            } catch (IOException e) {
                // Αν αποτύχει η εγγραφή στο αρχείο, χρησιμοποίησε την κανονική μέθοδο
                simulationManager.getSimulationLogger().printWithoutTime(fullMessage);
            }
        }
    }
    
    /**
     * Logs the completion of a task with execution times
     */
    public void logTaskCompletion(Task task) {
        if (simulationManager == null) return;
        
        double waitingTime = task.getWatingTime();
        double executionTime = task.getActualCpuTime();
        double networkTime = task.getActualNetworkTime();
        double totalTime = task.getTotalDelay();
        
        String status = (task.getStatus() == Task.Status.SUCCESS) ? "S" : "F";
        
        ComputingNode destination = task.getOffloadingDestination();
        String executionLocation = getExecutionLocation(task);
        
        // Calculate CPU usage
        double cpuUsage = (task.getLength() * 100) / (destination.getTotalMipsCapacity());
        
        // Find the instance ID of the edge device that created the task
        int edgeDeviceInstanceId = -1;
        List<ComputingNode> edgeDevices = simulationManager.getDataCentersManager()
                .getComputingNodesGenerator().getMistOnlyList();
        
        for (int i = 0; i < edgeDevices.size(); i++) {
            if (edgeDevices.get(i).equals(task.getEdgeDevice())) {
                edgeDeviceInstanceId = i;
                break;
            }
        }
        
        // Find the position of the drone that created the task
        Location droneLocation;
        if (droneLocations.containsKey(edgeDeviceInstanceId)) {
            droneLocation = droneLocations.get(edgeDeviceInstanceId);
        } else {
            // Default position
            droneLocation = new Location(0, 0);
        }
        
        // Create message for txt log
        String taskMessage = String.format(
            "Drone: %d | Drone Location (%.1f,%.1f) || Task ID: %6d, Application: %d, Length: %.0f | Assignment: %-20s | [%s] || " +
            "Wait: %.4fs | Exec: %.4fs | Net: %.4fs | Total: %.4fs | CPU: %.2f%%%%",
            edgeDeviceInstanceId, // Use instance ID of the edge device
            droneLocation.getXPos(),
            droneLocation.getYPos(),
            task.getId(),
            task.getApplicationID(),
            task.getLength(),
            executionLocation,
            status,
            waitingTime,
            executionTime,
            networkTime,
            totalTime,
            cpuUsage
        );
        
        // Add record to CSV with CPU usage
        String csvLine = String.format("%.4f,%.1f,%.1f,%d,%d,%d,%.0f,%s,%.4f,%.4f,%.4f,%.4f,%s,%.4f",
            simulationManager.getSimulation().clock(),
            droneLocation.getXPos(),
            droneLocation.getYPos(),
            edgeDeviceInstanceId, // Use the drone ID
            task.getId(),
            task.getApplicationID(),
            task.getLength(),
            executionLocation,
            waitingTime,
            executionTime,
            networkTime,
            totalTime,
            status,
            cpuUsage
        );
        csvRecords.add(csvLine);
        
        // Print to txt log
        printWithCustomTime(taskMessage);
    }
    /**
     * Logs a message to the simulation log
     */
    public void log(String message) {
        if (simulationManager != null) {
            simulationManager.getSimulationLogger().print(message);
        }
    }
    
    /**
     * Logs a formatted message
     */
    public void log(String format, Object... args) {
        if (simulationManager != null) {
            simulationManager.getSimulationLogger().print(String.format(format, args));
        }
    }
    
    // Method to save the CSV file
    public void saveCSVLog() {
        String csvFileName = getCSVFileName();
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(csvFileName))) {
            writer.write(CSV_HEADER);
            writer.newLine();
            for (String record : csvRecords) {
                writer.write(record);
                writer.newLine();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    // Helper method to determine execution location
    private String getExecutionLocation(Task task) {
        ComputingNode destination = task.getOffloadingDestination();
        if (destination.getType() == SimulationParameters.TYPES.EDGE_DEVICE) {
            return "Far-Edge (Drone)";
        } else {
            return "Edge Server: " + destination.getName();
        }
    }
    
    // Helper method for CSV file name
    private String getCSVFileName() {
        String baseFileName = simulationManager.getSimulationLogger().getFileName("");
        // Add "drone_" prefix before the .csv extension
        return baseFileName + "_drone.csv";
    }
    
    // Add method to save CSV at the end of simulation
    public void saveAllLogs() {
        // Save CSV
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(getCSVFileName()))) {
            writer.write(CSV_HEADER);
            writer.newLine();
            for (String record : csvRecords) {
                writer.write(record);
                writer.newLine();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        // Clear the list
        csvRecords.clear();
    } 
} 