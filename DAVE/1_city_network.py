import osmnx as ox
import geopandas as gpd
import pandapower as pp
import json
import os
from pathlib import Path
from dave_core.create import create_grid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dave_core import plot_grid_data

def create_city_geojson(city_name, size_km=2):
    """
    Creates a GeoJSON file for a city using data from OSM.
    """
    try:
        # Find city coordinates
        print(f"Finding coordinates for {city_name}...")
        location = ox.geocode(city_name)
        center_lat = location[0]
        center_lon = location[1]
        
        # Create bounding box
        bbox = ox.utils_geo.bbox_from_point((center_lat, center_lon), 
                                          dist=size_km*1000)
        
        # Download OSM data
        print(f"Downloading data for {city_name}...")
        G = ox.graph_from_bbox(bbox[0], bbox[1], bbox[2], bbox[3], 
                             network_type='drive',  # walk, drive, bike, all, all_public, drive_service
                             simplify=True,  # Simplify graph
                             retain_all=False)  # Keep only connected elements
        
        # Create GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "name": city_name,
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                }
            },
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": 1
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [bbox[2], bbox[0]],
                            [bbox[3], bbox[0]],
                            [bbox[3], bbox[1]],
                            [bbox[2], bbox[1]],
                            [bbox[2], bbox[0]]
                        ]]
                    }
                }
            ]
        }
        
        # Save GeoJSON
        script_dir = Path(__file__).parent
        geojson_path = script_dir / f"{city_name}.geojson"
        with open(geojson_path, 'w') as f:
            json.dump(geojson, f)
            
        print(f"GeoJSON file created successfully: {geojson_path}")
        return str(geojson_path)
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def create_dave_network(geojson_path, output_folder=None):
    """
    Creates an electricity network using DAVE.
    """
    try:
        # Read GeoJSON file
        print("Reading GeoJSON file...")
        own_area = gpd.read_file(geojson_path).iloc[0].geometry
        
        # Create output folder if not provided
        if output_folder is None:
            output_folder = Path(geojson_path).parent / "output"
            output_folder.mkdir(exist_ok=True)
        else:
            output_folder = Path(output_folder)
        
        grid_data, pp_net = create_grid(
            # Area definition
            own_area=own_area,
            # Geographic data
            geodata=["roads"], 
            # Voltage levels (MV only)
            power_levels=["mv"],  
            gas_levels=[],
            # Optional parameters
            combine_areas=[],
            convert_power=['pandapower'],
            # Network elements
            transformers=False,  
            renewable_powerplants=False,  
            conventional_powerplants=True,  
            loads=False,  
            # Output settings
            output_folder=str(output_folder.absolute()),
            output_format="json",
            save_data=True
        )
        print("Network created successfully!")
        plot_grid_data(grid_data)
   
    except Exception as e:
        print(f"An error occurred during network creation: {str(e)}")
        return None

# Usage example
if __name__ == "__main__":
    # Create GeoJSON for the area
    geojson_path = create_city_geojson("berlin", size_km=2)
    
    if geojson_path:
        # Create network with DAVE
        grid_data = create_dave_network(geojson_path)
