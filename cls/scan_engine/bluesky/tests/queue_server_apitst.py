from bluesky_queueserver_api import BPlan
from bluesky_queueserver_api.zmq import REManagerAPI
# from bluesky_queueserver_api.http import REManagerAPI
#     zmq_control_addr=None,
#     zmq_info_addr=None,
#     timeout_recv=default_zmq_request_timeout_recv,
#     timeout_send=default_zmq_request_timeout_send,
#     console_monitor_poll_timeout=default_console_monitor_poll_timeout,
#     console_monitor_max_msgs=default_console_monitor_max_msgs,
#     console_monitor_max_lines=default_console_monitor_max_lines,
#     zmq_public_key=None,
#     request_fail_exceptions=default_allow_request_fail_exceptions,
#     status_expiration_period=default_status_expiration_period,
#     status_polling_period=default_status_polling_period,
#
def open_env():
    print("opening and environment")
    is_now_open = False
    try:
        RM.environment_open()
        is_now_open = True
    except:
        RM.environment_close()

    if not is_now_open:
        try:
            RM.environment_open()
        except:
            RM.environment_close()
            exit()
    RM.wait_for_idle()

def add_item(item, plan_nm):
    print(f"adding a [{plan_nm}] plan to the QS")
    RM.item_add(item)

HOST1610001_addr = "<queue server host ip addr here>"
bs_qs_control = f"tcp://{HOST1610001_addr}:60615"

RM = REManagerAPI(zmq_control_addr=bs_qs_control)
RM.queue_clear()
#item = BPlan("count", ["det1", "det2"], num=10, delay=1)
#add_item(item, "count")
#scan(dets, posner, start, stop, npoints)
item2 = BPlan("scan", ["det1", "det2"], "motor1", -100, 100, 100)
add_item(item2, "scan")

#before we can add a script the environment must be open
open_env()


# # do_abs_scan(posner, start, stop, npoints, dets=[], md={}, display_only=False)
# load a scan that resides in the qserver startup directory
item3 = BPlan("do_abs_scan", posner="motor1", start=-500, stop=500, npoints=100, dets=["det1", "det2"], md={})
add_item(item3, "do_abs_scan")

# test sending a new plan over
with open("C:/controls/sandbox/pyStxm3/cls/scan_engine/bluesky/tests/qt5_tsts/bl_base/scans/qs_first_script.py") as f:
    s = f.read()
RM.script_upload(s, update_lists=True)
item4 = BPlan("do_abs_scan_from_uploaded_script", posner="motor1", start=-500, stop=500, npoints=100, dets=["det1", "det2"], md={'a different md': 'told ya'})
add_item(item4, "do_abs_scan_from_uploaded_script")

# # test sending a new plan over
# with open("C:/controls/sandbox/pyStxm3/cls/scan_engine/bluesky/tests/qt5_tsts/bl_base/scans/qs_single_posner.py") as f:
#     s = f.read()
# RM.script_upload(s, update_lists=True)
# # do_abs_scan(posner, start, stop, npoints, dets=[], md={}, display_only=False)
# item3 = BPlan("do_abs_scan", -500, 500, 100, ["det1", "det2"])
# add_item(item3, "do_abs_scan")

# close and re open the env so that the script we uploaded is included in list of available scans
#open_env()

print("calling start")
RM.queue_start()
RM.wait_for_idle()

print("checking status")
status = RM.status()
print(f"status={status}")

print("Closign the environment")
RM.environment_close()
print("waiting for idle")
RM.wait_for_idle()

print("calling close")
RM.close()
