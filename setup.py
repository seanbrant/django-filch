import os
from setuptools import setup, find_packages

from filch import VERSION


f = open(os.path.join(os.path.dirname(__file__), 'README'))
readme = f.read()
f.close()

setup(
    name='django-filch',
    version='.'.join(map(str, VERSION)),
    description='django-filch is a reusable Django application ' \
                'for easy denormalization.',
    long_description=readme,
    author='Sean Brant',
    author_email='brant.sean@gmail.com',
    url='http://github.com/seanbrant/django-filch/tree/master',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
)
