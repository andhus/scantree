import io
import os
from setuptools import setup, find_packages

VERSION = '0.0.1'

DESCRIPTION = (
    'Flexible recursive directory iterator: scandir meets glob("**", recursive=True)'
)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
try:
    with io.open(os.path.join(PROJECT_ROOT, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except IOError:
    long_description = DESCRIPTION

setup(
    name='scantree',
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/andhus/scantree',
    author="Anders Huss",
    author_email="andhus@kth.se",
    license='MIT',
    install_requires=[
        'attrs>=18.0.0',
        'pathspec>=0.5.9'
    ],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={},
    tests_require=['pytest', 'pytest-cov']
)
