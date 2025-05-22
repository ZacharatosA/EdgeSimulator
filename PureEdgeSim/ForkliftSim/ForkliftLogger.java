package ForkliftSim;

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
 * Κλάση για την καταγραφή δεδομένων σχετικά με το forklift και τις εργασίες του.
 * Χρησιμοποιεί το πρότυπο Singleton για να διασφαλίσει μια μοναδική παρουσία σε όλο το σύστημα.
 */
public class ForkliftLogger {
    private static ForkliftLogger instance;
    private SimulationManager simulationManager;
    @SuppressWarnings("unused")
    private SimLog simulationLogger;
    
    // Maps για αποθήκευση πληροφοριών ανά forklift
    private Map<Integer, Location> forkliftLocations = new HashMap<>();
    
    // Map για το ιστορικό θέσεων ανά forklift
    private Map<Integer, List<Location>> positionHistoryMap = new HashMap<>();
    
    // Αποθήκευση πληροφοριών για τα tasks ανά δευτερόλεπτο
    private boolean edgeDatacentersInfoPrinted = false;
    
    // Προσθήκη νέων πεδίων
    private List<String> csvRecords = new ArrayList<>();
    private static final String CSV_HEADER = "Time,ForkliftX,ForkliftY,ForkliftID,TaskID,AppType,TaskLength,ExecutionLocation,WaitingTime,ExecutionTime,NetworkTime,TotalTime,Status,CPUUsage (%)";
    
    // Ιδιωτικός constructor για το Singleton pattern
    private ForkliftLogger() {
    }
    
    /**
     * Αρχικοποιεί τον logger με τον simulation manager
     */
    public static ForkliftLogger initialize(SimulationManager simulationManager) {
        if (instance == null) {
            instance = new ForkliftLogger();
        }
        instance.simulationManager = simulationManager;
        instance.simulationLogger = simulationManager.getSimulationLogger();
        
        // Εκτύπωση πληροφοριών edge datacenters κατά την αρχικοποίηση
        instance.printEdgeDatacentersInfo();
        
        return instance;
    }
    
    /**
     * Επιστρέφει το instance του logger
     */
    public static ForkliftLogger getInstance() {
        if (instance == null) {
            instance = new ForkliftLogger();
        }
        return instance;
    }
    
    /**
     * Εκτυπώνει πληροφορίες για τα edge datacenters.
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
                    "%s - Θέση: (%.1f, %.1f) - Πόροι: %.0f cores, %.0f MIPS, %.0f RAM, %.0f Storage",
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
     * Καταγράφει την τρέχουσα θέση του forklift με ID
     */
    public void logForkliftPosition(int forkliftId, double time, Location position) {
        // Αποθήκευση θέσης στο map
        forkliftLocations.put(forkliftId, new Location(position.getXPos(), position.getYPos()));
        
        // Προσθήκη στο ιστορικό θέσεων
        positionHistoryMap.computeIfAbsent(forkliftId, k -> new ArrayList<>())
                         .add(new Location(position.getXPos(), position.getYPos()));
    }
    
    // Προσθήκη νέας μεθόδου για εκτύπωση με συγκεκριμένη μορφοποίηση χρόνου
    private void printWithCustomTime(String message) {
        if (simulationManager == null) return;
        
        double time = simulationManager.getSimulation().clock();
        String formattedTime = String.format("%.4f", time);
        
        // Προσθήκη της ημερομηνίας και του χρόνου με τη σωστή μορφοποίηση
        String fullMessage = String.format("%s - simulation time %s (s) : %s",
            new java.text.SimpleDateFormat("yyyy/MM/dd HH:mm:ss").format(new java.util.Date()),
            formattedTime,
            message);
            
        simulationManager.getSimulationLogger().printWithoutTime(fullMessage);
    }
    
    /**
     * Καταγράφει την ολοκλήρωση ενός task με τους χρόνους εκτέλεσης
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
        
        // Υπολογισμός CPU usage
        double cpuUsage = (task.getLength() * 100) / (destination.getTotalMipsCapacity());
        
        // Εύρεση του instance ID του edge device που δημιουργήθηκε το task
        int edgeDeviceInstanceId = -1;
        List<ComputingNode> edgeDevices = simulationManager.getDataCentersManager()
                .getComputingNodesGenerator().getMistOnlyList();
        
        for (int i = 0; i < edgeDevices.size(); i++) {
            if (edgeDevices.get(i).equals(task.getEdgeDevice())) {
                edgeDeviceInstanceId = i;
                break;
            }
        }
        
        // Βρίσκουμε τη θέση του forklift που δημιουργήθηκε το task
        Location forkliftLocation;
        if (forkliftLocations.containsKey(edgeDeviceInstanceId)) {
            forkliftLocation = forkliftLocations.get(edgeDeviceInstanceId);
        } else {
            // Προεπιλεγμένη θέση
            forkliftLocation = new Location(0, 0);
        }
        
        // Δημιουργία του μηνύματος για το txt log
        String taskMessage = String.format(
            "Forklift: %d | Forklift Location (%.1f,%.1f) || Task ID: %6d, Application: %d, Length: %.0f | Ανάθεση: %-20s | [%s] || " +
            "Wait: %.4fs | Exec: %.4fs | Net: %.4fs | Total: %.4fs | CPU: %.2f%%%%",
            edgeDeviceInstanceId,
            forkliftLocation.getXPos(),
            forkliftLocation.getYPos(),
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
        
        // Προσθήκη εγγραφής στο CSV με το CPU usage
        String csvLine = String.format("%.4f,%.1f,%.1f,%d,%d,%d,%.0f,%s,%.4f,%.4f,%.4f,%.4f,%s,%.4f",
            simulationManager.getSimulation().clock(),
            forkliftLocation.getXPos(),
            forkliftLocation.getYPos(),
            edgeDeviceInstanceId,
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
        
        // Εκτύπωση στο txt log
        printWithCustomTime(taskMessage);
    }
    
    /**
     * Καταγράφει μήνυμα στο log του simulation
     */
    public void log(String message) {
        if (simulationManager != null) {
            simulationManager.getSimulationLogger().print(message);
        }
    }
    
    /**
     * Καταγράφει μορφοποιημένο μήνυμα
     */
    public void log(String format, Object... args) {
        if (simulationManager != null) {
            simulationManager.getSimulationLogger().print(String.format(format, args));
        }
    }
    
    // Μέθοδος για αποθήκευση του CSV αρχείου
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
    
    // Βοηθητική μέθοδος για τον προσδιορισμό της τοποθεσίας εκτέλεσης
    private String getExecutionLocation(Task task) {
        ComputingNode destination = task.getOffloadingDestination();
        if (destination.getType() == SimulationParameters.TYPES.EDGE_DEVICE) {
            return "Far-Edge (Forklift)";
        } else {
            return "Edge Server: " + destination.getName();
        }
    }
    
    // Βοηθητική μέθοδος για το όνομα του CSV αρχείου
    private String getCSVFileName() {
        String baseFileName = simulationManager.getSimulationLogger().getFileName("");
        // Προσθήκη του προθέματος "forklift_" πριν την κατάληξη .csv
        return baseFileName + "_forklift.csv";
    }
    
    // Προσθήκη μεθόδου για αποθήκευση του CSV στο τέλος της προσομοίωσης
    public void saveAllLogs() {
        // Αποθήκευση του CSV
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
        // Καθαρισμός της λίστας
        csvRecords.clear();
    } 
} 