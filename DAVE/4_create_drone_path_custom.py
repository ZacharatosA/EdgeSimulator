import csv
import networkx as nx
import argparse
import json
import os
from collections import deque

# Initial node definition
START_NODE = '21'  
# Number of drones
NUM_DRONES = 5

def load_graph_from_csv(csv_file):
    """Loads the graph from a CSV file."""
    G = nx.Graph()
    node_coords = {}  # For storing coordinates
    
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            node_id = row['id']
            # Parse normalized_coordinates
            coords_str = row['normalized_coordinates'].strip('[]').split(',')
            x = int(coords_str[0])
            y = int(coords_str[1])
            node_coords[node_id] = (x, y)
            
            # Parse connections
            connections_str = row['connections'].strip('[]').replace("'", "").split(',')
            connections = [c.strip() for c in connections_str]
            
            # Parse edge_distances
            edge_distances_str = row['edge_distances'].replace("'", '"')
            try:
                edge_distances = json.loads(edge_distances_str)
            except json.JSONDecodeError:
                # Alternative parsing if JSON is not valid
                edge_distances = {}
                parts = edge_distances_str.strip('{}').split(',')
                for part in parts:
                    if ':' in part:
                        k, v = part.split(':')
                        edge_distances[k.strip()] = int(v.strip())
            
            # Add node
            G.add_node(node_id, pos=(x, y))
            
            # Add edges with weights
            for conn in connections:
                if conn and conn in edge_distances:
                    weight = edge_distances[conn]
                    G.add_edge(node_id, conn, weight=weight)
    
    return G, node_coords

def find_leaf_nodes(G):
    """Find all leaf nodes in the graph (nodes with only one connection)."""
    leaf_nodes = []
    for node in G.nodes():
        if G.degree(node) == 1:
            leaf_nodes.append(node)
    return leaf_nodes

def find_all_paths_to_leaves(G, start_node):
    """Find all paths from the starting node to leaf nodes."""
    leaf_nodes = find_leaf_nodes(G)
    all_paths = []
    all_path_weights = []
    
    for leaf in leaf_nodes:
        try:
            # Use networkx's all_simple_paths function to find all simple paths
            paths = list(nx.all_simple_paths(G, start_node, leaf))
            
            for path in paths:
                # Calculate total weight of the path
                total_weight = 0
                for i in range(len(path) - 1):
                    total_weight += G[path[i]][path[i+1]]['weight']
                
                all_paths.append(path)
                all_path_weights.append(total_weight)
        except nx.NetworkXNoPath:
            continue
    
    return all_paths, all_path_weights

def find_worst_path(paths, path_weights):
    """Find the worst path (with the largest total weight)."""
    if not paths:
        return None
    
    max_weight_idx = path_weights.index(max(path_weights))
    return paths[max_weight_idx], path_weights[max_weight_idx]

def create_smart_path(G, start_node, worst_path=None):
    """
    Creates a path that passes through all nodes, avoiding
    the worst path when alternatives exist.
    
    Returns:
        path: List of nodes constituting the path
        total_distance: Total distance of the path
    """
    if not start_node:
        # Use START_NODE if no starting node is specified
        start_node = START_NODE if START_NODE in G.nodes() else list(G.nodes())[0]
    
    # Convert worst_path to a set for quick checking
    worst_path_set = set(worst_path) if worst_path else set()
    
    remaining_nodes = set(G.nodes())
    path = [start_node]
    current = start_node
    remaining_nodes.remove(current)
    
    # For calculating total distance
    total_distance = 0
    
    # Continue until all nodes are visited
    while remaining_nodes:
        next_candidates = []
        
        # Find all candidate next nodes
        for target in remaining_nodes:
            try:
                shortest_path = nx.dijkstra_path(G, current, target, weight='weight')
                path_length = nx.dijkstra_path_length(G, current, target, weight='weight')
                
                # Check how many nodes in the path belong to the worst path
                overlap_count = sum(1 for node in shortest_path if node in worst_path_set)
                
                next_candidates.append((target, path_length, shortest_path, overlap_count))
            except nx.NetworkXNoPath:
                continue
        
        if not next_candidates:
            print(f"Cannot reach any remaining nodes from {current}")
            break
        
        # Sort candidates first by overlap with worst path
        # and then by total length
        next_candidates.sort(key=lambda x: (x[3], x[1]))
        
        # Select the best candidate
        best_candidate = next_candidates[0]
        target, path_length, shortest_path, _ = best_candidate
        
        # Add path to the total (except current node)
        path.extend(shortest_path[1:])
        
        # Add distance to total
        total_distance += path_length
        
        # Update current node and remaining nodes
        for node in shortest_path[1:]:
            if node in remaining_nodes:
                remaining_nodes.remove(node)
        
        current = target
    
    return path, total_distance

def find_split_points(G, path, total_distance, num_drones):
    """Finds the split points of the path for multiple drones with overlap."""
    if num_drones <= 1:
        return [0] * len(path)  # All points belong to drone 0
    
    target_distance = total_distance / num_drones
    split_points = []
    current_distance = 0
    current_drone = 0
    
    # List to store drone change points
    change_points = []
    
    for i in range(len(path) - 1):
        # Calculate distance between current nodes
        node1, node2 = path[i], path[i+1]
        edge_distance = G[node1][node2]['weight']
        
        # Check if we need to change drone
        if current_distance + edge_distance > target_distance * (current_drone + 1):
            change_points.append(i)  # Store change point
            current_drone = min(current_drone + 1, num_drones - 1)
        
        split_points.append(current_drone)
        current_distance += edge_distance
    
    # Add the last point
    split_points.append(current_drone)
    
    # Apply overlap - extend each drone's path to the first node of the next drone
    for i, change_point in enumerate(change_points):
        if change_point < len(split_points) - 1:  # Check we're not at the end
            # Find the first node of the next drone
            next_drone_start = change_point + 1
            # Extend current drone to this node
            for j in range(change_point + 1, next_drone_start + 1):
                if j < len(split_points):
                    split_points[j] = split_points[change_point]
    
    return split_points

def save_path_to_csv(path, node_coords, output_file, drone_ids):
    """Saves the path to a CSV file with drone_id and adds lines for edges between drones."""
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['NodeID', 'X', 'Y', 'drone_id'])
        
        # Find drone change points
        change_points = []
        for i in range(len(drone_ids) - 1):
            if drone_ids[i] != drone_ids[i + 1]:
                change_points.append(i)
        
        # Write points and add extra lines for edges
        for i, node in enumerate(path):
            x, y = node_coords[node]
            writer.writerow([node, x, y, drone_ids[i]])
            
            # If it's a drone change point, add the edge to the current drone
            if i in change_points and i < len(path) - 1:
                next_node = path[i + 1]
                next_x, next_y = node_coords[next_node]
                writer.writerow([next_node, next_x, next_y, drone_ids[i]])

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Create a smart path avoiding worst path to leaf nodes.')
    parser.add_argument('--input', default='Generated_Files/mv_nodes_info.csv', help='Input CSV file')
    parser.add_argument('--output-csv', default='Generated_Files/drone_path.csv', help='Output CSV file')
    parser.add_argument('--start-node', default=START_NODE, help='Starting node')
    parser.add_argument('--num-drones', type=int, default=NUM_DRONES, help='Number of drones to use')
    
    args = parser.parse_args()
    
    # Handle relative file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.isabs(args.input):
        input_file = args.input
    else:
        input_file = os.path.join(script_dir, args.input)
    
    output_csv = os.path.join(script_dir, args.output_csv)
    
    print(f"Loading data from {input_file}")
    
    # Load graph from CSV
    G, node_coords = load_graph_from_csv(input_file)
    
    # Check if start_node exists in the graph
    if args.start_node not in G.nodes():
        print(f"Starting node '{args.start_node}' not found in the graph. Available nodes: {list(G.nodes())}")
        print(f"Using first available node instead: {list(G.nodes())[0]}")
        start_node = list(G.nodes())[0]
    else:
        start_node = args.start_node
    
    # Find all paths to leaf nodes
    print(f"Finding all paths from {start_node} to leaf nodes...")
    paths, path_weights = find_all_paths_to_leaves(G, start_node)
    
    if not paths:
        print("No paths to leaf nodes found.")
        worst_path = None
        worst_path_weight = 0
    else:
        # Find the worst path
        worst_path, worst_path_weight = find_worst_path(paths, path_weights)
        print(f"\nWorst path (weight {worst_path_weight}):")
        print(" -> ".join(worst_path))
    
    # Create smart path avoiding the worst path
    print(f"\nCreating smart path starting from {start_node}, avoiding worst path when possible...")
    smart_path, total_distance = create_smart_path(G, start_node, worst_path)
    
    # Find split points for drones
    drone_ids = find_split_points(G, smart_path, total_distance, args.num_drones)
    
    # Calculate distance per drone
    drone_distances = [0] * args.num_drones
    for i in range(len(smart_path) - 1):
        current_node = smart_path[i]
        next_node = smart_path[i + 1]
        distance = G[current_node][next_node]['weight']
        drone_distances[drone_ids[i]] += distance
    
    # Print the path
    print("\nSmart path sequence:")
    current_drone = None
    for i, node in enumerate(smart_path):
        is_in_worst = "* " if worst_path and node in worst_path else ""
        drone_id = drone_ids[i]
        
        # Check if it's a drone change point
        if i < len(smart_path) - 1 and drone_ids[i] != drone_ids[i + 1]:
            print(f"{i+1}. {is_in_worst}{node} (Drone {drone_id})")
            print(f"{i+2}. {is_in_worst}{smart_path[i+1]} (Drone {drone_id}) [Overlap]")
        else:
            print(f"{i+1}. {is_in_worst}{node} (Drone {drone_id})")
    
    # Print distances per drone
    print("\nDistances per drone:")
    for i, distance in enumerate(drone_distances):
        print(f"Drone {i}: {distance} meters")
    
    # Print total distance
    print(f"\nTotal path distance: {total_distance} meters")
    
    # Save to CSV
    save_path_to_csv(smart_path, node_coords, output_csv, drone_ids)
    print(f"Path saved to CSV in {output_csv}")

if __name__ == "__main__":
    main() 