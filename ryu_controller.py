#!/usr/bin/python

# Based on template by Miguel Neves
# Extended by Ava Powelson

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

import networkx as nx


# For shortest path routing
import ryu.app.ofctl.api as ofctl_api


class Controller1(app_manager.RyuApp):

	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
		super(Controller1, self).__init__(*args, **kwargs)
		self.topology_api_app = self
		self.net = nx.DiGraph()

		
	@set_ev_cls(event.EventSwitchEnter)
	def get_topology_data(self, ev):
		switch_list = get_switch(self.topology_api_app, None)
		switches = [switch.dp.id for switch in switch_list]
		self.net.add_nodes_from(switches)

		link_list = get_link(self.topology_api_app, None)

		for link in link_list:
			self.net.add_edge(link.src.dpid, link.dst.dpid, port=link.src.port_no)
			self.net.add_edge(link.dst.dpid, link.src.dpid, port=link.dst.port_no)


	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
		#Process switch connection 
		datapath = ev.msg.datapath
		ofproto = datapath.ofproto	
		parser = datapath.ofproto_parser

		#Add default rule
		match = parser.OFPMatch()	
		actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
						  ofproto.OFPCML_NO_BUFFER)]
			
		self.add_flow(datapath, 0, match, actions)


	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		msg = ev.msg
		datapath = msg.datapath
		ofproto = datapath.ofproto

		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocol(ethernet.ethernet)

		dpid = datapath.id
		src = eth.src
		dst = eth.dst

		#Add end hosts to discovered topo
		if src not in self.net:
			self.net.add_node(src)
			self.net.add_edge(dpid,src,port=msg.match['in_port'])
			self.net.add_edge(src,dpid)

			print(">>>> Nodes <<<<")
			print(self.net.nodes())
			print(">>>> Edges <<<<")
			print(self.net.edges())
		
		elif src in self.net and dst in self.net:
			print("Packet_In From a Known Source & Dst")

			## Rule for shortest-path routing ##
			parser = datapath.ofproto_parser
			match = parser.OFPMatch(eth_dst=dst)

			# Shortest path from this switch to dst
			path = []
			try:
				path = nx.shortest_path(self.net, dpid, dst)
				print(path)
			except nx.NetworkXNoPath:
				print("No path from", dpid, "to", dst)

			# Add route to all switches in path
			for i in range(len(path)-1):
				current_datapath = ofctl_api.get_datapath(self, dpid=(path[i]))
				next_hop = path[i+1]
				out_port = self.net[path[i]][next_hop]['port']
				actions = [parser.OFPActionOutput(out_port)]
			
				self.add_flow(current_datapath, 1, match, actions)
				print("Added rule on", path[i], ": eth_dst=", dst, " out_port=", out_port)


				## Firewall Rule ##
				src_parity = int(src[-1]) % 2
				dst_parity = int(dst[-1]) % 2
				blocked = (src_parity != dst_parity)

				if(blocked):
					f_match = parser.OFPMatch(eth_src=src, eth_dst=dst)
					f_actions = [] # empty actions = drop packet
					self.add_flow(current_datapath, 2, f_match, f_actions)
					print("Added firewall rule on", path[i], ": eth_src=", src, "eth_dst=", dst, " out_port=", out_port)

			# Forward the packet if path exists & should not be blocked by firewall
			if len(path) > 0 and not blocked:
				next_hop = path[1]
				out_port = self.net[dpid][next_hop]['port']
				actions = [parser.OFPActionOutput(out_port)]
				parser = datapath.ofproto_parser
				
				out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.match['in_port'], actions=actions, data=pkt)
				datapath.send_msg(out)

	def add_flow(self, datapath, priority, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser

		#Construct flow_mod message and send it
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
						     actions)]

		mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
					match=match, instructions=inst)

		datapath.send_msg(mod)
