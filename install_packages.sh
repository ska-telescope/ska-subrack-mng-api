#!/bin/bash
#pip install -r requirements.pip || exit
pip install Cython
pip install future
pip install parse
pip install uritools
pip install psutil
pip install terminaltables
pip install ipython==5.5.0
pip install numpy
pip install lxml
pip install enum34
pip install pyserial
cd pyfabil
python setup.py install
pwd
cd ../
python setup.py install
#pip install matplotlib
#pip install scipypip list
