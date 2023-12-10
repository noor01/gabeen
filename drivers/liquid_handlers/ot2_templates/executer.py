from opentrons import protocol_api
import opentrons.execute
import subprocess
import argparse
import json

metadata = {'apiLevel': '2.5'}

def get_tip_num(experiment,step_num):
    # figure out which steps are liquid handling rounds
    liquid_handling_steps = []
    for step, value in experiment.items():
        if value['step_type'] == 'liquid_handler':
            liquid_handling_steps.append(step)
    tip_num = liquid_handling_steps.index(step_num)
    return tip_num

def load_custom_labware(labware_name,location):
    #parent_path = '/data/labware/v2/custom_definitions/'
    parent_path = '/data/user_storage/gabeen/custom_labware/'
    with open(f'{parent_path}{labware_name}.json') as labware_file:
        labware_def = json.load(labware_file)
        well_plate = protocol.load_labware_from_definition(labware_def, location)
    return well_plate

def run(protocol: protocol_api.ProtocolContext,step_num,start_tip_num=1):
    with open('/data/user_storage/gabeen/ot2_config.json') as f:
        ot2_config = json.load(f)
    with open('/data/user_storage/gabeen/experiment.json') as f:
        experiment = json.load(f)
    experimental_step = experiment[step_num]
    # Add labware
    labware = {}
    for key, value in ot2_config['labware'].items():
        if value['creator'] == 'opentrons':
            labware[key] = protocol.load_labware(value['api_name'], value['location'])
        else:
            labware[key] = load_custom_labware(value['api_name'], value['location'])
    # Add instruments
    instruments = {}
    for key, value in ot2_config['hardware'].items():
        tip_racks = []
        for rack in value['tip_racks']:
            tip_racks.append(labware[rack])
        instruments[key] = protocol.load_instrument(value['api_name'], mount=value['mount'], tip_racks=tip_racks)        
    reagent_metadata = experimental_step['step_metadata']['info']
    pipet = instruments[reagent_metadata['hardware']]
    pipet_type = reagent_metadata['hardware']
    tip_type = ot2_config['hardware'][pipet_type]['tip_racks'][0]
    tip_rack = labware[tip_type]
    tip_num = get_tip_num(experiment,step_num) + start_tip_num
    pipet.pick_up_tip(tip_rack.wells()[tip_num])
    repeat = int(reagent_metadata['repeat'])
    for i in range(repeat):
        pipet.aspirate(reagent_metadata['volume'], labware[reagent_metadata['labware']][reagent_metadata['location']])
        pipet.dispense(reagent_metadata['volume'], labware[experimental_step['step_metadata']['destination']]['A1'])
    pipet.drop_tip()
    
if __name__ == '__main__':
    protocol = opentrons.execute.get_protocol_api('2.15')
    protocol.home()
    parser = argparse.ArgumentParser()
    parser.add_argument('--step_num', type=int, help='Step number')
    parser.add_argument('--start_tip', type=int, help='Start tip number',default=0)

    args = parser.parse_args()
    step_num = str(args.step_num)
    start_tip_num = args.start_tip
    run(protocol, step_num, start_tip_num)
