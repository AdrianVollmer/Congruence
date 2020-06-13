from congruence.__init__ import __version__
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


setup(
    name='congruence',
    description=('A command line interface for Confluence'),
    author='Adrian Vollmer',
    url='https://github.com/AdrianVollmer/Congruence',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    version=__version__,
    license='GPL3',
    install_requires=[
        'html2text',
        'markdown',
        'beautifulsoup4',
        'pyyaml',
        'pyxdg',
        'pytz',
        'python-dateutil',
        'requests',
        'urwid',
    ],
    tests_require=[
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'congruence = congruence.__main__:main',
        ]
    },
    packages=find_packages(),
    scripts=[],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console :: Curses ',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop ',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Office/Business ',
    ],
)
