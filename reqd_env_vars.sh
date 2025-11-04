#!/bin/bash
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
export DATA_DIR="/tmp"

# This is the IP address of the computer that has the binary cnxvalidate on it,
# note this is only relevant for BlueSky configurations
export CNXVALIDATE_HOST_IPADDR="IP ADDR HERE"
export PATH_TO_CNXVALIDATE="DIR PATH HERE"
# this is the path to the directory that contains the nexus definitions cloned repo, Only needed if planning
# to validate nexus files using cnxvalidate via pyStxm
export PATH_TO_NX_DEFINITIONS="PATH HERE"