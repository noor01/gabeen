import os
import sys
import json
import pandas as pd

def compile_protocol(systemID, protocol_name):
    # Define file paths
    comports_path = f"../system-files/{systemID}/comports.json"
    fluid_nodes_path = f"../system-files/{systemID}/fluid_nodes.csv"
    experiment_path = f"../protocols/{systemID}/{protocol_name}/experiment.json"
    fluid_edges_path = f"../system-files/{systemID}/fluid_edges.csv"
    fluids_path = f"../protocols/{systemID}/{protocol_name}/fluids.csv"
    oni_params_path = f"../system-files/{systemID}/oni_params.json"
    
    print("Checking for:")
    print(comports_path)
    print(fluid_nodes_path)
    print(experiment_path)
    print(fluid_edges_path)
    print(fluids_path)
    print(oni_params_path)

    # Check if files exist
    if not os.path.exists(comports_path):
        raise Exception(f"comports.json not found at {comports_path}")
    if not os.path.exists(fluid_nodes_path):
        raise Exception(f"fluid_nodes.csv not found at {fluid_nodes_path}")
    if not os.path.exists(experiment_path):
        raise Exception(f"experiment.json not found at {experiment_path}")
    if not os.path.exists(fluid_edges_path):
        raise Exception(f"fluid_edges.csv not found at {fluid_edges_path}")
    if not os.path.exists(fluids_path):
        raise Exception(f"fluids.csv not found at {fluids_path}")

    # Load files
    with open(comports_path, "r") as f:
        comports = json.load(f)
    fluid_nodes = pd.read_csv(fluid_nodes_path)
    experiment = json.load(open(experiment_path, "r"))
    fluid_edges = pd.read_csv(fluid_edges_path)
    fluids = pd.read_csv(fluids_path)

    # Check if every value in the column "NodeID" in fluid_nodes.csv is a key in comport_keys
    node_ids = set(fluid_nodes["NodeID"])
    comport_keys = set(comports.keys())
    if not node_ids.issubset(comport_keys):
        raise Exception("Not every value in the column 'NodeID' in fluid_nodes.csv is a key in comport_keys")

    # Check to see that every unique value in the "Source" and "Target" columns in fluid_edges is in either the "NodeID" column in fluid_nodes or in the "NodeID" column in fluids.csv
    fluid_ids = set(fluids["NodeID"])
    edge_targets = set(fluid_edges["Target"])
    edge_sources = set(fluid_edges["Source"])
    if not edge_targets.issubset(node_ids.union(fluid_ids)):
        raise Exception("Not all unique values in fluid_edges.csv column 'Target' exist in the 'NodeID' column of fluid_nodes.csv OR in the 'NodeID' column of fluids.csv")
    if not edge_sources.issubset(node_ids.union(fluid_ids)):
        raise Exception("Not all unique values in fluid_edges.csv column 'Source' exist in the 'NodeID' column of fluid_nodes.csv OR in the 'NodeID' column of fluids.csv")

    # Check if experiment.json has "step_type": "image" in any of the nested dictionaries
    if any(step.get("step_type") == "image" for step_num, step in experiment.items()):
        # Check if there is a key, value pair in comports.json where the nested dictionary has a value "microscope" for key "hardware_type"
        microscope_comports = [comport for comport in comports.values() if comport.get("hardware_type") == "microscope"]
        if not microscope_comports:
            raise Exception(f"{systemID} not configured with 'hardware_type' = 'microscope'")
        # Check if the "hardware_manufacturer" is "ONI"
        oni_microscope_comports = [comport for comport in microscope_comports if comport.get("hardware_manufacturer") == "ONI"]
        if oni_microscope_comports and not os.path.exists(oni_params_path):
            raise Exception(f"ONI microscope comport found but oni_params.json not found at {oni_params_path}")

    print("all checks passed!")
