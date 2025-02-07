import argparse
import threading
import signal
import time
import socket
import struct
import epics
import os

import Queue as queue

PORT_CA_PROTO_SEARCH = 5064
HDR_LEN = 16


def get_ip_key(ip_addr):
    if isinstance(ip_addr, int):
        return ip_addr

    try:
        ip_key = struct.unpack("!I", socket.inet_aton(ip_addr))[0]
        # print("RESULT: %s ->%s " % (repr(ip_addr), repr(ip_key)))
        return int(ip_key)

    except Exception as err:
        print("EXCEPTION: %s ip_addr: %s" % (repr(err), repr(ip_addr)))


class Listen(object):

    def __init__(self, params):

        self._failed = False
        self._count_packets = 0
        self._count_requests = 0
        self._queue = queue.Queue()
        self._start_time = None
        self._port_to_pid_map = {}
        self._process_done_flag = False
        self._count_since_log = 0
        self._read_netstat_flag = False
        self._extended_banner_flag = False
        self._pvs = {}

        if params.ioc is None:
            hostname = socket.gethostname()
            self._read_netstat_flag = True
            self._extended_banner_flag = True
            # print("No IOC specified (-i); using localhost: %s" % hostname)
        else:
            hostname = params.ioc
            # TODO: verify that this listening host on same VLAN as target

        try:
            ip_addr = socket.gethostbyname(hostname)
        except Exception as err:
            print("Could not determine IP address for: %s" % hostname)
            self._failed = True
            return

        self._ip_address = ip_addr
        self._hostname = hostname

        self._ip_key = get_ip_key(ip_addr)

        # print("IOC: %s IP Address: %s key: %d" % (hostname, ip_addr, self._ip_key))

        self._listen_thread_req = threading.Timer(0, self.worker_listen_req)

        self._process_thread = threading.Timer(0, self.worker_process)
        self._terminate = False

        signal.signal(signal.SIGINT, self.handle_SIGINT)
        signal.signal(signal.SIGTERM, self.handle_SIGINT)

    def read_netstat(self):
        output = os.popen("netstat -eapn")
        # print(x)
        # print("type: %s" % type(output))

        lines = output.readlines()
        output.close()

        for line in lines:
            line = line.strip()

            # print("LINE: %s" % line.strip())

            parts = line.split(" ")
            real_parts = []
            for part in parts:
                if len(part) == 0: continue
                real_parts.append(part.strip())

            # print("real_parts: ===%d==== %s" % (len(real_parts), repr(real_parts)))
            if real_parts[0] != 'tcp' and real_parts[0] != 'udp':
                continue

            addr = real_parts[3]

            try:
                if real_parts[0] == 'tcp':
                    process = real_parts[8]
                else:
                    process = real_parts[7]

            except:
                print("FAILED: %s" % real_parts)

                raise ValueError("temp stop")
            # print("ADDRESS: %s PROCESS: %s" % (addr, process))

            addr_parts = addr.split(":")
            port = addr_parts[1]

            process_parts = process.split("/")
            pid = process_parts[0]

            try:
                port = int(port)
            except:
                # print("ERROR: invalid port: %s" % repr(port))
                port = None

            if port is None:
                continue

            try:
                pid = int(pid)
            except:
                pid = None

            # print("PORT: %d PID: %s" % (port, repr(pid)))

            if self._port_to_pid_map.has_key(port):
                # print("WARNING: already know about port: %d" % port)
                continue

            self._port_to_pid_map[port] = pid

    def start(self):
        if self._failed: return

        self._start_time = time.time()
        self._listen_thread_req.start()
        self._process_thread.start()

    def run(self):
        if self._failed: return

        count = 8

        while not self._terminate:
            # log.dbg(0, "running")
            time.sleep(1)
            count += 1

            if count >= 10:

                if self._count_since_log > 0:
                    self._count_since_log = 0
                else:
                    print("CA_PROTO_SEARCH Packets: %d PVs: %s (CTRL-C to quit)" %
                          (self._count_packets, self._count_requests))

                count = 0

        # Wait for all captured requests to be printed
        while not self._process_done_flag:
            time.sleep(0.1)

        self.display_pvs()
        self.display_ports()
        # self.check_pvs()

    def check_pvs(self):

        count = 0
        total = len(self._pvs)

        for pv_name, pv_data in self._pvs.items():
            req = pv_data.get('c')
            v = epics.caget(pv_name, timeout=0.5)
            print("%d/%d   PV: %s: (%d) %s" % (count, total, pv_name, req, repr(v)))
            count += 1

    def display_pvs(self):

        total = 0
        count_1_req = 0

        print("")

        print("Most Requested PVs (PVs with 1 request not listed)")
        print("-" * 80)

        # Sort the results by number of requests
        x = [(pv_data.get('c', 0), pv_name) for pv_name, pv_data in self._pvs.items()]
        x.sort()
        # x.reverse()

        elapsed_time = time.time() - self._start_time

        for item in x:
            count = item[0]
            if count < 2:
                count_1_req += 1
                continue

            pv_name = item[1]

            # try:
            #     result = epics.caget(pv_name, timeout=0.1)
            #     if result is not None:
            #         print("result: %s" % repr(result))
            #         info = epics.cainfo(pv_name, print_out=False)
            #         print("INFO: %s" % repr(info))
            #
            # except Exception as err:
            #     print("EXCEPTION --------- %s" % repr(err))

            req_per_minute = 60.0 * count / elapsed_time
            port_str = self.make_port_string(pv_name)
            print("PV: {:50s} Req: {:5d} ({:3.2f}/min)   Ports: {:s}".format(pv_name, item[0], req_per_minute, port_str))

        req_per_sec = self._count_requests / elapsed_time

        print("")
        print("PVs requested more than once:    %d" % (len(x) - count_1_req))
        print("PVs requested once:              %d" % count_1_req)
        print("Requests Total:                  %d" % self._count_requests)
        print("Requests/sec:                    %.3f" % req_per_sec)

    def display_ports(self):

        if len(self._pvs) == 0:
            return

        if self._read_netstat_flag:
            self.read_netstat()

        # print("-"*80)
        print("")

        try:
            input("Press ENTER for Most Active Ports...")
        except:
            pass

        # print("Most Active Ports")
        # print("-"*80)

        port_dict = {}

        for pv_name, pv_data in self._pvs.items():
            port_data = pv_data.get('p', {})
            for port, count in port_data.iteritems():
                port_count = port_dict.get(port, 0)
                port_count += count
                port_dict[port] = port_count

        x = [(count, port) for port, count in port_dict.items()]

        x.sort()
        x.reverse()

        for item in x:
            count = item[0]
            port = item[1]

            pid = self._port_to_pid_map.get(port, 0)
            cwd, cmd = self.get_pid_info(pid)

            if cwd is not None:
                print("Port: %6d  PV Req: %6d   PID: %6d  CWD: %-90s CMD: %s" % (port, count, pid, cwd, cmd))
            else:
                print("Port: %6d  PV Req: %6d" % (port, count))

    def clean_symlink(self, symlink):
        parts = symlink.split(' ')
        return parts[-1].strip()

    def get_pid_info(self, pid):

        cmd = None
        cwd = None

        if pid == 0:
            return cwd, cmd

        output = None
        try:
            output = os.popen("cat /proc/%d/cmdline" % pid)
            result = output.readlines()[0]
            result = result.strip()
            # Replace any '00' with 'space'
            result = result.replace('\00', ' ')
            result = result.strip()
            cmd = result

        except Exception as err:
            cmd = None

        finally:
            if output is not None: output.close()

        output = None
        try:
            output = os.popen("ls -l /proc/%d/cwd" % pid)
            result = output.readlines()[0]
            result = result.strip()
            # Replace any '00' with 'space'
            result = result.replace('\00', ' ')
            result = result.strip()
            cwd = self.clean_symlink(result)

        except Exception as err:
            cwd = None

        finally:
            if output is not None: output.close()

        return cwd, cmd

    def make_port_string(self, pv_name):
        pv_data = self._pvs.get(pv_name)
        port_data = pv_data.get('p')

        x = [(count, port) for port, count in port_data.items()]
        x.sort()
        x.reverse()

        result = ""

        for i, item in enumerate(x):
            result += "%d:%d" % (item[1], item[0])
            result += "  "
            if i > 4:
                break
        i += 1
        if len(x) > i:
            more_count = len(x) - i
            result += "  Plus %d more" % more_count

        return result

    def worker_process(self):

        while not self._terminate:
            try:
                item = self._queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            # print_binary(data)
            self.process_request(item)

        self._process_done_flag = True

    def banner(self):
        if self._failed: return

        # print("-"*80)
        print("")
        print("This script listens for PV requests (CA_PROTO_SEARCH) issued by the target IOC")
        print("")
        if (self._extended_banner_flag):
            print("By default, the target IOC is 'localhost'")
            print("To monitor a non-localhost IOC, use the -i <IOC_Name> option")
            print("(target IOC must be on same VLAN as listener)")
            print("")
        print("    TARGET IOC: %s" % self._hostname)
        print("    IP ADDRESS: %s" % repr(self._ip_address).strip("'"))
        print("")
        print("If this script is running as root on the target IOC,")
        print("it will attempt to map the requesting port to a process")
        print("")

        try:
            input("Press ENTER to start; CRTL-C to terminate...")
        except:
            pass

    def process_request(self, item):

        data = item[0]
        port = item[1]

        total_length = len(data)

        while True:
            # Unpack the message header
            try:
                c = struct.unpack_from("HHHHII", data)
            except Exception as err:
                print("Exception in process messages: %s" % str(err))
                return

            command = socket.ntohs(c[0])
            payload_len = socket.ntohs(c[1])
            msg_len = HDR_LEN + payload_len

            if command == 6:
                if payload_len == 0:
                    print("ERROR: no payload in request")
                    break

                pv_name_raw = data[HDR_LEN:msg_len]
                # print("type: %s" % type(pv_name_raw))

                pv_name = ''
                for c in pv_name_raw:
                    if ord(c) == 0: break
                    # pv_name += char(c)
                    pv_name += c

                # print_binary(pv_name)
                # if not pv_name:
                #     log.err(0, "bad PV name: %s" % p)
                #     # add_bad_pv(pv_name_raw, addr)
                # else:
                self._count_requests += 1
                self._count_since_log += 1

                pv_data = self._pvs.get(pv_name, {})
                count = pv_data.get('c', 0)
                count += 1
                pv_data['c'] = count

                ports = pv_data.get('p', {})
                port_count = ports.get(port, 0)
                port_count += 1
                ports[port] = port_count
                pv_data['p'] = ports

                self._pvs[pv_name] = pv_data

                print("{:6d}  PV --> {:50s}  Port: {:6d} Req: {:6d}".format(self._count_requests, pv_name, port, count))

                # print("%d: PV --> %s (P:%d C: %d)" % (self._count_pvs, pv_name, port, count))

            else:
                pass

            total_length -= msg_len

            # print total_length
            if total_length < 1:
                break

            # Advance to next message
            data = data[msg_len:]

    def worker_listen_resp(self):
        while not self._terminate:
            print("listen resp running")
            time.sleep(10)

    def worker_listen_req(self):

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(1)
        s.bind(('', PORT_CA_PROTO_SEARCH))

        while not self._terminate:
            try:
                data, address = s.recvfrom(10000)

            except socket.timeout:
                # print("got a timeout")
                continue

            ip_key = struct.unpack("!I", socket.inet_aton(address[0]))[0]
            port = int(address[1])

            # Ignore any requests coming from the target host
            if ip_key != self._ip_key: continue

            # log.dbg(0, lambda: "address: %s IP KEY: %d" % (repr(address), ip_key ))
            self._count_packets += 1
            # print_binary(data)

            self._queue.put_nowait((data, port))

    def handle_SIGINT(self, signum, frame):
        self._terminate = True
        # self.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="EPICS CA_PROTO_SEARCH Listen")
    parser.add_argument("-i", "--ioc", help="IOC Name", type=str, required=False)
    parser.add_argument("-l", "--list", help="Show Requests", required=False, action='store_true')

    params = parser.parse_args()
    thing = Listen(params)
    thing.banner()
    thing.start()
    thing.run()