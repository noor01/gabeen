# Gabeen 🐝 🍯 🤖

## Control Process

flowchart coming soon...

## File Structure
- config
- controllers
    - config_manager.py
    - experiment_manager.py
    - fluid_control.py
    - hardware_loader.py
    - microscope_control.py
- data_processing
    - local_storage_manager.py
    - remote_storage_transfer.py
- drivers
    - liquid_handlers
        - handler.py
        - ot2.py
        - ot2_templates
    - microscopes
        - microscope.py
        - oni.py
        - squid.py
    - pumps
        - new_era_peristaltic.py
        - new_era_syringe.py
        - pump.py
    - valves
        - hamilton.py
        - precigenome.py
        - valve.py
    - serial_com.py
- logs
- protocols
- runs
- system-files
- telemetry
    - slack_notify.py
- utils
    - dialog_options.py [depracated]
    - FOV_Picker.py [depracated]
    - loading_bar.py
    - oni_utils.py
    - protocol_system_compiler.py
    - squid_utils.py

