import zmq
import json
from databroker import Broker
from cls.data_io import nxptycho
def main():
    # Prepare the ZeroMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)  # REP is for reply
    socket.bind("tcp://*:5555")  # Bind to port 5555

    print("Server is listening on port 5555...")
    db = Broker.named("pystxm_amb_bl10ID1")

    while True:
        # Wait for the next request from a client
        message = socket.recv()
        #print("Received request: %s" % message)

        # Deserialize the JSON message to a Python dictionary
        data = json.loads(message)
        print("Deserialized data:", data)

        # Do something with the data (here we  just print it)
        run_uids = data['run_uids']
        fprefix = data['fprefix']
        data_dir = data['data_dir']

        # Send a reply back to the client (optional)
        reply = json.dumps({"status": "received"})
        socket.send_string(reply)
        first_uid = run_uids[0]

        print("starting basic export [%s]" % first_uid)
        for _uid in run_uids:
            print("processing [%s]" % _uid)
            header = db[_uid]
            md = json.loads(header["start"]["metadata"])
            _img_idx_map = json.loads(md["img_idx_map"])
            primary_docs = header.documents(fill=True)
            nxptycho.export(
                primary_docs, data_dir, file_prefix=fprefix, first_uid=first_uid, aborted=False
            )
        # suit_nxstxm.finish_export(data_dir, fprefix, first_uid, is_stack_dir=is_stack)
        nxptycho.finish_export(data_dir, fprefix, first_uid)

if __name__ == "__main__":
    main()
