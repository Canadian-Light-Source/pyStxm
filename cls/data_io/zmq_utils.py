import zmq
import json

from nx_server.nx_server import gen_nx_server_dict

def send_to_server(cmnd, run_uids=[], fprefix='', data_dir='', nx_app_def=None, fpaths=[],host='localhost',port='5555',verbose=False, cmd_args={}):
    """
    This function creates a zmq connecttion to the nxstxm_server
    and passes it serialized data in the form of:
        run_uids: a list of strings containsing the uid for the run as returned from the RE
        fprefix: a string representing the file prefix ex: A240526003
        data_dir: the string of the path to the data directory
    ex:
        run_uids = ('0f367d95-2b2b-434a-93af-22efc3634f60',
                     'f9b83f65-5586-4506-bdff-bce45c4582a7',
                     'd872a4cb-b728-4dd3-9286-ffed66ea8d84',
                     '4d8584bf-db85-433a-819f-61d95f20ee11',
                     'ad73f598-4035-4b47-a22f-066e670be1a9')
        fprefix = 'tester'
        data_dir = "C:/controls/sandbox/zmq_test/latest/data"
    """
    try:
        # Prepare the ZeroMQ context and socket
        context = zmq.Context()
        socket = context.socket(zmq.REQ)  # REQ is for request
        socket.connect(f"tcp://{host}:{port}")

        # Set the send timeout to 5 seconds (5000 milliseconds)
        socket.setsockopt(zmq.SNDTIMEO, 5000)
        socket.setsockopt(zmq.RCVTIMEO, 5000)

        data = gen_nx_server_dict(cmnd=cmnd, run_uids=run_uids,fprefix=fprefix,data_dir=data_dir,nx_app_def=nx_app_def,
                                  fpaths=fpaths, cmd_args=cmd_args)

        # Serialize the dictionary to JSON
        message = json.dumps(data)

        # Send the message to the server
        if verbose:
            print("Sending request:", message)
        socket.send_string(message)

        # Wait for the reply from the server
        reply = socket.recv()
        if verbose:
            print("Received reply:", reply)

        return reply

    except zmq.ZMQError as e:
        if e.errno == zmq.EAGAIN:
            print("\tERROR: Send operation timed out.")
            print(f"\tERROR: Check host [{host}] port [{port}] and make sure that mongodb is running")
        else:
            print(f"\tERROR: An unexpected error occurred: {e}")
        return -1



