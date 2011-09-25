"""
whirly
=====
whirly is a framework wrapper for the scalable, non-blocking web server tornado,
which provided an extension system to enhance the use of tornado web server.
Whirly is compatible with Google App Engine in WSGI mode.

Already provided extensions:
* Session
* Storage (MySQL, PostgreSQL, SQLite, MongoDB, Datastore, Redis)
* Auth
* Cache
* Flash Message
* Support different template engines
"""

from setuptools import setup, find_packages


setup(
    name='whirly',
    version='0.1',
    url='',
    license='Apache Software License',
    author='Yuanhao Li',
    author_email='yuanhao.li [at] gmail [dot] com',
    description='A framework wrapper for the scalable, non-blocking web server tornado.',
    long_description=__doc__,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    packages=['whirly']
)

