import networkx as nx
import time
G = nx.read_graphml('AttMpls.graphml')
nx.draw(G, with_labels=True)
print(G.nodes())
start=time.clock()
nx.shortest_path(G,'0','4')
end=time.clock()
print (nx.shortest_path(G,'0','4'),('{0:.3f}'.format((end-start)*1000)))

