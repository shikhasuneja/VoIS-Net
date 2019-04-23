from netmiko import ConnectHandler
from multiprocessing import Process
#IP of Linux box
SWITCH_IP= '172.16.3.11' 

#IP of CISCO router
ROUTER_IP= '172.16.3.16'


#Misconfigure controller IP on switch

def misconfigure_openflow():    
    net_device= {
                'device_type': "linux",
                'ip': SWITCH_IP,
                'username': "batman",
                'use_keys': "True"
                }
    
    net_connect= ConnectHandler(**net_device)
    net_connect.find_prompt()
    command="sudo -S <<< 7654321 ovs-vsctl del-controller br0"
    net_connect.send_command_timing(command, strip_command= False, strip_prompt= False)
    print("Injected OpenFlow misconfiguration on {}: Misconfigured controller IP".format(SWITCH_IP))

#Misconfigure BGP neighbor on router
def misconfigure_bgp():
    net_device= {
                'device_type': "cisco_ios",
                'ip': ROUTER_IP,
                'username': "batman",
                'password': "7654321"
                }
    
    net_connect= ConnectHandler(**net_device)
    commands= []
    commands.append('router bgp 65002')
    commands.append('no neighbor 172.16.3.15 remote-as 65001')
    net_connect.send_config_set(commands)
    print("Injected BGP misconfiguration on {}: Misconfigured neighbor IP and AS number".format(ROUTER_IP))

    
##MAIN
p1= Process(target= misconfigure_openflow())
p1.start()

p2= Process(target= misconfigure_bgp())
p2.start()

p1.join()
p2.join()


