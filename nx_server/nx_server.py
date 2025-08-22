from databroker import Broker
import json
import os
import platform
import re
import sys
import zmq

#make sure that the applications modules can be found, used to depend on PYTHONPATH environ var
sys.path.append( os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") )

from cls.data_io import nxstxm
from cls.data_io import nxptycho
from cls.utils.enum_utils import Enum
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.utils.cfgparser import ConfigClass

from cls.data_io.nxstxm_h5_to_dict import load_nxstxm_file_to_h5_file_dct
from cls.utils.file_system_tools import master_get_seq_names

appConfig = ConfigClass(abs_path_to_ini_file)
MONGO_DB_NM = appConfig.get_value("MAIN", "mongo_db_nm")

if "COMPUTERNAME" in os.environ.keys():
    HOSTNAME = os.environ["COMPUTERNAME"]
else:
    HOSTNAME = "localhost"
PORT = 5555

NX_SERVER_CMNDS = Enum('save_files', 'remove_files', 'test_connection', 'is_windows', 'get_file_sequence_names',
                       'loadfile_directory', 'loadfile_file', 'loadfile_files', 'list_directory')
# save_files: Saves standard nxStxm files
# remove_files: removes a list of files, used by ptycho scan to remove garbage tifs that were created during pxp line transaltions
# test_connection: client can send a test connection msg
# is_windows: this allows the client to know what type of path to send to nx_server with all of the correct replacements done already

NX_SERVER_REPONSES = Enum('fail', 'success')


def get_data_subdirectories(directory, extension):
    """
    Returns a list of dicts for all subdirectories that contain at least one file with the given extension,
    ordered from most recent to least recent by modification time.
    Each dict contains 'sub_dir' and 'num_h5_files'.
    Handles missing directory gracefully.
    """
    result = []
    try:
        subdirs = [
            d for d in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, d))
        ]
        # Sort subdirs by modification time (most recent first)
        subdirs.sort(
            key=lambda d: os.path.getmtime(os.path.join(directory, d)),
            reverse=True
        )
        for d in subdirs:
            subdir_path = os.path.join(directory, d)
            num_files = len([
                f for f in os.listdir(subdir_path)
                if os.path.isfile(os.path.join(subdir_path, f)) and f.endswith(extension)
            ])
            result.append({'sub_dir': d, 'num_h5_files': num_files})
    except FileNotFoundError:
        pass
    return result

def get_files_with_extension_and_subdirs(directory, extension):
    """
    Returns a dictionary with the directory, fileExtension, and a list of files matching the extension.
    Handles missing directory gracefully.
    """
    try:
        #sub_dirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
        sub_dirs = [
            d for d in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, d)) and any(
                f.endswith(extension) and f.startswith(d)
                for f in os.listdir(os.path.join(directory, d))
                if os.path.isfile(os.path.join(directory, d, f))
            )
        ]

        files = [f for f in os.listdir(directory)
                 if os.path.isfile(os.path.join(directory, f)) and f.endswith(extension)]
    except FileNotFoundError:
        files = []
        sub_dirs = []
    return {
        "directories": sub_dirs,
        "directory": directory,
        "fileExtension": extension,
        "files": files,
        "showHidden": 1
    }

def gen_nx_server_dict(cmnd='', run_uids=[], fprefix='FPREFIX', data_dir='', nx_app_def='nxstxm', fpaths=[], cmd_args={})->dict:
    dct = {}
    dct['cmnd'] = cmnd
    dct['run_uids'] = run_uids
    dct['fprefix'] = fprefix
    dct['data_dir'] = data_dir
    dct['nx_app_def'] = nx_app_def
    dct['fpaths'] = fpaths
    dct['cmd_args'] = cmd_args
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
        print(f"determine_exporter: the NeXus application definition string [{nx_app_def}] is not supported")
        return None


def start_server(db_name, host=HOSTNAME, port=PORT, is_windows=True):
    """
    Note this server currently needs to run on the same machine as the mongodb service in order to access the
    """
    # Prepare the ZeroMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)  # REP is for reply
    socket.bind(f"tcp://*:{port}")  # Bind to port 5555

    db = Broker.named(db_name)
    if not db:
        print(f"[{HOSTNAME}]Unable to connect to the database [{db_name}]")
        exit(1)

    print(f"NX Server is running on host [{HOSTNAME}] and connected to database [{db_name}] listening on port {port}...")
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
                ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "msg": f"NX_SERVER[{HOSTNAME}], [{PORT}]:nxstxm: finished exporting [{data_dir}/{fprefix}.hdf5"})

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
            ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS})

        elif cmnd == NX_SERVER_CMNDS.IS_WINDOWS:
            if is_windows:
                ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS})
            else:
                ret_msg = json.dumps({"status": NX_SERVER_REPONSES.FAIL})

        #DCS server support
        elif cmnd == NX_SERVER_CMNDS.LOADFILE_DIRECTORY:
            print(f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: loadfile_directory called with data={data}")
            cmd_args = data['cmd_args']
            directory_dct = get_files_with_extension_and_subdirs(cmd_args['directory'], cmd_args['extension'])
            ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "directories": directory_dct})

        elif cmnd == NX_SERVER_CMNDS.LOADFILE_FILE:
            print(f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: loadfile_file called with data={data}")
            cmd_args = data['cmd_args']
            fname = cmd_args['file']
            jstr = load_nxstxm_file_to_h5_file_dct(fname, ret_as_jstr=True)
            ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "directories": jstr})

        elif cmnd == NX_SERVER_CMNDS.LOADFILE_FILES:
            print(f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: loadfile_files called with data={data}")
            cmd_args = data['cmd_args']
            data_lst = []
            for fname in cmd_args['files']:
                jstr = load_nxstxm_file_to_h5_file_dct(fname, ret_as_jstr=True)
                data_lst.append(jstr)

            ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "data_lst": data_lst})

        elif cmnd == NX_SERVER_CMNDS.LIST_DIRECTORY:
            print(f"\nNX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: list_directory called with data={data}")
            cmd_args = data['cmd_args']
            directory = cmd_args['directory']
            extension = cmd_args['fileExtension']
            ## subdirs_jstr = json.dumps(get_date_subdirectories(directory))
            # ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "sub_directories": subdirs_jstr})
            subdirs = get_data_subdirectories(directory, extension=extension)
            ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "sub_directories": subdirs})
            print(f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: list_directory returning ret_msg={ret_msg}\n")

        elif cmnd == NX_SERVER_CMNDS.GET_FILE_SEQUENCE_NAMES:
            print(f"NX_SERVER[{HOSTNAME}, {PORT}]:nxstxm: get_file_sequence_names called with data={data}")
            cmd_args = data['cmd_args']
            data_dir = cmd_args['data_dir']
            thumb_ext = cmd_args['thumb_ext']
            dat_ext = cmd_args['dat_ext']
            stack_dir = cmd_args['stack_dir']
            num_desired_datafiles = cmd_args['num_desired_datafiles']
            new_stack_dir = cmd_args['new_stack_dir']
            prefix_char = cmd_args['prefix_char']
            dev_backend = cmd_args['dev_backend']
            seq_names_dct = master_get_seq_names(data_dir=data_dir,
                                                 thumb_ext=thumb_ext,
                                                 dat_ext=dat_ext,
                                                 stack_dir=stack_dir,
                                                 num_desired_datafiles=num_desired_datafiles,
                                                 new_stack_dir=new_stack_dir,
                                                 prefix_char=prefix_char,
                                                 dev_backend=dev_backend,
                                                 )
            seq_name_jstr = json.dumps(seq_names_dct)
            ret_msg = json.dumps({"status": NX_SERVER_REPONSES.SUCCESS, "seq_name_jstr": seq_name_jstr})




        # Send a reply back to the client (optional)
        #reply = json.dumps({"status": ret_msg})
        socket.send_string(ret_msg)


if __name__ == "__main__":
    import sys

    _db_name = MONGO_DB_NM
    is_windows = check_os()

    start_server(_db_name, HOSTNAME, PORT, is_windows=is_windows)


