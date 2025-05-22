package DroneSim;

import com.mechalikh.pureedgesim.locationmanager.Location;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters; 
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.locationmanager.MobilityModel;
import java.util.Random;

public class DroneMobilityModel extends MobilityModel {
    // Definition of GNB positions for the first drone (clockwise movement)
    private static final double[][] GNB_POSITIONS_DRONE_0 = {
        {100, 100},  //GNB1
        {300, 100},  //GNB2
        {200, 200},  //GNB3
        {100, 300},  //GNB4
        {300, 300}   //GNB5
    };
    
    // Definition of GNB positions for the second drone (counter-clockwise movement)
    private static final double[][] GNB_POSITIONS_DRONE_1 = {
        {300, 300},  //GNB5
        {100, 300},  //GNB4
        {200, 200},  //GNB3
        {300, 100},  //GNB2
        {100, 100}   //GNB1
    };
    
    // Definition of GNB positions for the third drone (starts from GNB2)
    private static final double[][] GNB_POSITIONS_DRONE_2 = {
        {300, 100},  //GNB2
        {200, 200},  //GNB3
        {100, 300},  //GNB4
        {300, 300},  //GNB5
        {100, 100}   //GNB1
    };
    
    // Definition of GNB positions for the fourth drone (starts from GNB4)
    private static final double[][] GNB_POSITIONS_DRONE_3 = {
        {100, 300},  //GNB4
        {200, 200},  //GNB3
        {300, 100},  //GNB2
        {100, 100},  //GNB1
        {300, 300}   //GNB5
    };
    
    // Variables for tracking position and movement
    private int currentGnbIndex = 0;   // Start from the first GNB
    private int nextGnbIndex = 1;      // Next destination is the second GNB
    private double remainingPauseTime = 480; // 8 minutes initial wait
    private boolean isMoving = false;   // Start with pause
    private boolean initialPositionSet = false; // Check if initial position has been set
    private int deviceId = -1; // Drone ID
    private double[][] currentGnbPositions; // Current GNB positions for this drone
    private Random random = new Random(); // For random positions
    
    public DroneMobilityModel(SimulationManager simulationManager, Location currentLocation) {
        super(simulationManager, currentLocation);
        
        // Immediate initialization of position for mobile node (drone)
        if (this.isMobile) {
            // Initial position will be set when we know the drone ID
            initialPositionSet = false;
        }
    }

    // Method for initializing the ID and first position logging
    public void initializeWithId(int id) {
        this.deviceId = id;
        
        // Use modulo 4 to distribute drones among 4 different routes
        int routeIndex = id % 4;
        
        // Select the appropriate path based on ID modulo
        switch (routeIndex) {
            case 0:
                currentGnbPositions = GNB_POSITIONS_DRONE_0; // Starts from GNB1
                break;
            case 1:
                currentGnbPositions = GNB_POSITIONS_DRONE_1; // Starts from GNB5
                break;
            case 2:
                currentGnbPositions = GNB_POSITIONS_DRONE_2; // Starts from GNB2
                break;
            case 3:
                currentGnbPositions = GNB_POSITIONS_DRONE_3; // Starts from GNB4
                break;
            default:
                currentGnbPositions = GNB_POSITIONS_DRONE_0; // Default
        }
        
        if (this.isMobile && !initialPositionSet) {
            // Set position based on drone ID
            this.currentLocation = new Location(currentGnbPositions[0][0], currentGnbPositions[0][1]);
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
            // If ID is not set, use random position
            if (currentGnbPositions == null) {
                // Random position between 100 and 300
                double randomX = 100 + random.nextDouble() * 200;
                double randomY = 100 + random.nextDouble() * 200;
                location = new Location(randomX, randomY);
            } else {
                location = new Location(currentGnbPositions[0][0], currentGnbPositions[0][1]);
            }
            initialPositionSet = true;
            return location;
        }
        
        // If not a mobile node (drone), return unchanged position
        if (!this.isMobile) {
            return location;
        }
        
        // Check if we are in pause state
        if (!isMoving) {
            // Reduce pause time
            remainingPauseTime -= SimulationParameters.updateInterval;
            
            // If the pause time is over, start moving to the next GNB
            if (remainingPauseTime <= 0) {
                isMoving = true;
                // Return current position for this iteration
                return location;
            } else {
                // Stay at the same position
                return location;
            }
        } else {
            // We are moving toward the next GNB
            double targetX = currentGnbPositions[nextGnbIndex][0];
            double targetY = currentGnbPositions[nextGnbIndex][1];
            
            // Calculate distance to target
            double dx = targetX - location.getXPos();
            double dy = targetY - location.getYPos();
            double distance = Math.sqrt(dx*dx + dy*dy);
            
            // If we reached the destination (or very close)
            if (distance < getSpeed() * SimulationParameters.updateInterval) {
                // Update GNB indices
                currentGnbIndex = nextGnbIndex;
                nextGnbIndex = (nextGnbIndex + 1) % currentGnbPositions.length; // Circular change
                
                // Set new position exactly at the GNB
                Location newLocation = new Location(targetX, targetY);
                
                // Start pause
                isMoving = false;
                remainingPauseTime = getMinPauseDuration(); // 8 minutes from edge_devices.xml
                
                return newLocation;
            } else {
                // Continue moving toward the next GNB
                // Calculate direction to target
                double ratio = getSpeed() * SimulationParameters.updateInterval / distance;
                
                // New position approaching the target
                double newX = location.getXPos() + dx * ratio;
                double newY = location.getYPos() + dy * ratio;
                
                return new Location(newX, newY);
            }
        }
    }
    
    // Override method that returns current position
    @Override
    public Location getCurrentLocation() {
        // If this is the first call for the drone, return initial position
        if (this.isMobile && !initialPositionSet) {
            // If ID is not set, use random position
            if (currentGnbPositions == null) {
                // Random position between 100 and 300
                double randomX = 100 + random.nextDouble() * 200;
                double randomY = 100 + random.nextDouble() * 200;
                this.currentLocation = new Location(randomX, randomY);
            } else {
                this.currentLocation = new Location(currentGnbPositions[0][0], currentGnbPositions[0][1]);
            }
            initialPositionSet = true;
        }
        return super.getCurrentLocation();
    }

    // updateLocation is the method that updates the drone position during runtime
    @Override
    public Location updateLocation(double time) {
        if (this.isMobile && !initialPositionSet) {
            // If ID is not set, use random position
            if (currentGnbPositions == null) {
                // Random position between 100 and 300
                double randomX = 100 + random.nextDouble() * 200;
                double randomY = 100 + random.nextDouble() * 200;
                this.currentLocation = new Location(randomX, randomY);
            } else {
                this.currentLocation = new Location(currentGnbPositions[0][0], currentGnbPositions[0][1]);
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