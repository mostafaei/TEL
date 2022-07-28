# TEL: Low-Latency Failover Traffic Engineering in Data Plane  (code and replication instructions)

We conducted the experiments on a VM using Mininet network emulator on an `Intel Xeon CPU E5-2667 3.3GH` VM with 190 GB RAM and 32 CPU cores running `Ubuntu server 18.04`. We also use the
recommendation in [official BMv2](https://github.com/p4lang/behavioral-model/blob/main/docs/performance.md) to achieve high bandwidth throughput.
Contact for repeatability questions: [Habib Mostafaei](https://mostafaei.bitbucket.io).
## The idea

TEL has two FRR mechanisms, namely, TEL-C and TEL-D. The first one computes backup forwarding rules in the control plane, satisfying max-min fair allocation. The second mechanism provides FRR in the data plane. Both algorithms require minimal memory on programmable data planes and are well-suited with modern line rate match-action forwarding architectures (e.g., PISA).

## Code organization
We organize the code into three main parts: 
 - the code evaluating the performance of TEL-C with KSP (called `python/KSP`)  
 - the P4 source code of TEL (called `code/P4/TEL`).
 - the code to evaluate for Datacenter and WAN scenarios (called `results`)  


### Installing dependencies

We explain how one can install the missing dependencies on a vanilla Ubuntu 18.04:

```
sudo apt update
sudo apt-get --yes install git python python-pip python-numpy python-networkx
sudo python -m pip install matplotlib==2.0.2
sudo apt-get --yes install texlive-latex-extra dvipng 
```

### Code organization

The repository is organized as follows:

```
code/
  ├── P4/
        ├── DDC/
			    ├── templateDDC.p4	# P4 code of DCC. We template the DDC implementation using Python Jinja2 since each P4 switch needs a separate P4 code due the different number of ports it has.
        ├── F10/
			    ├── f10-DC-wFailure-ECMP.p4	# P4 code of F10 for scenarios with failure using ECMP
				├── f10-DC-woFailure-ECMP.p4	# P4 code of F10 for scenarios without failure using ECMP
        ├── TEL/
		    ├── BMv2/
			    ├── TEL-DC-leaf.p4	# P4 code of TEL
			    ├── TEL-DC-spine.p4	# P4 code of TEL
			├── Tofino/
			    ├── TEL-Tofino.p4	# TEL code for Tofino 
  ├── Python/  
		├── KSP/                                         
              ├── AttMpls/	# Python code of TEL-C for AttMpls topology
              ├── Goodnet/	# Python code of TEL-C for Goodnet topology
results/
  ├── DDC/
        ├── AS1755/	# Code for simulations using TEL and DDC on AS1755
        ├── AS3967/	# Code for simulations using TEL and DDC on AS3967
        ├── B4	# Code for simulations using TEL and DDC on Google B4
  ├── F10/
        ├── CachFollower/	# Code for simulations using TEL and F10 using CacheFollower traffic trace
		├── WebSearch/	# Code for simulations using TEL and F10 using WebSearch traffic trace		
```

## Run the code

You need to run the topo.py to do the experiments.

```
sudo python topo.py
```

It will create the P4 network using the given topology in topo.txt file. This will use
the json representation file of P4 code to create the network and start P4 switches in 
Mininet. Then, it uses the s#-commands.txt to insert the initial forwarding rules on 
top of P4 switches. Now, the code is to run the measurements. This procedure is similar
for TEL, F10, and DDC solutions.

## Publication
```bibtex
@article{TEL-TNSM21,
 author={H. Mostafaei and M. Shojafar and M. Conti},
 title={{TEL}: Low-Latency Failover Traffic Engineering in Data Plane},
 journal={IEEE Transactions on Network and Service Management},
 year={2021},
 volume={18},
 number={4},
 pages= {4697--4710},
}
```
