import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import os
import pyproj

# Load data
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Colors for technology (4G/5G)
def get_tech_color(tech):
    return "#3498db" if tech == "4G" else "#e74c3c"  # Blue for 4G, Red for 5G

# Markers for tower types
def get_tower_marker(tower_type):
    markers = {
        "MACRO": "o",   # Circle
        "MICRO": "s",   # Square
        "DAS": "^",     # Triangle
        "PICO": "d"     # Diamond
    }
    return markers.get(tower_type, "*")  # Default: star

# Calculate distance between two points in meters
def calculate_area_dimensions(lats, lons):
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Convert coordinates to real meters
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

def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    generated_dir = os.path.join(script_dir, 'Generated_Files')
    if not os.path.exists(generated_dir):
        os.makedirs(generated_dir)
        print(f"Created directory: {generated_dir}")
    
    # Load data
    lte_path = os.path.join(script_dir, 'output', 'B8_vd_4g.json')
    nr_path = os.path.join(script_dir, 'output', 'B8_vd_5g.json')
    
    lte_data = load_data(lte_path)
    nr_data = load_data(nr_path)
    
    # Create plot
    plt.figure(figsize=(15, 12))
    
    # All coordinates to calculate area
    all_lats = []
    all_lons = []
    
    # Dict to store scatter objects for the ordered legend
    tech_tower_scatters = {}
    
    # Process 4G/LTE data
    for tower in lte_data['responseData']:
        lat = tower['latitude']
        lon = tower['longitude']
        all_lats.append(lat)
        all_lons.append(lon)
        
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
        all_lats.append(lat)
        all_lons.append(lon)
        
        tower_type = tower['towerAttributes'].get('TOWER_TYPE', 'UNKNOWN')
        key = (tower_type, '5G')
        
        if key not in tech_tower_scatters:
            tech_tower_scatters[key] = {'lats': [], 'lons': []}
        
        tech_tower_scatters[key]['lats'].append(lat)
        tech_tower_scatters[key]['lons'].append(lon)
    
    # Define order for legend (5G before 4G, and MACRO, MICRO, DAS, PICO order)
    tech_order = ['5G', '4G']
    tower_type_order = ['MACRO', 'MICRO', 'DAS', 'PICO']
    
    # Draw towers according to ordered groups and collect scatter objects for the legend
    legend_elements = []
    legend_labels = []
    
    # First iterate through technologies in order
    for tech in tech_order:
        # Then iterate through tower types in order
        for tower_type in tower_type_order:
            key = (tower_type, tech)
            
            if key in tech_tower_scatters and tech_tower_scatters[key]['lats']:
                # Get coordinates
                lats = tech_tower_scatters[key]['lats']
                lons = tech_tower_scatters[key]['lons']
                
                # Get marker and color
                marker = get_tower_marker(tower_type)
                color = get_tech_color(tech)
                
                # Draw the towers
                scatter = plt.scatter(lons, lats, c=color, marker=marker, s=100, alpha=0.7, 
                                     edgecolors='black', linewidths=0.5)
                
                # Add to legend
                legend_elements.append(scatter)
                legend_labels.append(f"{tech} {tower_type}")
    
    # Calculate area dimensions
    dimensions = calculate_area_dimensions(all_lats, all_lons)
    
    # Print area information
    print("Bounding box coordinates (latitude, longitude):")
    print(f"Bottom left: ({dimensions['min_lat']}, {dimensions['min_lon']})")
    print(f"Bottom right: ({dimensions['min_lat']}, {dimensions['max_lon']})")
    print(f"Top left: ({dimensions['max_lat']}, {dimensions['min_lon']})")
    print(f"Top right: ({dimensions['max_lat']}, {dimensions['max_lon']})")
    print(f"\nArea dimensions in meters:")
    print(f"Width: {dimensions['width']} meters")
    print(f"Height: {dimensions['height']} meters")
    print(f"Total area: {dimensions['area']} km²")
    
    # Configure plot
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('4G and 5G Cell Tower Map', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Legend with ordered elements
    plt.legend(legend_elements, legend_labels, loc='upper left', bbox_to_anchor=(1, 1))
    
    # Add bounding box information to the plot
    plt.figtext(0.02, 0.02, 
                f"Area: {dimensions['width']}m × {dimensions['height']}m ({dimensions['area']} km²)", 
                fontsize=10)
    
    plt.tight_layout()
    
    # Save to Generated_Files folder
    output_path = os.path.join(generated_dir, 'GNB_network_map.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nMap saved as: {output_path}")
    
    # Close the plot to avoid conflicts with other plots
    plt.close()

if __name__ == "__main__":
    main() 