# Ryu-Firewall
OpenFlow Ryu controller with firewall rules. \
Requires Mininet, Ryu, and NetworkX.

## Usage
Two terminals:
	1> ryu-manager --observe-links ryu_controller.py
	2> sudo python3 my_topo.py

 Try to ping between hosts and see the firewall block hosts based on their ID parity.
