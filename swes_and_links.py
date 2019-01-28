##TEAM VoIS-Network
##Date: 01/22/2019
##Topic: Topology Discovery
##Author: Srinidhi
##Instructions: ryu run --observe-links swes_and_links.py

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

from ryu.topology import event
from ryu.topology.api import get_switch, get_link
import sqlite3, re


class Topo_Discovery(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Topo_Discovery, self).__init__(*args, **kwargs)
        
        #Used for learning switch functioning
        self.mac_to_port= {}
        
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
        self.logger.info('OFPSwitchFeatures received: '
                         '\n\tdatapath_id=0x%016x n_buffers=%d '
                         '\n\tn_tables=%d auxiliary_id=%d '
                         '\n\tcapabilities=0x%08x',
                         msg.datapath_id, msg.n_buffers, msg.n_tables,
                         msg.auxiliary_id, msg.capabilities)

        datapath= ev.msg.datapath
        ofproto= datapath.ofproto
        parser= datapath.ofproto_parser
        match= parser.OFPMatch()
        actions= [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    
    #We are not using this function
    def delete_flow(self, datapath):
        ofproto= datapath.ofproto
        parser= datapath.ofproto_parser

        for dst in self.mac_to_port[datapath.id].keys():
            match= parser.OFPMatch(eth_dst=dst)
            mod= parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

    
    
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
        if len(self.final_topo_connections)== len(self.topo_connections)/2: 
            if len(self.final_topo_connections)!=0:
                return
        
        #To compare every element with every other element
        for i in range(0,len(self.topo_connections)):
            for j in range(0,len(self.topo_connections)):
                
                #For first iteration when final_topo_connections is empty, insert 
                #first element directly
                if len(self.final_topo_connections)== 0:
                    self.final_topo_connections.append(self.topo_connections[i])
                    continue
                
                #If source dpid of first element is equal to dest dpid of second element
                #or vice versa
                #Do not insert because this is redudant
                elif self.topo_connections[i][0]['source_dpid']== self.topo_connections[j][1]['dest_dpid'] and self.topo_connections[i][1]['dest_dpid']== self.topo_connections[j][0]['source_dpid']:
                    continue
                
                #If element already exists
                #Do not insert because this is duplicate
                elif self.topo_connections[j] in self.final_topo_connections:
                    continue 

                #Else insert second element which was just compared to first element and
                #found to be neither redundant nor duplicate 
                else:
                    self.final_topo_connections.append(self.topo_connections[j])


    #Add switches to db - non-unique with one switch dpid per row
    def add_swes_to_db(self):
        conn= sqlite3.connect('topology.db')
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
        conn= sqlite3.connect('topology.db')
        c= conn.cursor()
        
        """
        If table does not exist, create
        Make source and dest dpid unique column elements. If they repeat, we will then update
        Which means link info between these two switches has changed i.e. topology has changed 
        Note that this won't work for etherchannels i.e. a case where multiple links exist between same
        two switches
        """
        c.execute('''CREATE TABLE IF NOT EXISTS topo_connections 
                (source_dpid int, dest_dpid int, source_port int, dest_port int, UNIQUE(source_dpid, dest_dpid))''')
        
        for i in range(0,len(self.final_topo_connections)):
            self.source_dpid= self.final_topo_connections[i][0]['source_dpid']
            self.dest_dpid= self.final_topo_connections[i][1]['dest_dpid']
            self.source_port= self.final_topo_connections[i][2]['source_port']
            self.dest_port= self.final_topo_connections[i][3]['dest_port']
            
            #Read from existing table
            rows=c.fetchall()
            
            if len(rows)==0:
                #If not duplicate
                #Insert or replace to ensure topology updation takes place and 
                #duplicate entries are not created
                insert_command="INSERT OR REPLACE INTO topo_connections (source_dpid, dest_dpid, source_port, dest_port) values(?,?,?,?)"
                t=(self.source_dpid, self.dest_dpid, self.source_port, self.dest_port, )
                c.execute(insert_command, t)
            
            for row in rows:
                #If duplicate entry with just switches interchanged
                if (self.dest_dpid==row[0] and self.source_dpid==row[1]):
                    if self.dest_port== row[2] and self.source_port== row[3]:
                        #Means unchanged topo, just duplicate with switches interchanged
                        continue
                    #Switches interchanged, sure, but topo has also changed because ports have changed
                    else:
                        insert_command="INSERT OR REPLACE INTO topo_connections (source_dpid, dest_dpid, source_port, dest_port) values(?,?,?,?)"
                        t=(self.source_dpid, self.dest_dpid, self.source_port, self.dest_port, )
                        c.execute(insert_command, t)  
        
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

        #self.logger.info("\tpacket in %s %s %s %s", dpid, src, dst, in_port)

        #learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src]= in_port

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

    
    

    """
    The event EventSwitchEnter will trigger the activation of get_topology_data()
    i.e. we start getting topology data as soon a switch enters the ropology and connects to controller
    """
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        #The Function get_switch(self, None) outputs the list of switches.
        
        #Raw info
        self.topo_raw_switches= get_switch(self, None)
        #List with switch dpids as list elements
        self.topo_switches= [switch.dp.id for switch in self.topo_raw_switches]
        print("Switches")
        print(self.topo_switches)
        
        #Add switch info to db
        self.add_swes_to_db()
        
        
        self.topo_raw_links= get_link(self, None)
        
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
        
        print("Non-duplicate connections:")
        print(self.final_topo_connections) 
        
        #Adding topo_connections to database i.e. the link information
        self.add_topo_con_to_db()
        


    #This event is fired when a switch leaves the topo. i.e. fails.
    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def handler_switch_leave(self, ev):
        
        self.logger.info("Not tracking switch; switch left.")
        dpid= re.findall(r'\d+', str(ev))[0]
        print("Switch {} left topology".format(dpid))

        conn= sqlite3.connect('topology.db')
        c= conn.cursor()
        
        #Delete switch from TABLE switch
        delete_command="DELETE FROM switches WHERE switch_dpid={}".format(dpid)
        c.execute(delete_command)

        #Delete switch from TABLE switch
        delete_command="DELETE FROM topo_connections WHERE source_dpid={}".format(dpid)
        c.execute(delete_command)
        
        delete_command="DELETE FROM topo_connections WHERE dest_dpid={}".format(dpid)
        c.execute(delete_command)
        
        conn.commit()
        conn.close()

            
