import http.client
import json
import csv
import requests
import time

class queue_set_config(object):
    def __init__(self):
        self.controller_ip='192.168.199.6'
        self.conn = http.client.HTTPConnection("{}:8080".format(self.controller_ip))
        self.switchdpid_port_ip={}
        self.queue_config={'TCP':{'min':10000000,'max':20000000},'UDP':{'min':10000000,'max':30000000},'normal':{'min':10000000,'max':50000000}}
        self.max_R_common=100000000
        global switchdpid_port_ip


    def convert_dpid(self,n):
        n=hex(n)
        if len(n) < 16 and n[0:2] == '0x':
            return (n[2:].zfill(16))

    def get_response_from_Server(self,r1):
        if int(r1.status) not in [201,200]:
            print ("Rejected request, Status code: {}, Reason: {}".format(r1.status,(r1.read()).decode()))
        else:
            return r1.read()

    def getexample(self,body):
        self.conn.request("GET", body)
        r1 = self.conn.getresponse()
        responseObject = json.loads(self.get_response_from_Server(r1))
        return responseObject

    def csv_switch_ip(self,dpid):
        with open("network_sof.csv") as a:
            _file=csv.reader(a)
            next(_file)
            for i in _file:
                if dpid == int(i[0]):
                    return i[1]

    def topo_info(self):
        body="/stats/switches"
        switches=self.getexample(body)
        for m in switches:
            if m not in self.switchdpid_port_ip:
                self.switchdpid_port_ip[m]={}
                self.switchdpid_port_ip[m]['ports']={}
            body="/stats/portdesc/{}".format(m)
            for j in self.getexample(body).values():
                for i in j:
                    if i['port_no'] != "LOCAL":
                        if i['port_no'] not in self.switchdpid_port_ip[m]['ports']:
                            self.switchdpid_port_ip[m]['ports'][i['port_no']]={}
                            self.switchdpid_port_ip[m]['ports'][i['port_no']]['queue_port_data']={}
                        self.switchdpid_port_ip[m]['ports'][i['port_no']].update({'ports_name': i['name']})
                cdpid=self.convert_dpid(m)
                self.switchdpid_port_ip[m].update({"hx_dpid":cdpid})
            self.switchdpid_port_ip[m].update({"switch_ip":self.csv_switch_ip(m)})


    def put_ovsdb(self):
        for k,v in self.switchdpid_port_ip.items():
            BODY="\"tcp:{}:6632\"".format(v['switch_ip'])
            self.conn.request("PUT", "/v1.0/conf/switches/{}/ovsdb_addr".format(v['hx_dpid']), BODY)
            r1 = self.conn.getresponse()
            (self.get_response_from_Server(r1))

    def queue_format(self):
        a=list()
        for k,v in self.queue_config.items():
            b="{{\"max_rate\":\"{}\"}}".format(self.queue_config[k]['max'])
            a.append(b)
        return(", ".join(a))

    def post_queue(self,p_name,xdpid):
            a=self.queue_format()
            BODY="{{\"port_name\": \"{}\", \"type\": \"linux-htb\", \"max_rate\": \"{}\", \"queues\": [{}]}}".format(p_name,self.max_R_common,a)
            r = requests.post('http://{}:8080/qos/queue/{}'.format(self.controller_ip,xdpid), data=(BODY))
            print(r.status_code)

    def post_config(self):
        for k,v in self.switchdpid_port_ip.items():
            for i in v['ports']:
                self.post_queue(i,v['hx_dpid'])

class migrate_queue(queue_set_config):
    def __init__(self,a):
        super(migrate_queue,self).__init__()
        self.switchdpid_port_dict=a.switchdpid_port_ip
        self.error_dict={}
        #print(self.switchdpid_port_dict,'===')


    def error_find(self,a1):
        for i,j in a1.items():
            for k in j['ports']:
                    for l in j['ports'][k]['queue_port_data']:
                        if j['ports'][k]['queue_port_data'][l]['tx_errors'] != 0:
                            return("chnage queue")

    def update_errors(self):
        for k in self.switchdpid_port_dict:
            body='/stats/queue/{}'.format(k)
            a=queue_set_config.getexample(self,body)
            for v in a.values():
                for i in v:
                    if i['port_no'] in  self.switchdpid_port_dict[k]['ports']:
                        if i['queue_id'] not in self.switchdpid_port_dict[k]['ports'][i['port_no']]['queue_port_data']:
                                self.switchdpid_port_dict[k]['ports'][i['port_no']]['queue_port_data'][i['queue_id']]={}
                        self.switchdpid_port_dict[k]['ports'][i['port_no']]['queue_port_data'][i['queue_id']].update({"tx_errors":i['tx_errors']})
        ac=self.error_find(self.switchdpid_port_dict)

if __name__ == '__main__':
       config1=queue_set_config()
       config1.topo_info()
       a=migrate_queue(config1)
       while True:
           b=a.update_errors()
           if b:
               print('re-configure queues')

              
