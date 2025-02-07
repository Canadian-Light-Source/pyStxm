import sys
import os
import platform
import zmq
import json
from databroker import Broker

#make sure that the applications modules can be found, used to depend on PYTHONPATH environ var
sys.path.append( os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") )

from cls.data_io import nxstxm
from cls.data_io import nxptycho
from cls.utils.enum_utils import Enum
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.utils.cfgparser import ConfigClass

appConfig = ConfigClass(abs_path_to_ini_file)
MONGO_DB_NM = appConfig.get_value("MAIN", "mongo_db_nm")
HOST = 'localhost'
if "COMPUTERNAME" in os.environ.keys():
    HOSTNAME = os.environ["COMPUTERNAME"]
else:
    HOSTNAME = "NONE_SPECIFIED"
PORT = 5555

NX_SERVER_CMNDS = Enum('save_files', 'remove_files', 'test_connection', 'is_windows')
# save_files: Saves standard nxStxm files
# remove_files: removes a list of files, used by ptycho scan to remove garbage tifs that were created during pxp line transaltions
# test_connection: client can send a test connection msg
# is_windows: this allows the client to know what type of path to send to nx_server with all of the correct replacements done already

NX_SERVER_REPONSES = Enum('fail', 'success')


def gen_nx_server_dict(cmnd='', run_uids=[], fprefix='FPREFIX', data_dir='', nx_app_def='nxstxm', fpaths=[])->dict:
    dct = {}
    dct['cmnd'] = cmnd
    dct['run_uids'] = run_uids
    dct['fprefix'] = fprefix
    dct['data_dir'] = data_dir
    dct['nx_app_def'] = nx_app_def
    dct['fpaths'] = fpaths
    return dct


def check_os():
    """
    currently this process is only supported on windows as the file paths it expects to receive are windows only

    ToDo: implement this for Linux and somehow inform clients that
    """
    return platform.system() == "Windows"


def determine_exporter(nx_app_def):
    """
    take the Nexus application definition specified in received data and return the correct exporter module
    """
    if nx_app_def.lower().find("nxstxm") > -1:
        return nxstxm
    elif nx_app_def.lower().find("nxptycho") > -1:
        return nxptycho
    else:
        print(f"determine_exporter: the NExus application definition string [{nx_app_def}] is not supported")
        return None


def start_server(db_name, host=HOST, port=PORT, is_windows=True):
    """
    Note this server currently needs to run on the same machine as the mongodb service in order to access the
    """
    # Prepare the ZeroMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)  # REP is for reply
    socket.bind(f"tcp://*:{port}")  # Bind to port 5555

    # db = Broker.named("pystxm_amb_bl10ID1")
    db = Broker.named(db_name)
    if not db:
        print(f"[{HOSTNAME}]Unable to connect to the database [{db_name}]")
        exit(1)

    print(f"NX Server is running on host [{HOST}, {HOSTNAME}] and connected to database [{db_name}] listening on port {port}...")
    while True:
        # Wait for the next request from a client
        message = socket.recv()
        # print("Received request: %s" % message)

        # Deserialize the JSON message to a Python dictionary
        data = json.loads(message)
        print(f"\t[{HOSTNAME}, {PORT}]Deserialized data:", data)

        # Do something with the data (here we  just print it)
        cmnd = data['cmnd']
        run_uids = data['run_uids']
        fprefix = data['fprefix']
        data_dir = data['data_dir']
        nx_app_def = data['nx_app_def']
        if cmnd == NX_SERVER_CMNDS.SAVE_FILES:
            ret_msg = ''
            exporter = determine_exporter(nx_app_def)
            if exporter:
                first_uid = run_uids[0]
                last_uid = run_uids[-1]
                print(f"starting export of {nx_app_def}  file with uid[{first_uid}]")
                for _uid in run_uids:
                    print("processing [%s]" % _uid)
                    header = db[_uid]
                    md = json.loads(header["start"]["metadata"])
                    _img_idx_map = json.loads(md["img_idx_map"])
                    primary_docs = header.documents(fill=True)
                    exporter.export(
                        primary_docs, data_dir, file_prefix=fprefix, first_uid=first_uid, last_uid=last_uid, aborted=False
                    )
                exporter.finish_export(data_dir, fprefix, first_uid)
                ret_msg = f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: finished exporting [{data_dir}/{fprefix}.hdf5"

        elif cmnd == NX_SERVER_CMNDS.REMOVE_FILES:
            # ToDo: implement removal of files
            # used by ptycho scan
            fpaths = data['fpaths']
            # remove the files
            rm_files = []
            for f in fpaths:
                fpath = os.path.join(data_dir, f)
                if os.path.exists(fpath):
                    rm_files.append(fpath)
                    os.remove(fpath)
                    print(f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: Removed the following file [{fpath}]")
            ret_msg = f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: Removed {len(rm_files)} files"
            print(ret_msg)

        elif cmnd == NX_SERVER_CMNDS.TEST_CONNECTION:
            ret_msg = NX_SERVER_REPONSES.SUCCESS

        elif cmnd == NX_SERVER_CMNDS.IS_WINDOWS:
            if is_windows:
                ret_msg = NX_SERVER_REPONSES.SUCCESS
            else:
                ret_msg = NX_SERVER_REPONSES.FAIL

        # Send a reply back to the client (optional)
        reply = json.dumps({"status": ret_msg})
        socket.send_string(reply)


if __name__ == "__main__":
    import sys

    _db_name = MONGO_DB_NM
    is_windows = check_os()

    start_server(_db_name, HOST, PORT, is_windows=is_windows)


