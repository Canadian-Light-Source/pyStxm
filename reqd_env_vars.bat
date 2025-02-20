:: @echo off
:: this is the host name of th ecomputer that is running the DCS (Pixelator Controller)
set DCS_HOST="localhost"
set DCS_HOST_PROC_NAME="Pixelator"
set DCS_SUB_PORT="56561"
set DCS_REQ_PORT="56562"

:: This is the IP address of the computer that has the binary cnxvalidate on it, note this is only relevant for BlueSky configurations
:: Pixelator configs save their own files
set CNXVALIDATE_HOST_IPADDR="IP ADDR HERE"
set PATH_TO_CNXVALIDATE="DIR PATH HERE"
:: this is the path to the directory that contains the nexus definitions cloned repo
set PATH_TO_NX_DEFINITIONS="PATH HERE"


:: this is the IP addr of the computer that is running the NXserver, again only relevant for BlueSky configs
set NX_SERVER_HOST="IP ADDR HERE"


:: if pyStxm is run on windows then the path to the main data directory will needs to be specified here as a windows path
set PYSTXM_DATA_DIR="c:\tmp"
:: this is the path used by the areaDetector plugin to save the data for tomography scans, NOTE:
set LINUX_DATA_DIR="/tmp"