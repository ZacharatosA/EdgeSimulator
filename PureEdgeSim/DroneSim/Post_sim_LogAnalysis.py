import pandas as pd
import numpy as np
from tabulate import tabulate
import matplotlib
matplotlib.use('Agg')  # Change to 'Agg' backend
import matplotlib.pyplot as plt
import os  # Added for path handling
import logging
import sys
import argparse
import re
import traceback
import ast  # For parsing lists and dictionaries from CSV

# Set here the simulation output folder you want to analyze
SIM_OUTPUT_FOLDER = "DroneSim/Drone_output/2025-05-22_12-54-33"

# Definition of paths for all files and folders used
# Base directories
BASE_OUTPUT_DIR = "Drone_output"  # Base output folder
DRONE_SETTINGS_DIR = "Drone_settings"  # Settings folder

# Settings files
SIM_PARAMETERS_FILE = "simulation_parameters.properties"  # Simulation parameters file
ORCHESTRATOR_FILE = "DroneTaskOrchestratorD2.java"  # Orchestrator file

# Data files
MV_NODES_INFO_FILE = "mv_nodes_info.csv"  # MV nodes info file
DRONE_PATH_FILE = "drone_path.csv"  # Drone paths filename

# Output files
SEQUENTIAL_SIM_CSV = "Sequential_simulation.csv"  # General simulation output file
SEQUENTIAL_SIM_TXT = "Sequential_simulation.txt"  # Text simulation output file
SEQUENTIAL_SIM_DRONE_CSV = "Sequential_simulation_drone.csv"  # Drone data file
SIM_ANALYSIS_LOG = "simulation_analysis.log"  # Analysis log file
SIM_SUMMARY_CSV = "simulation_summary.csv"  # Simulation summary file

# Output chart filenames
SUCCESS_RATES_CHART = "success_rates.png"  # Success rates chart
EXECUTION_HEATMAP_CHART = "execution_heatmap_{0}_{1}min.png"  # Execution heatmap chart
INFERENCE_TIME_CHART = "inference_time_distribution.png"  # Inference time distribution chart
SIMULATION_MAP_CHART = "sim_map.png"  # Simulation map chart

# Configuration
SHOW_PLOTS = True  # Set to False to disable plots

# Time window configuration (in minutes) - Define as constants
TIME_WINDOW_START = 0  # Starting minute
TIME_WINDOW_END = 10   # Ending minute 

# Data size settings for each image quality (in KB)
IMAGE_QUALITIES = {
    '240p': 50,     # ~50KB per image
    '480p': 150,    # ~150KB per image
    '720p': 350,    # ~350KB per image
    '1080p': 800,   # ~800KB per image
    '1440p': 2000,  # ~2MB per image
    '2160': 8000   # ~8MB per image
}

# Setting the output folder directly from SIM_OUTPUT_FOLDER variable
output_folder = SIM_OUTPUT_FOLDER
simulation_folder = output_folder
simulation_path = os.path.join(simulation_folder, SEQUENTIAL_SIM_DRONE_CSV)

# Function to print the minute, X, Y table in the terminal
def print_minute_markers_table(minute_markers):
    print("\n=== Drone Positions by Minute ===")
    print("Minute | X | Y")
    print("------|-----|-----")
    
    # Gather all data from all drones
    all_markers = []
    for drone_id, markers in minute_markers.items():
        for time_val, x, y, minute, dx, dy in markers:
            all_markers.append((minute, x, y, drone_id))
    
    # Sort by minute and drone_id
    all_markers.sort()
    
    # Print
    for minute, x, y, drone_id in all_markers:
        print(f"{minute:5d} | {x:5.1f} | {y:5.1f} | Drone {drone_id}")

def create_simulation_map(csv_file, output_folder):
    if not SHOW_PLOTS:
        return
        
    # Use absolute path for simulation_parameters.properties file
    properties_file = "DroneSim/Drone_settings/simulation_parameters.properties"
    length = 5000  # Default value
    width = 5000   # Default value
    coverage_radius = 100.0  # Default value
    
    try:
        with open(properties_file, 'r') as f:
            for line in f:
                if line.startswith('length='):
                    length = int(line.split('=')[1].strip())
                elif line.startswith('width='):
                    width = int(line.split('=')[1].strip())
                elif line.startswith('edge_datacenters_coverage='):
                    coverage_radius = float(line.split('=')[1].strip())
    except Exception as e:
        print(f"Error reading simulation parameters: {e}")
        print(f"Using default values: length={length}, width={width}, coverage_radius={coverage_radius}")
    
    # Reading datacenter positions from the txt file
    datacenter_positions = []
    txt_file = os.path.join(output_folder, SEQUENTIAL_SIM_TXT)
    
    try:
        with open(txt_file, 'r') as f:
            lines = f.readlines()
            reading_datacenters = False
            for line in lines:
                if "===== EDGE DATACENTERS =====" in line:
                    reading_datacenters = True
                    continue
                if reading_datacenters and line.strip():
                    if "Θέση:" in line:
                        parts = line.split("Θέση: ")[1].split(")")[0].strip("(").split(",")
                        x = float(parts[0])
                        y = float(parts[1])
                        name = line.split("-")[0].strip()
                        datacenter_positions.append((name, x, y))
                    elif "Position:" in line:  # Also check for English version
                        parts = line.split("Position: ")[1].split(")")[0].strip("(").split(",")
                        x = float(parts[0])
                        y = float(parts[1])
                        name = line.split("-")[0].strip()
                        datacenter_positions.append((name, x, y))
                if reading_datacenters and not line.strip():
                    break
    except Exception as e:
        print(f"Error reading datacenter positions: {e}")
        print("Continuing without datacenter information...")

    # Reading mv_nodes and their connections
    mv_nodes = {}
    mv_connections = []
    
    try:
        try:
            # Use absolute path for mv_nodes_info.csv file
            mv_nodes_file = "DroneSim/mv_nodes_info.csv"
            mv_df = pd.read_csv(mv_nodes_file)
            print(f"Successfully read mv_nodes_info.csv file")
            for _, row in mv_df.iterrows():
                node_id = int(row['id'])  # Convert to integer
                normalized_coords = ast.literal_eval(row['normalized_coordinates'])
                x, y = normalized_coords
                mv_nodes[node_id] = (x, y)
                
                # Read connections
                connections = ast.literal_eval(row['connections'])
                edge_distances = ast.literal_eval(row['edge_distances'])
                
                for conn in connections:
                    conn_id = int(conn)  # Convert conn to integer
                    # Avoid duplicate connections
                    if node_id < conn_id:
                        distance = edge_distances.get(str(conn), "N/A")
                        mv_connections.append((node_id, conn_id, distance))
        except FileNotFoundError:
            print(f"File mv_nodes_info.csv not found.")
    except Exception as e:
        print(f"Error reading mv_nodes_info.csv: {e}")
        print("Continuing without mv_nodes information...")

    # Reading drone path from csv
    drone_paths = {}  # Dictionary to store paths by ID
    
    # Dictionary to store minute points for each drone
    minute_markers = {}  # Will have the form {drone_id: [(time, x, y), ...]}
    
    try:
        df = pd.read_csv(csv_file)
        # Group points by DroneID
        for drone_id, group in df.groupby('DroneID'):
            drone_paths[drone_id] = list(zip(group['DroneX'], group['DroneY']))
            
            # Find points at each minute (60, 120, 180 sec, etc.)
            minute_markers[drone_id] = []
            minute = 1  # Start from the first minute
            while minute * 60 <= group['Time'].max():  # Until the end of simulation
                target_time = minute * 60
                # Find the row closest to the target time (e.g., 60 sec)
                closest_row = group.iloc[(group['Time'] - target_time).abs().argsort()[:1]]
                if not closest_row.empty:
                    time_val = closest_row['Time'].values[0]
                    # Check if it's actually close to the minute (± 0.2 seconds)
                    if abs(time_val - target_time) < 0.2:
                        x = closest_row['DroneX'].values[0]
                        y = closest_row['DroneY'].values[0]
                        # Find the next position to calculate the direction of the arrow
                        next_minute_time = (minute + 1) * 60
                        next_row = group.iloc[(group['Time'] - next_minute_time).abs().argsort()[:1]]
                        
                        if not next_row.empty and abs(next_row['Time'].values[0] - next_minute_time) < 0.2:
                            next_x = next_row['DroneX'].values[0]
                            next_y = next_row['DroneY'].values[0]
                            
                            # Calculate movement direction
                            dx = next_x - x
                            dy = next_y - y
                            minute_markers[drone_id].append((time_val, x, y, minute, dx, dy))
                        else:
                            # If no next minute found, just store without direction
                            minute_markers[drone_id].append((time_val, x, y, minute, 0, 0))
                minute += 1  # Next minute
    except Exception as e:
        print(f"Error reading drone path: {e}")
        print("Cannot load drone data. The diagram will only contain datacenters and mv_nodes.")
    
    # Print minute table if we have data
    if minute_markers:
        print_minute_markers_table(minute_markers)

    # Creating plot with correct aspect ratio
    plt.figure(figsize=(20, 20))  
    ax = plt.gca()
    
    # Constants
    COVERAGE_RADIUS = coverage_radius  # Edge datacenter coverage
    DATACENTER_RADIUS = 8.0  # Datacenter size (increased from 5.0)
    MV_NODE_RADIUS = 3.0  # MV nodes size
    
    # Create colors for drones
    # Use 'tab10' colormap which has 10 different colors
    colors = plt.cm.tab10(np.linspace(0, 1, len(drone_paths)))
    drone_colors = {drone_id: colors[i] for i, drone_id in enumerate(sorted(drone_paths.keys()))}
    
    # Plot for each datacenter
    datacenter_colors = plt.cm.Set3(np.linspace(0, 1, len(datacenter_positions)))
    for (name, x, y), color in zip(datacenter_positions, datacenter_colors):
        # Plot datacenter - more intense, larger and with outline
        datacenter = plt.Circle((x, y), DATACENTER_RADIUS, 
                              color=color, 
                              alpha=0.9,    # Increased opacity (from 0.7)
                              ec='black',   # Add black outline
                              linewidth=1.5) # Outline thickness
        ax.add_patch(datacenter)
        
        # Plot coverage area
        coverage = plt.Circle((x, y), COVERAGE_RADIUS, color=color, alpha=0.2)
        ax.add_patch(coverage)
        
        # Add label with bolder text
        plt.annotate(name, (x, y), xytext=(5, 5), textcoords='offset points',
                   fontweight='bold', fontsize=9)

    # Plot mv_nodes and their connections
    if mv_nodes:
        # Drawing nodes
        for node_id, (x, y) in mv_nodes.items():
            node = plt.Circle((x, y), MV_NODE_RADIUS, color='purple', alpha=0.7)
            ax.add_patch(node)
            plt.text(x + 10, y, f"N{node_id}", fontsize=7, color='purple')
        
        # Drawing connections
        for node1, node2, distance in mv_connections:
            # Check if node1 and node2 exist in mv_nodes dictionary
            if node1 in mv_nodes and node2 in mv_nodes:
                x1, y1 = mv_nodes[node1]
                x2, y2 = mv_nodes[node2]
                plt.plot([x1, x2], [y1, y2], 'purple', linestyle='--', linewidth=0.7, alpha=0.5)
                
                # Calculate midpoint for distance label
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                plt.text(mid_x, mid_y, f"{distance}", fontsize=6, color='purple',
                        bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=0.1'))
            else:
                print(f"Skipping connection between nodes {node1}-{node2} as mv_nodes data is missing")

    # Plot drone path with arrows for each drone
    for drone_id, path in drone_paths.items():
        if path:
            path_x, path_y = zip(*path)
            color = drone_colors[drone_id]
            
            # Drawing path with thinner line
            plt.plot(path_x, path_y, color=color, alpha=0.2, label=f'Drone {drone_id} Path', linewidth=0.5)
            
            # Add arrows only when position changes - MORE INTENSE ARROWS
            prev_x, prev_y = path_x[0], path_y[0]
            for i in range(1, len(path_x)):
                curr_x, curr_y = path_x[i], path_y[i]
                
                # Check if position changed
                if curr_x != prev_x or curr_y != prev_y:
                    dx = curr_x - prev_x
                    dy = curr_y - prev_y
                    
                    # Calculate arrow size based on distance
                    distance = np.sqrt(dx*dx + dy*dy)
                    if distance > 0:  # Avoid division by zero
                        # Normalize arrow size - MORE INTENSE ARROWS
                        arrow_length = min(distance * 0.3, 15)  # Larger arrow
                        dx_norm = dx * arrow_length / distance
                        dy_norm = dy * arrow_length / distance
                        
                        plt.arrow(prev_x, prev_y, dx_norm, dy_norm,
                                head_width=3.0, head_length=4.0,  # Larger head sizes
                                fc=color, ec=color, alpha=0.8,    # Larger intensity (less transparency)
                                linewidth=1.8,                    # Larger line thickness
                                length_includes_head=True)
                    
                    prev_x, prev_y = curr_x, curr_y
            
            # Add red arrows for each minute of the simulation - MORE INTENSE ARROWS
            if drone_id in minute_markers:
                for time_val, x, y, minute, dx, dy in minute_markers[drone_id]:
                    # Calculate arrow size
                    direction_distance = np.sqrt(dx*dx + dy*dy)
                    
                    if direction_distance > 0:  # If we have movement direction
                        # Create larger arrow for minutes
                        arrow_length = min(direction_distance * 0.5, 30)  # Larger than regular arrows
                        dx_norm = dx * arrow_length / direction_distance
                        dy_norm = dy * arrow_length / direction_distance
                        
                        plt.arrow(x, y, dx_norm, dy_norm,
                                head_width=6.0, head_length=9.0,  # Larger head sizes
                                fc='red', ec='red', alpha=0.9,    # Larger intensity
                                linewidth=2.2,                    # Larger line thickness
                                length_includes_head=True)
                    else:
                        # If no direction, use a simple red circle
                        circle = plt.Circle((x, y), 8, color='red', alpha=0.8)
                        ax.add_patch(circle)

    # Plot settings
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.title('Simulation Map: Edge Datacenters, MV Nodes and Drone Paths')
    
    # Add legend for drones and mv_nodes
    legend_elements = [plt.Line2D([0], [0], color=color, label=f'Drone {drone_id}')
                      for drone_id, color in drone_colors.items()]
    # Add item to legend for red arrows of minutes
    legend_elements.append(plt.Line2D([0], [0], marker='>', color='red', markersize=10, 
                               label='Minute marker (direction)', linestyle='None'))
    # Add item to legend for mv_nodes
    if mv_nodes:
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='purple', markersize=5, 
                                label='MV Node', linestyle='None'))
        legend_elements.append(plt.Line2D([0], [0], color='purple', linestyle='--', alpha=0.5,
                                label='MV Connection'))
    
    plt.legend(handles=legend_elements, loc='upper right')
    
    # Plot settings
    ax.set_aspect('equal')
    plt.xlim(-10, length + 50)  # Use length value
    plt.ylim(-10, width + 50)   # Use width value
    
    # Save
    output_path = os.path.join(output_folder, 'sim_map.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Simulation map saved at: {output_path}")

def get_time_thresholds(times):
    return {
        'min': times.min(),
        'max': times.max(),
        'avg': times.mean(),
        'q1': times.quantile(0.25),
        'q3': times.quantile(0.75)
    }

def get_color(time, stats, status, is_total_time=False):
    if is_total_time:
        # For Total Time, failed tasks are always red
        if status == 'F':
            return 'red'
    
    # For all times with priority
    if time <= stats['q1']:
        return 'green'  # Fast tasks
    elif time >= stats['q3']:
        return 'orange'  # Slow tasks
    else:
        return 'yellow'  # Average tasks

def plot_task_distribution(tasks, title, subplot_pos, first_appearances):
    plt.subplot(2, 1, subplot_pos)
    
    # Adjust column names
    y_positions = {
        'TotalTime': 1.8,
        'NetworkTime': 1.4,
        'WaitingTime': 1.0,
        'ExecutionTime': 0.6
    }
    
    display_names = {
        'TotalTime': 'Total Time',
        'NetworkTime': 'Network Time',
        'WaitingTime': 'Waiting Time',
        'ExecutionTime': 'Execution Time'
    }
    
    # Calculate statistics for each time type
    time_stats = {
        column: get_time_thresholds(tasks[column])
        for column in y_positions.keys()
    }
    
    # Draw each bar
    for column, y_pos in y_positions.items():
        stats = time_stats[column]
        
        # Separate tasks based on status
        colors = [get_color(t, stats, s, is_total_time=(column == 'TotalTime')) 
                 for t, s in zip(tasks[column], tasks['Status'])]
        
        # Draw bar
        plt.scatter(tasks['TimeInMinutes'], 
                   [y_pos] * len(tasks),
                   c=colors,
                   alpha=0.5,
                   s=900 if column == 'TotalTime' else 450,
                   marker='s')
        
        # Add type label - move slightly to the right
        plt.text(TIME_WINDOW_END + 0.03 * (TIME_WINDOW_END - TIME_WINDOW_START), 
                y_pos, 
                display_names[column], 
                va='center')
        
        # Add statistics
        stats_text = f'Fast ≤ {stats["q1"]:.2f}s\nAvg: {stats["avg"]:.2f}s\nSlow ≥ {stats["q3"]:.2f}s'
        plt.text(TIME_WINDOW_END + 0.17 * (TIME_WINDOW_END - TIME_WINDOW_START),
                y_pos,
                stats_text,
                va='center',
                bbox=dict(facecolor='white', alpha=0.8))
    
    # Add color legend with better placement
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, fc='red', alpha=0.5, label='Failed Tasks (Total Time)'),
        plt.Rectangle((0, 0), 1, 1, fc='green', alpha=0.5, label='Fast Tasks'),
        plt.Rectangle((0, 0), 1, 1, fc='yellow', alpha=0.5, label='Average Tasks'),
        plt.Rectangle((0, 0), 1, 1, fc='orange', alpha=0.5, label='Slow Tasks')
    ]
    plt.legend(handles=legend_elements, 
              loc='center left', 
              bbox_to_anchor=(1.02, 0.5),
              borderaxespad=0)
    
    # Add vertical lines for GNB
    for gnb, time in first_appearances.items():
        plt.axvline(x=time, color='gray', linestyle='--', alpha=0.5)
        next_time = next((t for g, t in first_appearances.items() if t > time), TIME_WINDOW_END)
        center = (time + next_time) / 2
        plt.text(center, 2.1, gnb, ha='center', va='bottom')
    
    plt.title(title)
    plt.xlabel('Time (minutes)')
    plt.yticks([])
    # Reduce x-axis extension
    plt.xlim(TIME_WINDOW_START, TIME_WINDOW_END + 0.25 * (TIME_WINDOW_END - TIME_WINDOW_START))
    plt.ylim(0.4, 2.2)

def create_execution_heatmap(df, output_folder):
    if not SHOW_PLOTS:
        return
    
    # Convert time to minutes and filtering
    df['TimeInMinutes'] = df['Time'] / 60.0
    df = df[(df['TimeInMinutes'] >= TIME_WINDOW_START) & (df['TimeInMinutes'] <= TIME_WINDOW_END)]
    
    # Find first appearances of GNB
    first_appearances = {}
    for gnb in range(1, 6):
        gnb_tasks = df[df['ExecutionLocation'] == f'Edge Server: GNB{gnb}']
        if not gnb_tasks.empty:
            first_time = gnb_tasks['TimeInMinutes'].min()
            if first_time >= TIME_WINDOW_START and first_time <= TIME_WINDOW_END:
                first_appearances[f'GNB{gnb}'] = first_time
    
    # Διαχωρισμός tasks
    drone_tasks = df[df['ExecutionLocation'] == 'Far-Edge (Drone)']
    edge_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
    
    # Δημιουργία του γραφήματος με προσαρμοσμένο μέγεθος και layout
    plt.figure(figsize=(15, 12))  # Μικρότερο πλάτος
    
    # Αλλαγή σειράς των γραφημάτων - πρώτα το Drone και μετά τα Edge Servers
    plot_task_distribution(drone_tasks, 'Drone (Far-Edge) Task Distribution', 1, first_appearances)
    plot_task_distribution(edge_tasks, 'Edge Servers Task Distribution', 2, first_appearances)
    
    # Προσαρμογή του layout για καλύτερη εμφάνιση
    plt.tight_layout()
    plt.subplots_adjust(right=0.85)  # Αφήνει χώρο για το legend χωρίς μεγάλα κενά
    
    # Αποθήκευση
    output_path = os.path.join(output_folder, EXECUTION_HEATMAP_CHART.format(TIME_WINDOW_START, TIME_WINDOW_END))
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Execution heatmap saved at: {output_path}")

def main():
    print(f"Analyzing file: {simulation_path}")
    print(f"Results will be saved to: {output_folder}")
    
    # Read the CSV file
    try:
        df = pd.read_csv(simulation_path)
        
        # Calculate Total Time
        df['TotalTime'] = df['NetworkTime'] + df['WaitingTime'] + df['ExecutionTime']
        
        # Create execution heatmap chart
        create_execution_heatmap(df, output_folder)
        
        # Create simulation map
        create_simulation_map(simulation_path, output_folder)
        
        print("Analysis completed successfully!")
    except Exception as e:
        print(f"Error during analysis: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 