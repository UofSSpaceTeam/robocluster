# robocluster

[![Build Status](https://travis-ci.org/UofSSpaceTeam/robocluster.svg?branch=dev)](https://travis-ci.org/UofSSpaceTeam/robocluster)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/cbfd0fa1a8c64f9ea122553adfe32582)](https://www.codacy.com/app/UofSSpaceTeam/robocluster?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=UofSSpaceTeam/robocluster&amp;utm_campaign=Badge_Grade)
[![Code Health](https://landscape.io/github/UofSSpaceTeam/robocluster/dev/landscape.svg?style=flat)](https://landscape.io/github/UofSSpaceTeam/robocluster/dev)
[![Documentation Status](http://readthedocs.org/projects/robocluster/badge/?version=latest)](http://robocluster.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/UofSSpaceTeam/robocluster/badge.svg?branch=dev)](https://coveralls.io/github/UofSSpaceTeam/robocluster?branch=dev)

This is a library that powers the communication for the USST's mars rover,
but is also applicable to any robotics system where multiple modules are involved.
Robocluster allows you to build light weight distributed applications that talk to each other
over a local area network using IP multicast and TCP sockets.

## Documentation
We have sphinx generated documentation that can be found [here](http://robocluster.readthedocs.io/en/latest/index.html).
The [Usage Tutorial](http://robocluster.readthedocs.io/en/latest/tutorial.html) steps through
some example code to show off the features of using robocluster.
The `examples` folder contains some example scripts to test out robocluster as well.

## Installation (for development)
At some point (soon?) we'll put this on PyPi, but for now you can install robocluster as follows:
1. clone the repo from github
1. From the project root, do `pip install -r requirements.txt`.
1. From the project root, do `pip install -e .`.
1. Run the `examples/device.py` script to confirm everything works. It should print random numbers to the console.

## Contributing
Create a branch off of `dev` and make changes from there.
When your change is done, and you want feedback, submit a pull request,
and someone will review your code and merge it if it's ready.

