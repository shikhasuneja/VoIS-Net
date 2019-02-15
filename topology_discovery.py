##TEAM VoIS-Network
##Date: 01/22/2019
##Topic: Topology Discovery
##Author: Srinidhi
##Instructions: ryu run --observe-links topology_detection.py

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from ryu.lib.packet import ether_types
import sqlite3, re, calendar, time, copy

TOPOLOGY= 'topology.db'

class Topo_Discovery(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(Topo_Discovery, self).__init__(*args, **kwargs)
        #Used for learning switch functioning
        self.mac_to_port= {}
        self.host_macs= {}
        self.host_connections= []
        self.last_updated= calendar.timegm(time.gmtime())
        """
        Used to store whole topology information (unique and non-duplicate values)
        This will be a list of tuples
        Each tuple conveys info about a link for example
        Each tuple contains src and dst dpid and src and dst port
        """
        self.final_topo_connections= []
        
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg= ev.msg
        datapath= ev.msg.datapath
        ofproto= datapath.ofproto
        parser= datapath.ofproto_parser
        match= parser.OFPMatch()
        actions= [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto= datapath.ofproto
        parser= datapath.ofproto_parser
        inst= [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    """
    Takes data structure with potentially duplicate entries and deletes redudant and duplicate
    entries. For example 2,1,1,1 and 1,2,1,1 or 2,1,1,1 and 2,1,1,1
    """
    def non_duplicate(self):
        for element in self.topo_connections:
            this_tuple= element
            duplicate_tuple= ({'source_dpid': element[1]['dest_dpid']}, 
                              {'dest_dpid': element[0]['source_dpid']}, 
                              {'source_port': element[3]['dest_port']}, 
                              {'dest_port': element[2]['source_port']})
            #First iteration
            if len(self.final_topo_connections)== 0:
                self.final_topo_connections.append(element)
            
            #If exact duplicate
            elif this_tuple in self.final_topo_connections:
                continue
            
            #If interchanged duplicate
            elif duplicate_tuple in self.final_topo_connections:
                continue
            
            #Invalid topo_connection -> when switch not in topo_switches
            elif element[0]['source_dpid'] not in self.topo_switches or element[1]['dest_dpid'] not in self.topo_switches:
                continue

            #Non-duplicate and valid
            else:
                self.final_topo_connections.append(element)

    #Add switches to db - non-unique with one switch dpid per row
    def add_swes_to_db(self):
        conn= sqlite3.connect(TOPOLOGY)
        c= conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS switches 
                (switch_dpid int, UNIQUE(switch_dpid))''')
                
        for i in range(0,len(self.topo_switches)):
            self.switch_dpid=self.topo_switches[i]
            insert_command="INSERT OR REPLACE INTO switches (switch_dpid) values(?)"
            t=(self.switch_dpid, )
            c.execute(insert_command, t)            

        conn.commit()
        conn.close()
           
    """
    Add topo connections to db
    which is all link information (non-duplicate) in the whole topology
    """
    def add_topo_con_to_db(self):
        conn= sqlite3.connect(TOPOLOGY)
        c= conn.cursor()
        """
        If table does not exist, create
        Make source and dest dpid unique column elements. If they repeat, we will then update
        Which means link info between these two switches has changed i.e. topology has changed 
        Note that this won't work for etherchannels i.e. a case where multiple links exist between same
        two switches
        """
        c.execute('''CREATE TABLE IF NOT EXISTS topo_connections 
                (source_dpid int, dest_dpid int, source_port int, dest_port int, status text, UNIQUE(source_dpid, dest_dpid))''')
        
        for i in range(0,len(self.final_topo_connections)):
            self.source_dpid= self.final_topo_connections[i][0]['source_dpid']
            self.dest_dpid= self.final_topo_connections[i][1]['dest_dpid']
            self.source_port= self.final_topo_connections[i][2]['source_port']
            self.dest_port= self.final_topo_connections[i][3]['dest_port']
            
            #Read from existing table
            query='''SELECT * from topo_connections where source_dpid={} and dest_dpid={} 
            or source_dpid={} and dest_dpid={}'''.format(self.source_dpid, self.dest_dpid, self.dest_dpid, self.source_dpid)
            c.execute(query)
            rows=c.fetchall()
          
            if len(rows)== 0:
                #If not duplicate
                #Insert or replace to ensure topology updation takes place and 
                #duplic ate entries are not created
                status="UP"
                insert_command="INSERT OR REPLACE INTO topo_connections (source_dpid, dest_dpid, source_port, dest_port, status) values(?,?,?,?,?)"
                t=(self.source_dpid, self.dest_dpid, self.source_port, self.dest_port, status, )
                c.execute(insert_command, t)
            
            
            else:
                continue
                    
                     
        conn.commit()
        conn.close()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg= ev.msg
        datapath= msg.datapath
        ofproto= datapath.ofproto
        parser= datapath.ofproto_parser
        in_port= msg.match['in_port']
        pkt= packet.Packet(msg.data)
        eth= pkt.get_protocols(ethernet.ethernet)[0]
        dst= eth.dst
        src= eth.src
        dpid= datapath.id
        self.mac_to_port.setdefault(dpid, {})
        #learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src]= in_port
        
        #Ignore LLDP 
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        #Ignore BPDUs
        if eth.ethertype==38:
            return
        
        #Ignore IPv6
        if eth.ethertype==34525:
            return
        
        f=open('log.txt','w')
        f.write("False host packet in\n")
        f.write(eth)
        f.close()
        #Add host mapping if not present
        if src not in self.host_macs.values():
            self.host_macs[dpid]= src
            self.host_connections.append(({'switch_dpid': dpid}, {'switch_port': in_port}, 
                                 {'host_mac': src}))
        
            #Add to database
            conn= sqlite3.connect(TOPOLOGY)
            c= conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS host_connections 
                (switch_dpid int, switch_port int, host_mac text, UNIQUE(switch_dpid, switch_port))''')
    
            insert_command="INSERT OR REPLACE INTO host_connections (switch_dpid, switch_port, host_mac) values(?,?,?)"
            t=(dpid, in_port, src, )
            c.execute(insert_command, t)  
            conn.commit()
            conn.close()
            

        if dst in self.mac_to_port[dpid]:
            out_port= self.mac_to_port[dpid][dst]
        else:
            out_port= ofproto.OFPP_FLOOD

        actions= [parser.OFPActionOutput(out_port)]

        #install a flow to avoid packet_in next time
        if out_port!= ofproto.OFPP_FLOOD:
            match= parser.OFPMatch(in_port=in_port, eth_dst=dst)
            #verify if we have a valid buffer_id, if yes avoid to send both
            #flow_mod & packet_out
            if msg.buffer_id!= ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data= None
        
        if msg.buffer_id== ofproto.OFP_NO_BUFFER:
            data= msg.data

        out= parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        print("Host links:")
        print(self.host_connections)
        
    """
    The event EventSwitchEnter will trigger the activation of get_topology_data()
    i.e. we start getting topology data as soon a switch enters the ropology and connects to controller
    """
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        time.sleep(2)
        #The Function get_switch(self, None) outputs the list of switches.        
        #Raw info
        self.topo_raw_switches= copy.copy(get_switch(self, None))
        self.topo_raw_links= copy.copy(get_link(self, None))
        
        
        #List with switch dpids as list elements
        self.topo_switches= [switch.dp.id for switch in self.topo_raw_switches]
        #for dpid in self.topo_switches:
        #self.hosts= copy.copy(get_all_host(self))
        #print("Hosts:")
        #print(self.hosts)
        
        print("Switches")
        print(self.topo_switches)
        
        #Add switch info to db
        self.add_swes_to_db()        
        #List of tuple of dictionaries
        #Each list element is a tuple element describing each link
        #Each tuple consists of 4 elements describing link characteristics like so and dest id and ports
        self.topo_connections= [({'source_dpid':link.src.dpid}, {'dest_dpid':link.dst.dpid}, 
                                 {'source_port':link.src.port_no},
                                 {'dest_port':link.dst.port_no}) for link in self.topo_raw_links] 
        print("Connections:")
        print(self.topo_connections)
        
        #Remove duplicate and redundant elements
        self.non_duplicate()
        
        #Delete invalid switch-details
        self.final_topo_connections= [i for i in self.final_topo_connections 
                                 if i[0]['source_dpid'] in self.topo_switches 
                                 and i[1]['dest_dpid'] in self.topo_switches]
        print("Non-duplicate connections:")
        print(self.final_topo_connections) 
        #Adding topo_connections to database i.e. the link information
        self.add_topo_con_to_db()
        
    #This event is fired when a switch leaves the topo. i.e. fails.
    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev):
        self.logger.info("Not tracking switch; switch left.")
        dpid= int(re.findall(r'\d+', str(ev))[0])
        print("Switch {} left topology".format(dpid))

        conn= sqlite3.connect(TOPOLOGY)
        c= conn.cursor()
        
        #Delete switch from TABLE switch
        delete_command="DELETE FROM switches WHERE switch_dpid={}".format(dpid)
        c.execute(delete_command)

        #Delete switch-details from TABLE topo_connections
        delete_command="DELETE FROM topo_connections WHERE source_dpid={}".format(dpid)
        c.execute(delete_command)
        
        delete_command="DELETE FROM topo_connections WHERE dest_dpid={}".format(dpid)
        c.execute(delete_command)
        
        del self.host_macs[dpid]
        #self.host_macs.remove(dpid)
        #Remove host links connected to the switch
        try:
            delete_command="DELETE FROM host_connections WHERE switch_dpid={}".format(dpid)
            c.execute(delete_command)
            
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
                
        self.topo_connections= [i for i in self.topo_connections 
                                 if not dpid== i[0]['source_dpid'] or dpid== i[1]['dest_dpid']]
        
        #Delete switch-details from data structure self.final_topo_connections     
        self.final_topo_connections= [i for i in self.final_topo_connections 
                                 if not dpid== i[0]['source_dpid'] or dpid== i[1]['dest_dpid']]
   

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        #self.last_updated= calendar.timegm(time.gmtime())
        time_difference= calendar.timegm(time.gmtime()) -self.last_updated
        self.last_updated= calendar.timegm(time.gmtime())
        #print("Difference is {}".format(time_difference))
        
        msg= ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        ofproto = msg.datapath.ofproto
        
        if reason == ofproto.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        
        elif reason == ofproto.OFPPR_MODIFY:
            
            #Persistence for accuracy to avoid false positives encountered on RYU
            if time_difference<4:
                return
            
            else:
                time.sleep(2)
                self.logger.info("switch {}, port modified {}".format(msg.datapath.id, port_no))
                #print(type(msg.datapath.id))
                #print(type(port_no))
                #Open database
                conn= sqlite3.connect(TOPOLOGY)
                c= conn.cursor()    
                
                #Get switch and port row and check status
                query="SELECT * from topo_connections"
                c.execute(query)
                rows=c.fetchall()
                #print(rows)
                if len(rows)!=0:
                    for row in rows:
                        if msg.datapath.id== row[0] and port_no== row[2] or msg.datapath.id== row[1] and port_no== row[3]: 
                            delete_command='''DELETE FROM topo_connections WHERE source_dpid={} and 
                            dest_dpid={} and source_port={} and dest_port={}'''.format(row[0], row[1],
                                                                                       row[2], row[3])
                            c.execute(delete_command)
                            
                            #Flip port status
                            if row[4]== "UP":
                                status="DOWN"
     
                            else:
                                status="UP"
                            
                            insert_command='''INSERT OR REPLACE INTO topo_connections 
                            (source_dpid, dest_dpid, source_port, dest_port, status) values(?,?,?,?,?)'''
                            t=(row[0], row[1], row[2], row[3], status, )
                            c.execute(insert_command, t)
    
                        
                    conn.commit()
                    conn.close()
            
        else:
            self.logger.info("Illegal port state %s %s", port_no, reason)
