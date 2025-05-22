import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from tabulate import tabulate
import sys
import argparse
import re
import matplotlib
matplotlib.use('Agg')  # Αλλαγή σε 'Agg' backend

# Configuration
SHOW_PLOTS = True  # Set to False to disable plots

# Δημιουργία του parser
parser = argparse.ArgumentParser(description='Analyze simulation data')
parser.add_argument('output_folder', help='The output folder containing the simulation data')
args = parser.parse_args()

# Ορισμός του βασικού φακέλου εξόδου
base_output_dir = "PureEdgeSim/ForkliftSim/Forklift_output"
output_folder = args.output_folder
simulation_folder = os.path.join(base_output_dir, output_folder)
simulation_path = os.path.join(simulation_folder, "Sequential_simulation_forklift.csv")

# Time window configuration (in minutes)
TIME_WINDOW_START = 0  # Starting minute
TIME_WINDOW_END =30    # Ending minute

# Ορισμός μεγέθους δεδομένων για κάθε ποιότητα εικόνας (σε KB)
IMAGE_QUALITIES = {
    '240p': 50,     # ~50KB ανά εικόνα
    '480p': 150,    # ~150KB ανά εικόνα
    '720p': 350,    # ~350KB ανά εικόνα
    '1080p': 800,   # ~800KB ανά εικόνα
    '1440p': 2000,  # ~2MB ανά εικόνα
    '2160': 8000   # ~8MB ανά εικόνα
}

# Ορισμός του logger
logger = logging.getLogger('simulation_analysis')
logger.setLevel(logging.INFO)

# Προσθήκη handler για το console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def create_success_rate_plot(df, output_folder):
    if not SHOW_PLOTS:
        return
    
    plt.figure(figsize=(12, 6))
    
    df_sorted = df.sort_values('Time')
    df_sorted['TimeInMinutes'] = df_sorted['Time'] / 60.0
    
    # Συνολικό ποσοστό - αλλαγή χρώματος σε πορτοκαλί
    total_success = (df_sorted['Status'] == 'S').cumsum() / range(1, len(df_sorted) + 1) * 100
    plt.plot(df_sorted['TimeInMinutes'], total_success, label='Overall Success Rate', color='orange')
    
    # Ποσοστό για Forklift - αλλαγή χρώματος σε μπλε
    forklift_df = df_sorted[df_sorted['ExecutionLocation'] == 'Far-Edge (Forklift)']
    if len(forklift_df) > 0:
        forklift_success = (forklift_df['Status'] == 'S').cumsum() / range(1, len(forklift_df) + 1) * 100
        plt.plot(forklift_df['TimeInMinutes'], forklift_success, label='Forklift Success Rate', color='blue')
    
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
    
    output_path = os.path.join(output_folder, 'success_rates.png')
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
    forklift_tasks = df[df['ExecutionLocation'] == 'Far-Edge (Forklift)']
    edge_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
    
    # Δημιουργία του γραφήματος με προσαρμοσμένο μέγεθος και layout
    plt.figure(figsize=(15, 12))  # Μικρότερο πλάτος
    
    # Αλλαγή σειράς των γραφημάτων - πρώτα το Forklift και μετά τα Edge Servers
    plot_task_distribution(forklift_tasks, 'Forklift (Far-Edge) Task Distribution', 1, first_appearances)
    plot_task_distribution(edge_tasks, 'Edge Servers Task Distribution', 2, first_appearances)
    
    # Προσαρμογή του layout για καλύτερη εμφάνιση
    plt.tight_layout()
    plt.subplots_adjust(right=0.85)  # Αφήνει χώρο για το legend χωρίς μεγάλα κενά
    
    # Αποθήκευση
    output_path = os.path.join(output_folder, f'execution_heatmap_{TIME_WINDOW_START}_{TIME_WINDOW_END}min.png')
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
    log_file_path = os.path.join(simulation_folder, 'simulation_analysis.log')
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
    forklift_tasks = df[df['ExecutionLocation'] == 'Far-Edge (Forklift)']
    edge_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
    
    # Υπολογισμός στατιστικών για το Forklift
    forklift_mean = forklift_tasks['ExecutionTime'].mean()
    forklift_std = forklift_tasks['ExecutionTime'].std()
    
    # Υπολογισμός στατιστικών για τα Edge tasks
    edge_mean = edge_tasks['ExecutionTime'].mean()
    edge_std = edge_tasks['ExecutionTime'].std()
    
    # Δημιουργία των subplots
    plt.subplot(2, 1, 1)
    plt.hist(forklift_tasks['ExecutionTime'], bins=30, alpha=0.7, color='blue')
    plt.axvline(forklift_mean, color='red', linestyle='dashed', linewidth=1)
    plt.text(forklift_mean, plt.ylim()[1]*0.9, f'Mean: {forklift_mean:.3f}s\nStd: {forklift_std:.3f}s', 
             horizontalalignment='right', verticalalignment='top')
    plt.title('Forklift Inference Time Distribution')
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
    output_path = os.path.join(output_folder, 'inference_time_distribution.png')
    plt.savefig(output_path)
    plt.close()
    print(f"Inference time distribution plot saved at: {output_path}")

def create_simulation_map(simulation_folder):
    if not SHOW_PLOTS:
        return

    # Διάβασμα των θέσεων των datacenters από το txt αρχείο
    datacenter_positions = []
    txt_file = os.path.join(simulation_folder, "Sequential_simulation.txt")
    
    # Διάβασμα της τιμής edge_datacenters_coverage από το simulation_parameters.properties
    coverage_radius = 100.0  # Προεπιλεγμένη τιμή
    properties_file = os.path.join(os.path.dirname(os.path.dirname(simulation_folder)), "Forklift_settings/simulation_parameters.properties")
    try:
        with open(properties_file, 'r') as f:
            for line in f:
                if 'edge_datacenters_coverage' in line:
                    coverage_radius = float(line.split('=')[1].strip())
                    break
    except Exception as e:
        print(f"Error reading coverage radius from properties file: {e}")
    
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
                if reading_datacenters and not line.strip():
                    break
    except Exception as e:
        print(f"Error reading datacenter positions: {e}")
        return

    # Διάβασμα του forklift path από το csv
    forklift_paths = {}  # Λεξικό για αποθήκευση των διαδρομών ανά ID
    csv_file = os.path.join(simulation_folder, "Sequential_simulation_forklift.csv")
    try:
        df = pd.read_csv(csv_file)
        # Ομαδοποίηση των σημείων ανά ForkliftID
        for forklift_id, group in df.groupby('ForkliftID'):
            forklift_paths[forklift_id] = list(zip(group['ForkliftX'], group['ForkliftY']))
    except Exception as e:
        print(f"Error reading forklift path: {e}")
        return

    # Δημιουργία του plot με σωστό aspect ratio
    plt.figure(figsize=(10, 10))
    ax = plt.gca()
    
    # Σταθερές
    COVERAGE_RADIUS = coverage_radius  # Edge datacenter coverage από το properties file
    DATACENTER_RADIUS = 10.0  # Μέγεθος του datacenter
    
    # Δημιουργία χρωμάτων για τα forklifts
    colors = plt.cm.tab20(np.linspace(0, 1, len(forklift_paths)))
    forklift_colors = {forklift_id: colors[i] for i, forklift_id in enumerate(sorted(forklift_paths.keys()))}
    
    # Plot για κάθε datacenter
    datacenter_colors = plt.cm.Set3(np.linspace(0, 1, len(datacenter_positions)))
    for (name, x, y), color in zip(datacenter_positions, datacenter_colors):
        # Plot του datacenter με πιο έντονο χρώμα
        datacenter = plt.Circle((x, y), DATACENTER_RADIUS, facecolor=color, alpha=0.9, edgecolor='black', linewidth=2)
        ax.add_patch(datacenter)
        
        # Plot της περιοχής κάλυψης με πιο έντονο χρώμα
        coverage = plt.Circle((x, y), COVERAGE_RADIUS, facecolor=color, alpha=0.3, edgecolor=color, linewidth=2)
        ax.add_patch(coverage)
        
        # Προσθήκη ετικέτας
        plt.annotate(name, (x, y), xytext=(5, 5), textcoords='offset points')

    # Plot του forklift path με βέλη στις αλλαγές θέσης για κάθε forklift
    for forklift_id, path in forklift_paths.items():
        if path:
            path_x, path_y = zip(*path)
            color = forklift_colors[forklift_id]
            
            # Σχεδίαση της διαδρομής
            plt.plot(path_x, path_y, color=color, alpha=0.3, label=f'Forklift {forklift_id} Path', linewidth=1)
            
            # Προσθήκη βελών μόνο όταν αλλάζει η θέση
            prev_x, prev_y = path_x[0], path_y[0]
            for i in range(1, len(path_x)):
                curr_x, curr_y = path_x[i], path_y[i]
                
                # Έλεγχος αν η θέση άλλαξε
                if curr_x != prev_x or curr_y != prev_y:
                    dx = curr_x - prev_x
                    dy = curr_y - prev_y
                    
                    # Υπολογισμός του μεγέθους του βέλους με βάση την απόσταση
                    distance = np.sqrt(dx*dx + dy*dy)
                    if distance > 0:  # Αποφυγή division by zero
                        # Κανονικοποίηση του μεγέθους του βέλους
                        arrow_length = min(distance * 0.5, 10)  # Μείωση του μεγέθους του βέλους
                        dx_norm = dx * arrow_length / distance
                        dy_norm = dy * arrow_length / distance
                        
                        plt.arrow(prev_x, prev_y, dx_norm, dy_norm,
                                head_width=2, head_length=3,  # Μείωση του μεγέθους του βέλους
                                fc=color, ec=color, alpha=0.7,
                                length_includes_head=True)
                    
                    prev_x, prev_y = curr_x, curr_y

    # Ρυθμίσεις του plot
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.title('Simulation Map: Edge Datacenters and Forklift Paths')
    
    # Ρύθμιση των ορίων με ίσο aspect ratio
    ax.set_aspect('equal')
    plt.xlim(-10, 410)  # Λίγο μεγαλύτερα όρια για να φαίνονται όλα
    plt.ylim(-10, 410)
    
    # Αποθήκευση
    output_path = os.path.join(simulation_folder, 'sim_map.png')
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
    csv_path = os.path.join(simulation_folder, 'simulation_summary.csv')
    
    # Διάβασμα των τιμών από το log
    with open(os.path.join(simulation_folder, 'simulation_analysis.log'), 'r') as f:
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
    csv_path = os.path.join(output_folder, 'simulation_summary.csv')
    with open(csv_path, 'w') as f:
        f.write("Metric,Value\n")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Read parameters from files
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(csv_file))))
        properties_file = os.path.join(base_dir, 'ForkliftSim/Forklift_settings/simulation_parameters.properties')
        orchestrator_file = os.path.join(base_dir, 'ForkliftSim/ForkliftTaskOrchestratorD2.java')
        
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
            
            # Read offload probability from ForkliftTaskOrchestratorD2.java
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
        forklift_tasks = df[df['ExecutionLocation'] == 'Far-Edge (Forklift)']
        edge_tasks = df[df['ExecutionLocation'].str.contains('Edge Server')]
        
        # Calculate success statistics
        total_success = len(df[df['Status'] == 'S'])
        forklift_success = len(forklift_tasks[forklift_tasks['Status'] == 'S'])
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
            ['Far-Edge (Forklift)', f"{len(forklift_tasks)} ({len(forklift_tasks)/total_tasks*100:.2f}%)", 
             f"{(forklift_success/len(forklift_tasks))*100:.2f}" if len(forklift_tasks) > 0 else "N/A"],
            ['Edge Servers', f"{len(edge_tasks)} ({len(edge_tasks)/total_tasks*100:.2f}%)", 
             f"{(edge_success/len(edge_tasks))*100:.2f}" if len(edge_tasks) > 0 else "N/A"],
            # Κενή γραμμή για διαχωρισμό
            ['', '', '']
        ]
        
        # Section 3 - GNB statistics
        for gnb in range(1, 6):
            gnb_tasks = df[df['ExecutionLocation'] == f'Edge Server: GNB{gnb}']
            if len(gnb_tasks) > 0:
                gnb_success = len(gnb_tasks[gnb_tasks['Status'] == 'S'])
                distribution_data.append([
                    f'GNB{gnb}', 
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
        
        # Create table for Forklift times
        forklift_headers = ['Metric', 'Time (seconds)']
        forklift_data = []
        if len(forklift_tasks) > 0:
            forklift_data = [
                ['Average Network Time', f"{forklift_tasks['NetworkTime'].mean():.4f}"],
                ['Average Waiting Time', f"{forklift_tasks['WaitingTime'].mean():.4f}"],
                ['Average Execution Time', f"{forklift_tasks['ExecutionTime'].mean():.4f}"],
                ['Average Total Time', f"{forklift_tasks['TotalTime'].mean():.4f}"]
            ]
        
        logger.info("\n=== Forklift Times ===")
        logger.info(tabulate(forklift_data, headers=forklift_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        with open(csv_path, 'a') as f:
            f.write("\n=== Forklift Times ===\n")
            f.write("Metric,Time (seconds)\n")
            for row in forklift_data:
                f.write(f"{row[0]},{row[1]}\n")
        
        # Create table for Edge Server times
        headers = ['Metric', 'All Edge Servers']
        for gnb in range(1, 7):  # Αλλαγή από 6 σε 7 για να συμπεριλάβει το GNB6
            headers.append(f'GNB{gnb}')
        
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
            for gnb in range(1, 7):  # Αλλαγή από 6 σε 7 για να συμπεριλάβει το GNB6
                gnb_tasks = df[df['ExecutionLocation'] == f'Edge Server: GNB{gnb}']
                if len(gnb_tasks) > 0:
                    row.append(f"{gnb_tasks[metric_col].mean():.4f}")
                else:
                    row.append("N/A")
            table_data.append(row)
        
        logger.info("\n=== Edge Server Times ===")
        logger.info(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        with open(csv_path, 'a') as f:
            f.write("\n=== Edge Server Times ===\n")
            f.write("Metric,All Edge Servers,GNB1,GNB2,GNB3,GNB4,GNB5,GNB6\n")  # Προσθήκη GNB6
            for row in table_data:
                f.write(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]},{row[7]}\n")  # Προσθήκη GNB6

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
        
        # Ανάλυση χρήσης CPU για Edge και Mist (Forklift)
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
        csv_file = os.path.join(simulation_folder, "Sequential_simulation.csv")
        
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
            ['Mist (Forklift)', f"{mist_static:.4f}", f"{mist_dynamic:.4f}", f"{mist_static + mist_dynamic:.4f}"]
        ]
        
        logger.info("\n=== Energy Consumption Analysis ===")
        logger.info(tabulate(energy_data, headers=energy_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        csv_path = os.path.join(simulation_folder, 'simulation_summary.csv')
        with open(csv_path, 'a') as f:
            f.write("\n=== Energy Consumption Analysis ===\n")
            f.write("Level,Static Consumption (Wh),Dynamic Consumption (Wh),Total Consumption (Wh)\n")
            for row in energy_data:
                f.write(f"{row[0]},{row[1]},{row[2]},{row[3]}\n")
        
    except Exception as e:
        logger.info(f"\n=== Energy Consumption Analysis ===")
        logger.info(f"Σφάλμα κατά την ανάλυση κατανάλωσης ενέργειας: {str(e)}")

def analyze_cpu_usage(simulation_folder, logger):
    """Ανάλυση χρήσης CPU για Edge και Mist (Forklift)"""
    try:
        # Διαδρομή προς το αρχείο Sequential_simulation.csv
        csv_file = os.path.join(simulation_folder, "Sequential_simulation.csv")
        
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
            ['Mist (Forklift)', f"{mist_cpu:.4f}"]
        ]
        
        logger.info("\n=== CPU Usage Analysis ===")
        logger.info(tabulate(cpu_data, headers=cpu_headers, tablefmt='grid'))
        
        # Εγγραφή στο CSV
        csv_path = os.path.join(simulation_folder, 'simulation_summary.csv')
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
    csv_file = os.path.join(folder_path, 'forklift_Sequential_simulation.csv')
    if not os.path.exists(csv_file):
        print(f"Το αρχείο {csv_file} δεν βρέθηκε")
        return

# Run the analysis
analyze_simulation_data(simulation_path) 