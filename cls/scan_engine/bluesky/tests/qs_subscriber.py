from bluesky.callbacks.zmq import RemoteDispatcher

HOST1610001_addr = "<queue server ip addr here>"

d = RemoteDispatcher(f"{HOST1610001_addr}:5578")
d.subscribe(print)
print("starting to wait for msgs from queueserver on port 5578")
d.start()


