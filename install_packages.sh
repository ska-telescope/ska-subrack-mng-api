#!/bin/bash
cd pyfabil
python setup.py install
pwd
cd ../aavs-access-layer/python/
python setup.py install
cd ../../
python setup.py install
pip install Cython
pip install future
pip install parse
pip install uritools
pip install psutil
pip install terminaltables
pip install ipython==5.5.0
pip install numpy
#pip install lxml
pip install enum34
#pip install matplotlib
#pip install scipypip list
