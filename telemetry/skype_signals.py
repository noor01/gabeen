#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for communicating via skype
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 12/19/2018
# noorsher2@gmail.com
#
# This code is part of the Yeo lab's setup for automated microscopy fluidics.
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------------------
from skpy import Skype
import time
import pickle
import os
from pathlib import Path

class skype_signals:
    def __init__(self,mode="CLI",usr="NONE"):
        self.mode = mode
        tmp_path = Path(os.getcwd())
        if self.mode == "CLI":
            self.path = tmp_path
        else:
            self.path = tmp_path.parent.absolute()
        #self.target_usr = 'noorsher.ahmed'
        self.target_usr = usr
        # load chat_id
        if self.target_usr == "NONE":
            self.connected = False
        else:
            with open(os.path.join(self.path,"Library/skype_contacts.pkl"),'rb') as f:
                contacts_dict = pickle.load(f)
            self.chat_id = contacts_dict[self.target_usr]
            try:
                self.sk = Skype('squidward.yeolab@gmail.com','merfish123')
                print("Connected to skype")
                self.connected = True
            except:
                print("COULD NOT CONNECT")
                self.connected = False
            if self.connected == True:
                self.chat = self.sk.chats[self.chat_id]
                ### IGNORING THIS FOR NOW...NOT NEEDED ANYMORE. Boot up is faster without it ###
                """
                self.read_msgs = []
                # get message id's of all messages currently in conversation to ignore them
                print("Retrieving message history")
                n = False
                while n == False:
                    msgs = self.chat.getMsgs()
                    if len(msgs) > 0:
                        for i in msgs:
                            self.read_msgs.append(i.time)
                    else:
                        print("Finished building history")
                        n = True
                """
            else:
                pass

    def check_msgs(self,ignore_multiple = True):
        if self.connected == False:
            return
        else:
            pass
        try:
            time.sleep(1)
            msgs = self.chat.getMsgs()
            new_msgs = []
            for i in msgs:
                if i.time in self.read_msgs:
                    pass
                else:
                    self.read_msgs.append(i.time)
                    if i.user.id == self.target_usr:
                        new_msgs.append(i.content)
                    else:
                        pass
            if len(new_msgs) == 0:
                return False
            elif len(new_msgs) > 1:
                if ignore_multiple == False:
                    # send back message asking for one message at a time
                    self.chat.sendMsg("Please send one command")
                    #print("Please send one command")
                    return False
                else:
                    # Concat all messages
                    msg = ''
                    for i in new_msgs:
                        msg = msg + ';' + i
                    return msg
            else:
                return new_msgs[0]
        except:
            print("Skype connection failed")

    def msg_event(self):
        if self.connected == False:
            return
        else:
            pass
        try:
            n = False
            while n == False:
                msg = self.check_msgs()
                if msg != False:
                    return msg
                else:
                    pass
        except:
            print("Skype connection failed")

    def send_msg(self,msg):
        if self.connected == False:
            return
        else:
            pass
        try:
            self.chat.sendMsg(msg)
        except:
            print("Skype connection failed. Re-login at your own convenience")

    def send_img (self,img_path):
        if self.connected == False:
            return
        else:
            pass
        try:
            self.chat.sendFile(open(img_path,'rb'),'image',image=True)
        except:
            print("Skype connection failed")

"""
if __name__ == "__main__":
    x = skype_signals()
    n = True
    while n == True:
        z = x.msg_event()
        print(z)
        x.send_msg(z)
"""
