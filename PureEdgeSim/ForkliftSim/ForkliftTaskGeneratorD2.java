package ForkliftSim;

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

public class ForkliftTaskGeneratorD2 extends DefaultTaskGenerator {
    protected Random random;
    private static final int TASKS_PER_SECOND = 10; //tasks ανά δευτερόλεπτο
    private final NormalDistribution taskLengthDistribution;
    private final NormalDistribution requestSizeDistribution;
    
    // Παράμετροι για την κανονική κατανομή του task length
    private static final double MEAN_TASK_LENGTH = 1722.4; // MI για 53.7ms εκτέλεση
    private static final double STD_DEV = 96.2; // Τυπική απόκλιση για ~3ms διακύμανση
    
    // Παράμετροι για την κανονική κατανομή του request size
    private static final double MEAN_REQUEST_SIZE = 118; // 118KB
    private static final double REQUEST_SIZE_STD_DEV = 63; // 63KB
    
    public ForkliftTaskGeneratorD2(SimulationManager simulationManager) {
        super(simulationManager);
        try {
            random = SecureRandom.getInstanceStrong();
        } catch (NoSuchAlgorithmException e) {
            e.printStackTrace();
        }
        
        // Αρχικοποίηση των κανονικών κατανομών
        taskLengthDistribution = new NormalDistribution(MEAN_TASK_LENGTH, STD_DEV);
        requestSizeDistribution = new NormalDistribution(MEAN_REQUEST_SIZE, REQUEST_SIZE_STD_DEV);
    }
    
    @Override
    public FutureQueue<Task> generate() {
        if (simulationManager == null) return taskList;
        
        devicesList.removeIf(dev -> !dev.isGeneratingTasks());
        
        if (devicesList.isEmpty()) {
            simulationManager.getSimulationLogger().print("Προειδοποίηση: Δεν βρέθηκαν συσκευές που να δημιουργούν εργασίες!");
            return taskList;
        }
        
        double simulationTime = SimulationParameters.simulationDuration;
        int totalSeconds = (int) simulationTime;
        
        // Για κάθε συσκευή (forklift)
        for (ComputingNode forklift : devicesList) {
            // Για κάθε δευτερόλεπτο της προσομοίωσης
            for (int second = 0; second < totalSeconds; second++) {
                // Δημιουργία 15 tasks ανά δευτερόλεπτο
                for (int i = 0; i < TASKS_PER_SECOND; i++) {
                    // Υπολογισμός ακριβούς χρόνου με ίσα διαστήματα μέσα στο δευτερόλεπτο
                    double taskTime = second + (i * (1.0 / TASKS_PER_SECOND));
                    
                    // Δημιουργία task με μέγεθος από την κανονική κατανομή
                    long taskLength = (long) Math.max(1000, taskLengthDistribution.sample());
                    long requestSize = (long) Math.max(1, requestSizeDistribution.sample()); // Ελάχιστο 1KB
                    insertTask(taskTime, 0, forklift, taskLength, requestSize * 8192); // Μετατροπή σε bits
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