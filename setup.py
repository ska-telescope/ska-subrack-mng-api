from setuptools import setup

setup(
    name='subrack_mng_api',
    version='2.3',
    packages=['subrack_mng_api', 'subrack_mng_api.emulator_classes', 'cpld_mng_api', 'cpld_mng_api.netproto',
              'cpld_mng_api.bsp', 'web_server'],
    url='',
    license='GPLv3',
    author='Cristian Albanese',
    author_email='cristian.albanese@sanitaseg.it',
    description='Python API package for subrack management board',
    dependency_links=[],
    install_requires=['future', 'parse', 'uritools','psutil', ' terminaltables', 'ipython'],
)