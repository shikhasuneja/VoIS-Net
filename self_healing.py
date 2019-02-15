import _csv, os, threading, re
from netmiko.ssh_dispatcher import ConnectHandler

CONTROLLER_IP= "172.16.3.15"
USERNAME= 'batman'
PASSWORD= '7654321'
NETWORK_TRUTH= 'network_truth.csv'
BRIDGE= 'br0'
connected_ovses= []
disconnected_ovses= []
version_match_ovses= []
version_mismatch_ovses= []
version_config_ctl= []
version_misconfig_ctl= []


'''
Returns dpid, controller ip and of_version configured on a switch 
given the mgmt IP of a switch
'''
def parse_this_switch(switch_mgmt_ip):
    if os.path.isfile(NETWORK_TRUTH):
        with open(NETWORK_TRUTH) as csvfile:
            reader=_csv.reader(csvfile)
            
            for row in reader:
                if row[1]== switch_mgmt_ip:
                    '''
                    The function call should have: switch_dpid, controller_ip, of_versions 
                    to catch rows 0,1,2 respectively
                    '''
                    return(row[0], row[2], row[3])
            
            csvfile.close()

    else:
        ######Replace print with log later
        print("Please add network truth csv file immediately")
        return(None, None, None)


'''
Returns list of mgmt IPs of all switches
as reflected in csv file
'''
def get_my_switches():
    my_switch_mgmt_ips= []

    if os.path.isfile(NETWORK_TRUTH):
        with open(NETWORK_TRUTH) as csvfile:
            reader=_csv.reader(csvfile)

            for row in reader:
                if row[0]!= "Switch DPID":
                    my_switch_mgmt_ips.append(row[1])
            
            return(my_switch_mgmt_ips)
            csvfile.close()

    else:
        ######Replace print with log later
        print("Please add network truth csv file immediately")
        return(None)



class Check_Ctl_Connectivity(threading.Thread):
    def __init__(self, net_device):
        threading.Thread.__init__(self)
        self.net_device= net_device
    
    def run(self):
        self.net_connect= ConnectHandler(**self.net_device)
        self.net_connect.find_prompt()
        output= self.net_connect.send_command_timing("sudo -S <<< 7654321 ovs-vsctl show | grep is_connected", 
                                                     strip_command= False, strip_prompt= False)
        output= output.split('\n')[1]
        
        if 'true' in output:
            connected_ovses.append(self.net_device['ip'])
        
        else:
            #disconnected_ovses.append(self.net_device['ip'])
            command= "sudo -S <<< 7654321 ovs-vsctl get-controller {}".format(BRIDGE)
            controller_config= self.net_connect.send_command_timing(command, 
                                                                    strip_command= False, strip_prompt= False)
            controller_config= controller_config.split('\n')[1]

            
            of_ver= self.net_connect.send_command_timing("sudo -S <<< 7654321 ovs-vsctl get bridge br0 protocols", 
                                                               strip_command= False, strip_prompt= False)
            of_ver= of_ver.split('\n')[1]
            of_versions= re.findall(r'OpenFlow\d+', of_ver)
            
            disconnected_ovses.append({'switch_mgmt_ip': self.net_device['ip'],
                                       'controller_config': controller_config,
                                       'of_versions': of_versions, 
                                        })
        

class Check_Ver_Mismatch(threading.Thread):
    def __init__(self, ip, of_versions):
        threading.Thread.__init__(self)
        self.ip= ip
        self.of_versions= of_versions
    
    def run(self):
        global version_match_ovses, version_mismatch_ovses
        #self.net_connect= ConnectHandler(**self.net_device)
        #self.net_connect.find_prompt()
        switch_dpid, true_controller_config, true_of_version= parse_this_switch(self.ip)
        #print("Here")
        #print(true_of_version)
        #print(self.of_versions)
        if true_of_version in self.of_versions:
            version_match_ovses.append(self.ip)
        
        else:
            version_mismatch_ovses.append(self.ip)


class Check_Ctl_Misconfig(threading.Thread):
    def __init__(self, ip, controller_config):
        threading.Thread.__init__(self)
        self.ip= ip
        self.controller_config= controller_config
    
    def run(self):
        global version_config_ctl, version_misconfig_ctl
        switch_dpid, true_controller_config, true_of_version= parse_this_switch(self.ip)

        if self.controller_config== true_controller_config:
            version_config_ctl.append(self.ip)
        
        else:
            version_misconfig_ctl.append(self.ip)


class Detect_Issues():
    def __init__(self):
        pass
    
    #Calls threads to check ctl connectivity for all switches
    def check_controller_conn(self):
        global connected_ovses, disconnected_ovses
        #my_switches_mgmt_ips= ['172.16.3.10', '172.16.3.11', '172.16.3.13', '172.16.3.14'] #get_my_switches()
        my_switches_mgmt_ips= get_my_switches()
        #Check Connectivity to controller
        threads= []
        for ip in my_switches_mgmt_ips:
            self.net_device={
                'device_type':'linux',
                'ip': ip,
                'username': USERNAME,
                'use_keys': 'True',
                }
            
            thr_check_ctl_conn= Check_Ctl_Connectivity(self.net_device)
            thr_check_ctl_conn.daemon= True
            thr_check_ctl_conn.start()
            threads.append(thr_check_ctl_conn)
        
        for element in threads:
            element.join()
        
        #print("Connected OVSes")
        #print(connected_ovses)
        #print("Disconnected OVSes")
        #print(disconnected_ovses)
        connected_ovses1= connected_ovses
        disconnected_ovses1= disconnected_ovses
        connected_ovses= []
        disconnected_ovses= []
        return(connected_ovses1, disconnected_ovses1)


    #Calls threads to check version mismatch of disconnected switches provided as argument
    def check_ver_mismatch(self, disconnected_ovses):
        global version_match_ovses, version_mismatch_ovses
        self.disconnected_ovses= disconnected_ovses
        
        threads= []
        for ovs in self.disconnected_ovses: 
            thr_check_ver_mismatch= Check_Ver_Mismatch(ovs['switch_mgmt_ip'], ovs['of_versions'])
            thr_check_ver_mismatch.daemon= True
            thr_check_ver_mismatch.start()
            threads.append(thr_check_ver_mismatch)
        
        for element in threads:
            element.join()
        
        #print("Matched versions")
        #print(version_match_ovses)
        #print("Mismatched versions")
        #print(version_mismatch_ovses)
        version_match_ovses1= version_match_ovses
        version_mismatch_ovses1= version_mismatch_ovses
        version_match_ovses= []
        version_mismatch_ovses= []
        return(version_match_ovses1, version_mismatch_ovses1)


    #Calls threads to check ctl misconfig of disconnected switches provided as argument
    def check_ctl_misconfig(self, disconnected_ovses):
        global version_config_ctl, version_misconfig_ctl
        self.disconnected_ovses= disconnected_ovses
        
        threads= []
        for ovs in self.disconnected_ovses: 
            thr_check_ctl_misconfig= Check_Ctl_Misconfig(ovs['switch_mgmt_ip'], ovs['controller_config'])
            thr_check_ctl_misconfig.daemon= True
            thr_check_ctl_misconfig.start()
            threads.append(thr_check_ctl_misconfig)
        
        for element in threads:
            element.join()
        
        #print("Properly configured controllers:")
        #print(version_config_ctl)
        #print("Misconfigured controllers:")
        #print(version_misconfig_ctl)
        version_config_ctl1= version_config_ctl
        version_misconfig_ctl1= version_misconfig_ctl
        version_config_ctl= []
        version_misconfig_ctl= []
        return(version_config_ctl1, version_misconfig_ctl1)
        
           
#UNIT TESTS
print("\n\n")
print("*"*50)
print("STEP 1")
#Get Disconnected switches list    
obj= Detect_Issues()
connected_ovses, disconnected_ovses= obj.check_controller_conn()
print("Connected OVSes:")
print(connected_ovses)
print("Disconnected OVSes")
print(disconnected_ovses)

print("\n\n")
print("*"*50)
print("STEP 2")

#Get ver mismatched switches list
version_match_ovses, version_mismatch_ovses= obj.check_ver_mismatch(disconnected_ovses)
print("Ver matched OVSes")
print(version_match_ovses)
print("Ver mismatched OVSes")
print(version_mismatch_ovses)


'''
At this stage if any mismatched ovses, you want to 'ask' to fix 
and fix and check disconnected ovses. The disconnected ovses at
this stage should be fed to check ctl misconfig function
'''
print("\n\n")
print("*"*50)
print("STEP 3")
version_config_ctl, version_misconfig_ctl= obj.check_ctl_misconfig(disconnected_ovses)
print("Properly configured controllers:")
print(version_config_ctl)
print("Misconfigured controllers:")
print(version_misconfig_ctl)

