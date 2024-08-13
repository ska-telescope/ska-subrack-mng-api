from setuptools import setup
from subrack_mng_api.version import *

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='subrack_mng_api',
    version=get_version(),
    packages=['subrack_mng_api', 'subrack_mng_api.emulator_classes', 'cpld_mng_api', 'cpld_mng_api.netproto',
              'cpld_mng_api.bsp', 'web_server', 'tools'],
    package_data={'cpld_mng_api': ["pll_subrack_OCXO.txt","pll_subrack_OCXO_generate_internal.txt"]},
    url='',
    license='GPLv3',
    author='Cristian Albanese',
    author_email='cristian.albanese@sanitaseg.it',
    description='Python API package for subrack management board',
    dependency_links=[],
    install_requires=required,
)
