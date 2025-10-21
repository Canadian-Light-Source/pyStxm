#!/bin/bash

export OPHYD_CONTROL_LAYER="caproto"

# this is the host name of th ecomputer that is running the DCS (Pixelator Controller)
export DCS_HOST="localhost"
export DCS_HOST_PROC_NAME="Pixelator"
export DCS_SUB_PORT="56561"
export DCS_REQ_PORT="56562"

# This is the IP address of the computer that has the binary cnxvalidate on it, note this is only relevant for BlueSky configurations
# Pixelator configs save their own files
export CNXVALIDATE_HOST_IPADDR="IP ADDR HERE"
export PATH_TO_CNXVALIDATE="DIR PATH HERE"
#this is the IP addr of the computer that is running the NXserver, again only relevant for BlueSky configs
export NX_SERVER_HOST="10.52.32.38"
export DATA_SERVER_HOST="10.52.32.38"


# this is the path to the directory that contains the nexus definitions cloned repo
export PATH_TO_NX_DEFINITIONS="PATH HERE"


# if pyStxm is run on windows then the path to the main data directory will needs to be specified here as a windows path
export PYSTXM_DATA_DIR="/beamlinedata/SM/operations/STXM-data/ASTXM_upgrade_tmp/2025"
# this is the path used by the areaDetector plugin to save the data for tomography scans, NOTE:
export LINUX_DATA_DIR="/beamlinedata/SM/operations/STXM-data/ASTXM_upgrade_tmp/2025"




