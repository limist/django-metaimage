from setuptools import setup, find_packages

setup(
    name = 'django-metaimage',
    version = '0.1',
    url = '',
    license = 'GPLv3',
    description = 'Provides a useful subclass of photologue.ImageModel.',
    author = 'Kai Wu',
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    install_requires = ['setuptools'],
    )
