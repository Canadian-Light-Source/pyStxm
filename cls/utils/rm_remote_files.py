

import socket


# List of file paths to send
#
def remove_remote_files(remote_host, file_paths, port):
    # Send the file paths to the server
    for fstr in file_paths:
        # Define the server address and port
        server_address = (remote_host, port)  # Change to your desired server address and port

        # Create a socket and connect to the server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(server_address)
        try:
            print(f"remove_remote_files: sending [{fstr}]")
            client_socket.sendall(fstr.encode())
            #client_socket.sendall(b'\n')
            client_socket.close()
        finally:
            # Close the socket
            client_socket.close()

def break_paths_into_send_sized_strs(fpath_lst):
    """
    take a list of file paths and create strings that are less than 1024 bytes long and contain
    complete file paths
    """
    fstrs_lst = []
    s = ""
    for fp in fpath_lst:
        fp_len = len(fp)
        if len(s) < (1024 - fp_len):
            s += fp + "\n"
        else:
            fstrs_lst.append(s)
            s = fp + "\n"
    fstrs_lst.append(s)
    return(fstrs_lst)

if __name__ == '__main__':
    file_paths = ["/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000010.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000021.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000032.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000043.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000054.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000065.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000076.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000087.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000098.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000109.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000110.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000111.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000112.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000113.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000114.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000115.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000116.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000117.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000118.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000119.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000120.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/00_00/B230914005_000121.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000131.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000142.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000153.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000164.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000175.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000186.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000197.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000208.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000219.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000230.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000231.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000232.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000233.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000234.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000235.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000236.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000237.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000238.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000239.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000240.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000241.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/01_00/B230914005_000242.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000252.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000263.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000274.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000285.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000296.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000307.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000318.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000329.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000340.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000351.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000352.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000353.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000354.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000355.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000356.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000357.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000358.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000359.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000360.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000361.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000362.h5",
            "/opt/ASTXM_upgrade_tmp/guest/0914/B230914005/02_00/B230914005_000363.h5"]


    fstrs = break_paths_into_send_sized_strs(file_paths)
    remove_remote_files(remote_host="IOC1610-310",file_paths=fstrs,port=5066)

