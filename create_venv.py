__author__ = 'Cristian Albanese'
import os
import subprocess
import sys
from optparse import OptionParser

parser = OptionParser()
parser.add_option("--python_vers",  dest="python_version", default="3", help="select version of python for venv")
parser.add_option("-v","--venv_path",  dest="venv_path", default="./venv", help="select version of python for venv")



(options, args) = parser.parse_args()

if options.python_version == "2":
    if os.path.isdir(options.venv_path):
        print ("WARNING VIRTUALENV ALREADY EXIST PLEASE ACTIVATE RUNNING: source venv_py2/bin/activate")
    else:
        res = os.popen("whereis python2.7").read()
        lines = res.split(" ")
        for i in range(0, len(lines)):
            if lines[i].find("bin") != -1 and lines[i].find("config") == -1 and lines[i].find("python2.7") != -1:
                print (lines[i])
                os.system("virtualenv -p "+lines[i]+ " venv")
                #os.system("/bin/bash --rcfile venv/bin/activate")
                print ("VIRTUALENV CREATED PLEASE CONFIGURE RUNNING:")
                print ("source "+options.venv_path + "/bin/activate")
                print ("./install_packages.sh")
                #os.system("/bin/bash venv/bin/activate")
                #os.system("python ./management_cpu_scripts/setup.py install")
                #os.system("deactivate")
elif options.python_version == "3":
    if os.path.isdir(options.venv_path):
        print("WARNING VIRTUALENV ALREADY EXIST PLEASE ACTIVATE RUNNING: source " + options.venv_path + "/bin/activate")
    else:
        res = os.popen("python -m venv " + options.venv_path )
        print("VIRTUALENV CREATED PLEASE CONFIGURE RUNNING:")
        print("source " + options.venv_path + "/bin/activate")
        print("source install_packages.sh")
else:
    print("ERROR: Invalid option, permitted values are 2 or 3")
