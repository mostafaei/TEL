import random
import math
import networkx as nx
import sys
from LA import LearningAutomaton
__author__='Habib Mostafaei, 24 Jan 2020, Berlin/Germany'

sys.setrecursionlimit(10**6)

class DistributedLearningAutomaton(object):
    aNodes=[]
    name=None
    def __init__(self,name,G):
	self.name=name
        self.G=G

    def getNode(self,i):
        return self.aNodes[i]

    def buildNetwork(self):
        i=0
        for node in self.G.nodes():
            #print node," neighbors=",len(list(self.G.neighbors(node)))
            la_node=LearningAutomaton(node,len(list(self.G.neighbors(node))),i)
            la_node.addNeighborList(list(self.G.neighbors(node)))
            #print " node", node, " neighbors",list(self.G.neighbors(node))
            self.aNodes.append(la_node)
            i=i+1


    def resetAction(self):
        for node in self.aNodes:
            node.SetActionProbability(len(node.neighbors))
    
    # Count the number of possible links in the DLA network
    # This is done by counting the number of True value in the
    # ActionStatus pf LA of each node
    def countAvailableActions(self):
        sumAll=0
        for node in self.aNodes:
            sumAll+=sum(node.ActionStatus)
        return sumAll


    def printPath(self,path):
        print('*****************************************')
        print "final path",
        for i in path:
            print "->",i.name,
        print('')
        print('*****************************************')

    def evaluatePath(self,G,path):
        G.edges(data=True)
        #print G.edges.data()
        i=0
        sumDelay=0
        minBandwidth=float('inf')
        while i< len(path)-1:
            node1=path[i]
            node2=path[i+1]
            #print( '***Latency***',node1.name, node2.name,'***:',G[node1.name][node2.name]['latency'])
            #print( '***bandwidth***',node1.name, node2.name,'***:',G[node1.name][node2.name]['bandwidth'])
            if G[node1.name][node2.name][0]['bandwidth']< minBandwidth:
                minBandwidth=G[node1.name][node2.name][0]['bandwidth']
            sumDelay+=G[node1.name][node2.name][0]['latency']
            i=i+1
        return sumDelay


    def findIndex(self,nodeID):
        i=0
        #print "*****NODE ID:",nodeID
        while i< len(self.aNodes):
            node=self.aNodes[i]
            #print "i",i,node.name
            if nodeID==node.name:
                return i
            i=i+1

    # This function checks the existence of a node in the path
    # If added before pop all the nodes on the list to reach the current node
    # We do this for node uniqueness
    def checkNodeInPath(self,node,path):
        if node in path:
            while True:
                path.pop()
                tmp=path[-1]
                if tmp==node:
                    return

    def disableActionInDLA(self,node):
        for i in self.aNodes:
            #print("i:",i.name)
            j=0
            while j< len(i.neighbors) and i!=node and node.name in i.neighbors:
                m=i.neighbors[j]
                a=i.name
                #print('a:',a,'m:',m)
                if m==node.name:
                    i.disableAction(j)
                    #print("action " ,j," is disabled")
                #print ("i.neighbors[j]",type(i.neighbors[j]),i.neighbors[j])
                j=j+1



    def process3(self,src,dst,path):
        #disable action of each LA results in selecting the src again
        #self.disableActionInDLA(src)
        try:

            if src in path and dst in path:
                return path
            if src==dst:
                #print "I am inside if"
                if src not in path:
                    self.checkNodeInPath(src,path)
                    path.append(src)
                if dst not in path:
                    path.append(dst)    
                #self.printPath(path)
                return path 
            elif dst.name in src.neighbors:
                #print "I am inside elif"
                #print "src.neighbors:",src.neighbors
                if src not in path:
                    self.checkNodeInPath(src,path)
                    path.append(src)
                if dst not in path:
                    path.append(dst)    
                #self.printPath(path)
                return path
            else:
                if src.avilableNeighbors()>0:
                    #rnd=random.randrange(0,len(src.neighbors))
                    #print "src inside else:", src.name
                    tmp=src.name
                    rnd=src.selectAction()
                    src.disableAction(rnd)
                    src=src.neighbors[rnd]
                    #print "next selected index inside else:", rnd, "node:", src
                    src=self.aNodes[int(self.findIndex(src))]
                    #disable the reverse direction action
                    src.disableActionWithNodeID(tmp)
                    #if src not in path:
                    path.append(src)
                    if rnd=="Not":
                        #print("****POP***",path.pop())
                        path.pop()
                        src=path[-1]
                        if len(path)==0:
                            return
                        #print("***IF 2*****",self.countAvailableActions())
                        return self.process3(src,dst,path)
                    else:
                        #src=src.neighbors[rnd]
                        #src=self.aNodes[int(self.findIndex(src))]
                        #if len(src.neighbors)==1:
                            #print("****POP***",path.pop())
                            #path.pop()
                            #src=path[-1]
                            #self.process3(src,dst,path)
                        #print("**ELSE 2******",self.countAvailableActions())
                        return self.process3(src,dst,path)

                else:
                    path.pop()
                    #print("****POP***",path.pop())
                    src=path[-1]
                    if len(path)==0:
                        return
                    #print("****ELSE 3****",self.countAvailableActions())
                    return self.process3(src,dst,path)
        except Exception, e:
            print('Caught error: '+ str(e))
            return

    def process(self,src,dst):
        path=[]
        visited=[]
        path.append(src)
        node=self.aNodes[src]
        #add nodes to visited list to avoid selection in next round
        visited.append(node)
        path.append(nodei.name)
        dst_node=self.aNodes[dst]
        visited.append(dst_node)
        print("src=", node.name, "dst=",dst_node.name)
        #print len(node.neighbors)
        #print "neighbors", node.printNeighbors()
        rnd_node=random.randrange(0,len(node.neighbors))
        node=node.neighbors[rnd_node]
        print "first DLA selected",node,
        visited.append(node)

        node=self.aNodes[int(node)]
        path.append(node.name)
        if node==dst_node or dst_node in node.neighbors:
            path.append(dst_node.name)
            return
        print path,     
        while node != dst_node:
            #print "type(node)",type(node),"type(dst)",type(dst_node)
            #neighbors=list(self.G.neighbors(src))
            #print len(node.neighbors)
            #while node not in visited:
            rnd=random.randrange(0,len(node.neighbors))
            p= node.neighbors[rnd]
            node=self.aNodes[int(p)]
            visited.append(node)
            print  node.name,

            path.append(node.name)
            print(" Path:",path)
            if node==dst_node:
                return

    def printNodes(self):
        print "Total node count", len(self.aNodes)
        for obj in self.aNodes:
            #obj.SetActionProbability(obj.Action)
            print obj.name,
            #obj.printLA()


