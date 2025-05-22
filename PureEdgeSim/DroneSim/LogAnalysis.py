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

# Definition of paths for all files and folders used
# Base directories
BASE_OUTPUT_DIR = "DroneSim/Drone_output"  # Base output folder
DRONE_SETTINGS_DIR = "DroneSim/Drone_settings"  # Settings folder

# Settings files
SIM_PARAMETERS_FILE = "simulation_parameters.properties"  # Simulation parameters file
ORCHESTRATOR_FILE = "DroneTaskOrchestratorD2.java"  # Orchestrator file

# Data files
MV_NODES_INFO_FILE = "DroneSim/mv_nodes_info.csv"  # MV nodes info file
DRONE_PATH_FILE = "drone_path.csv"  # Drone path filename

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

# Time window configuration (in minutes)
TIME_WINDOW_START = 0  # Starting minute

# Reading simulation time from settings file
def read_simulation_time():
    try:
        # Path to settings file
        properties_file = os.path.join(DRONE_SETTINGS_DIR, SIM_PARAMETERS_FILE)
        
        with open(properties_file, 'r') as f:
            for line in f:
                if line.startswith('simulation_time='):
                    return int(line.split('=')[1].strip())
        
        # If value not found, return default value
        print("Parameter simulation_time not found, using default value 40")
        return 40
    except Exception as e:
        print(f"Error reading simulation_time: {e}")
        return 40  # Default value in case of error

# Setting TIME_WINDOW_END from settings file
TIME_WINDOW_END = read_simulation_time()
print(f"Simulation time (TIME_WINDOW_END) set to: {TIME_WINDOW_END} minutes")

# Data size settings for each image quality (in KB)
IMAGE_QUALITIES = {
    '240p': 50,     # ~50KB per image
    '480p': 150,    # ~150KB per image
    '720p': 350,    # ~350KB per image
    '1080p': 800,   # ~800KB per image
    '1440p': 2000,  # ~2MB per image
    '2160': 8000   # ~8MB per image
}

# Creating the parser
parser = argparse.ArgumentParser(description='Analyze simulation data')
parser.add_argument('output_folder', help='The output folder containing the simulation data')
args = parser.parse_args()

# Setting the base output folder
output_folder = args.output_folder
simulation_folder = os.path.join(BASE_OUTPUT_DIR, output_folder)
simulation_path = os.path.join(simulation_folder, SEQUENTIAL_SIM_DRONE_CSV)

def create_success_rate_plot(df, output_folder):
    if not SHOW_PLOTS:
        return
    
    plt.figure(figsize=(12, 6))
    
    df_sorted = df.sort_values('Time')
    df_sorted['TimeInMinutes'] = df_sorted['Time'] / 60.0
    
    # Συνολικό ποσοστό - αλλαγή χρώματος σε πορτοκαλί
    total_success = (df_sorted['Status'] == 'S').cumsum() / range(1, len(df_sorted) + 1) * 100
    plt.plot(df_sorted['TimeInMinutes'], total_success, label='Overall Success Rate', color='orange')
    
    # Ποσοστό για Drone - αλλαγή χρώματος σε μπλε
    drone_df = df_sorted[df_sorted['ExecutionLocation'] == 'Far-Edge (Drone)']
    if len(drone_df) > 0:
        drone_success = (drone_df['Status'] == 'S').cumsum() / range(1, len(drone_df) + 1) * 100
        plt.plot(drone_df['TimeInMinutes'], drone_success, label='Drone Success Rate', color='blue')
    
    # Ποσοστό για Edge - αλλαγή χρώματος σε πράσινο
    edge_df = df_sorted[df_sorted['ExecutionLocation'].str.contains('Edge Server')]
    if len(edge_df) > 0:
        edge_success = (edge_df['Status'] == 'S').cumsum() / range(1, len(edge_df) + 1) * 100
        plt.plot(edge_df['TimeInMinutes'], edge_success, label='Edge Success Rate', color='green')
    
    plt.xlabel('Time (minutes)')
    plt.ylabel('Success Rate (%)')
    plt.title('Success Rates Over Time')
    plt.grid(True)
    plt.legend()
    
    output_path = os.path.join(output_folder, SUCCESS_RATES_CHART)
    plt.savefig(output_path)
    plt.close()
    print(f"Success rate plot saved at: {output_path}")

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
        # Για το Total Time, τα failed tasks είναι πάντα κόκκινα
        if status == 'F':
            return 'red'
    
    # Για όλους τους χρόνους με priority
    if time <= stats['q1']:
        return 'green'  # Fast tasks
    elif time >= stats['q3']:
        return 'orange'  # Slow tasks
    else:
        return 'yellow'  # Average tasks

def plot_task_distribution(tasks, title, subplot_pos, first_appearances):
    plt.subplot(2, 1, subplot_pos)
    
    # Διόρθωση των ονομάτων των στηλών
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
    
    # Υπολογισμός στατιστικών για κάθε τύπο χρόνου
    time_stats = {
        column: get_time_thresholds(tasks[column])
        for column in y_positions.keys()
    }
    
    # Σχεδίαση κάθε λωρίδας
    for column, y_pos in y_positions.items():
        stats = time_stats[column]
        
        # Διαχωρισμός των tasks με βάση το status
        colors = [get_color(t, stats, s, is_total_time=(column == 'TotalTime')) 
                 for t, s in zip(tasks[column], tasks['Status'])]
        
        # Σχεδίαση της λωρίδας
        plt.scatter(tasks['TimeInMinutes'], 
                   [y_pos] * len(tasks),
                   c=colors,
                   alpha=0.5,
                   s=900 if column == 'TotalTime' else 450,
                   marker='s')
        
        # Προσθήκη ετικέτας τύπου χρόνου - μετακίνηση πιο δεξιά
        plt.text(TIME_WINDOW_END + 0.03 * (TIME_WINDOW_END - TIME_WINDOW_START), 
                y_pos, 
                display_names[column], 
                va='center')
        
        # Προσθήκη στατιστικών
        stats_text = f'Fast ≤ {stats["q1"]:.2f}s\nAvg: {stats["avg"]:.2f}s\nSlow ≥ {stats["q3"]:.2f}s'
        plt.text(TIME_WINDOW_END + 0.17 * (TIME_WINDOW_END - TIME_WINDOW_START),
                y_pos,
                stats_text,
                va='center',
                bbox=dict(facecolor='white', alpha=0.8))
    
    # Προσθήκη χρωματικού υπομνήματος με καλύτερη τοποθέτηση
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
    
    # Προσθήκη κάθετων γραμμών για GNB
    for gnb, time in first_appearances.items():
        plt.axvline(x=time, color='gray', linestyle='--', alpha=0.5)
        next_time = next((t for g, t in first_appearances.items() if t > time), TIME_WINDOW_END)
        center = (time + next_time) / 2
        plt.text(center, 2.1, gnb, ha='center', va='bottom')
    
    plt.title(title)
    plt.xlabel('Time (minutes)')
    plt.yticks([])
    # Μείωση της επέκτασης του x-άξονα
    plt.xlim(TIME_WINDOW_START, TIME_WINDOW_END + 0.25 * (TIME_WINDOW_END - TIME_WINDOW_START))
    plt.ylim(0.4, 2.2)

def create_execution_heatmap(df, output_folder):
    if not SHOW_PLOTS:
        return
    
    # Μετατροπή χρόνου σε λεπτά και φιλτράρισμα
    df['TimeInMinutes'] = df['Time'] / 60.0
    df = df[(df['TimeInMinutes'] >= TIME_WINDOW_START) & (df['TimeInMinutes'] <= TIME_WINDOW_END)]
    
    # Εύρεση πρώτων εμφανίσεων GNB
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

def calculate_image_quality_stats(df):
    # Παίρνουμε μόνο τα tasks που έγιναν offload στους Edge Servers
    offloaded_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
    total_offloaded_tasks = len(offloaded_tasks)
    
    stats_data = []
    for quality, size_kb in IMAGE_QUALITIES.items():
        # Υπολογισμός συνολικού όγκου δεδομένων για όλη την προσομοίωση
        total_data_mb = (total_offloaded_tasks * size_kb) / 1024  # Μετατροπή σε MB
        
        stats_data.append([
            quality,
            f"{total_data_mb:.2f}"  # Συνολικά MB
        ])
    
    return stats_data

def setup_logging(output_folder):
    # Δημιουργία του logger
    logger = logging.getLogger('SimulationAnalysis')
    logger.setLevel(logging.INFO)
    
    # Formatter για τα logs
    formatter = logging.Formatter('%(message)s')
    
    # File handler - τώρα δημιουργείται στον ίδιο φάκελο με τα άλλα αποτελέσματα
    log_file_path = os.path.join(simulation_folder, SIM_ANALYSIS_LOG)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Προσθήκη handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def create_inference_time_plot(df, output_folder):
    if not SHOW_PLOTS:
        return
    
    plt.figure(figsize=(12, 8))
    
    # Διαχωρισμός tasks
    drone_tasks = df[df['ExecutionLocation'] == 'Far-Edge (Drone)']
    edge_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
    
    # Υπολογισμός στατιστικών για το Drone
    drone_mean = drone_tasks['ExecutionTime'].mean()
    drone_std = drone_tasks['ExecutionTime'].std()
    
    # Υπολογισμός στατιστικών για τα Edge tasks
    edge_mean = edge_tasks['ExecutionTime'].mean()
    edge_std = edge_tasks['ExecutionTime'].std()
    
    # Δημιουργία των subplots
    plt.subplot(2, 1, 1)
    plt.hist(drone_tasks['ExecutionTime'], bins=30, alpha=0.7, color='blue')
    plt.axvline(drone_mean, color='red', linestyle='dashed', linewidth=1)
    plt.text(drone_mean, plt.ylim()[1]*0.9, f'Mean: {drone_mean:.3f}s\nStd: {drone_std:.3f}s', 
             horizontalalignment='right', verticalalignment='top')
    plt.title('Drone Inference Time Distribution')
    plt.xlabel('Execution Time (seconds)')
    plt.ylabel('Frequency')
    
    plt.subplot(2, 1, 2)
    plt.hist(edge_tasks['ExecutionTime'], bins=30, alpha=0.7, color='green')
    plt.axvline(edge_mean, color='red', linestyle='dashed', linewidth=1)
    plt.text(edge_mean, plt.ylim()[1]*0.9, f'Mean: {edge_mean:.3f}s\nStd: {edge_std:.3f}s', 
             horizontalalignment='right', verticalalignment='top')
    plt.title('Edge Server Inference Time Distribution')
    plt.xlabel('Execution Time (seconds)')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    
    # Αποθήκευση του γραφήματος
    output_path = os.path.join(output_folder, INFERENCE_TIME_CHART)
    plt.savefig(output_path)
    plt.close()
    print(f"Inference time distribution plot saved at: {output_path}")

def create_simulation_map(output_folder):
    if not SHOW_PLOTS:
        return
        
    # Διάβασμα των τιμών length και width από το simulation_parameters.properties
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(output_folder))))
    properties_file = os.path.join(base_dir, DRONE_SETTINGS_DIR, SIM_PARAMETERS_FILE)
    length = None  # Αρχικοποίηση με None
    width = None   # Αρχικοποίηση με None
    coverage_radius = 100.0  # Προεπιλεγμένη τιμή σε περίπτωση που δεν βρεθεί στο αρχείο
    
    try:
        with open(properties_file, 'r') as f:
            for line in f:
                if line.startswith('length='):
                    length = int(line.split('=')[1].strip())
                elif line.startswith('width='):
                    width = int(line.split('=')[1].strip())
                elif line.startswith('edge_datacenters_coverage='):
                    coverage_radius = float(line.split('=')[1].strip())
                    print(f"Read edge_datacenters_coverage: {coverage_radius}")
    except Exception as e:
        print(f"Error reading simulation parameters: {e}")
    
    # Χρήση προεπιλεγμένων τιμών μόνο αν δεν βρέθηκαν οι τιμές στο αρχείο
    if length is None:
        length = 5000
    if width is None:
        width = 5000
    
    # Reading datacenter positions from the txt file
    datacenter_positions = []
    txt_file = os.path.join(simulation_folder, SEQUENTIAL_SIM_TXT)
    
    try:
        with open(txt_file, 'r') as f:
            lines = f.readlines()
            reading_datacenters = False
            for line in lines:
                if "===== EDGE DATACENTERS =====" in line:
                    reading_datacenters = True
                    continue
                if reading_datacenters and line.strip():
                    if "Location:" in line:
                        parts = line.split("Location: ")[1].split(")")[0].strip("(").split(",")
                        x = float(parts[0])
                        y = float(parts[1])
                        name = line.split("-")[0].strip()
                        datacenter_positions.append((name, x, y))
                    else:
                        pass
                if reading_datacenters and not line.strip():
                    break
    except Exception as e:
        print(f"Error reading datacenter positions: {e}")
        print("Continuing without datacenter information...")

    # Reading mv_nodes and their connections
    mv_nodes = {}
    mv_connections = []
    
    try:
        # Path to the mv_nodes_info.csv file
        mv_nodes_csv = os.path.join(base_dir, MV_NODES_INFO_FILE)
        
        if os.path.exists(mv_nodes_csv):
            import ast
            
            mv_df = pd.read_csv(mv_nodes_csv)
            
            for _, row in mv_df.iterrows():
                node_id = int(row['id'])  # Convert to integer
                
                # Check if normalized_coordinates column exists
                if 'normalized_coordinates' in row:
                    try:
                        normalized_coords = ast.literal_eval(row['normalized_coordinates'])
                        x, y = normalized_coords
                        mv_nodes[node_id] = (x, y)
                    except Exception as e:
                        pass
                
                # Read connections
                if 'connections' in row and 'edge_distances' in row:
                    try:
                        connections = ast.literal_eval(row['connections'])
                        edge_distances = ast.literal_eval(row['edge_distances'])
                        
                        for conn in connections:
                            conn_id = str(conn)  # Keep as string for dictionary key
                            
                            # Avoid duplicate connections
                            if node_id < int(conn_id):
                                distance = edge_distances.get(conn_id, "N/A")
                                mv_connections.append((node_id, int(conn_id), distance))
                    except Exception as e:
                        pass
            
        else:
            pass
    except Exception as e:
        print(f"Error reading mv_nodes_info.csv: {e}")
        import traceback
        traceback.print_exc()
        # Continue without mv_nodes data

    # Reading drone path from csv
    drone_paths = {}  # Dictionary to store paths by ID
    csv_file = os.path.join(simulation_folder, SEQUENTIAL_SIM_DRONE_CSV)
    
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

    # Creating plot with correct aspect ratio
    plt.figure(figsize=(20, 20))  
    ax = plt.gca()
    
    # Constants
    COVERAGE_RADIUS = coverage_radius  # Use value from settings file
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
        # Draw nodes
        for node_id, (x, y) in mv_nodes.items():
            node = plt.Circle((x, y), MV_NODE_RADIUS, color='purple', alpha=0.7)
            ax.add_patch(node)
            plt.text(x + 10, y, f"N{node_id}", fontsize=7, color='purple')
        
        # Draw connections
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
                pass

    # Plot drone path with arrows at position changes for each drone
    for drone_id, path in drone_paths.items():
        if path:
            path_x, path_y = zip(*path)
            color = drone_colors[drone_id]
            
            # Draw path with thinner line
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
                                fc=color, ec=color, alpha=0.8,    # Larger intensity (less opacity)
                                linewidth=1.8,                    # Larger line thickness
                                length_includes_head=True)
                    
                    prev_x, prev_y = curr_x, curr_y
            
            # Add red arrows for each minute of simulation - MORE INTENSE ARROWS
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
    # Add item for mv_nodes
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
    output_path = os.path.join(simulation_folder, SIMULATION_MAP_CHART)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Simulation map saved at: {output_path}")

def write_simulation_info(logger, min_devices, exec_time, offload_prob):
    """Γράφει τις πληροφορίες της προσομοίωσης στο αρχείο log"""
    logger.info("\n=== Simulation Parameters ===")
    logger.info(f"Number of Edge Devices: {min_devices}")
    logger.info(f"Simulation Time: {exec_time} minutes")
    logger.info(f"Offload Probability: {offload_prob}")

def create_simulation_summary_csv(simulation_folder, logger):
    """Δημιουργεί ένα CSV αρχείο με τα βασικά αποτελέσματα της προσομοίωσης"""
    csv_path = os.path.join(simulation_folder, SIM_SUMMARY_CSV)
    
    # Διάβασμα των τιμών από το log
    with open(os.path.join(simulation_folder, SIM_ANALYSIS_LOG), 'r') as f:
        log_content = f.read()
        
        # Εξαγωγή των τιμών με χρήση regex
        # Ψάχνουμε συγκεκριμένα στο τμήμα CPU Usage Analysis
        cpu_match = re.search(r'=== CPU Usage Analysis ===(.*?)===', log_content, re.DOTALL)
        if cpu_match:
            cpu_section = cpu_match.group(1)
            cpu_value = re.search(r'Edge\s+\|\s+(\d+\.\d+)', cpu_section)
            if cpu_value:
                edge_cpu = float(cpu_value.group(1))
            else:
                print("Warning: Could not find CPU usage value in CPU Usage Analysis section")
                edge_cpu = 0.0
        else:
            print("Warning: Could not find CPU Usage Analysis section")
            edge_cpu = 0.0
        
        # Για τις άλλες τιμές
        edge_dynamic = float(re.search(r'Edge\s+\|\s+\d+\.\d+\s+\|\s+(\d+\.\d+)', log_content).group(1))
        edge_success = float(re.search(r'Edge Servers\s+\|\s+\d+\s+\(\d+\.\d+%\)\s+\|\s+(\d+\.\d+)', log_content).group(1))
    
    # Δημιουργία του CSV με όλες τις τιμές
    with open(csv_path, 'w') as f:
        f.write("Metric,Value\n")
        f.write(f"Edge Average CPU Usage (%),{edge_cpu:.3f}\n")
        f.write(f"Edge Dynamic Consumption (Wh),{edge_dynamic:.4f}\n")
        f.write(f"Edge Success Rate (%),{edge_success:.2f}\n")
        
        # Προσθήκη των τιμών από τους πίνακες
        # Task Distribution and Success Rates
        f.write("\n=== Task Distribution and Success Rates ===\n")
        f.write("Location,Tasks (% of Total),Success Rate (%)\n")
        for line in re.finditer(r'\|([^|]+)\|([^|]+)\|([^|]+)\|', log_content):
            location = line.group(1).strip()
            tasks = line.group(2).strip()
            success = line.group(3).strip()
            if location and tasks and success and not location.startswith('-'):
                f.write(f"{location},{tasks},{success}\n")
        
        # Edge Server Times
        f.write("\n=== Edge Server Times ===\n")
        f.write("Metric,All Edge Servers,GNB1,GNB2,GNB3,GNB4,GNB5\n")
        for line in re.finditer(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|', log_content):
            metric = line.group(1).strip()
            all_servers = line.group(2).strip()
            gnb1 = line.group(3).strip()
            gnb2 = line.group(4).strip()
            gnb3 = line.group(5).strip()
            gnb4 = line.group(6).strip()
            gnb5 = line.group(7).strip()
            if metric and not metric.startswith('-'):
                f.write(f"{metric},{all_servers},{gnb1},{gnb2},{gnb3},{gnb4},{gnb5}\n")
        
        # Image Quality Data Transfer Statistics
        f.write("\n=== Image Quality Data Transfer Statistics ===\n")
        f.write("Quality,Total Offloaded MB\n")
        for line in re.finditer(r'\|([^|]+)\|([^|]+)\|', log_content):
            quality = line.group(1).strip()
            total_mb = line.group(2).strip()
            if quality and total_mb and not quality.startswith('-'):
                f.write(f"{quality},{total_mb}\n")
        
        # Energy Consumption Analysis
        f.write("\n=== Energy Consumption Analysis ===\n")
        f.write("Level,Static Consumption (Wh),Dynamic Consumption (Wh),Total Consumption (Wh)\n")
        for line in re.finditer(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|', log_content):
            level = line.group(1).strip()
            static = line.group(2).strip()
            dynamic = line.group(3).strip()
            total = line.group(4).strip()
            if level and not level.startswith('-'):
                f.write(f"{level},{static},{dynamic},{total}\n")
    
    print(f"Simulation summary saved at: {csv_path}")

def analyze_simulation_data(csv_file):
    output_folder = os.path.dirname(csv_file)
    logger = setup_logging(output_folder)
    
    # Δημιουργία του CSV αρχείου
    csv_path = os.path.join(output_folder, SIM_SUMMARY_CSV)
    with open(csv_path, 'w') as f:
        f.write("Metric,Value\n")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Read parameters from files
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(csv_file))))
        properties_file = os.path.join(base_dir, 'DroneSim/Drone_settings/simulation_parameters.properties')
        orchestrator_file = os.path.join(base_dir, 'DroneSim/DroneTaskOrchestratorD2.java')
        
        # Default values
        min_devices = 8
        exec_time = 10
        offload_prob = 0.20
        
        try:
            # Read min devices and simulation time from properties file
            with open(properties_file, 'r') as f:
                for line in f:
                    if 'min_number_of_edge_devices' in line:
                        min_devices = int(line.split('=')[1].strip())
                    elif 'simulation_time' in line:
                        exec_time = int(line.split('=')[1].strip())
            
            # Read offload probability from DroneTaskOrchestratorD2.java
            with open(orchestrator_file, 'r') as f:
                content = f.read()
                prob_match = re.search(r'OFFLOAD_PROBABILITY\s*=\s*([0-9.]+)', content)
                if prob_match:
                    offload_prob = float(prob_match.group(1))
        except Exception as e:
            print(f"Error reading parameters: {e}")
            print(f"Properties file: {properties_file}")
            print(f"Orchestrator file: {orchestrator_file}")
        
        # Calculate Total Time
        df['TotalTime'] = df['NetworkTime'] + df['WaitingTime'] + df['ExecutionTime']
        
        # Create plots
        create_success_rate_plot(df, output_folder)
        create_execution_heatmap(df, output_folder)
        create_inference_time_plot(df, output_folder)
        create_simulation_map(output_folder)
        
        # Get basic statistics
        total_tasks = len(df)
        drone_tasks = df[df['ExecutionLocation'] == 'Far-Edge (Drone)']
        edge_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
        
        # Calculate success statistics
        total_success = len(df[df['Status'] == 'S'])
        drone_success = len(drone_tasks[drone_tasks['Status'] == 'S'])
        edge_success = len(edge_tasks[edge_tasks['Status'] == 'S'])
        
        # Create table for task distribution and success rates
        distribution_headers = ['Location', 'Tasks (% of Total)', 'Success Rate (%)']
        
        # Συνδυάζουμε όλα τα sections σε ένα, προσθέτοντας κενές γραμμές για διαχωρισμό
        distribution_data = [
            # Section 1
            ['Total Tasks', f"{total_tasks} (100%)", f"{(total_success/total_tasks)*100:.2f}"],
            # Κενή γραμμή για διαχωρισμό
            ['', '', ''],
            # Section 2
            ['Far-Edge (Drone)', f"{len(drone_tasks)} ({len(drone_tasks)/total_tasks*100:.2f}%)", 
             f"{(drone_success/len(drone_tasks))*100:.2f}" if len(drone_tasks) > 0 else "N/A"],
            ['Edge Servers', f"{len(edge_tasks)} ({len(edge_tasks)/total_tasks*100:.2f}%)", 
             f"{(edge_success/len(edge_tasks))*100:.2f}" if len(edge_tasks) > 0 else "N/A"],
            # Κενή γραμμή για διαχωρισμό
            ['', '', '']
        ]
        
        # Section 3 - Δυναμική αναγνώριση όλων των GNBs
        # Βρίσκουμε όλα τα μοναδικά ονόματα GNB από τη στήλη ExecutionLocation
        all_gnbs = []
        for location in df['ExecutionLocation'].unique():
            if 'Edge Server:' in location and 'Drone' not in location:
                gnb_name = location.replace('Edge Server: ', '').strip()
                all_gnbs.append((gnb_name, location))
        
        # Ταξινόμηση των GNBs (αν περιέχουν αριθμούς, ταξινόμηση με βάση τους αριθμούς)
        def extract_number(gnb_tuple):
            gnb_name = gnb_tuple[0]
            # Εξαγωγή αριθμού από το όνομα (αν υπάρχει)
            numbers = re.findall(r'\d+', gnb_name)
            if numbers:
                return int(numbers[0])
            return gnb_name  # Αν δεν υπάρχει αριθμός, επιστρέφουμε το όνομα για αλφαβητική ταξινόμηση
        
        all_gnbs.sort(key=extract_number)
        
        # Προσθήκη στατιστικών για κάθε GNB που βρέθηκε
        for gnb_name, location in all_gnbs:
            gnb_tasks = df[df['ExecutionLocation'] == location]
            if len(gnb_tasks) > 0:
                gnb_success = len(gnb_tasks[gnb_tasks['Status'] == 'S'])
                distribution_data.append([
                    gnb_name, 
                    f"{len(gnb_tasks)} ({len(gnb_tasks)/total_tasks*100:.2f}%)",
                    f"{(gnb_success/len(gnb_tasks))*100:.2f}"
                ])
        
        logger.info("\n=== Task Distribution and Success Rates ===")
        logger.info(tabulate(distribution_data, headers=distribution_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        with open(csv_path, 'a') as f:
            f.write("\n=== Task Distribution and Success Rates ===\n")
            f.write("Location,Tasks (% of Total),Success Rate (%)\n")
            for row in distribution_data:
                if row[0]:  # Αγνοούμε τις κενές γραμμές
                    f.write(f"{row[0]},{row[1]},{row[2]}\n")
        
        # Create table for Drone times
        drone_headers = ['Metric', 'Time (seconds)']
        drone_data = []
        if len(drone_tasks) > 0:
            drone_data = [
                ['Average Network Time', f"{drone_tasks['NetworkTime'].mean():.4f}"],
                ['Average Waiting Time', f"{drone_tasks['WaitingTime'].mean():.4f}"],
                ['Average Execution Time', f"{drone_tasks['ExecutionTime'].mean():.4f}"],
                ['Average Total Time', f"{drone_tasks['TotalTime'].mean():.4f}"]
            ]
        
        logger.info("\n=== Drone Times ===")
        logger.info(tabulate(drone_data, headers=drone_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        with open(csv_path, 'a') as f:
            f.write("\n=== Drone Times ===\n")
            f.write("Metric,Time (seconds)\n")
            for row in drone_data:
                f.write(f"{row[0]},{row[1]}\n")
        
        # Create table for Edge Server times
        # Δυναμική δημιουργία των headers με βάση τα GNBs που εντοπίστηκαν
        headers = ['Metric', 'All Edge Servers']
        for gnb_name, _ in all_gnbs:
            headers.append(gnb_name)
        
        table_data = []
        metrics = [
            ('Average Network Time', 'NetworkTime'),
            ('Average Waiting Time', 'WaitingTime'),
            ('Average Execution Time', 'ExecutionTime'),
            ('Average Total Time', 'TotalTime')
        ]
        
        for metric_name, metric_col in metrics:
            row = [metric_name]
            # All Edge Servers
            if len(edge_tasks) > 0:
                row.append(f"{edge_tasks[metric_col].mean():.4f}")
            else:
                row.append("N/A")
            
            # Individual GNBs
            for _, location in all_gnbs:
                gnb_tasks = df[df['ExecutionLocation'] == location]
                if len(gnb_tasks) > 0:
                    row.append(f"{gnb_tasks[metric_col].mean():.4f}")
                else:
                    row.append("N/A")
            table_data.append(row)
        
        logger.info("\n=== Edge Server Times ===")
        logger.info(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV με δυναμικό αριθμό στηλών
        with open(csv_path, 'a') as f:
            f.write("\n=== Edge Server Times ===\n")
            # Γράψε τις επικεφαλίδες
            f.write("Metric,All Edge Servers")
            for gnb_name, _ in all_gnbs:
                f.write(f",{gnb_name}")
            f.write("\n")
            
            # Γράψε τις γραμμές δεδομένων
            for row in table_data:
                f.write(f"{row[0]},{row[1]}")
                for i in range(2, len(row)):
                    f.write(f",{row[i]}")
                f.write("\n")

        # Εκτύπωση του πίνακα με μόνο το συνολικό όγκο
        logger.info("\n=== Image Quality Data Transfer Statistics ===")
        quality_stats = calculate_image_quality_stats(df)
        headers = ['Quality', 'Total Offloaded MB']
        logger.info(tabulate(quality_stats, headers=headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        with open(csv_path, 'a') as f:
            f.write("\n=== Image Quality Data Transfer Statistics ===\n")
            f.write("Quality,Total Offloaded MB\n")
            for row in quality_stats:
                f.write(f"{row[0]},{row[1]}\n")
        
        # Ανάλυση κατανάλωσης ενέργειας από το Sequential_simulation.csv
        analyze_energy_consumption(simulation_folder, logger)
        
        # Ανάλυση χρήσης CPU για Edge και Mist (Drone)
        analyze_cpu_usage(simulation_folder, logger)

        # Write simulation info to log
        write_simulation_info(logger, min_devices, exec_time, offload_prob)
        
        # Εγγραφή των παραμέτρων στο CSV
        with open(csv_path, 'a') as f:
            f.write("\n=== Simulation Parameters ===\n")
            f.write("Parameter,Value\n")
            f.write(f"Number of Edge Devices,{min_devices}\n")
            f.write(f"Simulation Time,{exec_time} minutes\n")
            f.write(f"Offload Probability,{offload_prob}\n")

    except Exception as e:
        logger.error(f"Σφάλμα κατά την ανάλυση των δεδομένων: {str(e)}")
        raise

def analyze_energy_consumption(simulation_folder, logger):
    """Ανάλυση κατανάλωσης ενέργειας από το Sequential_simulation.csv"""
    try:
        # Διαδρομή προς το αρχείο Sequential_simulation.csv
        csv_file = os.path.join(simulation_folder, SEQUENTIAL_SIM_CSV)
        
        if not os.path.exists(csv_file):
            logger.info("\n=== Energy Consumption Analysis ===")
            logger.info("Το αρχείο Sequential_simulation.csv δεν βρέθηκε.")
            return
        
        # Ανάγνωση του CSV αρχείου
        energy_df = pd.read_csv(csv_file)
        
        # Εξαγωγή των τιμών κατανάλωσης ενέργειας
        edge_static = energy_df['Edge static consumption (Wh)'].iloc[0]
        edge_dynamic = energy_df['Edge dynamic consumption (Wh)'].iloc[0]
        mist_static = energy_df['Mist static consumption (Wh)'].iloc[0]
        mist_dynamic = energy_df['Mist dynamic consumption (Wh)'].iloc[0]
        
        # Δημιουργία πίνακα για την κατανάλωση ενέργειας
        energy_headers = ['Level', 'Static Consumption (Wh)', 'Dynamic Consumption (Wh)', 'Total Consumption (Wh)']
        energy_data = [
            ['Edge', f"{edge_static:.4f}", f"{edge_dynamic:.4f}", f"{edge_static + edge_dynamic:.4f}"],
            ['Mist (Drone)', f"{mist_static:.4f}", f"{mist_dynamic:.4f}", f"{mist_static + mist_dynamic:.4f}"]
        ]
        
        logger.info("\n=== Energy Consumption Analysis ===")
        logger.info(tabulate(energy_data, headers=energy_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        csv_path = os.path.join(simulation_folder, SIM_SUMMARY_CSV)
        with open(csv_path, 'a') as f:
            f.write("\n=== Energy Consumption Analysis ===\n")
            f.write("Level,Static Consumption (Wh),Dynamic Consumption (Wh),Total Consumption (Wh)\n")
            for row in energy_data:
                f.write(f"{row[0]},{row[1]},{row[2]},{row[3]}\n")
        
    except Exception as e:
        logger.info(f"\n=== Energy Consumption Analysis ===")
        logger.info(f"Σφάλμα κατά την ανάλυση κατανάλωσης ενέργειας: {str(e)}")

def analyze_cpu_usage(simulation_folder, logger):
    """Ανάλυση χρήσης CPU για Edge και Mist (Drone)"""
    try:
        # Διαδρομή προς το αρχείο Sequential_simulation.csv
        csv_file = os.path.join(simulation_folder, SEQUENTIAL_SIM_CSV)
        
        if not os.path.exists(csv_file):
            logger.info("\n=== CPU Usage Analysis ===")
            logger.info("Το αρχείο Sequential_simulation.csv δεν βρέθηκε.")
            return
        
        # Ανάγνωση του CSV αρχείου
        cpu_df = pd.read_csv(csv_file)
        
        # Εξαγωγή των τιμών χρήσης CPU
        edge_cpu = cpu_df['Average CPU usage (Edge) (%)'].iloc[0]
        mist_cpu = cpu_df['Average CPU usage (Mist) (%)'].iloc[0]
        
        # Δημιουργία πίνακα για τη χρήση CPU
        cpu_headers = ['Level', 'Average CPU Usage (%)']
        cpu_data = [
            ['Edge', f"{edge_cpu:.4f}"],
            ['Mist (Drone)', f"{mist_cpu:.4f}"]
        ]
        
        logger.info("\n=== CPU Usage Analysis ===")
        logger.info(tabulate(cpu_data, headers=cpu_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        csv_path = os.path.join(simulation_folder, SIM_SUMMARY_CSV)
        with open(csv_path, 'a') as f:
            f.write("\n=== CPU Usage Analysis ===\n")
            f.write("Level,Average CPU Usage (%)\n")
            for row in cpu_data:
                f.write(f"{row[0]},{row[1]}\n")
        
    except Exception as e:
        logger.info(f"\n=== CPU Usage Analysis ===")
        logger.info(f"Σφάλμα κατά την ανάλυση χρήσης CPU: {str(e)}")

def process_simulation_folder(folder_path):
    # Διάβασμα του CSV αρχείου
    csv_file = os.path.join(folder_path, SEQUENTIAL_SIM_DRONE_CSV)
    if not os.path.exists(csv_file):
        print(f"Το αρχείο {csv_file} δεν βρέθηκε")
        return

# Run the analysis
analyze_simulation_data(simulation_path)