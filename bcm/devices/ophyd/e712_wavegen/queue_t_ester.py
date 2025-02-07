

import threading
import queue

q = queue.Queue()

def worker():
    abort = False
    while not abort:
        while not q.empty():
            item = q.get()
            print(f'Working on {item}')
            print(f'Finished {item}')
            if item == 'abort':
                abort = True
            q.task_done()

# Turn-on the worker thread.
threading.Thread(target=worker, daemon=True).start()

# Send thirty task requests to the worker.
i = 0
for item in range(30):
    q.put(list(range(i,i+50)))
    i += 50

q.put("abort")

# Block until all tasks are done.
q.join()
print('All work completed')
