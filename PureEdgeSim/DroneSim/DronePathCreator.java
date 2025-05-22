package DroneSim;

import java.io.*;
import java.util.*;
import java.util.Properties;

/**
 * Class that creates a path for drones based on a CSV data file.
 * This implementation is simpler and doesn't require external libraries.
 */
public class DronePathCreator {
    // Constants
    private static final String START_NODE = "21"; // Initial node
    private static int NUM_DRONES = 1; // Default value, will be changed from properties file
    
    // Class that represents a node in the graph
    private static class Node {
        String id;
        int x;
        int y;
        Map<String, Integer> connections = new HashMap<>();
        
        public Node(String id, int x, int y) {
            this.id = id;
            this.x = x;
            this.y = y;
        }
        
        @Override
        public String toString() {
            return "Node[" + id + " at (" + x + "," + y + ")]";
        }
    }

    /**
     * Class that represents a path with its weight.
     */
    private static class Path {
        List<String> nodes;
        int weight;
        
        public Path(List<String> nodes, int weight) {
            this.nodes = nodes;
            this.weight = weight;
        }
    }
    
    /**
     * Loads the number of drones from the settings file.
     */
    private static void loadNumDronesFromProperties() {
        try {
            Properties properties = new Properties();
            String propertiesFile = "DroneSim/Drone_settings/simulation_parameters.properties";
            
            // Check if file exists
            File file = new File(propertiesFile);
            if (!file.exists()) {
                System.out.println("Properties file not found: " + propertiesFile + 
                               ". Using default value NUM_DRONES=" + NUM_DRONES);
                return;
            }
            
            // Load properties file
            FileInputStream input = new FileInputStream(propertiesFile);
            properties.load(input);
            input.close();
            
            // Read max_number_of_edge_devices value
            String numDronesStr = properties.getProperty("max_number_of_edge_devices");
            if (numDronesStr != null && !numDronesStr.trim().isEmpty()) {
                try {
                    NUM_DRONES = Integer.parseInt(numDronesStr.trim());
                    System.out.println("Loaded number of drones from properties file: NUM_DRONES=" + NUM_DRONES);
                } catch (NumberFormatException e) {
                    System.err.println("Invalid value for max_number_of_edge_devices: " + numDronesStr + 
                                     ". Using default value NUM_DRONES=" + NUM_DRONES);
                }
            } else {
                System.out.println("Parameter max_number_of_edge_devices not found. Using default value NUM_DRONES=" + NUM_DRONES);
                try {
                    System.out.println("Waiting for 4 seconds...");
                    Thread.sleep(10000); // 4 seconds delay
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }
        } catch (IOException e) {
            System.err.println("Error loading properties file: " + e.getMessage());
            System.out.println("Using default value NUM_DRONES=" + NUM_DRONES);
        }
    }
    
    /**
     * Loads nodes from the CSV file.
     */
    private static Map<String, Node> loadNodesFromCsv(String csvFile) {
        Map<String, Node> nodes = new HashMap<>();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(csvFile))) {
            // Skip the first line (headers)
            String line = reader.readLine();

            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);
                String nodeId = parts[0];
                
                // Parse coordinates
                String coordsStr = parts[2].replace("[", "").replace("]", "").replace("\"", "").replace(" ", "");
                String[] coords = coordsStr.split(",");
                int x = 0;
                int y = 0;
                
                try {
                    x = Integer.parseInt(coords[0].trim());
                    y = Integer.parseInt(coords[1].trim());
                } catch (NumberFormatException e) {
                    System.err.println("Error converting coordinates: " + e.getMessage());
                    System.err.println("X value: '" + coords[0].trim() + "'");
                    System.err.println("Y value: '" + coords[1].trim() + "'");
                    continue; // Skip this line and continue with the next
                }
                
                // Create node
                Node node = new Node(nodeId, x, y);
                
                // Parse connections
                String connectionsStr = parts[3].replace("[", "").replace("]", "").replace("'", "").replace("\"", "").replace(" ", "");
                String[] connections = connectionsStr.split(",");
                
                // Parse distances
                Map<String, Integer> edgeDistances = parseEdgeDistances(parts[4]);
                
                // Add connections to the node
                for (String conn : connections) {
                    if (!conn.isEmpty() && edgeDistances.containsKey(conn)) {
                        node.connections.put(conn, edgeDistances.get(conn));
                    }
                }
                
                nodes.put(nodeId, node);
            }
            
            System.out.println("Loaded " + nodes.size() + " nodes from the file.");
            
        } catch (IOException e) {
            System.err.println("Error reading file: " + e.getMessage());
            e.printStackTrace();
        }
        
        return nodes;
    }
    
    /**
     * Parses the edge distances string.
     */
    private static Map<String, Integer> parseEdgeDistances(String edgeDistancesStr) {
        Map<String, Integer> edgeDistances = new HashMap<>();
        
        // Remove {} and whitespace
        edgeDistancesStr = edgeDistancesStr.replace("{", "").replace("}", "").replace("'", "").replace("\"", "").replace(" ", "");
        
        // Split key/value pairs
        String[] pairs = edgeDistancesStr.split(",");
        
        for (String pair : pairs) {
            try {
                String[] keyValue = pair.split(":");
                if (keyValue.length == 2) {
                    String key = keyValue[0].trim();
                    String valueStr = keyValue[1].trim();
                    // Remove double quotes
                    valueStr = valueStr.replace("\"", "");
                    
                    try {
                        Integer value = Integer.parseInt(valueStr);
                        edgeDistances.put(key, value);
                    } catch (NumberFormatException e) {
                        System.err.println("Error converting value: '" + valueStr + "' for key: '" + key + "'");
                    }
                }
            } catch (Exception e) {
                System.err.println("Error processing pair: " + pair);
            }
        }
        
        return edgeDistances;
    }
    
    /**
     * Finds the shortest path between two nodes using Dijkstra's algorithm.
     */
    private static List<String> findShortestPath(Map<String, Node> nodes, String start, String end) {
        // If the nodes start or end don't exist, return an empty list
        if (!nodes.containsKey(start) || !nodes.containsKey(end)) {
            return new ArrayList<>();
        }
        
        Set<String> visited = new HashSet<>();
        Map<String, Integer> distances = new HashMap<>();
        Map<String, String> previous = new HashMap<>();
        PriorityQueue<String> queue = new PriorityQueue<>(
            (a, b) -> distances.getOrDefault(a, Integer.MAX_VALUE) - 
                     distances.getOrDefault(b, Integer.MAX_VALUE));
        
        // Initialize
        for (String nodeId : nodes.keySet()) {
            distances.put(nodeId, Integer.MAX_VALUE);
        }
        distances.put(start, 0);
        queue.add(start);
        
        while (!queue.isEmpty()) {
            String current = queue.poll();
            
            // If we reached the destination, we're done
            if (current.equals(end)) {
                break;
            }
            
            if (visited.contains(current)) {
                continue;
            }
            
            visited.add(current);
            
            // Traverse neighbors
            Node currentNode = nodes.get(current);
            for (Map.Entry<String, Integer> entry : currentNode.connections.entrySet()) {
                String neighbor = entry.getKey();
                int weight = entry.getValue();
                
                if (!visited.contains(neighbor)) {
                    int newDistance = distances.get(current) + weight;
                    
                    if (newDistance < distances.getOrDefault(neighbor, Integer.MAX_VALUE)) {
                        distances.put(neighbor, newDistance);
                        previous.put(neighbor, current);
                        queue.add(neighbor);
                    }
                }
            }
        }
        
        // Reconstruct the path
        List<String> path = new ArrayList<>();
        String current = end;
        
        // If no path was found
        if (!previous.containsKey(end)) {
            return path;
        }
        
        while (current != null) {
            path.add(0, current);
            current = previous.get(current);
        }
        
        return path;
    }
    
    /**
     * Creates a path that traverses all nodes of the graph.
     */
    private static List<String> createPathThroughAllNodes(Map<String, Node> nodes, String startNode) {
        if (!nodes.containsKey(startNode)) {
            startNode = nodes.keySet().iterator().next();
        }
        
        List<String> completePath = new ArrayList<>();
        Set<String> unvisitedNodes = new HashSet<>(nodes.keySet());
        String current = startNode;
        
        completePath.add(current);
        unvisitedNodes.remove(current);
        
        while (!unvisitedNodes.isEmpty()) {
            String nearest = null;
            int minDistance = Integer.MAX_VALUE;
            List<String> shortestPath = null;
            
            // Find the nearest node
            for (String target : unvisitedNodes) {
                List<String> path = findShortestPath(nodes, current, target);
                
                if (!path.isEmpty()) {
                    int distance = calculatePathDistance(nodes, path);
                    
                    if (distance < minDistance) {
                        minDistance = distance;
                        nearest = target;
                        shortestPath = path;
                    }
                }
            }
            
            // If no reachable node was found, we're done
            if (nearest == null) {
                break;
            }
            
            // Add the path to completePath (excluding the first node which is already in the path)
            for (int i = 1; i < shortestPath.size(); i++) {
                completePath.add(shortestPath.get(i));
                unvisitedNodes.remove(shortestPath.get(i));
            }
            
            current = nearest;
        }
        
        return completePath;
    }
    
    /**
     * Calculates the total distance of a path.
     */
    private static int calculatePathDistance(Map<String, Node> nodes, List<String> path) {
        int totalDistance = 0;
        
        for (int i = 0; i < path.size() - 1; i++) {
            String current = path.get(i);
            String next = path.get(i + 1);
            
            Node currentNode = nodes.get(current);
            if (currentNode != null && currentNode.connections.containsKey(next)) {
                totalDistance += currentNode.connections.get(next);
            }
        }
        
        return totalDistance;
    }
    
    /**
     * Finds the split points of the path for multiple drones with overlap.
     */
    private static int[] findSplitPoints(Map<String, Node> nodes, List<String> path, double totalDistance, int numDrones) {
        if (numDrones <= 1) {
            // All points belong to drone 0
            int[] splitPoints = new int[path.size()];
            Arrays.fill(splitPoints, 0);
            return splitPoints;
        }

        double targetDistance = totalDistance / numDrones;
        int[] splitPoints = new int[path.size()];
        double currentDistance = 0;
        int currentDrone = 0;
        
        // List to store change points
        List<Integer> changePoints = new ArrayList<>();

        for (int i = 0; i < path.size() - 1; i++) {
            // Calculate distance between current nodes
            String node1 = path.get(i);
            String node2 = path.get(i + 1);
            
            Node currentNode = nodes.get(node1);
            int edgeDistance = currentNode.connections.getOrDefault(node2, 0);
            
            // Check if we need to change drone
            if (currentDistance + edgeDistance > targetDistance * (currentDrone + 1)) {
                changePoints.add(i);  // Store change point
                currentDrone = Math.min(currentDrone + 1, numDrones - 1);
            }

            splitPoints[i] = currentDrone;
            currentDistance += edgeDistance;
        }
        
        // Add the last point
        splitPoints[path.size() - 1] = currentDrone;

        // Apply overlap - extend the path for each drone until the first node of the next
        for (int i = 0; i < changePoints.size(); i++) {
            int changePoint = changePoints.get(i);
            if (changePoint < splitPoints.length - 1) {  // Check if we're not at the end
                // Find the first node of the next drone
                int nextDroneStart = changePoint + 1;
                // Extend the current drone until this node
                for (int j = changePoint + 1; j <= nextDroneStart; j++) {
                    if (j < splitPoints.length) {
                        splitPoints[j] = splitPoints[changePoint];
                    }
                }
            }
        }

        return splitPoints;
    }

    /**
     * Saves the path to a CSV file with drone_id.
     */
    private static void savePathToCsv(List<String> path, Map<String, Node> nodes, String outputFile, int[] droneIds) {
        FileWriter fw = null;
        BufferedWriter bw = null;
        
        try {
            // Absolute file path
            File file = new File(outputFile);
            String absolutePath = file.getAbsolutePath();
            System.out.println("ABSOLUTE FILE PATH: " + absolutePath);
            
            // Create output directory if it doesn't exist
            File outputDir = file.getParentFile();
            if (outputDir != null && !outputDir.exists()) {
                boolean created = outputDir.mkdirs();
                if (created) {
                    System.out.println("Output directory created: " + outputDir.getAbsolutePath());
                } else {
                    System.err.println("Output directory creation failed: " + outputDir.getAbsolutePath());
                }
            }
            
            // Create new file or overwrite existing
            System.out.println("Overwriting file content: " + file.getAbsolutePath());
            fw = new FileWriter(file, false); // false for overwriting content
            bw = new BufferedWriter(fw);
            
            System.out.println("Saving path to: " + file.getAbsolutePath());
            bw.write("NodeID,X,Y,drone_id");
            bw.newLine();
            
            // Find change points
            List<Integer> changePoints = new ArrayList<>();
            for (int i = 0; i < droneIds.length - 1; i++) {
                if (droneIds[i] != droneIds[i + 1]) {
                    changePoints.add(i);
                }
            }

            // Write points and add extra lines for edges
            for (int i = 0; i < path.size(); i++) {
                String nodeId = path.get(i);
                Node node = nodes.get(nodeId);
                bw.write(nodeId + "," + node.x + "," + node.y + "," + droneIds[i]);
                bw.newLine();
                
                // If it's a change point, add the edge to the current drone
                if (changePoints.contains(i) && i < path.size() - 1) {
                    String nextNode = path.get(i + 1);
                    Node next = nodes.get(nextNode);
                    bw.write(nextNode + "," + next.x + "," + next.y + "," + droneIds[i]);
                    bw.newLine();
                }
            }
            
            // Close streams
            bw.flush();
            System.out.println("File written successfully");
            
            // Check if the file was created successfully
            if (file.exists() && file.length() > 0) {
                System.out.println("Path saved successfully to file: " + file.getAbsolutePath());
                System.out.println("File size: " + file.length() + " bytes");
            } else {
                System.err.println("WARNING: File " + file.getAbsolutePath() + " does not exist or is empty!");
            }
            
        } catch (IOException e) {
            System.err.println("Error writing file: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // Close streams in finally block to ensure they will close
            try {
                if (bw != null) bw.close();
                if (fw != null) fw.close();
                System.out.println("File closed successfully.");
            } catch (IOException e) {
                System.err.println("Error closing file: " + e.getMessage());
            }
        }
    }
    
    /**
     * Finds the leaf nodes of the graph (nodes with only one connection).
     */
    private static List<String> findLeafNodes(Map<String, Node> nodes) {
        List<String> leafNodes = new ArrayList<>();
        
        for (Map.Entry<String, Node> entry : nodes.entrySet()) {
            if (entry.getValue().connections.size() == 1) {
                leafNodes.add(entry.getKey());
            }
        }
        
        return leafNodes;
    }
    
    /**
     * Finds all paths from the initial node to the leaves.
     */
    private static List<Path> findAllPathsToLeaves(Map<String, Node> nodes, String startNode) {
        List<String> leafNodes = findLeafNodes(nodes);
        List<Path> allPaths = new ArrayList<>();
        
        for (String leafNode : leafNodes) {
            if (!leafNode.equals(startNode)) {
                List<List<String>> paths = findAllPaths(nodes, startNode, leafNode, new ArrayList<>(), new HashSet<>());
                
                for (List<String> path : paths) {
                    int weight = calculatePathDistance(nodes, path);
                    allPaths.add(new Path(path, weight));
                }
            }
        }
        
        return allPaths;
    }
    
    /**
     * Helper method to find all paths between two nodes.
     */
    private static List<List<String>> findAllPaths(Map<String, Node> nodes, String start, String end, 
                                                 List<String> currentPath, Set<String> visited) {
        List<List<String>> result = new ArrayList<>();
        
        // Add the current node to the path and mark it as visited
        currentPath.add(start);
        visited.add(start);
        
        // If we reached the final node, return the path
        if (start.equals(end)) {
            result.add(new ArrayList<>(currentPath));
        } else {
            // Traverse neighbors
            Node currentNode = nodes.get(start);
            if (currentNode != null) {
                for (String neighbor : currentNode.connections.keySet()) {
                    if (!visited.contains(neighbor)) {
                        List<List<String>> newPaths = findAllPaths(nodes, neighbor, end, 
                                                                 new ArrayList<>(currentPath), new HashSet<>(visited));
                        result.addAll(newPaths);
                    }
                }
            }
        }
        
        return result;
    }
    
    /**
     * Finds the worst path (with the largest weight).
     */
    private static Path findWorstPath(List<Path> paths) {
        if (paths.isEmpty()) {
            return null;
        }
        
        Path worstPath = paths.get(0);
        
        for (Path path : paths) {
            if (path.weight > worstPath.weight) {
                worstPath = path;
            }
        }
        
        return worstPath;
    }
    
    /**
     * Creates a smart path that passes through all nodes, avoiding the worst path.
     */
    private static List<String> createSmartPath(Map<String, Node> nodes, String startNode, List<String> worstPath) {
        List<String> path = new ArrayList<>();
        Set<String> remainingNodes = new HashSet<>(nodes.keySet());
        Set<String> worstPathSet = new HashSet<>();
        
        // Convert the worst path to a set for quick check
        if (worstPath != null) {
            worstPathSet.addAll(worstPath);
        }
        
        path.add(startNode);
        remainingNodes.remove(startNode);
        final String[] currentRef = {startNode}; // Use a final array to "hold" the current value
        
        // Total distance for return
        int totalDistance = 0;
        
        while (!remainingNodes.isEmpty()) {
            // Candidate next nodes with their distances
            List<Map.Entry<String, Integer>> nextCandidates = new ArrayList<>();
            
            // For each remaining node, find the shortest path
            for (String target : remainingNodes) {
                List<String> shortestPath = findShortestPath(nodes, currentRef[0], target);
                
                if (!shortestPath.isEmpty()) {
                    int pathDistance = calculatePathDistance(nodes, shortestPath);
                    
                    // Count how many nodes of the path belong to the worst path
                    int overlapCount = 0;
                    for (String node : shortestPath) {
                        if (worstPathSet.contains(node)) {
                            overlapCount++;
                        }
                    }
                    
                    // Store the candidate with overlap and distance
                    Map<String, Integer> candidateInfo = new HashMap<>();
                    candidateInfo.put(target, pathDistance);
                    candidateInfo.put(target + "_overlap", overlapCount);
                    nextCandidates.add(Map.entry(target, overlapCount)); // Use overlapCount as value
                }
            }
            
            // If no candidates were found, we're done
            if (nextCandidates.isEmpty()) {
                break;
            }
            
            // Sort candidates first by overlap and then by distance
            nextCandidates.sort((a, b) -> {
                int aOverlap = a.getValue(); // Now the value is actually the overlap
                int bOverlap = b.getValue();
                
                if (aOverlap != bOverlap) {
                    return Integer.compare(aOverlap, bOverlap);
                } else {
                    // If they have the same overlap, compare by distance
                    int aDistance = calculatePathDistance(nodes, findShortestPath(nodes, currentRef[0], a.getKey()));
                    int bDistance = calculatePathDistance(nodes, findShortestPath(nodes, currentRef[0], b.getKey()));
                    return Integer.compare(aDistance, bDistance);
                }
            });
            
            // Select the best candidate
            String nextNode = nextCandidates.get(0).getKey();
            List<String> nextPath = findShortestPath(nodes, currentRef[0], nextNode);
            
            // Add the path to the total (excluding the current node)
            for (int i = 1; i < nextPath.size(); i++) {
                String node = nextPath.get(i);
                path.add(node);
                remainingNodes.remove(node);
            }
            
            // Update the current node
            currentRef[0] = nextNode;
        }
        
        return path;
    }
    
    /**
     * Main method.
     */
    public static void main(String[] args) {
        // Load the number of drones from the properties file
        loadNumDronesFromProperties();
        
        String inputFile = "DroneSim/mv_nodes_info.csv";
        String outputCsv = "DroneSim/drone_path.csv";
        
        // Test with absolute file paths
        String currentDir = System.getProperty("user.dir");
        System.out.println("Current working directory: " + currentDir);
        
        // Create absolute paths
        File inputFileObj = new File(currentDir, inputFile);
        File outputFileObj = new File(currentDir, outputCsv);
        
        // Update file paths
        inputFile = inputFileObj.getAbsolutePath();
        outputCsv = outputFileObj.getAbsolutePath();
        
        System.out.println("Absolute input file path: " + inputFile);
        System.out.println("Absolute output file path: " + outputCsv);
        
        String startNode = START_NODE;
        int numDrones = NUM_DRONES; // Use the number loaded from the properties file
        
        // Command line parameter check
        if (args.length > 0) {
            inputFile = args[0];
        }
        if (args.length > 1) {
            outputCsv = args[1];
        }
        if (args.length > 2) {
            startNode = args[2];
        }
        if (args.length > 3) {
            try {
                numDrones = Integer.parseInt(args[3]);
            } catch (NumberFormatException e) {
                System.err.println("Invalid drones number: " + args[3] + ". Using default: " + NUM_DRONES);
            }
        }
        
        System.out.println("Loading data from " + inputFile);
        System.out.println("Number of drones: " + numDrones);
        
        // Load nodes from CSV
        Map<String, Node> nodes = loadNodesFromCsv(inputFile);
        
        // Check if the start_node exists
        if (!nodes.containsKey(startNode)) {
            System.out.println("Start node '" + startNode + "' not found in the graph.");
            // Use the first available node
            String firstNode = nodes.keySet().iterator().next();
            System.out.println("Using the first available node: " + firstNode);
            startNode = firstNode;
            System.out.println("Printing all available nodes: " + nodes.keySet());
        }
        
        // Find all paths to leaves
        System.out.println("Finding paths to leaves...");
        List<Path> paths = findAllPathsToLeaves(nodes, startNode);
        
        // Find the worst path
        Path worstPath = findWorstPath(paths);
        if (worstPath != null) {
            System.out.println("\nWorst path (weight " + worstPath.weight + "):");
            System.out.println(String.join(" -> ", worstPath.nodes));
        } else {
            System.out.println("\nNo paths found to leaves.");
        }
        
        // Create a smart path that avoids the worst path
        System.out.println("\nCreating smart path from node " + startNode + "...");
        List<String> path = (worstPath != null) ? 
                           createSmartPath(nodes, startNode, worstPath.nodes) : 
                           createPathThroughAllNodes(nodes, startNode);
        
        // Calculate total distance
        double totalDistance = calculatePathDistance(nodes, path);
        
        // Find split points for the drones
        int[] droneIds = findSplitPoints(nodes, path, totalDistance, numDrones);
        
        // Calculate distance per drone
        double[] droneDistances = new double[numDrones];
        for (int i = 0; i < path.size() - 1; i++) {
            String current = path.get(i);
            String next = path.get(i + 1);
            
            Node currentNode = nodes.get(current);
            if (currentNode != null && currentNode.connections.containsKey(next)) {
                droneDistances[droneIds[i]] += currentNode.connections.get(next);
            }
        }
        
        // Print the path
        System.out.println("\nPath sequence:");
        Set<String> worstPathSet = new HashSet<>();
        if (worstPath != null) {
            worstPathSet.addAll(worstPath.nodes);
        }
        
        for (int i = 0; i < path.size(); i++) {
            String node = path.get(i);
            int droneId = droneIds[i];
            String isInWorst = worstPathSet.contains(node) ? "* " : "";
            
            // Check if it's a change point
            if (i < path.size() - 1 && droneIds[i] != droneIds[i + 1]) {
                System.out.println((i+1) + ". " + isInWorst + node + " (Drone " + droneId + ")");
                System.out.println((i+2) + ". " + isInWorst + path.get(i+1) + " (Drone " + droneId + ") [Overlap]");
            } else {
                System.out.println((i+1) + ". " + isInWorst + node + " (Drone " + droneId + ")");
            }
        }
        
        // Print distances per drone
        System.out.println("\nDistances per drone:");
        for (int i = 0; i < droneDistances.length; i++) {
            System.out.println("Drone " + i + ": " + droneDistances[i] + " meters");
        }
        
        // Print total distance
        System.out.println("\nTotal path distance: " + totalDistance + " meters");
        
        // Save to CSV
        try {
            System.out.println("Attempting to save to file: " + outputCsv);
            savePathToCsv(path, nodes, outputCsv, droneIds);
            System.out.println("Saved to: " + outputCsv);
            
            // Check if the file was created
            File outputFile = new File(outputCsv);
            if (outputFile.exists()) {
                System.out.println("Confirmation: File " + outputCsv + " created successfully.");
                System.out.println("File size: " + outputFile.length() + " bytes");
            } else {
                System.err.println("WARNING: File " + outputCsv + " does not exist after saving!");
            }
        } catch (Exception e) {
            System.err.println("CRITICAL ERROR during CSV file saving: " + e.getMessage());
            e.printStackTrace();
        }
    }
} 