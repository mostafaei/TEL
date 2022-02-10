from __future__ import division
import random
import math
import networkx as nx
import matplotlib.pyplot as plt
from LA import LearningAutomaton	
from DLA import DistributedLearningAutomaton	
import sys,time
import re
import numpy as np
import itertools

from kshortest import *

G = nx.read_graphml('Goodnet.graphml')
nx.draw(G, with_labels=True)
#create a list of nodes as DLA graph
aNodes=G.nodes
aEdges=G.edges
#print (aNodes)
#print (aEdges)
ed=list(G.edges(data=True))
ed.sort()
newE=[]
#print(type(ed[0]),'gggggggggg')
f11 = open('topo.txt', "a")
for e in ed:
    k=e[0]
    #print('kk',k,k[0],'yyyyy',k[1])
    newE.append((int(e[0]),int(e[1])))
newE.sort()

f11.write('switches '+str(len(aNodes))+' \n')
f11.write('hosts '+str(len(aNodes))+' \n')
for i in range(len(aNodes)):
    f11.write('h'+str(i+1)+' '+ 's'+str(i+1)+' \n')
for e in newE:
    f11.write('s'+str(e[0]+1)+' '+ 's'+str(e[1]+1)+' \n')
f11.close()
#print('new---E--',newE)



#portFinder************************************************************
#
#**********************************************************************
Nodes=[]
infile = open('topo.txt', 'r')
firstLine = infile.readline()
#print('count:',firstLine)
count=firstLine.split(' ')[1]
#print('count:',count)
Nodes=[[] for x in xrange(int(count))]
for g in xrange(int(count)):
    fname="s%d-commands.txt"%(int(g)+1)
    f1 = open(fname, "a")
    #ruleReg="register_write MyIngress.port_reg 0 31 \n"
    #f1.write(ruleReg)
    f1.close()
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

#print("*****************************************Nodes*************************: ",Nodes)
#*********************************************************************                
#*************************************
# NOW PARSE ELEMENT SETS TO GET THE DATA FOR THE TOPO
# GET NODE_NAME DATA
# GET LONGITUDE DATK
# GET LATITUDE DATA

for e in aEdges:
    #print "e:",aEdges[e]['LinkNote']
    #print aNodes[e[0]]['Latitude'], aNodes[e[0]]['Longitude']
    latitude_src=math.radians(float(aNodes[e[0]]['Latitude']))
    latitude_dst=math.radians(float(aNodes[e[1]]['Latitude']))
    longitude_src=math.radians(float(aNodes[e[0]]['Longitude']))
    longitude_dst=math.radians(float(aNodes[e[1]]['Longitude']))
    first_product               = math.sin(latitude_dst) * math.sin(latitude_src)
    second_product_first_part   = math.cos(latitude_dst) * math.cos(latitude_src)
    second_product_second_part  = math.cos(longitude_dst - longitude_src)

    distance = math.acos(first_product + (second_product_first_part * second_product_second_part)) * 6378.137

    # t (in ms) = ( distance in km * 1000 (for meters) ) / ( speed of light / 1000 (for ms))
    # t         = ( distance       * 1000              ) / ( 1.97 * 10**8   / 1000         )
    latency = ( distance * 1000 ) / ( 197000 )
    #print "latency:", latency
    G[e[0]][e[1]]['latency']=latency
    #get the numbers from BW with value like 45Mbps
    #print(aEdges[e],e[0],e[1])
    G[e[0]][e[1]]['bandwidth']=45
    #G[e[0]][e[1]]['bandwidth']=map(int, re.findall(r'\d+', aEdges[e]['LinkNote'].encode('utf-8')))
    #print aNodes[e[1]['Latitude'], aNodes[e[1]['Longitude']
    # GET IDS FOR EASIER HANDLING



# *************************************************************************
# Create the DLA graph from the network graph
# *************************************************************************
dla=DistributedLearningAutomaton('DLA',G)
dla.buildNetwork()
#dla.printNodes()
bestPaths=[]
bestBackupPaths=[]


# *************************************************************************
# We print all the found k shortest paths by DLA using this function
# *************************************************************************
def printFinalPath():
    print(" ********************************************** ")
    print(" Final ",k," paths are:")
    for i in bestPaths:
        print (bestPaths.index(i),':',i)
    print(" ********************************************** ")
    print(" Final backup",k," paths are:")
    for i in bestBackupPaths:
        print (bestBackupPaths.index(i),':',i)


# ******************************************************************************
# This function updates the cacity of each link by deducting the current
# flow bandiwth request from the available bandwidth
# ******************************************************************************
def updatePathsGraph(path,req):
    G.edges(data=True)
    i=0
    while i< len(path)-1:
        node1=path[i]
        node2=path[i+1]
        #print ("******",type(G[node1][node2]['bandwidth']),G[node1][node2]['bandwidth'],"***",node1,node2)
        if isinstance(G[node1][node2]['bandwidth'], int):
            bw=G[node1][node2]['bandwidth']
        else:
            bw=G[node1][node2]['bandwidth'][0]
        bw-=req
        G[node1][node2]['bandwidth']=bw
        #print("****NEW SPARE BW******************",G[node1][node2]['bandwidth'])
        i+=1

# ******************************************************************************
# This function updates generates rules for P4 switches
# flow bandiwth request from the available bandwidth
# ******************************************************************************
def GenerateRule():

    for i in bestPaths:
        #print ('Rule generation for path ',bestPaths.index(i),':',i)
        p=i
        src=p[0]
        dst=p[-1]
        #writeRegisterRules(src)
        writeHostRules(src,dst)
        writeHostRules(dst,src)
        #writeHostRules(dst)
        for j in range(0,len(p),1):
            if j<len(p)-1:
                neighborIndex(p[j],p[j+1],dst,src,bestPaths.index(i))
                #writeRegisterRules(p[j])
        #create the oppoiste direction rules
        reverseP = p[::-1]
        #print('rrrrrrrrrrrrrrrr',reverseP)
        for k in range(0,len(reverseP),1):
           if k<len(reverseP)-1:
                neighborIndex(reverseP[k],reverseP[k+1],src,dst,bestPaths.index(i)+len(bestPaths))

    #Generate rules for Backup Path

    for i in bestBackupPaths:
        #print ('Rule generation for path ',bestBackupPaths.index(i),':',i)
        if len(i)>1:
		    p=i
		    src=p[0]
		    dst=p[-1]
		    for j in range(0,len(p),1):
		        if j<len(p)-1:
		            neighborIndexBackupPath(p[j],p[j+1],dst,src,bestBackupPaths.index(i))
		    #create the oppoiste direction rules
		    reverseP = p[::-1]
		    #print('rrrrrrrrrrrrrrrr',reverseP)
		    for k in range(0,len(reverseP),1):
		        if k<len(reverseP)-1:
		            neighborIndexBackupPath(reverseP[k],reverseP[k+1],src,dst,bestBackupPaths.index(i)+len(bestBackupPaths))


def GenerateRuleKSP(primaryPaths,backupPaths):

    for i in primaryPaths:
        #print ('Rule generation for path ',bestPaths.index(i),':',i)
        p=i
        src=p[0]
        dst=p[-1]
        #writeRegisterRules(src)
        writeHostRules(src,dst)
        writeHostRules(dst,src)
        #writeHostRules(dst)
        for j in range(0,len(p),1):
            if j<len(p)-1:
                neighborIndex(p[j],p[j+1],dst,src,primaryPaths.index(i))
                #writeRegisterRules(p[j])
        #create the oppoiste direction rules
        reverseP = p[::-1]
        #print('rrrrrrrrrrrrrrrr',reverseP)
        for k in range(0,len(reverseP),1):
           if k<len(reverseP)-1:
                neighborIndex(reverseP[k],reverseP[k+1],src,dst,primaryPaths.index(i)+len(primaryPaths))

    #Generate rules for Backup Path

    for i in backupPaths:
        #print ('Rule generation for path ',bestBackupPaths.index(i),':',i)
        if len(i)>1:
		    p=i
		    src=p[0]
		    dst=p[-1]
		    for j in range(0,len(p),1):
		        if j<len(p)-1:
		            neighborIndexBackupPath(p[j],p[j+1],dst,src,backupPaths.index(i))
		    #create the oppoiste direction rules
		    reverseP = p[::-1]
		    #print('rrrrrrrrrrrrrrrr',reverseP)
		    for k in range(0,len(reverseP),1):
		        if k<len(reverseP)-1:
		            neighborIndexBackupPath(reverseP[k],reverseP[k+1],src,dst,backupPaths.index(i)+len(backupPaths))
		            
def ComputeAvgHops():
    avgPrimary=0
    avgBackup=0
    for i in bestPaths:
        avgPrimary+=len(i)
    print('AvgPrimary:',avgPrimary,float(avgPrimary/25)+2)


    for i in bestBackupPaths:
        avgBackup+=len(i)
    print('AvgBackup:',avgBackup,float(avgBackup/25)+2)
		   
def checkfile(fname,rule):
    flag=False
    with open(fname) as f:
        #line=f.read()
        for line in f:
            if rule in line:
                flag=True
                return flag
    return flag

def writeHostRules(src,dst):
    fname="s%d-commands.txt"%(int(src)+1)
    f1 = open(fname, "a")
    rule1="table_add MyIngress.table_1 MyIngress.host_set 10.0.%s.%s 10.0.%s.%s => 0  \n"%(int(dst)+1 ,int(dst)+1, int(src)+1 ,int(src)+1)
    rule2="table_add MyIngress.table_2 MyIngress.ipv4_forward 0 0 => 00:00:00:00:%02x:%02x 1  \n"%( int(src)+1 ,int(src)+1)
    if not checkfile(fname,rule1):
        f1.write(rule1)
    if not checkfile(fname,rule2):
        f1.write(rule2)
    f1.close()


def neighborIndex(a,b,dst,src,p_i):
    fname="s%d-commands.txt"%(int(a)+1)
    f1 = open(fname, "a")
    eport=egressPort(a,b)
    rule1="table_add MyIngress.table_1 MyIngress.host_set 10.0.%s.%s 10.0.%s.%s => %s  \n"%(int(src)+1 ,int(src)+1,int(dst)+1 ,int(dst)+1,bin(int(p_i)+1))
    rule2="table_add MyIngress.table_2 MyIngress.ipv4_forward %s 0 => 00:00:00:%02x:%02x:00 %s \n"%(bin(int(p_i)+1),int(dst)+1 ,int(dst)+1,str(int(eport)+1))
    if not checkfile(fname,rule1):
        f1.write(rule1)
    if not checkfile(fname,rule2):
        f1.write(rule2)
    f1.close()
def egressPort(src,dst):
    #print(Nodes[int(src)])
    egress=Nodes[int(src)].index('s'+str(int(dst)+1))
    #print('------EGRESS---',egress)
    return egress

def neighborIndexBackupPath(a,b,dst,src,p_i):
    fname="s%d-commands.txt"%(int(a)+1)
    f1 = open(fname, "a")
    eport=egressPort(a,b)
    rule1="table_add MyIngress.table_1 MyIngress.host_set 10.0.%s.%s 10.0.%s.%s => %s  \n"%(int(src)+1 ,int(src)+1,int(dst)+1 ,int(dst)+1,bin(int(p_i)+1))
    rule2="table_add MyIngress.table_2 MyIngress.ipv4_forward %s 1 => 00:00:00:%02x:%02x:00 %s \n"%(bin(int(p_i)+1),int(dst)+1 ,int(dst)+1,str(int(eport)+1))
    if not checkfile(fname,rule1):
        #print("Write BB rule1 in %s %s"%(fname,rule1))
        f1.write(rule1)
    if not checkfile(fname,rule2):
        #print("Write BB rule2 in %s %s"%(fname,rule2))
        f1.write(rule2)
    f1.close()


#-------------------------------------------------------------------------------
# Test Yen's k-shortest path algorithm
#-------------------------------------------------------------------------------
from heapq import heappush, heappop
def YenKSP(Graph, source, target, K, weight):

    def path2length(path):
        return sum(Graph[i][j][weight] for i, j in zip(path, path[1:]))

    #  Determine the shortest path from the source to the sink.
    A = [nx.shortest_path(Graph, source=source, target=target, weight=weight)]
    # Initialize the set to store the potential kth shortest path.
    B = [];

    for k in range(K-1):
        # The spur node ranges from the first node to the next to last node in the previous (k+1)-shortest path.
        for i in range(len(A[k]) - 1):
            H = Graph.copy()
            # Spur node is retrieved from the previous k-shortest path
            spur_node = A[k][i]
            # The sequence of nodes from the source to the spur node of the previous k-shortest path.
            root_path = A[k][:i+1];

            for path in A:
                if root_path == path[:i+1]:
                    # Remove the links that are part of the previous shortest paths which share the same root path.
                    # remove p.edge(i,i + 1) from Graph;
                    if (path[i], path[i+1]) in H.edges():
                        H.remove_edge(path[i], path[i+1])

            # for each node rootPathNode in rootPath except spurNode:
            #     remove rootPathNode from Graph;
            for i, j in zip(root_path, root_path[1:]):
                if (i, j) in H.edges():
                    H.remove_edge(i, j)
            try:
                # Calculate the spur path from the spur node to the sink.
                spur_path = nx.shortest_path(H, source=spur_node, target=target, weight=weight)
                # Entire path is made up of the root path and spur path.
                total_path = root_path[:-1] + spur_path
                # Add the potential k-shortest path to the heap.
                total_path_len = path2length(total_path)
                if (total_path_len, total_path) not in B:
                    heappush(B, (total_path_len, total_path))
            except:
                pass

        if not B:
            # This handles the case of there being no spur paths, or no spur paths left.
            # This could happen if the spur paths have already been exhausted (added to A),
            # or there are no spur paths at all - such as when both the source and sink vertices
            # lie along a "dead end".
            break;
        # Add the lowest cost path becomes the k-shortest path.
        A.append(heappop(B)[1]);

    return A

H = nx.DiGraph()
H= nx.read_graphml('Goodnet.graphml')
nx.draw(H, with_labels=True)
from itertools import islice
bNodes=H.nodes
bEdges=H.edges
for e in bEdges:
    latitude_src=math.radians(float(bNodes[e[0]]['Latitude']))
    latitude_dst=math.radians(float(bNodes[e[1]]['Latitude']))
    longitude_src=math.radians(float(bNodes[e[0]]['Longitude']))
    longitude_dst=math.radians(float(bNodes[e[1]]['Longitude']))
    first_product               = math.sin(latitude_dst) * math.sin(latitude_src)
    second_product_first_part   = math.cos(latitude_dst) * math.cos(latitude_src)
    second_product_second_part  = math.cos(longitude_dst - longitude_src)
    distance = math.acos(first_product + (second_product_first_part * second_product_second_part)) * 6378.137
    latency = ( distance * 1000 ) / ( 197000 )
    H[e[0]][e[1]]['latency']=latency
    H[e[0]][e[1]]['bandwidth']=45

nodeList=range(len(H))
randList = list(itertools.permutations(nodeList, 2))
random.shuffle(randList)

start=time.time()
kkk=2
k=0
sumPrimaryPaths=[]
sumBackupPaths=[]
#AllKSPpaths=[]
KSPprimaryPaths=[]
KSPbackupPaths=[]
while k<25:
    src,dst=randList[k]
    src=dla.getNode(src)
    dst=dla.getNode(dst)
    AllKSPpaths=YenKSP(H, src.name, dst.name, kkk, "bandwidth")
    print('AllKSPpaths: ',AllKSPpaths)
    KSPprimaryPaths.append(AllKSPpaths[0])
    KSPbackupPaths.append(AllKSPpaths[1])
    
    k+=1
end=time.time()

print('-----------------------YEN time:',end-start,AllKSPpaths)
print('KSP primary:', KSPprimaryPaths)
print('KSP backup:', KSPbackupPaths)

# *************************************************************************
# Repeat k times the algorithm to find k different shortest paths from the
# network graph using DLA
# First, we create a unique random list of src and dst nodes and then we
# run our algorithm to find the shortest path between the src and the dst
# We also record the backup path for the failure scenario
# *************************************************************************
#nodeList=range(len(G))
#randList = list(itertools.permutations(nodeList, 2))
#random.shuffle(randList)
AllDLApaths=[]
k=0

sumPrimaryPathsTEL=[]
sumBackupPathsTEL=[]


while k<25:
    #src=random.randrange(0, len(G))
    #dst=random.randrange(0, len(G))
    
    # *************************************************************************
    # We have to disable the corresponding actions of the links that do not have
    # spare bandwidth to place further flows
    # *************************************************************************

    #src,dst=random.sample(range(0, len(G)), 2)
    #src=7
    #dst=13
    src,dst=randList[k]
    src=dla.getNode(src)
    dst=dla.getNode(dst)
    itr=0
    currentBestPath=[]
    currentBestBackupPath=[]
    listOfLists=[]
    bestLatency=float("inf")
    bestBackupLatency=float("inf")
    start=time.time()
    while itr<15:
        path=[]
        path.append(src)
        #print ("src",src.name," dst:",dst.name)
        dla.disableActionInDLA(src)
        dla.process3(src,dst,path)
        pathLatency=dla.evaluatePath(G,path)
        tmp=[]
        if path not in listOfLists:
            listOfLists.append(path)
            for i in path:
				tmp.append(i.name)
            AllDLApaths.append(tmp)
        if pathLatency<bestLatency:
            currentBestPath[:]=[]
            bestLatency=pathLatency
            for i in path:
                #print i.name," ",
                currentBestPath.append(i.name)
        dla.resetAction()
        itr+=1
    end=time.time()
    print('-----------------------DLA time:',end-start)    
    updatePathsGraph(currentBestPath,10)
    updatePathsGraph(currentBestBackupPath,10)
    listOfLists.sort(key = len)
    BBPath=[]
    if len(listOfLists)==1:
        BBPath=listOfLists[0]
    else:
        BBPath=listOfLists[1]
    for i in BBPath:
       currentBestBackupPath.append(i.name)
    l=0
    while l<len(listOfLists):
        if currentBestBackupPath==currentBestPath:
            BBPath=listOfLists[l]
            currentBestBackupPath=[]
            for u in BBPath:
                currentBestBackupPath.append(u.name)
        l+=1
    # *************************************************************************
    # we have deduct the bandwidth request of this path from the available bandwidth
    # *************************************************************************
    k=k+1
    bestPaths.append(currentBestPath)
    bestBackupPaths.append(currentBestBackupPath)
    sumPrimaryPathsTEL.append(len(currentBestPath)+1)
    sumBackupPathsTEL.append(len(currentBestBackupPath)+1)

    #print('-----------ALL DLA Paths %d:'%(k),(len(currentBestPath)+1+len(currentBestBackupPath)+1)/2)
    

AllDLApaths.sort(key=len)
sumDLA=[]
sumKSP=[]
for i in range(kkk):
	print(i,len(AllDLApaths[i]))
	sumDLA.append(len(AllDLApaths[i]))
	sumKSP.append(len(AllKSPpaths[i]))
print('------------ALL DLA paths--------------', np.mean(sumDLA),np.std(sumDLA))
print('------------AllKSPpaths--------------', np.mean(sumKSP),np.std(sumKSP))

print('******************************BEST PATHS***********************************',bestPaths)
printFinalPath()
GenerateRule()
ComputeAvgHops()
print('******************************waiting****************************')
time.sleep(60)
GenerateRuleKSP(KSPprimaryPaths,KSPbackupPaths)
#plt.show()

