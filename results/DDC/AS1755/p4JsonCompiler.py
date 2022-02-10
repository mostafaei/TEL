import os

for i in range(1,112):
	os.system('p4c-bm2-ss --p4v 16 -o sw%d.json sw%d.p4'%(i,i))
