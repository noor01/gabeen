from opentrons import protocol_api
import opentrons.execute
import subprocess
import argparse
import json

metadata = {'apiLevel': '2.5'}



def run(protocol: protocol_api.ProtocolContext,step_num):
    with open('/data/user_storage/gabeen/ot2_config.json') as f:
        ot2_config = json.load(f)
    with open('/data/user_storage/gabeen/experiment.json') as f:
        experiment = json.load(f)
    experimental_step = experiment[step_num]
    # Add labware
    labware = {}
    for key, value in ot2_config['labware'].items():
        labware[key] = protocol.load_labware(value['api_name'], value['location'])
    # Add instruments
    instruments = {}
    for key, value in ot2_config['hardware'].items():
        tip_racks = []
        for rack in value['tip_racks']:
            tip_racks.append(labware[rack])
        instruments[key] = protocol.load_instrument(value['api_name'], mount=value['mount'], tip_racks=tip_racks)        
    reagent_metadata = experimental_step['step_metadata']['info']
    pipet = instruments[reagent_metadata['hardware']]
    pipet.pick_up_tip()
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

    args = parser.parse_args()
    step_num = str(args.step_num)
    run(protocol,step_num)