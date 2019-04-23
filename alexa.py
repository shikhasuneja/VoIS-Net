rom flask import Flask
from flask_ask import Ask, statement, question, session
from network_visualization import visualize_topology
from self_healing import Detect_Issues, Resolve_Issues
import json, subprocess
import requests
import time

app = Flask(__name__)
ask = Ask(app, "/capstone")


def heal_my_network:
    while True:
        print("\n\n")
        print("*"*50)
        print("STEP 1")
        #Get Disconnected switches list    
        obj1= Detect_Issues()
        connected_ovses, disconnected_ovses= obj1.check_controller_conn()
        print("Connected OVSes:")
        print(connected_ovses)
        print("Disconnected OVSes")
        print(disconnected_ovses)
        
        if len(disconnected_ovses)!= 0:
            print("\n\n")
            print("*"*50)
            print("STEP 2")
            
            #Get ver mismatched switches list
            version_match_ovses, version_mismatch_ovses= obj1.check_ver_mismatch(disconnected_ovses)
            print("Ver matched OVSes")
            print(version_match_ovses)
            print("Ver mismatched OVSes")
            print(version_mismatch_ovses)
            
            
            '''
            At this stage if any mismatched ovses, you want to 'ask' to fix 
            and fix and check disconnected ovses. The disconnected ovses at
            this stage should be fed to check ctl misconfig function
            '''
            
            obj2= Resolve_Issues()
            #Fix version mismatch
            if len(version_mismatch_ovses)!= 0:
                obj2.resolve_ver_mismatch(version_mismatch_ovses)
                print("Attempted fixing version. Waiting for 10s...")
                time.sleep(10)
                #Check connectivity again now
                connected_ovses, disconnected_ovses= obj1.check_controller_conn()
            
            else:
                print("No version mismatch detected. Moving on to next step.")
            
            
            if len(disconnected_ovses)!= 0:
                print("\n\n")
                print("*"*50)
                print("STEP 3")
                version_config_ctl, version_misconfig_ctl= obj1.check_ctl_misconfig(disconnected_ovses)
                print("Properly configured controllers:")
                print(version_config_ctl)
                print("Misconfigured controllers:")
                print(version_misconfig_ctl)
                
                if len(version_misconfig_ctl)!= 0:
                    obj2.resolve_ctl_misconfig(version_misconfig_ctl)
                    print("Attempted fixing controller config. Waiting for 10s...")
                    time.sleep(10)
                    break            
    
                else:
                    print("No ctl misconfig detected. Moving on to next step")
                    break
                
            else:
                print("All OVSes are connected to controller")
                break
                
        else:
            print("All OVSes are connected to controller")
            break
    

@app.route("/")
def homepage():
   return "hi there, how ya doin?"

@ask.launch
def start_skill():
   welcome_message = 'Hello there, what would you like to do?'
   return question(welcome_message)

'''
@ask.intent("YesIntent")
def share_headlines():
   hi_text = 'GREAT! Here it is'   
   visualize_topology()

   return statement(hi_text)
'''

@ask.intent("Topology")
def share_headlines():
   hi_text = 'GREAT! Here is the topology'   
   visualize_topology()
   return statement(hi_text)

@ask.intent("Healing")
def share_headlines():
   hi_text = 'Detected and resolved network issues'   
   heal_my_network()
   return statement(hi_text)



@ask.intent("NoIntent")
def no_intent():
   bye_text = 'I am not sure why you asked me to run then, but okay... bye'
   return statement(bye_text)


if __name__ == '__main__':
   app.run(debug=True)
