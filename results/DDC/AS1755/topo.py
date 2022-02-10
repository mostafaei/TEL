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
import os, time, re
import subprocess
import networkx as nx

_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_THRIFT_BASE_PORT = 9090

parser = argparse.ArgumentParser(description='Mininet demo')
parser.add_argument('--behavioral-exe', help='Path to behavioral executable',
                    type=str, action="store", required=True)
#parser.add_argument('--log-file', help='Path to log file',
#                    type=str, action="store", required=True)
parser.add_argument('--json', help='Path to JSON config file',
                    type=str, action="store", required=False)
parser.add_argument('--cli', help='Path to BM CLI',
                    type=str, action="store", required=False)
parser.add_argument('--size', help='UDP packet size',
                    type=str, action="store", required=False)

args = parser.parse_args()

G = nx.Graph()
args.json="ddc.json"
args.cli="simple_switch_CLI"

class MyTopo(Topo):
    def __init__(self, sw_path, json_path, nb_hosts, nb_switches, links, **opts):
        # Initialize topology and default options
        print('opts',opts)
        Topo.__init__(self, **opts)

        for i in xrange(nb_switches):
            G.add_node('s%d' % (i + 1))
            switch = self.addSwitch('s%d' % (i + 1),
                                    sw_path = sw_path,
                                    json_path = 'sw%d.json' % (i + 1),
                                    thrift_port = _THRIFT_BASE_PORT + i,
                                    log_console = False,
                                    pcap_dump = False,
                                    device_id = i)
        
        for h in xrange(nb_hosts):
            G.add_node('s%d' % (h + 1))
            #host_ip = "10.0.%d.%d" % (nb_switches, h+1)
            host_ip = "10.0.%d.%d/24" % (h+1, h+1)
            print('host_ip',host_ip)
            #host_mac = '00:00:00:00:%02x:%02x' % (nb_switches, h+1)
            host_mac = '00:00:00:00:%02x:%02x' % (h+1, h+1)
            print('host_mac',host_mac)
            host = self.addHost('h%d' % (h + 1),ip=host_ip,mac=host_mac,cpu=.8 / nb_hosts)

        for a, b in links:
            #delay_key = ''.join([host_name, sw])
            #delay = latencies[delay_key] if delay_key in latencies else '0ms'
            #bw = bws[delay_key] if delay_key in bws else None
            self.addLink(a, b, bw=12)
            G.add_edge(a,b)
            

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
    
Nodes=[]
infile = open('topo.txt', 'r')
firstLine = infile.readline()
count=firstLine.split(' ')[1]
Nodes=[[] for x in xrange(int(count))]
with open('topo.txt') as f:
    for line in f:
        if 'hosts' not in  line and 'switches' not in line:
            a=line.split(' ')[0]
            indexa=re.findall(r'\d+',a)
            b=line.split(' ')[1]
            indexb=re.findall(r'\d+',b)
            #print('index:',indexa[0],indexb[0])
            if 'h' in a:
                Nodes[int(indexb[0])-1].append(a)
            elif 's' in a or 's' in b:
                Nodes[int(indexa[0])-1].append(b)
                Nodes[int(indexb[0])-1].append(a)  

def checkfile(fname,rule):
    flag=False
    with open(fname) as f:
        #line=f.read()
        for line in f:
            if rule in line:
                flag=True
                return flag
    return flag
def egressPort(src,dst):
    egress=5
    src=src.replace("s", "")
    #print('s-----------',src)
    for i in Nodes[int(src)-1]:
        if src in i:
           egress=5
    return egress
def neighborIndex(a,b,dst,src):
    fname="%s-commands.txt"%(a)
    f1 = open(fname, "a")
    eport=egressPort(a,b)
    rule1="table_add MyIngress.table_1 MyIngress.host_set 10.0.%s.%s 10.0.%s.%s => 11  \n"%((src) ,(src),(dst) ,(dst))
    rule2="table_add MyIngress.table_2 MyIngress.ipv4_forward 11 0 => 00:00:00:%02s:%02s:00 %s \n"%(dst ,(dst),(eport))
    if not checkfile(fname,rule1):
        f1.write(rule1)
    if not checkfile(fname,rule2):
        f1.write(rule2)
    f1.close()

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
            h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
            #h.cmd("sysctl -w net.ipv4.tcp_congestion_control=reno")
            h.cmd("iptables -I OUTPUT -p icmp --icmp-type destination-unreachable -j DROP")

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
        #read custom json file
        cmd = [args.cli, "--json", 'sw%d.json' % (i + 1),
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
    print G.nodes()
    print G.edges()
    ## do test for link failure
    print("********************** Link faliure test *********************")
    print( "Testing bandwidth between clients and server\n" )
    #G = nx.read_graphml('AttMpls.graphml')
    #nx.draw(G, with_labels=True)
    #h1, h2 = net.getNodeByName('h1', 'h2')
    #s1, s2, s5 = net.getNodeByName('s1', 's2', 's5')
    #net.iperf((h1,h2)) 
    #h1.cmd("sudo ifconfig h1-eth0 mtu %s &"%(args.size))
    #h2.cmd("iperf -s -i 1  >h2-TCP-naive-%s.txt &"%(int(args.size),args.size))
    #h2.cmd("iperf3 -s -i 1  > h2-UDP-TEL-18Aug.txt  &")
    #h1.cmd("iperf -c 10.0.2.2 -t 10 -p 50%d >h1 &"%(int(args.size)))
    #h1.cmd("for n in {1..500}; do iperf3 -c 10.0.2.2 -n 4500 -J a.json; done > fct.json &")
    #h1.cmd("iperf -c 10.0.2.2 -t 10 -b 12M -u &")
    #h2.cmd("ITGRecv  &>/dev/null &")
    #sleep(1)
    #h1.cmd("ITGSend -a 10.0.2.2 -C 1360 -c 1470 -rp 9500 -T TCP -t 10000 -x recv_log_TCP22_naive &>/dev/null &")
    #--h1.cmd("ITGSend script_file -l sender_log_file &>/dev/null &")
    #h1.cmd("ITGSend script_file1 -l habib1 &>/dev/null &")

    sleep(.10)
    #start=time.clock()
    #net.configLinkStatus('s1','s2','down')
    #s1.cmd("echo register_write MyIngress.port_reg 1 1 | /home/vagrant/behavioral-model/targets/simple_switch/runtime_CLI --thrift-port %s  &>/dev/null &"%(_THRIFT_BASE_PORT + 0))
    #s5.cmd("echo register_write MyIngress.port_reg 1 1 | /home/vagrant/behavioral-model/targets/simple_switch/runtime_CLI --thrift-port %s  &>/dev/null &"%(_THRIFT_BASE_PORT + 4))
    #s1.cmd("echo register_write MyEgress.port_status 0 1 | simple_switch_CLI --thrift-port 9090 &")
    '''
    G.remove_edge('s1','s2')
    new_path=[]
    new_path=nx.shortest_path(G,'s1','s5')
    print('new path:',new_path[0],len(new_path))
    src=new_path[0]
    dst=new_path[-1]
    p=i
    print('src , dst:', src,dst,i)
    for j in range(0,len(new_path),1):
        if j<len(new_path)-1:
           neighborIndex(new_path[j],new_path[j+1],dst,src)
    for j in range(0,len(new_path),1):
        if j<len(new_path)-1:
           neighborIndex(new_path[j],new_path[j+1],dst,src)
    sleep(0.0003)
    '''
    #s1.cmd("echo register_write MyIngress.port_reg 2 1 | simple_switch_CLI --thrift-port 9090")
    #s5.cmd("echo register_write MyIngress.port_reg 2 1 | simple_switch_CLI --thrift-port 9094 ")


    #end=time.clock()
    #print('new path:',new_path,end-start)
    #start=time.clock()
    #s1.cmd("echo register_write MyEgress.port_status 0 1 | simple_switch_CLI --thrift-port 9090 &")
    #start=time.clock()
    #net.configLinkStatus('s1','s2','down')
    #s5.cmd("echo register_write MyEgress.port_status 0 1 | simple_switch_CLI --thrift-port 9094 &")
    #end=time.clock()
    #print('The time to write :', end-start)

    #start=time.clock()
    #sleep(0.005)
    #s1.cmd("echo register_write MyIngress.port_reg 0 1 | /home/vagrant/behavioral-model/targets/simple_switch/runtime_CLI --thrift-port 9090 ")
    #s5.cmd("echo register_write MyIngress.port_reg 0 1 | /home/vagrant/behavioral-model/targets/simple_switch/runtime_CLI --thrift-port 9094 ")
    #end=time.clock()
    #print (nx.shortest_path(G,'0','4'),('{0:.3f}'.format((end-start))))
    #sleep(0.003)
    #net.configLinkStatus('s1','s2','up')


    #sleep(6)
  
    CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    main()
