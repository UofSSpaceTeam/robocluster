# robocluster

[![Build Status](https://travis-ci.org/UofSSpaceTeam/robocluster.svg?branch=dev)](https://travis-ci.org/UofSSpaceTeam/robocluster)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/cbfd0fa1a8c64f9ea122553adfe32582)](https://www.codacy.com/app/UofSSpaceTeam/robocluster?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=UofSSpaceTeam/robocluster&amp;utm_campaign=Badge_Grade)
[![Documentation Status](http://readthedocs.org/projects/robocluster/badge/?version=latest)](http://robocluster.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/UofSSpaceTeam/robocluster/badge.svg?branch=dev)](https://coveralls.io/github/UofSSpaceTeam/robocluster?branch=dev)

This is a library that will hopefully power the communication for the USST's mars rover,
but is also ablicable to any robotics system where multiple modules are involved.
We are serializing data with JSON, with the intention of a switching to alternatives like msgpack in the future if performance becomes an issue.
Transport of data will be done with ZeroMQ which in turn is a wrapper for socket programming.
All communication between modules is done with sockets, IPC or TCP, so the framework should run on any operating system platform.

TODO; Please update this readme as development continues...
