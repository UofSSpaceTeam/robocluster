import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    """
    Copied from the pytest documentation,
    Allows the test suite to be run from setup.py
    """
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]
    '''`python setup.py test -a "duration=5"`'''

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = '--cov=robocluster tests'

    def run_tests(self):
        import shlex, pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)

setup(name='robocluster',
      version='0.1',
      description='Distributed robotics framework',
      url='https://github.com/UofSSpaceTeam/robocluster',
      author='UofSSpaceTeam',
      author_email='software@usst.ca',
      license='ECL-2.0',
      packages=['robocluster'],
      install_requires=[
          'pyserial',
          'pyserial-asyncio',
          'pyvesc'
      ],
      dependency_links=[
          'git+https://github.com/UofSSpaceTeam/PyVESC.git#egg=PyVESC'
      ],
      zip_safe=False,
      tests_require=['pytest', 'coverage', 'pytest-cov'],
      cmdclass={'test': PyTest},
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Framework :: AsyncIO',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Software Development :: Embedded Systems',
          'Topic :: System :: Distributed Computing',
          'Topic :: System :: Networking',
      ]
)
