# !/usr/bin/env python

from distutils.core import setup
setup(
    name='modern-relay',
    packages=[],
    version='0.0.1',
    description='An asynchronous SMTP relay with selectable delivery agents',
    author='Brett Buford',
    license='MIT',
    author_email='blbuford@gmail.com',
    url='https://github.com/blbuford/ModernRelay',
    keywords=['SMTP', 'Relay', ],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Communications :: Email',
    ],
)