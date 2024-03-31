import pandas as pd
import json
import os
import networkx as nx
from utils import loading_bar
import time

class fluid_control():
    def __init__(self, hardware, pump_types, system_name, protocol) -> None:
        self.hardware = hardware # hardware is a dictionary of hardware names and their instantiated objects
        self.pump_types = pump_types
        self.system_name = system_name
        self.protocol = protocol
        self.graph = self.create_graph()

    def read_protocol(self):
        # Define file paths
        experiment_file = f"../protocols/{self.system_name}/{self.protocol}/experiment.json"
        fluids_file = f"../protocols/{self.system_name}/{self.protocol}/fluids.csv"
        fluid_edges_file = f"../system-files/{self.system_name}/fluid_edges.csv"
        fluid_nodes_file = f"../system-files/{self.system_name}/fluid_nodes.csv"

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
        self.fluids = fluids
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
        
        self.path_mode = 'linear'
        if 'new_era_syringe' in self.pump_types.values():
            self.path_mode = 'bifurcated'
        

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
            'type3': 'green',
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
        pumps = set(pumps)
        return pumps

    def run_protocol_step(self,protocol_step):
        fluid = protocol_step['step_metadata']["fluid"]
        volume = float(protocol_step['step_metadata']["volume"])
        speed = float(protocol_step['step_metadata']["speed"])
        if 'pump_wait' in protocol_step['step_metadata'].keys():
            pump_wait = protocol_step['step_metadata']['pump_wait']
        else:
            pump_wait = 0
        if self.path_mode == 'linear':
            path_edges = self.get_path(fluid, 'waste')
            self.linear_pump_action(path_edges,volume,speed)
            
        elif self.path_mode == 'bifurcated':
            path_edges = [self.get_path(fluid,'pump1'),
                          self.get_path('pump1','waste')]
            self.bifurcated_pump_action(path_edges,volume,speed,pump_wait)
                
    def linear_pump_action(self,path_edges,volume,speed):
        pumps = self.set_path(path_edges)
        if len(pumps) > 0:
            for pump in pumps:
                self.hardware[pump].set_rate('INF', speed)
                self.hardware[pump].set_volume(volume)
                self.hardware[pump].start()
                loading_bar.loading_bar_wait(60*volume/speed)
                
    def bifurcated_pump_action(self,path_edges,volume,speed,pump_wait):
        pump = 'pump1' # hardcoded for the timebeing
        if pump_wait == 0:
            switch_latency = 2 # wait for pressure to equalize before switching
        else:
            switch_latency = pump_wait
        vol_limit = self.hardware[pump].syringe_limit # this should break the code in case you're doing this with peristaltic...not supported
        vol_limit = float(vol_limit)
        volume = float(volume)
        speed = float(speed)
        if volume > vol_limit:
            num_splits = volume // vol_limit
            remainder = volume % vol_limit
            volumes = [vol_limit] * int(num_splits)
            if remainder > 0:
                volumes.append(remainder)
        else:
            volumes = [volume]
            
        for vol in volumes:
            _ = self.set_path(path_edges[0])
            self.hardware[pump].set_rate('WDR', speed)
            self.hardware[pump].set_volume(vol)
            self.hardware[pump].start()
            time.sleep(60*vol/speed + switch_latency) # loading bar would get out of hand
            _ = self.set_path(path_edges[1])
            self.hardware[pump].set_rate('INF', speed)
            self.hardware[pump].set_volume(vol)
            self.hardware[pump].start()
            time.sleep(60*vol/speed + switch_latency)
        

    def quick_valve(self, line_num):
        path_edges = self.get_path(str(line_num), 'waste')
        pumps = self.set_path(path_edges)
        return pumps
        
    def quick_pump(self, volume, speed, pumps):
        for pump in pumps:
            self.hardware[pump].set_rate('INF', speed)
            self.hardware[pump].set_volume(volume)
            self.hardware[pump].start()
            loading_bar.loading_bar_wait(60*volume/speed)
            
    def quick_run(self,line_num,volume,speed,pump_wait=3):
        if self.path_mode == 'linear':
            pumps = self.quick_valve(line_num)
            self.quick_pump(volume,speed,pumps)
        elif self.path_mode == 'bifurcated':
            path_edges = [self.get_path(str(line_num),'pump1'),
                          self.get_path('pump1','waste')]
            self.bifurcated_pump_action(path_edges,volume,speed,pump_wait)