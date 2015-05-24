"""
aio.web.server
"""
import os
import sys
from setuptools import setup, find_packages

version = "0.0.12"

install_requires = [
    'distribute',
    'aio.core',
    'aio.app',
    'aio.http.server',
    'aiohttp',
    'aiohttp_jinja2']

if sys.version_info < (3, 4):
    install_requires += [
        'asyncio']

tests_require = install_requires + ['aio.testing']


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = (
    'Detailed documentation\n'
    + '**********************\n'
    + '\n'
    + read("README.rst")
    + '\n')

try:
    long_description += (
        '\n'
        + read("aio", "web", "server", "README.rst")
        + '\n')
except FileNotFoundError:
    pass


setup(
    name='aio.web.server',
    version=version,
    description="Aio web server",
    long_description=long_description,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    keywords='',
    author='Ryan Northey',
    author_email='ryan@3ca.org.uk',
    url='http://github.com/phlax/aio.web.server',
    license='GPL',
    packages=find_packages(),
    namespace_packages=['aio', "aio.web"],
    include_package_data=True,
    test_suite="aio.app.tests",
    zip_safe=False,
    tests_require=tests_require,
    install_requires=install_requires,
    entry_points={})
