@echo on
DOSKEY ls=dir
DOSKEY cd=cd $1$Tdir
DOSKEY cdb=cd C:\controls\epics\R7\base
DOSKEY cdl=cd C:\controls\epics\R7\local\src
DOSKEY cde=cd C:\controls\epics\R7\extensions
DOSKEY cds=cd C:\controls\epics\R7\modules\support

set PYTHONPATH=%CD%

set EPICS_BASE=C:\controls\epics\R7\base
set PATH=%EPICS_BASE%\bin\windows-x64-mingw;%PATH%
set EPICS_HOST_ARCH=windows-x64-mingw

set BASE=C:\controls\epics\R7\base
set MODS=C:\controls\epics\R7\modules\support
set EXTS=C:\controls\epics\R7\extensions
set LOC=C:\controls\epics\R7\local

set C:\GnuWin32\bin;C:\Perl\bin;%EXTS%\bin\windows-x64;%LOC%\bin\windows-x64-mingw;C:\controls\EPICS Windows Tools;%PATH%
set PATH=%MODS%/asyn-4-21/bin/windows-x64-mingw4;%PATH%

cd %CD%\cls\data_io
C:\controls\anaconda3\envs\pyStxm310\python.exe %CD%\nx_server.py

