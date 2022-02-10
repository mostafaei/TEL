fname="script_file1"
f1 = open(fname, "a")
for i in range(0,200):    
    rule1="   -a 10.0.2.2 -z 2 -c 450 -rp %s -T UDP \n"%(51000+int(i))
    f1.write(rule1)
f1.close()
fname="script_file2"
f1 = open(fname, "a")
for i in range(201,400):    
    rule1="   -a 10.0.2.2 -z 2 -c 450 -rp %s -T UDP \n"%(51000+int(i))
    f1.write(rule1)
f1.close()
fname="script_file3"
f1 = open(fname, "a")
for i in range(401,600):    
    rule1="   -a 10.0.2.2 -z 2 -c 450 -rp %s -T UDP \n"%(51000+int(i))
    f1.write(rule1)
f1.close()
fname="script_file4"
f1 = open(fname, "a")
for i in range(601,800):    
    rule1="   -a 10.0.2.2 -z 2 -c 450 -rp %s -T UDP \n"%(51000+int(i))
    f1.write(rule1)
f1.close()
