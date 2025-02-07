import threading
import zmq
import time
import queue


# Worker function that processes requests
def worker(worker_queue, result_queue):
    while True:
        # Get the task from the worker queue
        req_id, request_data = worker_queue.get()

        # Simulate time-consuming processing
        print(f"Worker is processing request: {request_data}")
        time.sleep(3)  # Simulate some processing delay

        # Create a response
        response = f"Processed data: {request_data}"

        # Put the result into the result queue with the corresponding request ID
        result_queue.put((req_id, response))


# Function that handles the REP socket
def zmq_REP_server():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5557")

    worker_queue = queue.Queue()
    result_queue = queue.Queue()

    # Start a few worker threads
    for _ in range(3):
        threading.Thread(target=worker, args=(worker_queue, result_queue), daemon=True).start()

    # Dictionary to store pending requests (maps request IDs to original request message)
    pending_requests = {}

    req_id = 0

    while True:
        try:
            # Non-blocking receive on the socket
            if socket.poll(timeout=100, flags=zmq.POLLIN):
                message = socket.recv_string()
                print(f"Received request: {message}")

                # Add the request to the worker queue with a unique req_id
                worker_queue.put((req_id, message))

                # Store the request so we can respond later
                pending_requests[req_id] = message
                req_id += 1

            # Check if any workers have completed their tasks
            try:
                completed_req_id, response = result_queue.get_nowait()
                if completed_req_id in pending_requests:
                    print(f"Sending response for request {completed_req_id}: {response}")
                    socket.send_string(response)

                    # Remove the completed request from pending_requests
                    del pending_requests[completed_req_id]
            except queue.Empty:
                # No completed tasks, continue
                pass

        except Exception as e:
            print(f"Error: {e}")
            break

    socket.close()
    context.term()


if __name__ == "__main__":
    zmq_REP_server()