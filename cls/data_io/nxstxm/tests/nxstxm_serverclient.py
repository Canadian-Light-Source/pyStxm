import zmq
import json


def main():
    # Prepare the ZeroMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)  # REQ is for request
    socket.connect("tcp://localhost:5555")

    # Create a dictionary to send
    # data = {
    #     "name": "Alice",
    #     "age": 30
    # }
    run_uids = ('0f367d95-2b2b-434a-93af-22efc3634f60',
                 'f9b83f65-5586-4506-bdff-bce45c4582a7',
                 'd872a4cb-b728-4dd3-9286-ffed66ea8d84',
                 '4d8584bf-db85-433a-819f-61d95f20ee11',
                 'ad73f598-4035-4b47-a22f-066e670be1a9')
    fprefix = 'tester'
    data_dir = "C:/controls/sandbox/zmq_test/latest/data"
    data = {
        'fprefix': fprefix,
        'data_dir': data_dir,
        'run_uids': run_uids,
    }


    #for data in primary_docs:
    # Serialize the dictionary to JSON
    message = json.dumps(data)

    # Send the message to the server
    #print("Sending request:", message)
    socket.send_string(message)

    # Wait for the reply from the server
    reply = socket.recv()
    print("Received reply:", reply)



if __name__ == "__main__":
    main()
