import re
Nodes=[]
infile = open('topo.txt', 'r')
firstLine = infile.readline()
print('count:',firstLine)
count=firstLine.split(' ')[1]
print('count:',count)
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
for i in range(len(Nodes)):
    print('s%d:'%(i+1),Nodes[i])
