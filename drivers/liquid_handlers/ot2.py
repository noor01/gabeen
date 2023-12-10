import time
import os
import subprocess
from .handler import Handler
from dotenv import load_dotenv
import platform

class OT2(Handler):
    def __init__(self,protocol_file, ot2_config_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_path = protocol_file
        self.ot2_config_path = ot2_config_file
        load_dotenv()
        self.ROBOT_IP = os.environ.get('ROBOT_IP')
        self.ROBOT_KEY = os.environ.get('ROBOT_KEY')
        self.ROBOT_USERNAME = os.environ.get('ROBOT_USERNAME')
        self.init_ssh()
        self.init_scp()
        self.init_protocol()   
        self.upload_custom_labware()   
        
    def init_protocol(self):
        # Upload executer script
        executer_path = os.path.abspath("../drivers/liquid_handlers/ot2_templates/executer.py")
        remote_path = '/data/user_storage/gabeen/executer.py'
        self.remove_remote_file(remote_path)
        self.upload_file(executer_path, remote_path)
        
        # Upload protocol
        remote_path = '/data/user_storage/gabeen/experiment.json'
        self.remove_remote_file(remote_path)
        self.upload_file(self.protocol_path, remote_path)
        
        # Upload config
        remote_path = '/data/user_storage/gabeen/ot2_config.json'
        self.remove_remote_file(remote_path)
        self.upload_file(self.ot2_config_path, remote_path)
    
    def init_ssh(self):
        system32 = os.path.join(os.environ['SystemRoot'], 'SysNative' if platform.architecture()[0] == '32bit' else 'System32')
        self.ssh_path = os.path.join(system32, 'OpenSSH/ssh.exe')
        
    def init_scp(self):
        system32 = os.path.join(os.environ['SystemRoot'], 'SysNative' if platform.architecture()[0] == '32bit' else 'System32')
        self.scp_path = os.path.join(system32, 'OpenSSH/scp.exe')
    
    def ssh_command(self,command):
        #print(command)
        ssh = subprocess.Popen([self.ssh_path, '-i', self.ROBOT_KEY, "{}@{}".format(self.ROBOT_USERNAME, self.ROBOT_IP)],
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        res = ssh.communicate(command.encode())
        decoded = [x.decode() for x in res]
        ssh.terminate()
        return decoded
    
    def upload_file(self,local_path,remote_path):
        #print(f'uploading {local_path} to {remote_path}')
        scp = subprocess.Popen([self.scp_path, '-i', self.ROBOT_KEY, local_path, f'{self.ROBOT_USERNAME}@{self.ROBOT_IP}:{remote_path}'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        scp.wait()
    
    def remove_remote_file(self,remote_path):
        command = "rm {}".format(remote_path)
        self.ssh_command(command)
        
    def upload_custom_labware(self):
        local_dir = os.path.abspath('../drivers/liquid_handlers/ot2_templates/custom_labware')
        files = os.listdir(local_dir)
        for f in files:
            #remote_path = '/usr/lib/python3.7/site-packages/opentrons_shared_data/data/labware/definitions/2/'
            remote_path = '/data/user_storage/gabeen/custom_labware/'
            #file_name = f.split('.')[0]
            #self.ssh_command(f'mkdir {remote_path}{file_name}')
            remote_path = os.path.join(remote_path,f)
            self.remove_remote_file(remote_path)
            self.upload_file(os.path.join(local_dir,f), remote_path)
            #self.ssh_command(f'mv {remote_path2} {remote_path}{file_name}/1.json')
        
    def run_protocol_step(self,step_num,tip_num=0):
        command = "python3 /data/user_storage/gabeen/executer.py --step_num {} --start_tip {}".format(step_num,tip_num)
        res = self.ssh_command(command)
        return res