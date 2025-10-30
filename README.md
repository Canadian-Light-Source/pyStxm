# pyStxm
python Qt software for STXM data acquisition, this application was originally put together to perform data collection 
on the UHV STXM at the SM beam line (10ID1) at the CLS. The application uses several main frameworks to deliver the 
data collection capability, namely:
 
* Python >=3.10, The open source programming used
* Qt5, The open source application framework used

If using the Bluesky data collection framework then the following are also required:
* Epics, R7, The open source distributed control system
* BlueSky, 1.12.0, Bluesky Data Collection Framework 
* Synapps 5.7, The device and data collection software
* PyEpics 3, The connection to the DCS from the python side


There is a second part to this software and that is the SynApps Epics applications that provide the low level device 
control, namely:
	
- **motor**: to provide the positioner control


## Getting Started

pyStxm can be configured to connect to two different types of data acquisition systems, namely:

- **BlueSky with Epics**

	This software is completely dependant on Epics for providing the connection to all positioners and counters as well as 
	the engine for doing scans. When the software is started a connection is made to all configured devices and therefore 
	the Epics side of the software must be running before attempting to start pyStxm.

	Next there is a second process called **nx_server** that must be running in order to save NeXus **nxstxm** files, 
	typically the nx_server process is running on a Windows or Linux computer that has a drive mapping to the base data 
	directory.
	
	To use pyStxm with BlueSky follow the instructions below under **Installing**.

	Then look at the **nx_server** section and get it running.


- **Pixelator with Epics or Tango**

	If running pyStxm with Pixelator then the Pixelator controller must be running and publishing/replying on ports 56561 
	and 56562 respectively. The Pixelator controller is a separate piece of software that is used to control the Pixelator
	server which is a device that controls the beamline devices and the data acquisition process.
	
	To use pyStxm with Pixelator follow the instructions below for **Configure pyStxm with Pixelator**

--------------------------------------
### Installing

On the machine where you are going to run pyStxm:
1.	Install miniforge: https://conda-forge.org/download/
2.	```conda create -n pyStxm python=3.11.5```
3.	```git clone https://github.com/Canadian-Light-Source/pyStxm```
4.	```pip install -r requirements.txt```
5.	Edit the file ```reqd_env_vars.sh``` and set:
 
      ```shell
      export DCS_HOST="localhost"
      export DCS_HOST_PROC_NAME="Pixelator"
      export DCS_SUB_PORT="55561"
      export DCS_REQ_PORT="55562"
      export DATA_SUB_PORT="55563"
      
      export PYSTXM_DATA_DIR =”/tmp”
      export LINUX_DATA_DIR =”/tmp”
      ```
The rest you can leave as is. If your configuration is for BlueSky with Epics it will not actively use the information
in the DCS variables but they do need to exist.

The reason for the two data directories is because pyStxm can run on Windows OS and if it is configured for BlueSky 
then pyStxm needs to send the process that saves the files (nx_server) the paths to the data files. A Pixelator 
configuration does not use nx_server so just set both ```PYSTXM_DATA_DIR``` and ```LINUX_DATA_DIR``` to the same 
location of where Pixelator will be saving the data.

6.	The display needs to support a resolution of 3840x2160, find out the name of the display:
Run xrandr and check its output:

      ```shell
      >xrandr
      Screen 0: minimum 256 x 256, current 3840 x 2160, maximum 16384 x 16384
      rdp0 connected primary 3840x2160+0+0 0mm x 0mm
      3840x2160     50.00*
      ```

      Here the display name is ```rdp0```
      If connecting over noMachine, edit the ```.bashrc``` file of the user account and add these at the bottom, 
      
      NOTE you need the path to the ```reqd_env_vars.sh``` file you edited earlier:
      
      ```shell
      export QT_SCREEN_SCALE_FACTORS=1.0
      export QT_AUTO_SCREEN_SCALE_FACTOR=0
      export QT_SCALE_FACTOR=1.0
      xrandr --output rdp0 --mode 3840x2160
      source /home/control/github/pyStxm/reqd_env_vars.sh
      ```
      
7.	to run pyStxm execute the file runpyStxm.sh:

      ```shell
        ./runpyStxm.sh
      ```

You should see the pyStxm splash screen come up as well as as see output on the console about devices that are being 
connected to. 
If the process appears to stop for a lengthy amount of time it is likely that pyStxm cannot see the Pixelator 
Controller, make sure its running and that it is **PUB**lishing on port ```56561``` and **REP**lying on port ```56562```.

--------------------------------------
## nx_server ```(BlueSky with Epics only)```

**nx_server** should be setup to run as a service on a linux machine so the server can be stopped and started from 
there using the **systemctl** command.

The service runs a python file ```nx_server.py```
it opens a zmq socket and receives data from an instance of pyStxm 
in the form of a serialized dict, 

the service is used to:
- save nexus nxstxm and nxptyho files
- remove garbage tiff files following a ptychography scan
- respond to pyStxm if the service is running or not
- respond back if the service is running on linux or windows
  (so that the instance of pyStxm can determine the appropriate data_dir format)

The nx_server service must be installed on a computer that 
has a mount point to the data computer such that the ```/etc/fstab``` file contains the entry in its list of mount points.

**Service Commands**:

    - Enable the service: 
        >sudo systemctl enable nx_server
    - Force a reload of the service file:
        >sudo systemctl daemon-reload
    - Start the service:
        >sudo systemctl start nx_server.service  
    - Check the status:
        >sudo systemctl status nx_server.service
    - View the output of the nx_server.py file:
        >sudo journalctl -u nx_server -f 
    - Stop the service:
        >sudo systemctl stop nx_server.service 
    - Restart the service:
        >sudo systemctl restart nx_server.service 


--------------------------------------
### Configure pyStxm with Pixelator

1. First complete steps 1 through 6 above under **Installing**

2. Edit the file ```reqd_env_vars.sh``` and modify the following variables to your Pixelator settings:
 
      ```shell
      export DCS_HOST="localhost"
      export DCS_HOST_PROC_NAME="Pixelator"
      export DCS_SUB_PORT="56561"
      export DCS_REQ_PORT="56562"
      ```

   
3. If Pixelator is running on the same machine as ```pyStxm``` **then you can skip this step**.


If Pixelator is going to run on a different machine than ```pyStxm```, setup port forwarding for 56561 and 56562:

- if Jump server is used (example with 3 jump servers):
  ```shell
  ssh -J <user>@<jump server 1>,<user>@<jump server 2>,<user>@<jump server 3> <user>@<pixelator server> -L 56561:localhost:56561 -L 56562:localhost:56562
  ```
- else if no jump server:
  ```shell
  ssh <user>@<Pixelator server> -L 56561:localhost:56561 -L 56562:localhost:56562
  ```



4. run pyStxm execute the file runpyStxm.sh:
    ```shell
      >./runpyStxm.sh
    ```

pyStxm should start up, If the process appears to stop for a lengthy amount of time it is likely that pyStxm cannot see the Pixelator 
Controller, make sure its running and that it is **PUB**lishing and **REP**lying on the port numbers that you entered
in ```reqd_env_vars.sh```.

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



## Documentation

The documentation for the software has been started and will soon be available on github pages:

## Built With

* [Python](https://www.python.org/) - The open source programming used
* [Qt](https://www.qt.io/) - The open source application framework used
* [BlueSky](https://nsls-ii.github.io/bluesky/) - Bluesky Data Collection Framework
* [Epics](http://www.aps.anl.gov/epics/) - The open source device and data acquisition control
* [Synapps](https://www1.aps.anl.gov/bcda/synapps/) The device and data collection software the 


## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Author

* **Russ Berg** -  [pyStxm](https://github.com/Canadian-Light-Source/pyStxm)


## License

This project is licensed under the GPL3 License - see the [LICENSE.md](LICENSE.md) file for details







