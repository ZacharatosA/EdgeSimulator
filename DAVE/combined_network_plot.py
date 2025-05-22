import json
import matplotlib.pyplot as plt
import numpy as np
import os
import csv
import pyproj
import re
from collections import defaultdict


JSON_FILENAME = f"B2_dave_dataset.json"
LTE_FILENAME = f"B8_vd_4g.json"
NR_FILENAME = f"B8_vd_5g.json"

def load_data(file_path):
    """Load data from JSON file"""
    with open(file_path, 'r') as file:
        return json.load(file)

def extract_mv_data(data):
    """Extract MV data from DAVE dataset"""
    try:
        # Check if mv_data exists
        if '_object' not in data:
            print("No _object key in data")
            return {}, {}
            
        if 'mv_data' not in data['_object']:
            print("No mv_data key in data['_object']")
            return {}, {}
            
        if '_object' not in data['_object']['mv_data']:
            print("No _object key in data['_object']['mv_data']")
            return {}, {}
        
        mv_data = data['_object']['mv_data']['_object']
        
        # Create a simpler GeoJSON structure for nodes
        nodes_features = []
        if 'mv_nodes' in mv_data:
            nodes_json = mv_data['mv_nodes']
            # Check if mv_nodes is already in the correct format
            if '_object' in nodes_json and isinstance(nodes_json['_object'], str):
                # Try to extract from the string
                try:
                    return json.loads(nodes_json['_object']), json.loads(mv_data['mv_lines']['_object'])
                except json.JSONDecodeError:
                    print(f"Error decoding mv_nodes/_object or mv_lines/_object as JSON")
        
        # Alternative approach: reading from the attached file
        print("Attempting to read MV data from attached file...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Check if the file exists
        json_path = os.path.join(script_dir, 'output', JSON_FILENAME)
        print(f"Looking for data in: {json_path}")
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                # Search for mv_nodes and mv_lines as strings in the file
                content = f.read()
                # Search for the section containing mv_nodes
                mv_nodes_match = re.search(r'"mv_nodes":\s*{\s*"_module":[^}]+?"_object":\s*"({[^"]+})"', content)
                mv_lines_match = re.search(r'"mv_lines":\s*{\s*"_module":[^}]+?"_object":\s*"({[^"]+})"', content)
                
                if mv_nodes_match and mv_lines_match:
                    try:
                        # Decode the JSON strings containing the GeoJSON
                        nodes_str = mv_nodes_match.group(1).replace('\\', '')
                        lines_str = mv_lines_match.group(1).replace('\\', '')
                        
                        # Replace escaped characters
                        nodes_str = nodes_str.replace('\\"', '"')
                        lines_str = lines_str.replace('\\"', '"')
                        
                        # Decode JSON objects
                        nodes_geojson = json.loads(nodes_str)
                        lines_geojson = json.loads(lines_str)
                        
                        print(f"Successfully extracted MV data from file. Found {len(nodes_geojson.get('features', []))} nodes and {len(lines_geojson.get('features', []))} lines.")
                        return nodes_geojson, lines_geojson
                    except json.JSONDecodeError as e:
                        print(f"Error decoding extracted JSON: {e}")
                else:
                    print("Could not find mv_nodes or mv_lines patterns in the file.")
        else:
            print(f"Warning: File {json_path} not found")
        
        return {}, {}
        
    except Exception as e:
        print(f"Error in extract_mv_data: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}

def parse_nodes(nodes_data):
    """Convert GeoJSON nodes to dictionary"""
    nodes_dict = {}
    for feature in nodes_data.get('features', []):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        node_id = properties.get('dave_name', '')
        coordinates = geometry.get('coordinates', [0, 0])
        
        nodes_dict[node_id] = {
            'id': node_id,
            'coordinates': coordinates,
            'connections': []
        }
    
    return nodes_dict

def parse_lines(lines_data, nodes_dict):
    """Convert GeoJSON lines to list and add connections to nodes"""
    lines = []
    total_length = 0
    
    for feature in lines_data.get('features', []):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        from_bus = properties.get('from_bus', '')
        to_bus = properties.get('to_bus', '')
        length_km = properties.get('length_km', 0)
        
        # Add connections to nodes
        if from_bus in nodes_dict:
            nodes_dict[from_bus]['connections'].append(to_bus)
        if to_bus in nodes_dict:
            nodes_dict[to_bus]['connections'].append(from_bus)
        
        coordinates = geometry.get('coordinates', [])
        
        if from_bus and to_bus and coordinates:
            lines.append({
                'from_bus': from_bus,
                'to_bus': to_bus,
                'length_km': length_km,
                'coordinates': coordinates
            })
            total_length += length_km
    
    return lines, total_length

def calculate_distance(coord1, coord2):
    """Calculate distance between two points in meters"""
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    
    x1, y1 = transformer.transform(coord1[0], coord1[1])
    x2, y2 = transformer.transform(coord2[0], coord2[1])
    
    # Calculate distance in meters
    distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    return distance

def calculate_area_dimensions(coordinates):
    """Calculate area dimensions from coordinates"""
    if not coordinates:
        return {
            'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0,
            'width': 0, 'height': 0, 'area': 0
        }
        
    lats = [coord[1] for coord in coordinates]
    lons = [coord[0] for coord in coordinates]
    
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Convert coordinates to meters
    x1, y1 = transformer.transform(min_lon, min_lat)
    x2, y2 = transformer.transform(max_lon, max_lat)
    
    # Calculate dimensions
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    area = width * height / 1000000  # in square kilometers
    
    return {
        'min_lat': min_lat,
        'max_lat': max_lat,
        'min_lon': min_lon,
        'max_lon': max_lon,
        'width': int(width),
        'height': int(height),
        'area': round(area, 2)
    }

# Functions for GNB Network
def get_tech_color(tech):
    """Returns color for 4G/5G"""
    return "#3498db" if tech == "4G" else "#e74c3c"  # Blue for 4G, Red for 5G

def get_tower_marker(tower_type):
    """Returns marker for tower type"""
    markers = {
        "MACRO": "o",   # Circle
        "MICRO": "s",   # Square
        "DAS": "^",     # Triangle
        "PICO": "d"     # Diamond
    }
    return markers.get(tower_type, "*")  # Default: star

def plot_combined_network(nodes_dict, lines, total_length, lte_data, nr_data):
    """Plot combined MV and GNB network"""
    # Change aspect ratio to cover more space
    plt.figure(figsize=(20, 12))
    
    # Collect all coordinates for dimension calculation
    all_coordinates = []
    
    # Plot MV lines
    for line in lines:
        from_node = nodes_dict.get(line['from_bus'])
        to_node = nodes_dict.get(line['to_bus'])
        
        if from_node and to_node:
            x1, y1 = from_node['coordinates']
            x2, y2 = to_node['coordinates']
            
            plt.plot([x1, x2], [y1, y2], 'k-', linewidth=1.0, alpha=0.5, zorder=1)
            all_coordinates.append([x1, y1])
            all_coordinates.append([x2, y2])
            
            # Calculate distance in meters
            distance = calculate_distance([x1, y1], [x2, y2])
            
            # Display distance above the line
            midx = (x1 + x2) / 2
            midy = (y1 + y2) / 2
            
            # Calculate the slope of the line for the direction of the offset
            if x2 != x1:  # Avoid division by zero
                slope = (y2 - y1) / (x2 - x1)
                angle = np.arctan(slope)
                offset_x = -0.00001 * np.sin(angle)
                offset_y = 0.00001 * np.cos(angle)
            else:  # Vertical line
                offset_x = 0.00001
                offset_y = 0
            
            # Selective display of only larger distances to avoid crowding
            if distance > 500:  # Display only distances > 500m
                plt.text(midx + offset_x, midy + offset_y, f"{int(distance)}m", 
                        fontsize=7, ha='center', va='center', 
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1'),
                        zorder=3)
    
    # Dictionary for GNB towers
    tech_tower_scatters = {}
    
    # Process 4G/LTE data
    for tower in lte_data['responseData']:
        lat = tower['latitude']
        lon = tower['longitude']
        all_coordinates.append([lon, lat])  # Add to coordinates
        
        tower_type = tower['towerAttributes'].get('TOWER_TYPE', 'UNKNOWN')
        key = (tower_type, '4G')
        
        if key not in tech_tower_scatters:
            tech_tower_scatters[key] = {'lats': [], 'lons': []}
        
        tech_tower_scatters[key]['lats'].append(lat)
        tech_tower_scatters[key]['lons'].append(lon)
    
    # Process 5G/NR data
    for tower in nr_data['responseData']:
        lat = tower['latitude']
        lon = tower['longitude']
        all_coordinates.append([lon, lat])  # Add to coordinates
        
        tower_type = tower['towerAttributes'].get('TOWER_TYPE', 'UNKNOWN')
        key = (tower_type, '5G')
        
        if key not in tech_tower_scatters:
            tech_tower_scatters[key] = {'lats': [], 'lons': []}
        
        tech_tower_scatters[key]['lats'].append(lat)
        tech_tower_scatters[key]['lons'].append(lon)
    
    # Calculate area dimensions
    dimensions = calculate_area_dimensions(all_coordinates)
    
    # Set equal aspect ratio for normal circles
    ax = plt.gca()
    ax.set_aspect('equal')
    
    # Set axis limits with smaller padding to maximize the graph
    padding = 0.0005
    plt.xlim(dimensions['min_lon'] - padding, dimensions['max_lon'] + padding)
    plt.ylim(dimensions['min_lat'] - padding, dimensions['max_lat'] + padding)
    
    # Define MV node size
    mv_node_color = 'lightblue'
    mv_node_radius = 0.0005  # Adjusted size
    
    # Plot MV nodes
    for node_id, node_data in nodes_dict.items():
        x, y = node_data['coordinates']
        
        # Extract numerical part of ID
        node_num = node_id.split('_')[-1]
        
        # Draw MV circle
        circle = plt.Circle((x, y), radius=mv_node_radius, fc=mv_node_color, ec='black', alpha=0.8, zorder=2)
        ax.add_patch(circle)
        
        # Add ID inside circle
        plt.text(x, y, node_num, fontsize=7, ha='center', va='center', weight='bold', zorder=3)
    
    # Define display order for legend
    tech_order = ['5G', '4G']
    tower_type_order = ['MACRO', 'MICRO', 'DAS', 'PICO']
    
    # Plot GNB towers and collect elements for legend
    legend_elements = []
    legend_labels = []
    
    # First iterate through technologies in predefined order
    for tech in tech_order:
        # Then iterate through tower types in predefined order
        for tower_type in tower_type_order:
            key = (tower_type, tech)
            
            if key in tech_tower_scatters and tech_tower_scatters[key]['lats']:
                # Get coordinates
                lats = tech_tower_scatters[key]['lats']
                lons = tech_tower_scatters[key]['lons']
                
                # Get shape and color
                marker = get_tower_marker(tower_type)
                color = get_tech_color(tech)
                
                # Plot towers
                scatter = plt.scatter(lons, lats, c=color, marker=marker, s=80, alpha=0.7, 
                                     edgecolors='black', linewidths=0.5, zorder=4)
                
                # Add to legend
                legend_elements.append(scatter)
                legend_labels.append(f"{tech} {tower_type}")
    
    # Add MV nodes to legend
    mv_node_patch = plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=mv_node_color, 
                              markersize=10, label='MV Nodes', markeredgecolor='black')
    legend_elements.append(mv_node_patch)
    legend_labels.append("MV Nodes")
    
    # Set graph properties
    plt.title('Combined Medium Voltage and GNB Network', fontsize=16, fontweight='bold')
    plt.xlabel('Longitude', fontsize=12)
    plt.ylabel('Latitude', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.4)
    
    # Create more space for the graph and less for information
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    
    # Legend
    plt.legend(legend_elements, legend_labels, loc='upper left', bbox_to_anchor=(1, 1))
    
    # Add total length and area information at the bottom center
    # Position closer to bottom of graph with larger frame
    plt.figtext(0.5, 0.02, 
                f"Total MV Line Length: {total_length:.2f} km\n"
                f"Area: {dimensions['width']}m × {dimensions['height']}m ({dimensions['area']} km²)", 
                fontsize=12, bbox=dict(facecolor='white', alpha=0.9, boxstyle='round,pad=0.8', edgecolor='gray', linewidth=1.5),
                ha='center', weight='bold')
    
    # Add information for corners - position closer to graph corners
    # Bottom left - larger frame size
    plt.figtext(0.05, 0.02, 
               f"Bottom left:\n({dimensions['min_lat']:.6f}, {dimensions['min_lon']:.6f})", 
               fontsize=10, ha='left', va='bottom', 
               bbox=dict(facecolor='lightyellow', alpha=0.9, boxstyle='round,pad=0.7', edgecolor='gray', linewidth=1.5))
    
    # Bottom right - larger frame size
    plt.figtext(0.95, 0.02, 
               f"Bottom right:\n({dimensions['min_lat']:.6f}, {dimensions['max_lon']:.6f})", 
               fontsize=10, ha='right', va='bottom', 
               bbox=dict(facecolor='lightyellow', alpha=0.9, boxstyle='round,pad=0.7', edgecolor='gray', linewidth=1.5))
    
    # Top left - larger frame size
    plt.figtext(0.05, 0.98, 
               f"Top left:\n({dimensions['max_lat']:.6f}, {dimensions['min_lon']:.6f})", 
               fontsize=10, ha='left', va='top', 
               bbox=dict(facecolor='lightyellow', alpha=0.9, boxstyle='round,pad=0.7', edgecolor='gray', linewidth=1.5))
    
    # Top right - larger frame size
    plt.figtext(0.95, 0.98, 
               f"Top right:\n({dimensions['max_lat']:.6f}, {dimensions['max_lon']:.6f})", 
               fontsize=10, ha='right', va='top', 
               bbox=dict(facecolor='lightyellow', alpha=0.9, boxstyle='round,pad=0.7', edgecolor='gray', linewidth=1.5))
    
    
    return dimensions

def main():
    # Load data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create Generated_Files directory if it doesn't exist
    generated_dir = os.path.join(script_dir, 'Generated_Files')
    if not os.path.exists(generated_dir):
        os.makedirs(generated_dir)
        print(f"Created directory: {generated_dir}")
    
    # DAVE MV Network data
    dave_data_path = os.path.join(script_dir, 'output', JSON_FILENAME)
    
    # GNB Network data
    lte_path = os.path.join(script_dir, 'output', LTE_FILENAME)
    nr_path = os.path.join(script_dir, 'output', NR_FILENAME)
    
    print(f"Loading data from DAVE dataset: {dave_data_path}")
    print(f"Loading data from LTE dataset: {lte_path}")
    print(f"Loading data from NR dataset: {nr_path}")
    
    try:
        # Load DAVE data
        dave_data = load_data(dave_data_path)
        
        # Load GNB data
        lte_data = load_data(lte_path)
        nr_data = load_data(nr_path)
        
        # Extract MV data
        mv_nodes_data, mv_lines_data = extract_mv_data(dave_data)
        
        if not mv_nodes_data or not mv_lines_data:
            print("No MV data found in the DAVE dataset.")
            return
        
        # Process MV data
        nodes_dict = parse_nodes(mv_nodes_data)
        if not nodes_dict:
            print("No nodes could be parsed from the MV data.")
            return
            
        lines, total_length = parse_lines(mv_lines_data, nodes_dict)
        if not lines:
            print("No lines could be parsed from the MV data.")
            return
        
        print(f"Found {len(nodes_dict)} MV nodes and {len(lines)} MV lines.")
        print(f"Found {len(lte_data['responseData'])} 4G towers and {len(nr_data['responseData'])} 5G towers.")
        
        # Plot combined network
        dimensions = plot_combined_network(nodes_dict, lines, total_length, lte_data, nr_data)
        
        # Save image to Generated_Files folder
        output_image = 'combined_network_map.png'
        output_path = os.path.join(generated_dir, output_image)
        plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
        print(f"Combined network map saved as: {output_path}")
        plt.close()
        
        # Print information
        print("\nBounding box coordinates (latitude, longitude):")
        print(f"Bottom left: ({dimensions['min_lat']}, {dimensions['min_lon']})")
        print(f"Bottom right: ({dimensions['min_lat']}, {dimensions['max_lon']})")
        print(f"Top left: ({dimensions['max_lat']}, {dimensions['min_lon']})")
        print(f"Top right: ({dimensions['max_lat']}, {dimensions['max_lon']})")
        print(f"\nArea dimensions in meters:")
        print(f"Width: {dimensions['width']} meters")
        print(f"Height: {dimensions['height']} meters")
        print(f"Total area: {dimensions['area']} km²")
        print(f"\nTotal MV network line length: {total_length:.2f} km")
        
    except Exception as e:
        print(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 