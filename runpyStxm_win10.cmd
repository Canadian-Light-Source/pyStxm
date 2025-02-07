@echo on
set PATH=C:\controls\Anaconda3\shell\condabin;C:\Perl\bin;%EXTS%\bin\win32-x86;%LOC%\bin\win32-x86;C:\controls\EPICS Windows Tools;%PATH%

REM Set the path to your Anaconda/Miniconda installation
set CONDA_PATH=C:\controls\Anaconda3

REM Activate the desired Conda environment
call "%CONDA_PATH%\Scripts\activate.bat" pyStxm310



REM Navigate to the desired directory
cd cls\applications\pyStxm

REM Run the Python script
python runPyStxm.py

REM Deactivate the Conda environment (optional)
call "%CONDA_PATH%\Scripts\deactivate.bat"


