package DroneSim;

import com.mechalikh.pureedgesim.locationmanager.Location;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.locationmanager.MobilityModel;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public class DroneMobilityModel2 extends MobilityModel {
    // Map that will contain coordinates for each drone ID
    private Map<Integer, double[][]> dronePathsMap = new HashMap<>();
    
    // Coordinate array for the current drone
    private double[][] currentDronePath;
    
    // Variables for tracking position and movement
    private int currentGnbIndex = 0;   // Current index in the path
    private int nextNodeIndex = 1;      // Next index in the path
    private boolean isMoving = true;   // Always moving, no pause
    private boolean initialPositionSet = false; // Check if initial position has been set
    private int deviceId = -1; // Drone ID
    private Random random = new Random(); // For random positions
    
    public DroneMobilityModel2(SimulationManager simulationManager, Location currentLocation) {
        super(simulationManager, currentLocation);
        
        // Load paths from CSV file during initialization
        loadPathFromCSV();
        
        // Immediate initialization of position for mobile node (drone)
        if (this.isMobile) {
            // Initial position will be set when we know the drone ID
            initialPositionSet = false;
        }
    }
    
    // Method to load coordinates from CSV file
    private void loadPathFromCSV() {
        // Map for temporary storage of coordinates per drone ID
        Map<Integer, List<double[]>> coordinatesMap = new HashMap<>();
        
        try {
            String csvFilePath = "DroneSim/drone_path.csv";
            System.out.println("DroneMobilityModel2: Reading coordinates from: " + csvFilePath);
            
            BufferedReader reader = new BufferedReader(new FileReader(csvFilePath));
            String line;
            
            // Skip first line (headers)
            reader.readLine();
            
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",");
                if (parts.length >= 4) {
                    double x = Double.parseDouble(parts[1]);
                    double y = Double.parseDouble(parts[2]);
                    int droneId = Integer.parseInt(parts[3]);
                    
                    // Create list for this drone ID if it doesn't exist
                    coordinatesMap.putIfAbsent(droneId, new ArrayList<>());
                    
                    // Add coordinates to the list for this drone
                    coordinatesMap.get(droneId).add(new double[]{x, y});
                }
            }
            
            reader.close();
            
            // Convert lists to arrays for each drone ID
            for (Map.Entry<Integer, List<double[]>> entry : coordinatesMap.entrySet()) {
                int droneId = entry.getKey();
                List<double[]> coords = entry.getValue();
                
                double[][] pathArray = new double[coords.size()][2];
                for (int i = 0; i < coords.size(); i++) {
                    pathArray[i] = coords.get(i);
                }
                
                dronePathsMap.put(droneId, pathArray);
                
                System.out.println("DroneMobilityModel2: Loaded " + pathArray.length + " points for drone ID " + droneId);
            }
            
            // Print arrays for confirmation
            for (Map.Entry<Integer, double[][]> entry : dronePathsMap.entrySet()) {
                System.out.println("Path for drone ID " + entry.getKey() + " = {");
                for (double[] coords : entry.getValue()) {
                    System.out.println("    {" + coords[0] + ", " + coords[1] + "},");
                }
                System.out.println("}");
            }
            
        } catch (IOException e) {
            System.err.println("Error reading drone_path.csv file: " + e.getMessage());
            e.printStackTrace();
            
            // In case of error, create a default path for drone ID 0
            double[][] defaultPath = new double[][]{
                {0,0}
            };
            dronePathsMap.put(0, defaultPath);
        }
    }

    // Method for initializing the ID and first position logging
    public void initializeWithId(int id) {
        this.deviceId = id;
        
        // Assign the correct path for this drone ID
        if (dronePathsMap.containsKey(id)) {
            currentDronePath = dronePathsMap.get(id);
        } else {
            System.out.println("WARNING: No path found for drone with ID " + id + ". Using path ID 0 or default");
            
            // Use drone 0 path or a default
            if (dronePathsMap.containsKey(0)) {
                currentDronePath = dronePathsMap.get(0);
            } else if (!dronePathsMap.isEmpty()) {
                // Take any available path
                currentDronePath = dronePathsMap.values().iterator().next();
            } else {
                // Create a default path
                currentDronePath = new double[][]{
                    {0,0}
                };
            }
        }
        
        if (this.isMobile && !initialPositionSet && currentDronePath.length > 0) {
            // Set position based on the path
            this.currentLocation = new Location(currentDronePath[0][0], currentDronePath[0][1]);
            initialPositionSet = true;
            
            // Update DroneLogger with initial values
            DroneLogger.getInstance().logDronePosition(
                this.deviceId,
                simulationManager.getSimulation().clock(),
                this.currentLocation
            );
        }
    }

    @Override
    protected Location getNextLocation(Location location) {
        // Make sure it starts from the correct position even if the position changed after the constructor
        if (this.isMobile && !initialPositionSet) {
            if (currentDronePath == null || currentDronePath.length == 0) {
                // Random position between 100 and 300
                double randomX = 100 + random.nextDouble() * 200;
                double randomY = 100 + random.nextDouble() * 200;
                location = new Location(randomX, randomY);
            } else {
                location = new Location(currentDronePath[0][0], currentDronePath[0][1]);
            }
            initialPositionSet = true;
            return location;
        }
        
        // If not a mobile node (drone), return unchanged position
        if (!this.isMobile || currentDronePath == null || currentDronePath.length == 0) {
            return location;
        }
        
        // We are always moving toward the next position
        // Check validity of indices
        if (nextNodeIndex >= currentDronePath.length) {
            // Stay at the last position in the array
            nextNodeIndex = currentDronePath.length - 1;
            
            // Return current position, as there is no next
            return location;
        }
        
        // Coordinates of the next destination
        double targetX = currentDronePath[nextNodeIndex][0];
        double targetY = currentDronePath[nextNodeIndex][1];
        
        // Calculate distance to target
        double dx = targetX - location.getXPos();
        double dy = targetY - location.getYPos();
        double distance = Math.sqrt(dx*dx + dy*dy);
        
        // Print drone movement information
        System.out.println("Drone ID " + this.deviceId + " - Moving from: (" + location.getXPos() + ", " + location.getYPos() + 
                         ") to: (" + targetX + ", " + targetY + 
                         "), Distance: " + distance + 
                         ", Speed: " + getSpeed());
        
        // If we reached the destination (or very close)
        if (distance < getSpeed() * SimulationParameters.updateInterval) {
            // Update indices
            currentGnbIndex = nextNodeIndex;
            nextNodeIndex++;
            
            // If we reached the end, stay there
            if (nextNodeIndex >= currentDronePath.length) {
                nextNodeIndex = currentDronePath.length - 1;
            }
            
            // Set new position exactly at the destination
            Location newLocation = new Location(targetX, targetY);
            
            System.out.println("Drone ID " + this.deviceId + " - REACHED destination: (" + targetX + ", " + targetY + ")");
            
            // If we're not at the end, show the next destination
            if (nextNodeIndex < currentDronePath.length && nextNodeIndex != currentGnbIndex) {
                System.out.println("Next destination: (" + 
                               currentDronePath[nextNodeIndex][0] + ", " + 
                               currentDronePath[nextNodeIndex][1] + ")");
            } else {
                System.out.println("Final destination reached. The drone remains at the last position.");
            }
            
            return newLocation;
        } else {
            // Continue moving toward the next destination
            // Calculate direction to target
            double ratio = getSpeed() * SimulationParameters.updateInterval / distance;
            
            // New position approaching the target
            double newX = location.getXPos() + dx * ratio;
            double newY = location.getYPos() + dy * ratio;
            
            return new Location(newX, newY);
        }
    }
    
    // Override method that returns current position
    @Override
    public Location getCurrentLocation() {
        // If this is the first call for the drone, return initial position
        if (this.isMobile && !initialPositionSet) {
            if (currentDronePath == null || currentDronePath.length == 0) {
                // Random position between 100 and 300
                double randomX = 100 + random.nextDouble() * 200;
                double randomY = 100 + random.nextDouble() * 200;
                this.currentLocation = new Location(randomX, randomY);
            } else {
                this.currentLocation = new Location(currentDronePath[0][0], currentDronePath[0][1]);
            }
            initialPositionSet = true;
        }
        return super.getCurrentLocation();
    }

    // updateLocation is the method that updates the drone position during runtime
    @Override
    public Location updateLocation(double time) {
        if (this.isMobile && !initialPositionSet) {
            if (currentDronePath == null || currentDronePath.length == 0) {
                // Random position between 100 and 300
                double randomX = 100 + random.nextDouble() * 200;
                double randomY = 100 + random.nextDouble() * 200;
                this.currentLocation = new Location(randomX, randomY);
            } else {
                this.currentLocation = new Location(currentDronePath[0][0], currentDronePath[0][1]);
            }
            initialPositionSet = true;
        }
        
        Location updatedLocation = super.updateLocation(time);
        
        if (this.isMobile) {
            // Add position to path with drone ID
            DroneLogger.getInstance().logDronePosition(
                this.deviceId, // Use the drone ID
                time,
                updatedLocation
            );
        }
        
        return updatedLocation;
    }
    
    // Getter for currentGnbIndex needed by DroneNetworkModel
    public int getCurrentGnbIndex() {
        return currentGnbIndex;
    }

    // Method to get drone ID
    public int getDeviceId() {
        return deviceId;
    }
} 