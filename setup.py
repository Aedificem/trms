from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='trms',
    version='0.2.4a1',

    description='Third-party Regis Moodle Scraper',
    long_description=long_description,

    url='https://github.com/Apexal/trms',

    author='Frank Matranga',
    author_email='thefrankmatranga@gmail.com',

    license='MIT',

    install_requires=['pymongo', 'requests', 'lxml'],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
    ],

    keywords='regis moodle scraper education school academics',

    packages=find_packages(),

    entry_points={
        'console_scripts': [
            'trms=trms:main',
        ],
    }
)
