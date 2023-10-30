import pandas as pd
import json
import os
import networkx as nx

class fluid_control():
    def __init__(self, hardware, system_name, protocol) -> None:
        self.hardware = hardware # hardware is a dictionary of hardware names and their instantiated objects
        self.system_name = system_name
        self.protocol = protocol
        self.graph = self.create_graph()

    def read_protocol(self):
        # Define file paths
        experiment_file = f"protocols/{self.system_name}/{self.protocol}/experiment.json"
        fluids_file = f"protocols/{self.system_name}/{self.protocol}/fluids.csv"
        fluid_edges_file = f"protocols/{self.system_name}/{self.protocol}/fluid_edges.csv"
        fluid_nodes_file = f"system-files/{self.system_name}/fluid_nodes.csv"

        # Check if files exist
        if not os.path.exists(experiment_file):
            raise FileNotFoundError(f"{experiment_file} not found")
        if not os.path.exists(fluids_file):
            raise FileNotFoundError(f"{fluids_file} not found")
        if not os.path.exists(fluid_edges_file):
            raise FileNotFoundError(f"{fluid_edges_file} not found")
        if not os.path.exists(fluid_nodes_file):
            raise FileNotFoundError(f"{fluid_nodes_file} not found")

        # Read files
        self.experiment = json.load(open(experiment_file))
        fluids = pd.read_csv(fluids_file)
        fluid_edges = pd.read_csv(fluid_edges_file)
        fluid_nodes = pd.read_csv(fluid_nodes_file)

        # Create graph
        graph = nx.Graph()

        # Add nodes
        for _, row in fluids.iterrows():
            node_id = row["NodeID"]
            node_type = row["FluidType"]
            graph.add_node(node_id, node_type=node_type, **row.to_dict())

        for _, row in fluid_nodes.iterrows():
            node_id = row["NodeID"]
            node_type = row["HardwareType"]
            graph.add_node(node_id, node_type=node_type, **row.to_dict())

        # Add edges
        for _, row in fluid_edges.iterrows():
            source = str(row["Source"])
            target = str(row["Target"])
            graph.add_edge(source, target, **row.to_dict())

        self.graph = graph

    def create_graph(self):
        self.read_protocol()
        return self.graph

    def get_path(self, source, target):
        path_nodes = nx.shortest_path(self.graph, source, target)
        path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
        return path_edges
    
    def draw_graph(self):
        color_map = {
    'type1': 'red',
    'type2': 'blue',
    'type3': 'green'
}

        nx.draw(self.graph, with_labels=True)
    
    def set_path(self,path_edges):
        pumps = []
        for edge in path_edges:
            source = edge[0]
            target = edge[1]
            detailed_edge = self.graph.edges[edge]
            if self.graph.nodes[source]["node_type"] == "Pump":
                pumps.append(source)
            elif self.graph.nodes[source]["node_type"] == "Valve":
                line_num = detailed_edge['source_pos']
                if line_num == 0:
                    pass
                else:
                    self.hardware[source].valve_switch(line_num)
            else:
                pass
            
            if self.graph.nodes[target]["node_type"] == "Pump":
                pumps.append(target)
            elif self.graph.nodes[target]["node_type"] == "Valve":
                line_num = detailed_edge['target_pos']
                if line_num == 0:
                    pass
                else:
                    self.hardware[target].valve_switch(line_num)
            else:
                pass

    def run_protocol_step(self,protocol_step):
        fluid = protocol_step["fluid"]
        volume = float(protocol_step["volume"])
        speed = float(protocol_step["speed"])
        path_edges = self.get_path(fluid, 'waste')
        pumps = self.set_path(path_edges)
        for pump in pumps:
            self.hardware[pump].set_rate('INF', speed)
            self.hardware[pump].set_volume(volume)
            self.hardware[pump].start()
