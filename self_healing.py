import _csv, os, threading, re, time
from netmiko.ssh_dispatcher import ConnectHandler

CONTROLLER_IP= "172.16.3.15"
USERNAME= 'batman'
PASSWORD= '7654321'
SDN_NETWORK_TRUTH= 'network_truth.csv'
TRADITIONAL_NETWORK_TRUTH= 'traditional_network_truth.csv'
BRIDGE= 'br0'
connected_ovses= []
disconnected_ovses= []
version_match_ovses= []
version_mismatch_ovses= []
version_config_ctl= []
version_misconfig_ctl= []
misconfigured_routers_info= []


'''
Returns dpid, controller ip and of_version configured on a switch 
given the mgmt IP of a switch
'''
def parse_this_switch(switch_mgmt_ip):
    if os.path.isfile(SDN_NETWORK_TRUTH):
        with open(SDN_NETWORK_TRUTH) as csvfile:
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
Get BGP configuration info from the router whose IP is input. Remote AS and Remote IP
'''
def get_bgp_config(router_ip):

    if os.path.isfile(TRADITIONAL_NETWORK_TRUTH):
        with open(TRADITIONAL_NETWORK_TRUTH) as csvfile:
            reader=_csv.reader(csvfile)
            
            for row in reader:    
                    if row[0]==router_ip:
                        '''This function call
                        shall have remote_as,remote_bgp_ip to catch returned
                        values
                        '''
                        return(row[2], row[3])
                                 
    else:
        ######Replace print with log later
        print("Please add traditional network truth csv file immediately")
        return(None, None)
 
 
'''
Returns list of mgmt IPs of all switches
as reflected in csv file
'''
def get_my_switches():
    my_switch_mgmt_ips= []

    if os.path.isfile(SDN_NETWORK_TRUTH):
        with open(SDN_NETWORK_TRUTH) as csvfile:
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
    
'''
Returns list of mgmt IPs of all routers
as reflected in traditional network truth
'''
def get_my_routers():
    my_router_ips= []
    if os.path.isfile(TRADITIONAL_NETWORK_TRUTH):
        with open(TRADITIONAL_NETWORK_TRUTH) as csvfile:
            reader=_csv.reader(csvfile)
            
            for row in reader:    
                if row[0]!= "Device":
                    my_router_ips.append(row[0])
                
            return(my_router_ips)
            csvfile.close()    
                                                
    else:
        ######Replace print with log later
        print("Please add traditional network truth csv file immediately")
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


class Check_BGP_Misconfig(threading.Thread):
    def __init__(self, net_device):
        threading.Thread.__init__(self)
        self.net_device= net_device
        
        
    def run(self):
        global misconfigured_routers_info
        #true remote ip is controller
        self.true_remote_as, self.true_remote_ip= get_bgp_config(self.net_device['ip'])
        
        
        self.net_connect= ConnectHandler(**self.net_device)
        #Assuming one neighbor
        self.neighbor_line= self.net_connect.send_command_timing("sh run | include neighbor | exclude bgp",
                                                                 strip_command= False, strip_prompt= False)
        self.neighbor_line_list= self.neighbor_line.split()
        
        self.bgp_line= self.net_connect.send_command_timing("sh run | include router bgp",
                                                                 strip_command= False, strip_prompt= False)
        
        self.bgp_line_list= self.bgp_line.split()
        
        self.local_as= self.bgp_line_list[8]
        self.neighbor_line= self.neighbor_line.split('bgp\n ')[-1]
        self.neighbor_line= self.neighbor_line.split('\n')[0]
        
        if len(self.neighbor_line_list)!= 0:
            #Check for misconfiguration
            configured_remote_as= self.neighbor_line_list[3]
            configured_remote_ip= self.neighbor_line_list[1]
            
            if self.true_remote_as== configured_remote_as and configured_remote_ip== self.true_remote_ip:
                pass
            
            else:
                misconfigured_routers_info.append({
                    'router_ip': self.net_device['ip'],
                    'local_as': self.local_as,
                    'misconfigured_line': self.neighbor_line,
                    'true_remote_as': self.true_remote_as,
                    'true_remote_ip': self.true_remote_ip})
            
            
        #Neighbor not configured at all. Configure now    
        else:
            misconfigured_routers_info.append({
                'router_ip': self.net_device,
                'local_as': self.local_as,
                'misconfigured_line': None,
                'true_remote_as': self.true_remote_as,
                'true_remote_ip': self.true_remote_ip})        
        
        
        
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




class Resolve_BGP_Misconfig(threading.Thread):
    def __init__(self, net_device, misconfigured_routers_info):
        threading.Thread.__init__(self)
        self.net_device= net_device
        self.misconfigured_routers_info= misconfigured_routers_info

    def run(self):
        self.config_set= []
        self.net_connect= ConnectHandler(**self.net_device)
        
        self.local_as= misconfigured_routers_info[0]['local_as']
        self.misconfigured_line= self.misconfigured_routers_info[0]['misconfigured_line']
        self.true_remote_as= self.misconfigured_routers_info[0]['true_remote_as']
        self.true_remote_ip= self.misconfigured_routers_info[0]['true_remote_ip']
        
        self.config_set.append('router bgp {}'.format(self.local_as))
        if self.misconfigured_line:
            self.config_set.append('no {}'.format(self.misconfigured_line))
            
        self.config_set.append('neighbor {} remote-as {}'.format(self.true_remote_ip, self.true_remote_as))
        self.net_connect.send_config_set(self.config_set)
        #print(self.config_set)
        
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
        
    
    #Calls threads to check misconfiguration on CISCO router    
    def detect_bgp_misconfig(self, my_routers):
        global misconfigured_routers_info
        
        #misconfigured_routers= [], correct_remote_ases= [], correct_remote_ips= []
        self.my_routers= my_routers
      
        threads= []
        
        for router_ip in self.my_routers:
            net_device={
                'device_type':'cisco_ios',
                'ip': router_ip,
                'username': USERNAME,
                'password': '7654321',
                }  

            thr_check_bgp_misconfig= Check_BGP_Misconfig(net_device)
            thr_check_bgp_misconfig.daemon= True
            thr_check_bgp_misconfig.start()
            threads.append(thr_check_bgp_misconfig)
            
        for element in threads:
            element.join()
             
        return(misconfigured_routers_info)


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


    #Takes misconfigured_routers_info as argument and resolves BGP misconfiguration
    def resolve_bgp_misconfig(self, misconfigured_routers_info): 
        self.misconfigured_routers_info= misconfigured_routers_info
        
        threads= []
        
        for router in misconfigured_routers_info:
            #Device to login to
            self.net_device={
                'device_type':'cisco_ios',
                'ip': router['router_ip'],
                'username': USERNAME,
                'password': '7654321',
                } 
            
            thr_resolve_bgp_misconfig= Resolve_BGP_Misconfig(self.net_device, misconfigured_routers_info)
            thr_resolve_bgp_misconfig.daemon= True
            thr_resolve_bgp_misconfig.start()
            threads.append(thr_resolve_bgp_misconfig)
        
        for element in threads:
            element.join()
        
    
#UNIT TESTS
while True:
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
                            


            print("\n\n")
            print("*"*50)
            print("STEP 4")
            print("Checking BGP misconfiguration")
            
            
            my_routers= get_my_routers()    
            #Detect misconfigured routers
            obj3= Detect_Issues()
            misconfigured_routers_info= obj3.detect_bgp_misconfig(my_routers)
            print("Misconfigured BGP routers:")
            for i in range(0,len(misconfigured_routers_info)):
                print(misconfigured_routers_info[i]['router_ip'])
            
            if len(misconfigured_routers_info)!= 0:
                #Resolve misconfigured routers
                print("BGP misconfiguration detected. Attempting to resolve... Waiting for 5s")
                obj4= Resolve_Issues()
                obj4.resolve_bgp_misconfig(misconfigured_routers_info) 
                misconfigured_routers_info= []
                time.sleep(5)
                print("Resolved BGP misconfiguration.")
                print("\n\n")
                print("*"*50)
                print("END OF SELF_HEALING. If not resolved after 30s, check bgp_self_healing.log")
                print("*"*50)
                break
            
        else:
            print("All OVSes are connected to controller. Checking BGP misconfiguration")
            print("*"*50)
            print("STEP 3")
            my_routers= get_my_routers()
            #Detect misconfigured routers
            obj3= Detect_Issues()
            misconfigured_routers_info= obj3.detect_bgp_misconfig(my_routers)
            print("Misconfigured BGP routers:")
            for i in range(0,len(misconfigured_routers_info)):
                print(misconfigured_routers_info[i]['router_ip'])    
    
            
            if len(misconfigured_routers_info)!= 0:
                #Resolve misconfigured routers
                print("BGP misconfiguration detected. Attempting to resolve... Waiting for 5s")
                obj4= Resolve_Issues()
                obj4.resolve_bgp_misconfig(misconfigured_routers_info) 
                misconfigured_routers_info= []
                time.sleep(5)
                print("Resolved BGP misconfiguration.")
                print("\n\n")
                print("*"*50)
                print("END OF SELF_HEALING. If not resolved after 30s, check bgp_self_healing.log")
                print("*"*50)
                break

            
    else:
        print("All OVSes are connected to controller. Checking BGP misconfiguration")
        print("\n\n")
        print("*"*50)
        print("STEP 2")        
        my_routers= get_my_routers()
        #Detect misconfigured routers
        obj3= Detect_Issues()
        misconfigured_routers_info= obj3.detect_bgp_misconfig(my_routers)
        print("Misconfigured BGP routers:")
        for i in range(0,len(misconfigured_routers_info)):
            print(misconfigured_routers_info[i]['router_ip'])

        if len(misconfigured_routers_info)!= 0:
            #Resolve misconfigured routers
            print("BGP misconfiguration detected. Attempting to resolve... Waiting for 5s")
            obj4= Resolve_Issues()
            obj4.resolve_bgp_misconfig(misconfigured_routers_info) 
            misconfigured_routers_info= []
            time.sleep(5)
            print("Resolved BGP misconfiguration.")
            print("\n\n")
            print("*"*50)
            print("END OF SELF_HEALING. If not resolved after 30s, check bgp_self_healing.log")
            print("*"*50)
        
            break
