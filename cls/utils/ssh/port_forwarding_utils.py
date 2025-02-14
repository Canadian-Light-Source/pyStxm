import subprocess
import shutil


def check_netstat():
    # Check if netstat is available
    if shutil.which('netstat') is not None:
        return 'netstat'
    # If netstat isn't found, check for ss
    elif shutil.which('ss') is not None:
        return 'ss'
    else:
        return None


def is_port_forwarded(port):
    tool = check_netstat()

    if tool:
        try:
            # Choose the appropriate tool (netstat or ss)
            if tool == 'netstat':
                result = subprocess.run(
                    ['netstat', '-tuln'], capture_output=True, text=True, check=True
                )
            elif tool == 'ss':
                result = subprocess.run(
                    ['ss', '-tuln'], capture_output=True, text=True, check=True
                )

            # Check if the port is listed in the output
            if str(port) in result.stdout:
                return True
            else:
                return False
        except subprocess.CalledProcessError as e:
            print(f"Error running {tool}: {e}")
            return False
    else:
        print("Neither netstat nor ss is available on this system.")
        return False


if __name__ == '__main__':
    port = 56561  # You can change this to the desired port number
    if is_port_forwarded(port):
        print(f"Port {port} is forwarded.")
    else:
        print(f"Port {port} is not forwarded.")
