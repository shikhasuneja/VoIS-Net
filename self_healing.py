import _csv, os, threading, re, time
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


class Resolve_Ver_Mismatch(threading.Thread):
    def __init__(self, net_device, true_of_version):
        threading.Thread.__init__(self)
        self.net_device= net_device
        self.true_of_version= true_of_version
    
    def run(self):
        self.net_connect= ConnectHandler(**self.net_device)
        self.net_connect.find_prompt()
        
        #Add true_of_version
        command="sudo -S <<< 7654321 ovs-vsctl set bridge {} protocols={}".format(BRIDGE, 
                                                                                  self.true_of_version) 
        
        output= self.net_connect.send_command_timing(command, 
                                                     strip_command= False, strip_prompt= False)

        
        print("Added Version: {}, Switch: {}".format(self.true_of_version, self.net_device['ip']))


class Resolve_Ctl_Misconfig(threading.Thread):
    def __init__(self, net_device, true_ctl_config):
        threading.Thread.__init__(self)
        self.net_device= net_device
        self.true_ctl_config= true_ctl_config
    
    def run(self):
        self.net_connect= ConnectHandler(**self.net_device)
        self.net_connect.find_prompt()
    
        #Remove false ctl config
        command="sudo -S <<< 7654321 ovs-vsctl del-controller {}".format(BRIDGE) 
        output= self.net_connect.send_command_timing(command, 
                                                     strip_command= False, strip_prompt= False)
        
        #Add true ctl config
        command="sudo -S <<< 7654321 ovs-vsctl set-controller {} {}".format(BRIDGE, 
                                                                        self.true_ctl_config)
        output= self.net_connect.send_command_timing(command, 
                                                     strip_command= False, strip_prompt= False)


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
        


class Resolve_Issues():
    def __init__(self):
        pass
    
    #Takes version_mismatch_ovses as argument and resolves version mismatch on those ovses
    def resolve_ver_mismatch(self, version_mismatch_ovses):
        self.version_mismatch_ovses= version_mismatch_ovses
        threads= []
        
        for ip in self.version_mismatch_ovses:
            #Device to log in to
            self.net_device={
                'device_type':'linux',
                'ip': ip,
                'username': USERNAME,
                'use_keys': 'True',
                }
            
            #New version to add is the actual of_version from csv
            switch_dpid, true_controller_config, true_of_version= parse_this_switch(ip)  
            
            thr_resolve_ver_mismatch= Resolve_Ver_Mismatch(self.net_device, true_of_version)
            thr_resolve_ver_mismatch.daemon= True
            thr_resolve_ver_mismatch.start()
            threads.append(thr_resolve_ver_mismatch)
        
        for element in threads:
            element.join() 


    #Takes version_misconfig_ctl as argument and resolves ctl misconfig on those ovses
    def resolve_ctl_misconfig(self, version_misconfig_ctl):    
        self.version_misconfig_ctl= version_misconfig_ctl
        
        threads= []
        for ip in version_misconfig_ctl:
            #Device to log in to
            self.net_device={
                'device_type':'linux',
                'ip': ip,
                'username': USERNAME,
                'use_keys': 'True',
                }
            
            #New version to add is the actual of_version from csv
            switch_dpid, true_controller_config, true_of_version= parse_this_switch(ip)              
            
            thr_resolve_ctl_misconfig= Resolve_Ctl_Misconfig(self.net_device, true_controller_config)
            thr_resolve_ctl_misconfig.daemon= True
            thr_resolve_ctl_misconfig.start()
            threads.append(thr_resolve_ctl_misconfig)
        
        for element in threads:
            element.join()




#UNIT TESTS
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
        if len(version_match_ovses)!= 0:
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
        
            else:
                print("No ctl misconfig detected. Moving on to next step")
                break
            
        else:
            print("All OVSes are connected to controller")
            break
            
    else:
        print("All OVSes are connected to controller")
        break
