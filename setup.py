from setuptools import setup

setup(
    name='subrack_mng_api',
    version='1.0',
    packages=['subrack_mng_api','subrack_mng_api.emulator_classes'],
    url='',
    license='GPLv3',
    author='Cristian Albanese',
    author_email='cristian.albanese@sanitaseg.it',
    description='Python API package for subrack management board',
    dependency_links=['https://bitbucket.org/lessju/pyfabil/get/master.zip#egg=pyfabil'],
    install_requires=['pyfabil'],
)