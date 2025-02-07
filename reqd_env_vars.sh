#!/bin/bash

# this is the host name of th ecomputer that is running the DCS (Pixelator Controller)
export PYSTXM_DCS_HOST="MACHINE_NAME_HERE"

# This is the IP address of the computer that has the binary cnxvalidate on it, note this is only relevant for BlueSky configurations
# Pixelator configs save their own files
export CNXVALIDATE_HOST_IPADDR="IP ADDR HERE"
export PATH_TO_CNXVALIDATE="DIR PATH HERE"
#this is the IP addr of the computer that is running the NXserver, again only relevant for BlueSky configs
export NX_SERVER_HOST="IP ADDR HERE"

# this is the path to the directory that contains the nexus definitions cloned repo
export PATH_TO_NX_DEFINITIONS="PATH HERE"


# if pyStxm is run on windows then the path to the main data directory will needs to be specified here as a windows path
export PYSTXM_DATA_DIR="PATH HERE"
# this is the path used by the areaDetector plugin to save the data for tomography scans, NOTE:
export LINUX_DATA_DIR="PATH HERE"




