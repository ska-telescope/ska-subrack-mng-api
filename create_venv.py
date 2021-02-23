__author__ = 'Cristian Albanese'
import os
import subprocess
import sys

if os.path.isdir("./venv"):
    print ("WARNING VIRTUALENV ALREADY EXIST PLEASE ACTIVATE RUNNING: source venv/bin/activate")
else:
    res=os.popen("whereis python2.7").read()
    lines=res.split(" ")
    for i in range(0, len(lines)):
        if lines[i].find("bin") != -1 and lines[i].find("config") == -1 and lines[i].find("python2.7") != -1:
            print (lines[i])
            os.system("virtualenv -p "+lines[i]+ " venv")
            #os.system("/bin/bash --rcfile venv/bin/activate")
            print ("VIRTUALENV CREATED PLEASE CONFIGURE RUNNING:")
            print ("source venv/bin/activate")
            print ("./install_packages.sh")
            #os.system("/bin/bash venv/bin/activate")
            #os.system("python ./management_cpu_scripts/setup.py install")
            #os.system("deactivate")