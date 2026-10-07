
import socket
import time

PROXY_IP = "127.0.0.1"
PROXY_PORT = 30002

def send_script(script):
    with socket.create_connection(
        (PROXY_IP, PROXY_PORT), timeout=5
    ) as sock:
        sock.sendall(script.encode("utf-8"))

def close_gripper():
    print("Testing gripper CLOSE")

    send_script("""
def test_close():
  set_standard_digital_out(0, True)
  textmsg("rq_close_and_wait()")
end
""")

def open_gripper():
    print("Testing gripper OPEN")

    send_script("""
def test_open():
  set_standard_digital_out(0, False)
  textmsg("rq_open_and_wait()")
end
""")

close_gripper()
time.sleep(3)
open_gripper()
