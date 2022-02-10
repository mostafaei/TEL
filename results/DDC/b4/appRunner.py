import os
from time import sleep
size=[600]
#size=[200,400,600,800,1000,1200, 1400]
for i in range(len(size)):
    os.system("sudo python topo.py --behavioral-exe simple_switch --json te.json --cli simple_switch_CLI --size %d"%(size[i]))
    sleep(15)
