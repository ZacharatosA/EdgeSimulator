import csv
import os
import shutil

def convert_gnb_to_xml():
    # Find the directory where the current script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to Generated_Files directory
    generated_dir = os.path.join(script_dir, 'Generated_Files')
    
    # Make sure Generated_Files directory exists
    if not os.path.exists(generated_dir):
        os.makedirs(generated_dir)
        print(f"Created directory: {generated_dir}")
    
    # Path to gnb_info.csv
    gnb_csv_path = os.path.join(generated_dir, 'gnb_info.csv')
    
    # Read the gnb_info.csv file
    gnbs = []
    try:
        with open(gnb_csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                gnbs.append(row)
    except FileNotFoundError:
        print(f"Error: The file {gnb_csv_path} was not found.")
        return
    except Exception as e:
        print(f"Error reading GNB CSV file: {e}")
        return
    
    # Create XML
    xml_content = '<?xml version="1.0" ?>\n<edge_datacenters>\n'
    
    # Track coordinates that have already been used
    used_coordinates = set()
    
    # List to store GNBs to include
    included_gnbs = []
    
    # Add each GNB as a datacenter if it has unique coordinates
    for gnb in gnbs:
        # Extract coordinates and check for negative values
        coords = gnb['normalized_coordinates'].strip('[]').split(', ')
        x_pos = max(0, int(coords[0]))  # If negative, set to 0
        y_pos = max(0, int(coords[1]))
        
        # Check if these coordinates have already been used
        coord_key = f"{x_pos}_{y_pos}"
        if coord_key in used_coordinates:
            print(f"Skipping gnb_{gnb['id']} (coordinates {x_pos},{y_pos} already in use)")
            continue
        
        # Add coordinates to the set of used coordinates
        used_coordinates.add(coord_key)
        
        # Add GNB to the list of included GNBs
        included_gnbs.append(gnb)
    
    # Create datacenters with sequential numbering
    for new_id, gnb in enumerate(included_gnbs):
        original_id = gnb['id']
        
        # Extract coordinates and check for negative values
        coords = gnb['normalized_coordinates'].strip('[]').split(', ')
        x_pos = max(0, int(coords[0]))  # If negative, set to 0
        y_pos = max(0, int(coords[1]))
        
        # Create datacenter in XML
        xml_content += f'\t<datacenter name="gnb_{new_id}">\n'
        xml_content += '\t\t<periphery>true</periphery>\n'
        xml_content += '\t\t<idleConsumption>7</idleConsumption>\n'
        xml_content += '\t\t<maxConsumption>15</maxConsumption>\n'
        xml_content += '\t\t<isOrchestrator>false</isOrchestrator>\n'
        xml_content += '\t\t<location>\n'
        xml_content += f'\t\t\t<x_pos>{x_pos}</x_pos>\n'
        xml_content += f'\t\t\t<y_pos>{y_pos}</y_pos>\n'
        xml_content += '\t\t</location>\n'
        xml_content += '\t\t<cores>1</cores>\n'
        xml_content += '\t\t<mips>71000</mips>\n'
        xml_content += '\t\t<ram>8192</ram>\n'
        xml_content += '\t\t<storage>64000</storage>\n'
        xml_content += '\t</datacenter>\n'
        
        if original_id != str(new_id):
            print(f"ID renumbering: gnb_{original_id} -> gnb_{new_id}")
    
    # Add network connections
    xml_content += '\t<network_links>\n'
    
    # Connect node 0 to the cloud (node 0 will always exist with the new numbering)
    xml_content += '\t\t<link>\n'
    xml_content += '\t\t\t<from>default_cloud</from>\n'
    xml_content += '\t\t\t<to>gnb_0</to>\n'
    xml_content += '\t\t\t<latency>0.05</latency>\n'
    xml_content += '\t\t</link>\n'
    
    # Add connections between neighboring GNBs (optional)
    # Connect each GNB to the next one in the list
    if len(included_gnbs) > 1:
        for i in range(len(included_gnbs) - 1):
            xml_content += '\t\t<link>\n'
            xml_content += f'\t\t\t<from>gnb_{i}</from>\n'
            xml_content += f'\t\t\t<to>gnb_{i+1}</to>\n'
            xml_content += '\t\t\t<latency>0.002</latency>\n'
            xml_content += '\t\t</link>\n'
    
    # Close the XML
    xml_content += '\t</network_links>\n</edge_datacenters>\n'
    
    # Save XML to Generated_Files
    xml_output_path = os.path.join(generated_dir, 'edge_datacenters.xml')
    with open(xml_output_path, 'w') as xmlfile:
        xmlfile.write(xml_content)
    
    print(f"XML file created: {xml_output_path}")
    
    # Also save a copy to EdgeSimulator/PureEdgeSim/DroneSim/Drone_settings
    drone_settings_dir = os.path.join(os.path.dirname(script_dir), 'PureEdgeSim', 'DroneSim', 'Drone_settings')
    
    if os.path.exists(drone_settings_dir):
        drone_xml_path = os.path.join(drone_settings_dir, 'edge_datacenters.xml')
        # Αντιγραφή του αρχείου
        shutil.copy2(xml_output_path, drone_xml_path)
        print(f"Also saved XML to: {drone_xml_path}")
    else:
        print(f"Warning: Directory {drone_settings_dir} not found, couldn't save XML there")
    
    print(f"Included {len(included_gnbs)} GNBs out of {len(gnbs)} total")

if __name__ == "__main__":
    convert_gnb_to_xml() 