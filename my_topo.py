#!/usr/bin/python

# Based on template by Miguel Neves
# Extended by Ava Powelson

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.node import RemoteController

class MyTopo( Topo ):
	def __init__(self):
		Topo.__init__( self )
        
		switches = []
		edges = [(1, 2), (2, 3), (3, 1), (3, 4), (4, 5), (5, 6), (6, 4), (4, 7), (5, 8)]
        
	    # Add all hosts and switches and link them
		for i in range(1, 9):
			h = self.addHost('h%s' % i)
			s = self.addSwitch('s%s' % i)
			switches.append(s)
			self.addLink(h, s)
			
		for edge in edges:
			self.addLink(switches[edge[0]-1], switches[edge[1]-1])


def runner():
	my_topo = MyTopo()
	
	# Essentially: mn --topo=my_topo.py --controller=remote --mac --arp
	net = Mininet(topo=my_topo, controller=RemoteController, autoSetMacs=True, autoStaticArp=True)
	
	net.start()
	CLI(net)
	net.stop()
	
if __name__ == '__main__':
	runner()
