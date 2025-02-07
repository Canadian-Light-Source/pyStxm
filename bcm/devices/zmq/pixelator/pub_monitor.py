import zmq

def pub_monitor(host, port, ignore_detector=False):
    # Create a ZeroMQ context
    context = zmq.Context()

    # Create a SUB socket to subscribe to the PUB socket
    sub_socket = context.socket(zmq.SUB)

    # Connect to the PUB socket using the provided host and port
    sub_socket.connect(f"tcp://{host}:{port}")

    # Subscribe to all messages (empty string subscribes to all topics)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')

    print(f"Monitoring PUB socket at tcp://{host}:{port}...")
    j = 0
    while True:
        try:
            # Receive multipart message
            parts = []
            print(f"[{j}] WAITING FOR NEXT MESSAGE")
            #message_part = sub_socket.recv_string()
            parts = sub_socket.recv_multipart()
            # Check if this is the last part of the multipart message
            # if not sub_socket.getsockopt(zmq.RCVMORE):
            #     break
            msg_parts = []
            for idx, part in enumerate(parts):
                # dct = json.loads(part.decode('utf-8'))
                #print(f"message_parts={message_parts}")
                #print(f"Part {idx + 1}: {part.decode('utf-8')}")
                msg_parts.append(part.decode('utf-8'))

            if msg_parts[0].find('detectorValues') > -1 and ignore_detector:
                pass
            else:
                j += 1
                # Print each part of the multipart message
                print("Received multipart message:")
                for i, part in enumerate(msg_parts):
                    print(f"  Part {i+1}: {part}")

        except zmq.ZMQError as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    # Set the host and port dynamically
    HOST = "VOPI1610-005"  # Replace with the PUB socket host
    PORT = 56561        # Replace with the PUB socket port

    # Start the PUB socket monitor
    pub_monitor(HOST, PORT, ignore_detector=True)
