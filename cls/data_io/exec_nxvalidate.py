import os
import time
import paramiko
import pathlib

from cls.utils.environment import get_environ_var

CNXVALIDATE_HOST_IPADDR = get_environ_var('CNXVALIDATE_HOST_IPADDR')
PATH_TO_CNXVALIDATE = get_environ_var('PATH_TO_CNXVALIDATE')
PATH_TO_NX_DEFINITIONS = get_environ_var('PATH_TO_NX_DEFINITIONS')

def validate_nxstxm_file(fpath, uname, pword):
    # ensure proper path separaters
    winpath = pathlib.Path(fpath)
    i = 0
    while (not winpath.exists()) and (i < 500):
        #print(f"validate_nxstxm_file: [{i}] waiting 0.1")
        time.sleep(0.1)
        i += 1
    if i >= 500:
        print("validate_nxstxm_file: timed out waiting for file to exist")
        return

    #get windows drive letter and replace with hardcded (for now) path to validator
    # driver_letter = fpath[0]
    print(f"validate_nxstxm_file: waiting for [{fpath}] to exist in order to validate")
    pl_fpath = pathlib.Path(fpath)
    pos_path = pl_fpath.as_posix()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(f"{CNXVALIDATE_HOST_IPADDR}", username=uname, password=pword)

    # nxvalidate -l /home/bergr/nexus/nexusformat/definitions/ NXarchive.h5
    stdin, stdout, stderr = client.exec_command(
        f"{PATH_TO_CNXVALIDATE}/nxvalidate -l {PATH_TO_NX_DEFINITIONS}/nexusformat/definitions/ {pos_path}"
    )

    for line in stdout:
        print(line.strip("\n"))

    client.close()


if __name__ == "__main__":
    validate_nxstxm_file(
        "/tmp/NXarchive.h5",
        "",
    )
