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

	This software is completely dependant on Epics for providing the connection to all positioners and counters as well 
    as the engine for doing scans. When the software is started a connection is made to all configured devices and 
    therefore the Epics side of the software must be running before attempting to start pyStxm.

	Next there is a second process called **nx_server** that must be running in order to save NeXus **nxstxm** files, 
	typically the nx_server process is running on a Windows or Linux computer that has a drive mapping to the base data 
	directory.
	
	To use pyStxm with BlueSky follow the instructions below under **Installing**.

	Then look at the **nx_server** section and get it running.


- **Pixelator with Epics or Tango**

	If running pyStxm with Pixelator then the Pixelator controller must be running and publishing/replying on default 
    ports 56561 and 56562 respectively and the data will be published on port 56563. The Pixelator controller is a 
    separate piece of software that is used to control the Pixelator server which is a device that controls the beamline 
    devices and the data acquisition process.
	
    To use pyStxm with Pixelator follow the instructions below for **Configure pyStxm with Pixelator**

--------------------------------------
### Installation

On the machine where you are going to run pyStxm:
1.	Install miniforge: https://conda-forge.org/download/
2.	```conda create -n pyStxm python=3.11.5```
3.  ```conda activate pyStxm```
4.	```git clone https://github.com/Canadian-Light-Source/pyStxm```
5.  ```cd pyStxm```
6.	```pip install -r requirements.txt```
7.	Edit the file ```reqd_env_vars.sh``` and set:
 
      ```shell
      # required for EPICS only, if using Pixelator only you can leave these as is
      export OPHYD_CONTROL_LAYER="caproto"

      # this is the host name of the computer that is running the DCS (Pixelator Controller)
      export DCS_HOST="IP ADDR HERE"
      export DCS_HOST_PROC_NAME="Pixelator"
      export DCS_SUB_PORT="56561"
      export DCS_REQ_PORT="56562"
      
      #this is the IP addr of the computer that is running the NXserver or Pixelator depending on your setup
      export DATA_SERVER_HOST="IP ADDR HERE"
      # this is the port that the data will be published on for pyStxm to display
      export DATA_SUB_PORT="56563"
      
      # this is the base path to the data
      # NOTE: for Pixelator this path must match the path configured in the Pixelator software settings.json file
      # for the entries `NeXusBaseDirectory` and `NeXusDiscardSubDirectory`
      export DATA_DIR="PATH HERE"
            
      # This is the IP address of the computer that has the binary cnxvalidate on it, 
      # note this is only relevant for BlueSky configurations
      export CNXVALIDATE_HOST_IPADDR="IP ADDR HERE"
      export PATH_TO_CNXVALIDATE="DIR PATH HERE"
      # this is the path to the directory that contains the nexus definitions cloned repo, Only needed if planning
      # to validate nexus files using cnxvalidate via pyStxm
      export PATH_TO_NX_DEFINITIONS="PATH HERE"

      ```
If your configuration is for BlueSky with Epics it will not actively use the information
in the DCS variables but they do need to exist.

8. Edit the `cls/applications/pyStxm/app.ini` file and set the **bl_config** to the configuration name that has been 
created for your beamline.

Example:
```shell
bl_config = sls_x07da_polLux
```

9. The display needs to support a resolution of 3840x2160, find out the name of the display:
Run xrandr and check its output:

      ```shell
      >xrandr
      Screen 0: minimum 256 x 256, current 3840 x 2160, maximum 16384 x 16384
      rdp0 connected primary 3840x2160+0+0 0mm x 0mm
      3840x2160     50.00*
      ```

      Here the display name is ```rdp0```
      If connecting over noMachine, edit the ```.bashrc``` file of the user account and add these at the bottom, 
      
      ```shell
      export QT_SCREEN_SCALE_FACTORS=1.0
      export QT_AUTO_SCREEN_SCALE_FACTOR=0
      export QT_SCALE_FACTOR=1.0
      xrandr --output rdp0 --mode 3840x2160
      ```
      
10.	To run pyStxm execute the file runpyStxm.sh:

      ```shell
        ./runpyStxm.sh
      ```

You should see the pyStxm splash screen come up as well as as see output on the console about devices that are being 
connected to. 
If the process appears to stop for a lengthy amount of time it is likely that pyStxm cannot see **PixelatorController** 
(Pixelator configurations) or **nx_server** (EPICS), make sure that the appropriate server is running and check that the
the ports used to publish match those for subscribing.

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
has a mount point to the data computer such that the ```/etc/fstab``` file contains the entry in its list of mount 
points.

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

1. First complete steps 1 through 7 above under **Installation**

2. Ensure that the pixelator settings file located in teh Pixelator config directory, specifies the same port numbers as 
above for the PUB, REP and data publishing sockets.

Open the settings.json file and check/add the following entries:

```json
  "publisherPort": 56561,
  "requestPort": 56562,
  "dataPublisherPort": 56563,
```
The _dataPublisherPort_ is used to send requested data to pyStxm from a threaded task in PixelatorController.

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

pyStxm should start up, If the process appears to stop for a lengthy amount of time it is likely that pyStxm cannot see 
the PixelatorController, make sure its running and that it is **PUB**lishing and **REP**lying on the port numbers that 
you entered in ```reqd_env_vars.sh```.

## Documentation

The documentation for the software has been started and will soon be available on github pages:

## Author

* **Russ Berg** -  [pyStxm](https://github.com/Canadian-Light-Source/pyStxm)


## License

This project is licensed under the GPL3 License - see the [LICENSE.md](LICENSE.md) file for details







