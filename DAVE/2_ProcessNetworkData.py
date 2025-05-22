import json
import matplotlib.pyplot as plt
import numpy as np
import os
import csv
import pyproj
import re
from collections import defaultdict

# Variable for the name of the JSON file to be read
JSON_FILENAME = 'B2_dave_dataset.json'
GNB_4G_FILENAME = 'B8_vd_4g.json'
GNB_5G_FILENAME = 'B8_vd_5g.json'

def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def extract_mv_data(data):
    # Extraction of medium voltage data
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
            
            # Alternative approach: manual creation of GeoJSON
            if 'dtype' in nodes_json:
                print("Found mv_nodes with dtype, creating features manually...")
                # Here we may need to read the data directly from the JSON file
                # as it may be stored in a different format
        
        # Create a simpler GeoJSON structure for lines
        lines_features = []
        if 'mv_lines' in mv_data:
            lines_json = mv_data['mv_lines']
            # Similar approach to nodes

        # Create GeoJSON objects
        nodes_geojson = {"type": "FeatureCollection", "features": nodes_features}
        lines_geojson = {"type": "FeatureCollection", "features": lines_features}
        
        # Alternative approach: reading from the attached file
        print("Attempting to read MV data from attached file...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Check if the file exists
        json_path = os.path.join(script_dir, 'output', 'B2dave_dataset.json')
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
        
        return nodes_geojson, lines_geojson
        
    except Exception as e:
        print(f"Error in extract_mv_data: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}

def convert_to_normalized_coordinates(coords_list, bbox):
    """
    Converts geographic coordinates to a normalized (X,Y) system
    with margin so that the bottom left point is not (0,0).
    
    Args:
        coords_list: List with coordinates in the form [longitude, latitude]
        bbox: Dictionary with min_lon, min_lat, max_lon, max_lat of the system
        
    Returns:
        List with converted coordinates [x, y]
    """
    # Calculation of scale factors
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    
    # Conversion of bbox limits to meters
    min_x, min_y = transformer.transform(bbox['min_lon'], bbox['min_lat'])
    max_x, max_y = transformer.transform(bbox['max_lon'], bbox['max_lat'])
    
    # Calculation of the width and height of the space
    width = max_x - min_x
    height = max_y - min_y
    
    # Adding a 10% margin on all sides
    margin_x = width * 0.1
    margin_y = height * 0.1
    
    # Conversion of the point coordinates
    x, y = transformer.transform(coords_list[0], coords_list[1])
    
    # Normalization with margin
    norm_x = x - min_x + margin_x
    norm_y = y - min_y + margin_y
    
    # Return normalized coordinates
    return [int(norm_x), int(norm_y)]

def parse_nodes(nodes_data):
    nodes_dict = {}
    all_coordinates = []
    
    for feature in nodes_data.get('features', []):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        node_id = properties.get('dave_name', '')
        # Extract the numerical part of the ID
        node_num = node_id.split('_')[-1]
        coordinates = geometry.get('coordinates', [0, 0])
        all_coordinates.append(coordinates)
        
        nodes_dict[node_id] = {
            'id': node_num,  # Store only the numerical part
            'coordinates': coordinates,
            'connections': []
        }
    
    # Calculate bounding box
    if all_coordinates:
        lats = [coord[1] for coord in all_coordinates]
        lons = [coord[0] for coord in all_coordinates]
        
        bbox = {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }
        
        # Add normalized coordinates to each node
        for node_id, node_data in nodes_dict.items():
            node_data['normalized_coordinates'] = convert_to_normalized_coordinates(
                node_data['coordinates'], bbox
            )
    
    return nodes_dict

def parse_lines(lines_data, nodes_dict):
    lines = []
    total_length = 0
    
    # Add a dictionary to store edge distances
    edge_distances = {}
    # To avoid double calculation of the same edge
    processed_edges = set()
    # New variable for total length based on Euclidean distance
    euclidean_total_length_m = 0
    
    for feature in lines_data.get('features', []):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        from_bus = properties.get('from_bus', '')
        to_bus = properties.get('to_bus', '')
        length_km = properties.get('length_km', 0)
        
        # Calculate the distance between nodes
        if from_bus in nodes_dict and to_bus in nodes_dict:
            coord1 = nodes_dict[from_bus]['coordinates']
            coord2 = nodes_dict[to_bus]['coordinates']
            distance = calculate_distance(coord1, coord2)
            
            # Store the distance in both directions
            edge_key1 = f"{from_bus}-{to_bus}"
            edge_key2 = f"{to_bus}-{from_bus}"
            edge_distances[edge_key1] = int(distance)
            edge_distances[edge_key2] = int(distance)
            
            # Add the Euclidean distance to the total length
            # only once for each pair of nodes
            if (from_bus, to_bus) not in processed_edges and (to_bus, from_bus) not in processed_edges:
                euclidean_total_length_m += distance
                processed_edges.add((from_bus, to_bus))
        
        # Add connections to the nodes
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
                'coordinates': coordinates,
                'euclidean_distance': edge_distances.get(f"{from_bus}-{to_bus}", 0)
            })
            total_length += length_km
    
    # Add distances to node data
    for node_id, node_data in nodes_dict.items():
        node_data['edge_distances'] = {}
        for connection in node_data['connections']:
            edge_key = f"{node_id}-{connection}"
            if edge_key in edge_distances:
                node_data['edge_distances'][connection] = edge_distances[edge_key]
    
    # Convert from meters to kilometers
    euclidean_total_length_km = euclidean_total_length_m / 1000
    
    return lines, euclidean_total_length_km

def calculate_distance(coord1, coord2):
    # Convert from geographic coordinates to meters
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    
    x1, y1 = transformer.transform(coord1[0], coord1[1])
    x2, y2 = transformer.transform(coord2[0], coord2[1])
    
    # Calculate distance in meters
    distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    return distance

def calculate_area_dimensions(coordinates):
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

def get_tech_color(tech):
    """
    Returns the color based on the technology of the tower
    
    Args:
        tech: Technology of the tower (4G or 5G)
        
    Returns:
        Color as a string
    """
    colors = {
        '4G': '#2ecc71',  # Green
        '5G': '#ff7f0e'   # Orange
    }
    return colors.get(tech, '#2ecc71')  # Green as default

def get_tower_marker(tower_type):
    """
    Returns the marker based on the tower type
    
    Args:
        tower_type: Type of the tower (MACRO, MICRO, DAS, PICO)
        
    Returns:
        Marker as a string
    """
    markers = {
        'MACRO': 'o',    # Circle
        'MICRO': 's',    # Square
        'DAS': '^',      # Triangle
        'PICO': 'D'      # Diamond
    }
    return markers.get(tower_type, 'o')  # Circle as default

def save_nodes_to_csv(nodes_dict, output_path):
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['id', 'coordinates', 'normalized_coordinates', 'connections', 'edge_distances']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for node_id, node_data in nodes_dict.items():
            # Convert connections to simple numbers for CSV
            numeric_connections = []
            for conn in node_data['connections']:
                num_conn = conn.split('_')[-1]
                numeric_connections.append(num_conn)
            
            # Convert edge_distances with numeric keys
            numeric_edge_distances = {}
            for conn, dist in node_data['edge_distances'].items():
                num_conn = conn.split('_')[-1]
                numeric_edge_distances[num_conn] = dist
            
            writer.writerow({
                'id': node_data['id'],  # Already only numerical part
                'coordinates': str(node_data['coordinates']),
                'normalized_coordinates': str(node_data['normalized_coordinates']),
                'connections': str(numeric_connections),
                'edge_distances': str(numeric_edge_distances)
            })

def plot_network(nodes_dict, lines, total_length):
    # Increase the size of the plot and improve the ratio
    plt.figure(figsize=(18, 15))
    
    # Collect all coordinates for dimension calculation
    all_coordinates = []
    
    # Plot lines and add distances
    for line in lines:
        from_node = nodes_dict.get(line['from_bus'])
        to_node = nodes_dict.get(line['to_bus'])
        
        if from_node and to_node:
            x1, y1 = from_node['coordinates']
            x2, y2 = to_node['coordinates']
            
            plt.plot([x1, x2], [y1, y2], 'k-', linewidth=1.0, alpha=0.8, zorder=1)
            all_coordinates.append([x1, y1])
            all_coordinates.append([x2, y2])
            
            # Calculate distance in meters
            distance = calculate_distance([x1, y1], [x2, y2])
            
            # Display the distance above the line
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
            
            plt.text(midx + offset_x, midy + offset_y, f"{int(distance)}m", 
                    fontsize=8, ha='center', va='center', 
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'),
                    zorder=3)
    
    # Calculate area dimensions to adjust aspect ratio
    dimensions = calculate_area_dimensions(all_coordinates)
    
    # Set axis limits with small padding for clearer plot display
    padding = 0.0005
    plt.xlim(dimensions['min_lon'] - padding, dimensions['max_lon'] + padding)
    plt.ylim(dimensions['min_lat'] - padding, dimensions['max_lat'] + padding)
    
    # Set equal aspect ratio for normal circles
    ax = plt.gca()
    ax.set_aspect('equal')
    
    # Define node size - adjusted for equal aspect ratio
    node_color = 'lightblue'
    node_radius = 0.0005  # Adjusted size
    
    # Plot nodes as circles with their IDs inside - all same color and size
    for node_id, node_data in nodes_dict.items():
        x, y = node_data['coordinates']
        
        # Use the already stored numerical ID
        node_num = node_data['id']
        
        # Draw circle - all same color and size
        circle = plt.Circle((x, y), radius=node_radius, fc=node_color, ec='black', alpha=0.8, zorder=2)
        ax.add_patch(circle)
        
        # Add ID inside the circle
        plt.text(x, y, node_num, fontsize=9, ha='center', va='center', weight='bold', zorder=3)
    
    # Set plot properties
    plt.title('Medium Voltage Network', fontsize=16, fontweight='bold')
    plt.xlabel('Longitude', fontsize=12)
    plt.ylabel('Latitude', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.4)
    
    # Create more space for the plot and less for the information
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    
    # Add total length and area information at the bottom center
    # Place closer to the bottom of the plot with a larger frame
    plt.figtext(0.5, 0.02, 
                f"Total Euclidean Line Length: {total_length:.2f} km\n"
                f"Area: {dimensions['width']}m × {dimensions['height']}m ({dimensions['area']} km²)", 
                fontsize=12, bbox=dict(facecolor='white', alpha=0.9, boxstyle='round,pad=0.8', edgecolor='gray', linewidth=1.5),
                ha='center', weight='bold')
    
    # Add information for the corners - place closer to the corners of the plot
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

def parse_gnb_data(gnb_4g_file, gnb_5g_file, bbox):
    """
    Reads the GNB data from 4G and 5G files and filters those
    that are within the MV network bounding box (with additional margin)
    
    Args:
        gnb_4g_file: Path to the 4G file
        gnb_5g_file: Path to the 5G file
        bbox: The bounding box of the MV network
        
    Returns:
        Dictionary with filtered GNBs and normalized coordinates
    """
    gnb_dict = {}
    gnb_id = 0
    
    # Calculate an expanded bounding box to include more GNBs
    # Add 10% margin to the original bounding box
    margin_lon = (bbox['max_lon'] - bbox['min_lon']) * 0.1
    margin_lat = (bbox['max_lat'] - bbox['min_lat']) * 0.1
    
    extended_bbox = {
        'min_lon': bbox['min_lon'] - margin_lon,
        'max_lon': bbox['max_lon'] + margin_lon,
        'min_lat': bbox['min_lat'] - margin_lat,
        'max_lat': bbox['max_lat'] + margin_lat
    }
    
    print(f"Original bounding box: {bbox}")
    print(f"Extended bounding box: {extended_bbox}")
    
    try:
        # Load 4G data
        if os.path.exists(gnb_4g_file):
            print(f"Reading 4G data from {gnb_4g_file}")
            data_4g = load_data(gnb_4g_file)
            for gnb in data_4g.get('responseData', []):
                lat = gnb.get('latitude', 0)
                lon = gnb.get('longitude', 0)
                
                # Check if the point is within the expanded bounding box
                if (extended_bbox['min_lon'] <= lon <= extended_bbox['max_lon'] and 
                    extended_bbox['min_lat'] <= lat <= extended_bbox['max_lat']):
                    
                    # Create a list of coordinates [longitude, latitude]
                    coords = [lon, lat]
                    
                    # Calculate normalized coordinates using the original bbox
                    # to maintain the correct scale
                    normalized_coords = convert_to_normalized_coordinates(coords, bbox)
                    
                    # Determine GNB type from towerAttributes
                    gnb_type = "MACRO"  # Default
                    if "towerAttributes" in gnb and "TOWER_TYPE" in gnb["towerAttributes"]:
                        gnb_type = gnb["towerAttributes"]["TOWER_TYPE"]
                    
                    # Store information
                    gnb_dict[gnb_id] = {
                        'coordinates': coords,
                        'normalized_coordinates': normalized_coords,
                        'type': gnb_type,
                        'technology': '4G'
                    }
                    gnb_id += 1
        
        # Load 5G data
        if os.path.exists(gnb_5g_file):
            print(f"Reading 5G data from {gnb_5g_file}")
            data_5g = load_data(gnb_5g_file)
            for gnb in data_5g.get('responseData', []):
                lat = gnb.get('latitude', 0)
                lon = gnb.get('longitude', 0)
                
                # Check if the point is within the expanded bounding box
                if (extended_bbox['min_lon'] <= lon <= extended_bbox['max_lon'] and 
                    extended_bbox['min_lat'] <= lat <= extended_bbox['max_lat']):
                    
                    # Create a list of coordinates [longitude, latitude]
                    coords = [lon, lat]
                    
                    # Calculate normalized coordinates using the original bbox
                    normalized_coords = convert_to_normalized_coordinates(coords, bbox)
                    
                    # Determine GNB type from towerAttributes
                    gnb_type = "MACRO"  # Default
                    if "towerAttributes" in gnb and "TOWER_TYPE" in gnb["towerAttributes"]:
                        gnb_type = gnb["towerAttributes"]["TOWER_TYPE"]
                    
                    # Store information
                    gnb_dict[gnb_id] = {
                        'coordinates': coords,
                        'normalized_coordinates': normalized_coords,
                        'type': gnb_type,
                        'technology': '5G'
                    }
                    gnb_id += 1
        
        print(f"Found {len(gnb_dict)} GNBs within the MV network bounding box")
        
        # Detailed information about station types
        tech_counts = {
            '4G': sum(1 for gnb in gnb_dict.values() if gnb.get('technology') == '4G'),
            '5G': sum(1 for gnb in gnb_dict.values() if gnb.get('technology') == '5G')
        }
        
        type_counts = {}
        for gnb in gnb_dict.values():
            gnb_type = gnb.get('type', 'UNKNOWN')
            if gnb_type not in type_counts:
                type_counts[gnb_type] = 0
            type_counts[gnb_type] += 1
        
        print(f"GNB Technologies: {tech_counts}")
        print(f"GNB Types: {type_counts}")
        
        return gnb_dict
    
    except Exception as e:
        print(f"Error parsing GNB data: {e}")
        import traceback
        traceback.print_exc()
        return {}

def determine_gnb_type(properties):
    """
    Determines the type of GNB based on its properties
    
    Args:
        properties: Dictionary with GNB properties
        
    Returns:
        String with the type of GNB (MACRO, MICRO, DAS, PICO)
    """
    # Extract information from properties
    # This logic can be adapted according to the data structure
    
    # Search for common keywords
    props_str = str(properties).lower()
    
    if 'macro' in props_str:
        return 'MACRO'
    elif 'micro' in props_str:
        return 'MICRO'
    elif 'das' in props_str:
        return 'DAS'
    elif 'pico' in props_str:
        return 'PICO'
    else:
        # Default value
        return 'MACRO'

def save_gnbs_to_csv(gnb_dict, output_file):
    """
    Saves GNB information to a CSV file
    
    Args:
        gnb_dict: Dictionary with GNB data
        output_file: File path for saving
    """
    try:
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['id', 'coordinates', 'normalized_coordinates', 'type', 'technology']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for gnb_id, gnb_data in gnb_dict.items():
                writer.writerow({
                    'id': gnb_id,
                    'coordinates': gnb_data['coordinates'],
                    'normalized_coordinates': gnb_data['normalized_coordinates'],
                    'type': gnb_data['type'],
                    'technology': gnb_data['technology']
                })
        print(f"Successfully saved {len(gnb_dict)} GNBs to {output_file}")
    except Exception as e:
        print(f"Error saving GNB data to CSV: {e}")

def plot_combined_network(nodes_dict, lines, gnb_dict, total_length, output_filename='combined_network_map.png'):
    """
    Creates and saves a plot that includes the MV network and GNBs
    
    Args:
        nodes_dict: Dictionary with MV node data
        lines: List with MV network line data
        gnb_dict: Dictionary with GNB data
        total_length: Total length of MV network lines
        output_filename: Filename for saving the plot
    
    Returns:
        Dictionary with the dimensions of the plot
    """
    # Increase the size of the plot and improve the ratio
    plt.figure(figsize=(16, 14), dpi=100)
    
    # Set plot style
    plt.style.use('default')
    
    # Collect all coordinates for dimension calculation
    x_coords = [node['normalized_coordinates'][0] for node in nodes_dict.values()]
    y_coords = [node['normalized_coordinates'][1] for node in nodes_dict.values()]
    
    # Also add GNB coordinates
    gnb_x_coords = [gnb['normalized_coordinates'][0] for gnb in gnb_dict.values()]
    gnb_y_coords = [gnb['normalized_coordinates'][1] for gnb in gnb_dict.values()]
    
    # Combine all coordinates to determine limits
    all_x_coords = x_coords + gnb_x_coords
    all_y_coords = y_coords + gnb_y_coords
    
    # Plot lines and add distances
    for line in lines:
        from_node_id = line['from_bus']
        to_node_id = line['to_bus']
        
        if from_node_id in nodes_dict and to_node_id in nodes_dict:
            from_x = nodes_dict[from_node_id]['normalized_coordinates'][0]
            from_y = nodes_dict[from_node_id]['normalized_coordinates'][1]
            to_x = nodes_dict[to_node_id]['normalized_coordinates'][0]
            to_y = nodes_dict[to_node_id]['normalized_coordinates'][1]
            
            # Plot the line
            plt.plot([from_x, to_x], [from_y, to_y], 'k-', linewidth=1.0, alpha=0.6, zorder=1)
            
            # Add distance label to the middle of the edge
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            
            # Calculate distance (if available in data)
            distance = None
            
            if 'euclidean_distance' in line:
                distance = line['euclidean_distance']
            elif 'edge_distances' in nodes_dict[from_node_id] and to_node_id in nodes_dict[from_node_id]['edge_distances']:
                distance = nodes_dict[from_node_id]['edge_distances'][to_node_id]
                
            if distance is not None:
                # Add distance label to the edge
                plt.text(mid_x, mid_y, f"{int(distance)}m", fontsize=7, 
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray', boxstyle='round,pad=0.2'),
                        ha='center', va='center', zorder=5)
    
    # Plot MV nodes
    # Use a single color for all MV nodes
    mv_color = '#add8e6'  # Light blue
    mv_size = 210         # Triple size (70 * 3 = 210)
    
    for node_id, node_data in nodes_dict.items():
        x, y = node_data['normalized_coordinates'][0], node_data['normalized_coordinates'][1]
        node_num = node_data['id']  # Use numerical ID
        
        # Plot the node
        plt.scatter(x, y, color=mv_color, s=mv_size, edgecolors='black', linewidths=0.8, alpha=0.9, zorder=2)
        
        # Add node ID inside the node (larger size due to larger node)
        plt.text(x, y, node_num, fontsize=9, ha='center', va='center', 
                color='black', weight='bold', zorder=3)
    
    # Define sizes for different tower types
    gnb_sizes = {
        'MACRO': 120,  # Larger size
        'MICRO': 100,
        'DAS': 80,
        'PICO': 60
    }
    
    # Maintain references to scatter objects for legend
    tech_scatter_refs = {}  # For different technologies
    type_scatter_refs = {}  # For different tower types
    
    # Plot GNB towers
    for gnb_id, gnb_data in gnb_dict.items():
        x, y = gnb_data['normalized_coordinates'][0], gnb_data['normalized_coordinates'][1]
        tech = gnb_data.get('technology', '4G')
        tower_type = gnb_data.get('type', 'MACRO')
        
        # Use color, marker, and size with helper functions
        color = get_tech_color(tech)
        marker = get_tower_marker(tower_type)
        size = gnb_sizes.get(tower_type, 80)
        
        # Plot the GNB
        scatter = plt.scatter(x, y, color=color, marker=marker, s=size, 
                    edgecolors='black', linewidths=0.8, alpha=0.9, zorder=4)
        
        # Add label with type and technology
        label_text = f"{tech}/{tower_type[:2]}"
        plt.text(x, y + 100, label_text, fontsize=6, ha='center', va='center',
                color='black', weight='bold',
                bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.1', 
                         edgecolor=color, linewidth=0.5),
                zorder=5)
        
        # Maintain references for legend
        tech_key = tech
        if tech_key not in tech_scatter_refs:
            tech_scatter_refs[tech_key] = (color, 'o')  # Simplified for legend
            
        type_key = tower_type
        if type_key not in type_scatter_refs:
            type_scatter_refs[type_key] = marker
    
    # Create legend elements
    legend_elements = []
    
    # Add MV network to legend
    legend_elements.append(plt.Line2D([0], [0], color='black', lw=1.5, label='MV Network Connection'))
    legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=mv_color, 
                                     markeredgecolor='black', markersize=10, label='MV Node'))
    
    # Add GNB technology legend
    for tech, (color, _) in tech_scatter_refs.items():
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                         markerfacecolor=color, markeredgecolor='black', 
                                         markersize=8, label=f'{tech} Base Station'))
    
    # Add tower type legend
    for tower_type, marker in type_scatter_refs.items():
        # Use gray color for tower types in legend
        legend_elements.append(plt.Line2D([0], [0], marker=marker, color='w', 
                                         markerfacecolor='darkgray', markeredgecolor='black', 
                                         markersize=8, label=f'{tower_type} Tower'))
    
    # Create legend with smaller size and transparency
    legend = plt.legend(handles=legend_elements, loc='upper right', fontsize=9, framealpha=0.8)
    
    # Add title and labels to axes
    plt.title('Combined Medium Voltage Network and Telecommunication Base Stations', 
              fontsize=14, fontweight='bold', pad=10)
    plt.xlabel('Normalized X Coordinate', fontsize=11)
    plt.ylabel('Normalized Y Coordinate', fontsize=11)
    
    # Add grid for better readability
    plt.grid(True, linestyle='--', alpha=0.3)
    
    # Adjust axis limits
    min_x = min(all_x_coords) if all_x_coords else 0
    max_x = max(all_x_coords) if all_x_coords else 1
    min_y = min(all_y_coords) if all_y_coords else 0
    max_y = max(all_y_coords) if all_y_coords else 1
    
    # Add 5% margin
    margin_x = (max_x - min_x) * 0.05
    margin_y = (max_y - min_y) * 0.05
    
    plt.xlim(min_x - margin_x, max_x + margin_x)
    plt.ylim(min_y - margin_y, max_y + margin_y)
    
    # Create statistics for info box
    total_gnbs = len(gnb_dict)
    gnb_4g_count = sum(1 for gnb in gnb_dict.values() if gnb.get('technology') == '4G')
    gnb_5g_count = sum(1 for gnb in gnb_dict.values() if gnb.get('technology') == '5G')
    
    # Add tower type statistics
    tower_types_count = {}
    for gnb in gnb_dict.values():
        tower_type = gnb.get('type', 'UNKNOWN')
        if tower_type not in tower_types_count:
            tower_types_count[tower_type] = 0
        tower_types_count[tower_type] += 1
    
    # Create text for tower type statistics
    tower_types_text = "\n".join([f"  • {t_type}: {count}" for t_type, count in tower_types_count.items()])
    
    # Add statistics to plot
    info_text = (
        f"Network Statistics:\n"
        f"- Total MV Network Length: {total_length:.2f} km\n"
        f"- Number of MV Nodes: {len(nodes_dict)}\n"
        f"- Telecom Base Stations: {total_gnbs}\n"
        f"  • 4G Stations: {gnb_4g_count}\n"
        f"  • 5G Stations: {gnb_5g_count}\n"
        f"- Tower Types:\n{tower_types_text}"
    )
    
    # Add text box for information
    plt.figtext(0.02, 0.02, info_text, fontsize=9, 
               bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5', 
                         edgecolor='darkgray', linewidth=0.5))
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the plot
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Combined network map saved as: {output_path}")
    
    # Return dimensions for possible future use
    dimensions = {
        'min_x': min_x,
        'max_x': max_x,
        'min_y': min_y,
        'max_y': max_y,
    }
    
    return dimensions

def main(json_filename=JSON_FILENAME):
    # Load the data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, 'output', json_filename)
    
    print(f"Loading data from {data_path}")
    try:
        data = load_data(data_path)
        
        # Extract MV data
        mv_nodes_data, mv_lines_data = extract_mv_data(data)
        
        if not mv_nodes_data or not mv_lines_data:
            print("No MV data found in the JSON file.")
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
        
        print(f"Found {len(nodes_dict)} nodes and {len(lines)} lines.")
        
        # Create Generated_Files directory if it doesn't exist
        generated_dir = os.path.join(script_dir, 'Generated_Files')
        if not os.path.exists(generated_dir):
            os.makedirs(generated_dir)
            print(f"Created directory: {generated_dir}")
        
        # Plot MV network only
        dimensions = plot_network(nodes_dict, lines, total_length)
        
        # Αποθήκευση του mv_network_map.png στο Generated_Files
        mv_network_map = os.path.join(generated_dir, 'mv_network_map.png')
        plt.savefig(mv_network_map, dpi=300, bbox_inches='tight', pad_inches=0.2)
        print(f"MV network map saved as: {mv_network_map}")
        plt.close()
        
        # Save MV node information to CSV in Generated_Files
        mv_csv_path = os.path.join(generated_dir, 'mv_nodes_info.csv')
        save_nodes_to_csv(nodes_dict, mv_csv_path)
        
        # Also save a copy to EdgeSimulator/PureEdgeSim/DroneSim
        dronesim_dir = os.path.join(os.path.dirname(script_dir), 'PureEdgeSim', 'DroneSim')
        if os.path.exists(dronesim_dir):
            dronesim_mv_csv = os.path.join(dronesim_dir, 'mv_nodes_info.csv')
            save_nodes_to_csv(nodes_dict, dronesim_mv_csv)
            print(f"Also saved MV nodes info to: {dronesim_mv_csv}")
        else:
            print(f"Warning: Directory {dronesim_dir} not found, couldn't save MV nodes info there")
        
        # Create bounding box from dimensions
        bbox = {
            'min_lat': dimensions['min_lat'],
            'max_lat': dimensions['max_lat'],
            'min_lon': dimensions['min_lon'],
            'max_lon': dimensions['max_lon']
        }
        
        # Load and process GNB data
        gnb_4g_path = os.path.join(script_dir, 'output', GNB_4G_FILENAME)
        gnb_5g_path = os.path.join(script_dir, 'output', GNB_5G_FILENAME)
        
        print(f"Loading and processing GNB data from {gnb_4g_path} and {gnb_5g_path}")
        
        # Extract GNB data (4G and 5G)
        gnb_dict = parse_gnb_data(gnb_4g_path, gnb_5g_path, bbox)
        
        if not gnb_dict:
            print("No GNBs found within the MV network bounding box.")
        else:
            # Save GNB information to CSV in Generated_Files
            gnb_csv_path = os.path.join(generated_dir, 'gnb_info.csv')
            save_gnbs_to_csv(gnb_dict, gnb_csv_path)
            print(f"GNB information saved to: {gnb_csv_path}")
            
            # Create combined network map with MV and GNB
            plot_combined_network(nodes_dict, lines, gnb_dict, total_length, os.path.join(generated_dir, 'combined_network_map.png'))
        
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
        print(f"\nTotal Euclidean network line length: {total_length:.2f} km")
        print(f"\nNode information saved to: {mv_csv_path}")
        
    except Exception as e:
        print(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 