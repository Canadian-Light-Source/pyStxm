@echo on
DOSKEY ls=dir
DOSKEY cd=cd $1$Tdir
DOSKEY cdb=cd C:\controls\epics\R7\base
DOSKEY cdl=cd C:\controls\epics\R7\local\src
DOSKEY cde=cd C:\controls\epics\R7\extensions
DOSKEY cds=cd C:\controls\epics\R7\modules\support

DOSKEY cdmotor=cd C:\controls\epics\R7\modules\support\motor-6-8
DOSKEY cddaq=cd C:\controls\epics\R7\local\src\daqmx_asynPortDriver
DOSKEY cdsscan=cd C:\controls\epics\R7\modules\support\sscan-2-9

set EPICS_BASE=C:\controls\epics\R7\base
set PATH=%EPICS_BASE%\bin\windows-x64-mingw;%PATH%
set EPICS_HOST_ARCH=windows-x64-mingw

set BASE=C:\controls\epics\R7\base
set MODS=C:\controls\epics\R7\modules\support
set EXTS=C:\controls\epics\R7\extensions
set LOC=C:\controls\epics\R7\local

set C:\GnuWin32\bin;C:\Perl\bin;%EXTS%\bin\windows-x64-mingw;%LOC%\bin\windows-x64-mingw;%PATH%
set PATH=%MODS%/asyn-4-21/bin/windows-x64-mingw;%PATH%;


set CONDAPATH=C:\controls\Anaconda3
rem Define here the name of the environment
set ENVNAME=pySTXM
rem The following command activates the base environment.
rem call C:\ProgramData\Miniconda3\Scripts\activate.bat C:\ProgramData\Miniconda3
if %ENVNAME%==base (set ENVPATH=%CONDAPATH%) else (set ENVPATH=%CONDAPATH%\envs\%ENVNAME%)

rem Activate the conda environment
rem Using call is required here, see: https://stackoverflow.com/questions/24678144/conda-environments-and-bat-files
call %CONDAPATH%\Scripts\activate.bat %ENVPATH%

set PYTHONPATH=%CD%

cd cls\applications\pyStxm\widgets
C:\controls\Anaconda3\envs\pySTXM\pythonw.exe epics_interferometer_voltages.py


