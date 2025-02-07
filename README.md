# pyStxm
python Qt software for STXM data acquisition, this application was originally put together to preform data collection 
on the UHV STXM at the SM beam line (10ID1) at the CLS. The application uses several main frameworks to deliver the 
data collection capability, namely:
 
* Python 3.10, The open source programming used
* Qt5, The open source application framework used
* Epics, R7, The open source distributed control system
* BlueSky, 1.12.0, Bluesky Data Collection Framework 
* Synapps 5.7, The device and data collection software
* PyEpics 3, The connection to the DCS from the python side


There is a second part to this software and that is the SynApps Epics applications that provide the low level device 
control, namely:
	
- **motor**: to provide the positioner control


## Getting Started

This software is completely dependant on Epics for providing the connection to all positioners and counters as well as 
the engine for doing scans. When the software is started a connection is made to all configured devices and therefore 
the Epics side of the software must be running before attempting to start pyStxm.

Next there is a second process called **nx_server** that must be running in order to save NEXUS **nxstxm** files, 
typically the nx_server process is running on a Windows or Linux computer that has a drive mapping to the base data 
directory.

## nx_server

**nx_server** has already been setup to run as a service on a linux machine so the server can be stopped and started from 
there
using the **systemctl** command.

The service runs a python file _nx_server.py_
it opens a zmq socket and receives data from an instance of pyStxm3 
in the form of a serialized dict, 

the service is used to:
- save nexus nxstxm and nxptyho files to loki
- remove garbage tiff files following a ptychography scan
- respond to pyStxm3 if the service is running or not
- respond back if the service is running on linux or windows
  (so that the instance of pyStxm3 can determine the appropriate data_dir format)

The nx_server service must be installed on a computer that 
has a mount point to the data computer such that the /etc/fstab file contains the entry in its list of mount points.:
--------------------------------------
### Prerequisites

The pyStxm software is dependent on the following python modules (note that their individual dependencies are not listed):

 - guidata (3.1.1)
 - plotpy (2.0.0) 
 - h5py (3.10.0)
 - NeXpy (1.0.5)
 - nexusformat (1.0.2)
 - numpy (1.26.1)
 - pyepics (3.5.2)
 - qwt (0.11.1)
 - QtPy (2.4.1)
 - bluesky (1.12.0)
 - ophyd (1.9.0)
 - databroker (1.2.5)
 - caproto (1.1.0)
 - suitcase (0.11.0)
 - scipy (1.11.3)
 - simplejson (3.19.2)
 - pymongo (4.6.0)


### Installing

Start by creating a clone of the repo:

1. Create a directory to clone the repo

```C:\tmp\Feb21>git clone https://github.clsi.ca/bergr/pyStxm.git```

This will create a **pyStxm** directory with all of the software in it.

## Set environment 

set your **PYTHONPATH** variable to point to the directory that you  cloned the repo into


LINUX:

 - ```setenv PYTHONPATH <repo dir>/pyStxm```

WINDOWS:

- ```set PYTHONPATH=<repo dir>/pyStxm```

## Edit the reqd_env_vars.sh file to reflect the ip address's and paths for your setup then ensure that
those environment variables are set in your shell before starting the software

## Edit app.ini
Before the application can be started you must first edit some paths in the pyStxm/app.ini file.
This file is located in:
```<repo dir>/pyStxm/applications/pyStxm```

Under the section [DEFAULT]change **top** and **dataDir** to point to the correct location for your pyStxm, examples are show below:

```top = C://tmp//Feb21//pyStxm//cls//```

```dataDir = S://STXM-data//Cryo-STXM//2017```


## Create the guest data directory

Create a directory called **guest** in your data directory that you gave above in the app.ini file.

## Running a test 

You should now be able to cd to:

```<repo dir>/cls/applications/pyStxm```

and run pyStxm like this:

```>python runPyStxm.py```

## Documentation

The documentation for the software has been started and can be found here https://github.lightsource.ca/pages/cid/pyStxm3/

## Built With

* [Python](https://www.python.org/) - The open source programming used
* [Qt](https://www.qt.io/) - The open source application framework used
* [BlueSky] (https://nsls-ii.github.io/bluesky/) - Bluesky Data Collection Framework
* [Epics](http://www.aps.anl.gov/epics/) - The open source device and data acquisition control
* [Synapps] (https://www1.aps.anl.gov/bcda/synapps/) The device and data collection software the 


## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Author

* **Russ Berg** -  [pyStxm](https://github.clsi.ca/bergr/pyStxm)



## License

This project is licensed under the GPL2 License - see the [LICENSE.md](LICENSE.md) file for details







