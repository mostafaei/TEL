import random
import math

__author__='Habib Mostafaei, 23 Jan 2020, Berlin/Germany'

class LearningAutomaton(object):
    ActionProbability=[]
    ActionStatus=[]
    neighbors=[]
    name=None

    #def __init__(self,x,y,name,n):
    def __init__(self,name,n,index):
        #self.x=x
        #self.y=y
        self.name=name
        self.Action=n
        self.indexLA=index
        for i in range(0,n):
            self.ActionProbability.append(0)
            self.ActionStatus.append(True)
        self.SetActionProbability(n)
		
    def addNeighbor(self, node):
        self.neighbors.append(node)
    
    def disableAction(self,index):
        self.ActionStatus[index]=False

    def disableActionWithNodeID(self,node):
        i=0
        while i<len(self.neighbors):
            if node==self.neighbors[i]:
                #print ("action ",i," node:",self.neighbors[i]," is dsiabled")
                self.ActionStatus[i]=False
            i+=1


    def avilableNeighbors(self):
        count=sum(self.ActionStatus)
        return count

    def addNeighborList(self, node_list):
        self.neighbors=node_list
        #print "neighbors in LA", self.neighbors


    def Reward(self, ActionIndex, a):
        self.ActionProbability[ActionIndex] += a * (1 - self.ActionProbability[ActionIndex])
        i = 0

        for i in range(0, self.Action):
            if i != ActionIndex:
                self.ActionProbability[i] -= (a) * self.ActionProbability[i]
		i += 1
    
    def Penalty(self, ActionIndex, b):
        self.ActionProbability[ActionIndex] -= b * self.ActionProbability[ActionIndex]
        i = 0
        while i < self.Action:
            if i != ActionIndex:
                self.ActionProbability[i] -= b * self.ActionProbability[i]
                v = b / (self.Action)
                self.ActionProbability[i] += v
                i += 1

    def SetActionProbability(self, n):
	self.Action = n
	#self.ActionProbability = Array.CreateInstance(Double, Action)
	pro = float(1.0 / self.Action)
        self.ActionProbability=[pro]*n
        self.ActionStatus=[True]*n

    def getActionPro(self, i):
	return  self.ActionProbability[i]

    def ReturnBestAction(self):
	BestAction = self.ActionProbability.index(max(self.ActionProbability))
        return BestAction

    def selectAction(self):
        #rnd = random.randrange(0, self.Action )
        rnd =None
        if self.avilableNeighbors()>0:
            #print ("***************inside selecAction*********")
            rnd = random.randrange(0, self.Action )
            while self.ActionStatus[rnd]!=True:
                rnd = random.randrange(0, self.Action )
        elif not any(self.ActionStatus):
            return "Not"
	#self._SelectedAction = rnd
	return rnd
	
    def printNeighbors(self):
        for n in self.neighbors:
            print n,

    def printLA(self):
	print("The number of actions is",len(self.ActionProbability))
	for i in range(self.Action):
            print("action[{i}]=".format(i=i), (self.ActionProbability[i]))
		
