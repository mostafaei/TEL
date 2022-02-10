#!/usr/bin/python

# Copyright 2013-present Barefoot Networks, Inc. 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink

from p4_mininet import P4Switch, P4Host

import argparse
from time import sleep
import os, time
import subprocess

_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_THRIFT_BASE_PORT = 9090

parser = argparse.ArgumentParser(description='Mininet demo')
parser.add_argument('--behavioral-exe', help='Path to behavioral executable',
                    type=str, action="store", required=True)
#parser.add_argument('--log-file', help='Path to log file',
#                    type=str, action="store", required=True)
parser.add_argument('--json', help='Path to JSON config file',
                    type=str, action="store", required=True)
parser.add_argument('--cli', help='Path to BM CLI',
                    type=str, action="store", required=True)
parser.add_argument('--size', help='UDP packet size',
                    type=str, action="store", required=True)

args = parser.parse_args()

class MyTopo(Topo):
    def __init__(self, sw_path, json_path, nb_hosts, nb_switches, links, **opts):
        # Initialize topology and default options
        print('opts',opts)
        Topo.__init__(self, **opts)

        for i in xrange(nb_switches):
            switch = self.addSwitch('s%d' % (i + 1),
                                    sw_path = sw_path,
                                    json_path = json_path,
                                    thrift_port = _THRIFT_BASE_PORT + i,
                                    log_console = True,
                                    pcap_dump = False,
                                    device_id = i)
        
        for h in xrange(nb_hosts):
            #host_ip = "10.0.%d.%d" % (nb_switches, h+1)
            host_ip = "10.0.%d.%d/24" % (h+1, h+1)
            print('host_ip',host_ip)
            #host_mac = '00:00:00:00:%02x:%02x' % (nb_switches, h+1)
            host_mac = '00:00:00:00:%02x:%02x' % (h+1, h+1)
            print('host_mac',host_mac)
            host = self.addHost('h%d' % (h + 1),ip=host_ip,mac=host_mac,cpu=.5 / (nb_hosts+nb_switches))

        for a, b in links:
            #delay_key = ''.join([host_name, sw])
            #delay = latencies[delay_key] if delay_key in latencies else '0ms'
            #bw = bws[delay_key] if delay_key in bws else None
            self.addLink(a, b, bw=10)
            

def read_topo():
    nb_hosts = 0
    nb_switches = 0
    links = []
    with open("topo.txt", "r") as f:
        line = f.readline()[:-1]
        w, nb_switches = line.split()
        assert(w == "switches")
        line = f.readline()[:-1]
        w, nb_hosts = line.split()
        assert(w == "hosts")
        for line in f:
            if not f: break
            a, b = line.split()
            links.append( (a, b) )
    return int(nb_hosts), int(nb_switches), links
            
def program_hosts(self):
        """ Adds static ARP entries and default routes to each mininet host.

            Assumes:
                - A mininet instance is stored as self.net and self.net.start() has
                  been called.
        """
        for host_name in self.topo.hosts():
            h = self.net.get(host_name)
            h_iface = h.intfs.values()[0]
            link = h_iface.link

            sw_iface = link.intf1 if link.intf1 != h_iface else link.intf2
            # phony IP to lie to the host about
            host_id = int(host_name[1:])
            sw_ip = '10.0.%d.254' % host_id

            # Ensure each host's interface name is unique, or else
            # mininet cannot shutdown gracefully
            h.defaultIntf().rename('%s-eth0' % host_name)
            # static arp entries and default routes
            h.cmd('arp -i %s -s %s %s' % (h_iface.name, sw_ip, sw_iface.mac))
            h.cmd('ethtool --offload %s rx off tx off' % h_iface.name)
            h.cmd('ip route add %s dev %s' % (sw_ip, h_iface.name))
            h.setDefaultRoute("via %s" % sw_ip)
def main():
    nb_hosts, nb_switches, links = read_topo()

    topo = MyTopo(args.behavioral_exe,
                  args.json,
                  nb_hosts, nb_switches, links)

    net = Mininet(topo = topo,
                  host = P4Host,
                  switch = P4Switch,
                  link = TCLink,
                  controller = None )
    net.start()

    for host_name in topo.hosts():
            h = net.get(host_name)
            h_iface = h.intfs.values()[0]
            link = h_iface.link

            sw_iface = link.intf1 if link.intf1 != h_iface else link.intf2
            # phony IP to lie to the host about
            host_id = int(host_name[1:])
            sw_ip = '10.0.%d.254' % host_id

            # Ensure each host's interface name is unique, or else
            # mininet cannot shutdown gracefully
            h.defaultIntf().rename('%s-eth0' % host_name)
            # static arp entries and default routes
            h.cmd('arp -i %s -s %s %s' % (h_iface.name, sw_ip, sw_iface.mac))
            h.cmd('ethtool --offload %s rx off tx off' % h_iface.name)
            h.cmd('ip route add %s dev %s' % (sw_ip, h_iface.name))
            h.setDefaultRoute("via %s" % sw_ip)

    sleep(1)

    for i in xrange(nb_switches):
        s = net.get('s%d' % (i + 1))
        print "##################################\n"
        print "Switch (s%d)" % (i + 1)
        result = s.cmd('ifconfig')
        print	result
        print "MAC Address: \t%s" 	% s.MAC()
        print "IP Address: \t%s\n" 	% s.IP()
        print "##################################"
        cmd = [args.cli, "--json", args.json,
               "--thrift-port", str(_THRIFT_BASE_PORT + i)]
        with open("s%d-commands.txt"%(i + 1), "r") as f:
            print " ".join(cmd)
            try:
                output = subprocess.check_output(cmd, stdin = f)
                print output
            except subprocess.CalledProcessError as e:
                print e
                print e.output

    sleep(1)

    print "Ready !"
    
    ## do test for link failure
    print("********************** Link faliure test *********************")
    print( "Testing bandwidth between clients and server\n" )
    h1, h2 = net.getNodeByName('h1', 'h2')
    s1, s2, s5 = net.getNodeByName('s1', 's2', 's5')
    #net.iperf((h1,h2))
    h1.cmd("sudo ifconfig h1-eth0 mtu %s &"%(args.size))
    h2.cmd("iperf -s -i 0.5 >h2-TCP-TEL-%s.txt &"%(args.size))
    h1.cmd("iperf -c 10.0.2.2 -t 10  >h1 &")
    sleep(5)
    '''
    s1.cmd("echo register_write MyIngress.port_status 0 1 | simple_switch_CLI --thrift-port 9090 &")
    s5.cmd("echo register_write MyIngress.port_status 0 1 | simple_switch_CLI --thrift-port 9094")
    s1.cmd("sudo ifconfig s1-eth2 down &")
    s2.cmd("sudo ifconfig s2-eth1 down &")
    s5.cmd("sudo ifconfig s5-eth2 down &")
    print('ifconfig s5-eth2 down')

    #h3.cmd('echo The path is switched >> h3.txt&')
    #we write teh register value using the following command as the API for BMv2 is not ready
    #start=time.clock()
    print(' recirculation')
    #sleep(0.006)
    #sleep(1)
    s1.cmd("echo register_write MyIngress.port_status 0 0 | simple_switch_CLI --thrift-port 9090 &")
    s5.cmd("echo register_write MyIngress.port_status 0 0 | simple_switch_CLI --thrift-port 9094")
    s1.cmd("echo register_write MyIngress.port_reg 0 1 | simple_switch_CLI --thrift-port 9090 &")
    s5.cmd("echo register_write MyIngress.port_reg 0 1 | simple_switch_CLI --thrift-port 9094 &")

    #end=time.clock()
    '''
    print('The register values are written :')

    s1.cmd("echo register_write MyIngress.port_status 0 1 | simple_switch_CLI --thrift-port 9090 &")
    net.configLinkStatus('s1','s2','down')
    #sleep(0.003)
    #net.configLinkStatus('s1','s2','up')
    s1.cmd("echo register_write MyIngress.port_reg 0 1 | simple_switch_CLI --thrift-port 9090 ")
    s5.cmd("echo register_write MyIngress.port_reg 0 1 | simple_switch_CLI --thrift-port 9094 ")
    s1.cmd("echo register_write MyIngress.port_status 0 0 | simple_switch_CLI --thrift-port 9090")
    sleep(5)
    #CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    main()
