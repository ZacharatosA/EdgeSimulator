package ForkliftSim;

import com.mechalikh.pureedgesim.locationmanager.Location;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters; 
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.locationmanager.MobilityModel;
import java.util.Random;

public class ForkliftMobilityModel extends MobilityModel {
    // Μεταβλητές για παρακολούθηση της θέσης και της κίνησης
    private boolean initialPositionSet = false; // Έλεγχος αν έχει τεθεί η αρχική θέση
    private int deviceId = -1; // ID του forklift
    private Random random; // Για τυχαίες θέσεις
    private Location targetLocation; // Ο στόχος προς τον οποίο κινούμαστε
    private static final int NUM_EDGE_DEVICES = 50; // Αριθμός edge devices
    private boolean firstTargetReached = false; // Έλεγχος αν έχει φτάσει στον πρώτο στόχο
    
    // Ο πρώτος στόχος για όλα τα edge devices
    private static final Location FIRST_TARGET = new Location(122, 109);
    
    public ForkliftMobilityModel(SimulationManager simulationManager, Location currentLocation) {
        super(simulationManager, currentLocation);
        
        // Άμεση αρχικοποίηση της θέσης για κινητό κόμβο (forklift)
        if (this.isMobile) {
            // Η αρχική θέση θα οριστεί όταν γνωρίζουμε το ID του forklift
            initialPositionSet = false;
        }
    }

    // Μέθοδος για την αρχικοποίηση του ID και την πρώτη καταγραφή θέσης
    public void initializeWithId(int id) {
        this.deviceId = id;
        // Αρχικοποίηση του Random με seed το ID του device για σταθερή τροχιά ανά προσομοίωση
        this.random = new Random(id);
        
        if (this.isMobile && !initialPositionSet) {
            // Υπολογισμός της αρχικής θέσης με βάση το ID
            double startX = (id * 400.0) / NUM_EDGE_DEVICES;
            double startY = (id % 2 == 0) ? 0 : 400; // Ζυγό ID -> y=0, Μονό ID -> y=400
            this.currentLocation = new Location(startX, startY);
            initialPositionSet = true;
            
            // Ορίζουμε τον πρώτο στόχο
            targetLocation = FIRST_TARGET;
            
            // Ενημέρωση του ForkliftLogger με τις αρχικές τιμές
            ForkliftLogger.getInstance().logForkliftPosition(
                this.deviceId,
                simulationManager.getSimulation().clock(),
                this.currentLocation
            );
        }
    }

    // Μέθοδος για την επιλογή νέου στόχου
    private void selectNewTarget() {
        // Επιλογή πλήρως τυχαίας θέσης X
        double newX = random.nextDouble() * 400.0;
        
        // Επιλογή πλήρως τυχαίας θέσης Y
        double newY = random.nextDouble() * 400.0;
        
        // Δημιουργία του νέου targetLocation
        targetLocation = new Location(newX, newY);
    }

    @Override
    protected Location getNextLocation(Location location) {
        // Βεβαιωνόμαστε ότι ξεκινά από τη σωστή θέση
        if (this.isMobile && !initialPositionSet) {
            // Υπολογισμός της αρχικής θέσης με βάση το ID
            double startX = (deviceId * 400.0) / NUM_EDGE_DEVICES;
            location = new Location(startX, 0);
            initialPositionSet = true;
            targetLocation = FIRST_TARGET;
            return location;
        }
        
        // Αν δεν είναι κινητός κόμβος (forklift), επιστρέφουμε αμετάβλητη τη θέση
        if (!this.isMobile) {
            return location;
        }
        
        // Κίνηση προς τον στόχο
        double currentX = location.getXPos();
        double currentY = location.getYPos();
        
        // Υπολογισμός απόστασης από τον στόχο
        double dx = targetLocation.getXPos() - currentX;
        double dy = targetLocation.getYPos() - currentY;
        double distance = Math.sqrt(dx*dx + dy*dy);
        
        // Αν φτάσαμε στον στόχο (ή πολύ κοντά)
        if (distance < getSpeed() * SimulationParameters.updateInterval) {
            // Ενημερώνουμε την τρέχουσα θέση
            currentLocation = targetLocation;
            
            // Αν δεν έχουμε φτάσει στον πρώτο στόχο, τον ορίζουμε
            if (!firstTargetReached) {
                firstTargetReached = true;
                // Επιλογή νέου τυχαίου στόχου
                selectNewTarget();
            } else {
                // Επιλογή νέου τυχαίου στόχου
                selectNewTarget();
            }
            
            // Επιστρέφουμε τη νέα θέση
            return currentLocation;
        } else {
            // Συνεχίζουμε την κίνηση προς τον στόχο
            // Υπολογισμός της επόμενης θέσης στην ευθεία γραμμή προς τον στόχο
            double ratio = getSpeed() * SimulationParameters.updateInterval / distance;
            double newX = currentX + dx * ratio;
            double newY = currentY + dy * ratio;
            
            // Ενημερώνουμε την τρέχουσα θέση
            currentLocation = new Location(newX, newY);
            return currentLocation;
        }
    }
    
    // Επικάλυψη της μεθόδου που επιστρέφει την τρέχουσα θέση
    @Override
    public Location getCurrentLocation() {
        // Αν είναι η πρώτη κλήση για το forklift, επιστρέφουμε την αρχική θέση
        if (this.isMobile && !initialPositionSet) {
            double startX = (deviceId * 400.0) / NUM_EDGE_DEVICES;
            this.currentLocation = new Location(startX, 0);
            initialPositionSet = true;
            targetLocation = FIRST_TARGET;
        }
        return super.getCurrentLocation();
    }

    // H updateLocation είναι η μέθοδος που ενημερώνει τη θέση του Forklift κατά το RunTime 
    @Override
    public Location updateLocation(double time) {
        if (this.isMobile && !initialPositionSet) {
            double startX = (deviceId * 400.0) / NUM_EDGE_DEVICES;
            this.currentLocation = new Location(startX, 0);
            initialPositionSet = true;
            targetLocation = FIRST_TARGET;
        }
        
        Location updatedLocation = super.updateLocation(time);
        
        if (this.isMobile) {
            // Προσθήκη της θέσης στο path με το ID του forklift
            ForkliftLogger.getInstance().logForkliftPosition(
                this.deviceId,
                time,
                updatedLocation
            );
        }
        
        return updatedLocation;
    }
    
    // Μέθοδος για λήψη του ID του forklift
    public int getDeviceId() {
        return deviceId;
    }
} 