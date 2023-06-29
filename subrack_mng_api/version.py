__author__ = 'Cristian Albanese'
import os
import subprocess

__version__ = '2.2.0'

def get_version():
    try:
        cmd="git -C %s describe --tags --dirty --always"%os.path.dirname(__file__)
        result = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE)
        if result.returncode == 0:
            return __version__ + " (%s)"%str(result.stdout.decode('utf-8').strip())
        return __version__
    except:
        return __version__


