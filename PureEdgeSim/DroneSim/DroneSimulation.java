package DroneSim;
import com.mechalikh.pureedgesim.simulationmanager.Simulation;

import java.io.BufferedReader;
import java.io.File;
import java.io.FilenameFilter;
import java.io.InputStreamReader;
import java.util.Arrays;

/**
 * Main class for executing the drone simulation.
 */
public class DroneSimulation {
    // Define paths for settings and output folders
    private static String settingsPath = "DroneSim/Drone_settings/";
    private static String outputPath = "DroneSim/Drone_output/";

    public DroneSimulation() {
        // Create output folder if it doesn't exist
        File outputDir = new File(outputPath);
        if (!outputDir.exists()) {
            outputDir.mkdirs();
        }
        
        // Execute DronePathCreator to create the drone_path.csv file
        System.out.println("DroneSimulation - Creating drone paths using DronePathCreator...");
        try {
            // Define parameters for DronePathCreator
            String inputFile = "DroneSim/mv_nodes_info.csv";
            String outputCsvPath = "DroneSim/drone_path.csv";
            
            // Check if input file exists
            File inputFileObj = new File(inputFile);
            if (!inputFileObj.exists()) {
                System.err.println("WARNING: The file " + inputFile + " was not found.");
                System.err.println("Creation of drone_path.csv will be skipped.");
            } else {
                // Execute DronePathCreator
                DronePathCreator.main(new String[]{inputFile, outputCsvPath});
                System.out.println("DroneSimulation - Drone paths created successfully!");
                
                // Check if file was created
                File outputCsvFile = new File(outputCsvPath);
                if (outputCsvFile.exists()) {
                    System.out.println("DroneSimulation - Drone path file created at: " + outputCsvPath);
                } else {
                    System.err.println("DroneSimulation - WARNING: Failed to create drone path file!");
                }
            }
        } catch (Exception e) {
            System.err.println("DroneSimulation - Error while creating drone paths:");
            e.printStackTrace();
        }

        // Main simulation code
        Simulation sim = new Simulation();
        
        // Set custom folders and models
        sim.setCustomOutputFolder(outputPath);
        sim.setCustomSettingsFolder(settingsPath);
        sim.setCustomMobilityModel(DroneMobilityModel2.class);
        sim.setCustomEdgeOrchestrator(DroneTaskOrchestratorD2.class);
        sim.setCustomTaskGenerator(DroneTaskGeneratorD2.class);
        sim.setCustomNetworkModel(DroneNetworkModel.class);
        sim.setCustomComputingNodesGenerator(DroneComputingNodesGenerator.class);
        
        // Diagnostic message
        System.out.println("DroneSimulation - Starting simulation with DroneMobilityModel2...");
        
        // Start simulation
        sim.launchSimulation();
        
        // Diagnostic message after simulation
        System.out.println("DroneSimulation - Simulation completed, saving logs...");
        
        // Save logs to CSV
        DroneLogger logger = DroneLogger.getInstance();
        if (logger != null) {
            logger.saveAllLogs();
            System.out.println("DroneSimulation - Logs saved successfully.");
        } else {
            System.err.println("DroneSimulation - Error: DroneLogger instance is null!");
        }
        
        // Execute LogAnalysis.py
        try {
            // Find the most recently created folder
            File[] folders = new File(outputPath).listFiles(File::isDirectory);
            if (folders != null && folders.length > 0) {
                // Sort by last modified date
                Arrays.sort(folders, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
                String latestFolder = folders[0].getName();
                
                // Hardcoded path for Python script
                String pythonScript = "DroneSim/LogAnalysis.py";
                File scriptFile = new File(pythonScript);
                
                if (!scriptFile.exists()) {
                    System.err.println("LogAnalysis.py file not found at: " + pythonScript);
                    return;
                }
                
                // Construct the command to execute the Python script
                String command = String.format("python3 %s %s", pythonScript, latestFolder);
                System.out.println("Executing command: " + command);
                
                // Execute the command
                Process process = Runtime.getRuntime().exec(command);
                
                // Print output
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                BufferedReader errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream()));
                
                String line;
                System.out.println("\n=== Output from LogAnalysis.py ===");
                while ((line = reader.readLine()) != null) {
                    System.out.println(line);
                }
                
                // Print errors if any
                boolean hasErrors = false;
                while ((line = errorReader.readLine()) != null) {
                    System.err.println("Error from LogAnalysis.py: " + line);
                    hasErrors = true;
                }
                
                if (hasErrors) {
                    System.err.println("There were errors during LogAnalysis.py execution");
                }
                
                process.waitFor();
            } else {
                System.err.println("No output folder found for analysis");
            }
        } catch (Exception e) {
            System.err.println("Error while executing LogAnalysis.py:");
            e.printStackTrace();
        }
    }

    /**
     * Main method to run the simulation
     */
    public static void main(String[] args) {
        new DroneSimulation();
    }
}