import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'django-metaimage',
    version = '0.1',
    url = '',
    license = 'GPLv3',
    description = 'Provides a useful subclass of photologue.ImageModel.',
    long_description = read('README'),
    author = 'Kai Wu',
    author_email = 'k@limist.com',

    packages = find_packages('src'),
    package_dir = {'': 'src'},
    install_requires = ['setuptools'],

    classifiers = [
	'Development Status :: 3 - Alpha',
	'Framework :: Django',
	'Intended Audience :: Developers',
	'License :: OSI Approved :: GNU General Public License (GPL)',
	'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP'
	]
    )
