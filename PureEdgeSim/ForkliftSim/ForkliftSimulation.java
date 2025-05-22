package ForkliftSim;
import com.mechalikh.pureedgesim.simulationmanager.Simulation;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.util.Arrays;

/**
 * Κύρια κλάση εκτέλεσης της προσομοίωσης του forklift.
 */
public class ForkliftSimulation {
    // Ορισμός μονοπατιών για τις ρυθμίσεις και τους φακέλους εξόδου
    private static String settingsPath = "PureEdgeSim/ForkliftSim/Forklift_settings/";
    private static String outputPath = "PureEdgeSim/ForkliftSim/Forklift_output/";

    public ForkliftSimulation() {
        // Δημιουργία φακέλου εξόδου εάν δεν υπάρχει
        File outputDir = new File(outputPath);
        if (!outputDir.exists()) {
            outputDir.mkdirs();
        }

        // Κύριος κώδικας προσομοίωσης
        Simulation sim = new Simulation();
        
        // Ορισμός ειδικών φακέλων και μοντέλων
        sim.setCustomOutputFolder(outputPath);
        sim.setCustomSettingsFolder(settingsPath);
        sim.setCustomMobilityModel(ForkliftMobilityModel.class);
        sim.setCustomEdgeOrchestrator(ForkliftTaskOrchestrator.class);
        sim.setCustomTaskGenerator(ForkliftTaskGeneratorD2.class);
        sim.setCustomNetworkModel(ForkliftNetworkModel.class);
        sim.setCustomComputingNodesGenerator(ForkliftComputingNodesGenerator.class);
        
        // Εκκίνηση προσομοίωσης
        sim.launchSimulation();
        
        // Αποθήκευση των logs στο CSV
        ForkliftLogger.getInstance().saveAllLogs();
        
        // Εκτέλεση του LogAnalysis.py
        try {
            // Βρίσκουμε το τελευταίο φάκελο που δημιουργήθηκε
            File[] folders = new File(outputPath).listFiles(File::isDirectory);
            if (folders != null && folders.length > 0) {
                // Ταξινομούμε με βάση την τελευταία τροποποίηση
                Arrays.sort(folders, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
                String latestFolder = folders[0].getName();
                
                // Hardcoded path για το Python script
                String pythonScript = "PureEdgeSim/ForkliftSim/LogAnalysis.py";
                File scriptFile = new File(pythonScript);
                
                if (!scriptFile.exists()) {
                    System.err.println("Το αρχείο LogAnalysis.py δεν βρέθηκε στο: " + pythonScript);
                    return;
                }
                
                // Κατασκευή της εντολής για την εκτέλεση του Python script
                String command = String.format("python3 %s %s", pythonScript, latestFolder);
                System.out.println("Εκτέλεση εντολής: " + command);
                
                // Εκτέλεση της εντολής
                Process process = Runtime.getRuntime().exec(command);
                
                // Εκτύπωση του output
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                BufferedReader errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream()));
                
                String line;
                System.out.println("\n=== Output από το LogAnalysis.py ===");
                while ((line = reader.readLine()) != null) {
                    System.out.println(line);
                }
                
                // Εκτύπωση των errors αν υπάρχουν
                boolean hasErrors = false;
                while ((line = errorReader.readLine()) != null) {
                    System.err.println("Σφάλμα από LogAnalysis.py: " + line);
                    hasErrors = true;
                }
                
                if (hasErrors) {
                    System.err.println("Υπήρξαν σφάλματα κατά την εκτέλεση του LogAnalysis.py");
                }
                
                process.waitFor();
            } else {
                System.err.println("Δεν βρέθηκε φάκελος εξόδου για ανάλυση");
            }
        } catch (Exception e) {
            System.err.println("Σφάλμα κατά την εκτέλεση του LogAnalysis.py:");
            e.printStackTrace();
        }
    }

    /**
     * Μέθοδος main για την εκτέλεση της προσομοίωσης
     */
    public static void main(String[] args) {
        new ForkliftSimulation();
    }
}