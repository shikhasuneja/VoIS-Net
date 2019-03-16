import re
import subprocess

sport = '41570'
src = '192.168.56.3'
disp_filter = 'ip.src==' + src + '&& tcp.srcport==' + sport

def detect_attack():
    pkt_count = 0
    cmd = ['sudo', 'tshark', '-i', 'enp0s8', '-f', 'tcp', '-Y', disp_filter, '-a', 'duration:120']
    while True:
        output = (subprocess.check_output(cmd)).decode('utf-8')
        pkt_count += len(output.splitlines())
        if pkt_count > 10:
            print("Atack detected on the controller!")
            return True

def stop_attack():
    print("Adding iptables rule to block traffic from port {} to the controller 192.168.56.5 and port 6653".format(sport))
    cmd1 = ['sudo', 'iptables', '-A', 'INPUT', '-p', 'tcp', '-d', '192.168.56.5', '--dport', '6653', '--sport', sport, '-j', 'DROP']
    cmd2 = ['sudo', 'iptables', '-L', '-n', '-v']
    out1 = (subprocess.check_output(cmd1)).decode('utf-8')
    #verify iptables drop rule
    capture_cmd = ['sudo', 'tshark', '-i', 'enp0s8', '-f', 'tcp', '-Y', disp_filter, '-a', 'duration:60']
    subprocess.check_output(capture_cmd)
    out2 = (subprocess.check_output(cmd2)).decode('utf-8')
    print("The following iptables rule has been added:\n")
    print(out2)
    rule = re.search('.*192.168.56.5.*tcp\\sspt:' + sport + '\\sdpt:6653.*', out2)
    if hasattr(rule, 'group'):
        dropped_pkts = rule.group().split()[0]
        print(dropped_pkts)
    if int(dropped_pkts) > 0:
        print("The attack is stopped. As a result, {} packets have been dropped by the controller till now to prevent the attack".format(dropped_pkts))

if __name__ == "__main__":
    if detect_attack():
        stop_attack()

