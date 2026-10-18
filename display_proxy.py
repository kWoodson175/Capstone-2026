import socket
import threading
import time
import struct # imports struct to translate raw binary bytes into python numbers
import re  # imports regex to hunt for numbers inside text strings
from security_policy import check_motion_limits #imports the motion limits 
from security_policy import is_ip_allowed # imports the ip whitelist

URSIM_IP = "192.168.56.101"
#URSIM_IP = "192.168.1.112"  # Physical robot IP
LOCAL_HOST = "127.0.0.1"

PORTS_TO_PROXY = [29999, 30001, 30002, 30003, 30004] 
                # DISPLAY CHANGES   
                # 29999 = dashboard server
                # 30001 =  Primary
                # 30002 =  Secondary
                # 30003 = Real-time
                # 30004 =  RTDE

# ----------------------------------------------
# DISPLAY CHANGES
# This part sends an event (command data + reason) to the display
# This way I can get rid of the proxy_translator which reads off stdout
# ----------------------------------------------
_event_callback = None

def set_event_callback(callback):
    global _event_callback
    _event_callback = callback

def emit_event(event):
    if _event_callback is None:
        return

    try:
        _event_callback(event)

    except Exception as e:
        print(f"EVENT CALLBACK ERROR: {e}")

# ---------------------------------------------
# DISPLAY CHANGES 
# inspection and forwarding got seperated cause 30002 takes data and 30004 takes packets

# returns True to forward TCP data
#      or False to block TCP data
def inspect_urscript(data):
    allow_packet = True
    
    try:
        text_cmd = data.decode("utf-8").strip()
        for line in text_cmd.split('\n'):
            clean_line = line.strip()
            cmd_lower = clean_line.lower()

            # RTDE movement commands
            if cmd_lower.startswith("movel(") or cmd_lower.startswith("movej(") or cmd_lower.startswith("speedl("):
                
                # Use Regex to hunt down the 'a=' and 'v=' values anywhere in the text string
                a_match = re.search(r'a\s*=\s*([0-9\.]+)', cmd_lower)
                v_match = re.search(r'v\s*=\s*([0-9\.]+)', cmd_lower)
                
                if a_match and v_match:
                    # Extract the numbers from the text
                    a_val = float(a_match.group(1))
                    v_val = float(v_match.group(1))
                    
                    # Firewall Intervention
                    # We feed dummy safe coordinates (0.1, 0.1, 0.1) into the checker 
                    # so it only evaluates our intercepted velocity and acceleration!
                    is_safe, reason = check_motion_limits(0.1, 0.1, 0.1, v_val, a_val)
                    
                    if is_safe:
                        print(f"[TEXT ALLOWED] {clean_line}")
                    else:
                        print(f"[TEXT BLOCKED] {clean_line}")
                        print(f"    -> Reason: {reason}")
                        allow_packet = False

                    # DISPLAY CHANGES
                    # Live_display needs a command name or ID
                    # also I changed the numbers from moveType to what I think the ID is
                    # Send command event to live_display
                    if cmd_lower.startswith("movel("):
                        cmd_name = "moveL"
                        cmd_id = 3                  # moveTypes not used here
                    elif cmd_lower.startswith("movej("):
                        cmd_name = "moveJ"
                        cmd_id = 1
                    elif cmd_lower.startswith("speedl("):
                        cmd_name = "speedL"
                        cmd_id = 11

                    emit_event({
                        "command": cmd_name,
                        "command_id": cmd_id,
                        "raw_command": clean_line,
                        "speed": v_val,
                        "acceleration": a_val,
                        "allowed": is_safe,
                        "reason": (None if is_safe else reason)
                        #"source_ip": LOCAL_HOST,
                        #"destination_port": 30002
                    })
            
    except UnicodeDecodeError:
        pass

    return allow_packet

def inspect_rtde(packet):
    if len(packet) < 3:
        return False
    
    packet_size = struct.unpack(">H",packet[0:2])[0]

    packet_type = packet[2]

    # If not a RTDE data package
    if packet_type != 85:
        return True

    recipe_id = packet[3]

    # inspects recipe 1 only
    if recipe_id != 1:
        return True
    
    if packet_size < 76:
        return False

    try:
        cmd_id = struct.unpack(">i", packet[4:8])[0]

        values = struct.unpack(">8d", packet[8:72])
        
        async_flag = struct.unpack(">i", packet[72:76])[0]

    except struct.error as e:
        print(f"RTDE BLOCKED: {e}")
        return False
    
    cmd_name = None
    if cmd_id == 1: cmd_name = "moveJ"
    elif cmd_id == 2: cmd_name = "moveJ" #movej_ik
    elif cmd_id == 3: cmd_name = "moveL"
    elif cmd_id == 4: cmd_name = "moveL" #movel_fk
    elif cmd_id == 11: cmd_name = "speedL"

    if cmd_id in (1, 2, 3, 4) and len(packet) >= 76:

        target = list(values[0:6])

        v, a = values[6], values[7]

        # -----------------------------------------
        # Safety check
        # -----------------------------------------
        # Firewall Intervention
        
        if cmd_name == "moveL":   # Cartesian moveL target
            # x, y, z = payload[1], payload[2], payload[3]
            # rx, ry, rz = payload[4], payload[5], payload[6]

            x, y, z = target[0], target[1], target[2]
            rx, ry, rz = target[3], target[4], target[5]

            is_safe, reason = check_motion_limits(x, y, z, v, a)

        elif cmd_name == "moveJ":
            # We feed dummy safe coordinates (0.1, 0.1, 0.1) into the checker 
            # so it only evaluates our intercepted velocity and acceleration!
            is_safe, reason = check_motion_limits(
                0.1, 0.1, 0.1, v, a
            )

        # DISPLAY CHANGE
        # it refused to send the target (joints) for moveJ to my display when it was XYZ
        target_string = ", ".join(f"{value:.4f}" for value in target)
        
        formatted_cmd = (
            f"{cmd_name}"
            f"([{target_string}], "
            f"a={a:.4f}, "
            f"v={v:.4f})"
        )

        if is_safe:
            print(f"[BINARY ALLOWED] {formatted_cmd}")
        else:
            print(f"[BINARY BLOCKED] {formatted_cmd}")
            print(f"    -> Reason: {reason}")
            allow_packet = False

        emit_event({    
            "command": cmd_name,
            "command_id": cmd_id,
            "target": target, # x y z Rx Ry Rz or J1-6
            "speed": v,
            "acceleration": a,
            "allowed": is_safe,
            "reason": (None if is_safe else reason)
            #"source_ip": LOCAL_HOST,
            #"destination_port": 30004
        })

        return is_safe

# STOP CHANGES
ACTIVE_EMERGENCY = False

stop_script = b"stopj(5.0)\n" # deceleration in rad/s^2

def send_stop_command():
    """
    Stop the running UR program
    """
    try:
        global ACTIVE_EMERGENCY 
                
        ACTIVE_EMERGENCY = True
        
        print("[FIREWALL] Sending STOP command to robot...")

        while(ACTIVE_EMERGENCY):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((URSIM_IP, 30002))
                s.sendall(stop_script)

        print("[FIREWALL] stopj() loop exited")

    except Exception as e:
        print(f"[ERROR] Unable to send motion stop: {e}")

def resume():
    global ACTIVE_EMERGENCY
    print("[FIREWALL] Resuming movement in robot...")
    ACTIVE_EMERGENCY = False

def start_stop_thread():
        threading.Thread(
            target=send_stop_command,
            daemon=True).start()

"""
Read arbitrary TCP chunks from port 30004.

Buffer them until complete RTDE packets exist.

Each complete RTDE packet is inspected and forwarded
independently.
"""
def forward_rtde_stream(source, destination):
    rtde_buffer = b""

    while True:

        data = source.recv(4096)

        if not data:
            break

        # Add bytes from this recv() to persistent buffer.
        rtde_buffer += data

        # ----------------------------------------------------
        # Extract every complete RTDE packet currently
        # available in the buffer.
        # ----------------------------------------------------

        while True:

            # Need enough data to read packet size and type.
            if len(rtde_buffer) < 3:
                break

            packet_size = struct.unpack(">H", rtde_buffer[0:2])[0]

            if packet_size < 3:

                raise RuntimeError(
                    f"Invalid RTDE packet size: {packet_size}"
                )


            if len(rtde_buffer) < packet_size:
                break

            # ------------------------------------------------
            # Extract ONE complete RTDE packet.
            # ------------------------------------------------

            packet = rtde_buffer[:packet_size]

            # Remove only that packet from buffer.
            rtde_buffer = rtde_buffer[packet_size:]

            # ------------------------------------------------
            # Inspect THIS packet.
            # ------------------------------------------------

            allow_packet = inspect_rtde(packet)

            # ------------------------------------------------
            # Forward THIS packet only.
            #
            # A blocked packet does NOT affect any other
            # packet that happened to arrive in the same
            # recv().
            # ------------------------------------------------

            if allow_packet:
                destination.sendall(packet)            
            else:
                print("[PROXY] RTDE packet discarded")
                
                # Added for the Stop()            
                # The packet is blocked and not sent to the robot
                # CHANGED runs stop command as a thread
                start_stop_thread()
                
# general forwarder
def forward_traffic(source, destination, port, direction):

    try:
        # special case goes first
        if port == 30004 and direction == "to_robot": 
            # calls inspect_rtde()
            forward_rtde_stream(source, destination)
            return

        while True:
            data = source.recv(4096)
            if not data:
                break
            
            allow_data = True  
            
            # -------------------------------------------------------------
            # Parse cleartext URScript and enforce policy (Port 30002)
            # Uses regex to get text from strings and checks for both lowercase and uppercase commands
            # -------------------------------------------------------------
            if port == 30002 and direction == "to_robot":
                allow_data = inspect_urscript(data)        
                                     
            # Packet Forwarding Decision
            if allow_data:
                destination.sendall(data)
            # Added for the Stop()
            elif direction == "to_robot":
                # The packet is blocked and not sent to the robot
                # Runs stop command as a thread
                start_stop_thread()

            
    except ConnectionResetError:
        pass 
    except ConnectionAbortedError:
        pass
    except Exception as e: 
        print(f"THREAD ERROR: {e}")
    finally: # DISPLAY CHANGES
        # if I remember right, this was closing sockets/threads prematurely
        pass
        #source.close()
        #destination.close()

def handle_connection(local_socket, target_port):
    try:
        ursim_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ursim_socket.connect((URSIM_IP, target_port))
        threading.Thread(target=forward_traffic, args=(local_socket, ursim_socket, target_port, "to_robot"), daemon=True).start()
        threading.Thread(target=forward_traffic, args=(ursim_socket, local_socket, target_port, "to_client"), daemon=True).start()
    except Exception as e:
        local_socket.close()


def start_listener(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOCAL_HOST, port))
    server.listen(5)
    print(f"Listening on local port {port}...")
    
    while True:
        local_socket, addr = server.accept()
        client_ip = addr[0]
        ip_allowed = True

        #-----------------------------------------
        # Whitelist IP check
        #------------------------------------------
        ip_allowed = is_ip_allowed(client_ip)

        # DISPLAY CHANGE
        # This needs to happen before the connection is dropped
        emit_event({    
            "event_type": "connection",
            "client_ip": client_ip,
            "port": port,
            "ip_decision": ip_allowed
        })

        if not ip_allowed:
            print(f"[FIREWALL] BLOCKED connection attempt from unauthorized IP: {client_ip} on port {port}")
            local_socket.close() # Drop connection instantly
            continue # Wait for the next connection
            
        threading.Thread(target=handle_connection, args=(local_socket, port), daemon=True).start()

# DISPLAY CHANGES
def start_proxy():
    print(f"Starting proxy bridge to URSim at {URSIM_IP}...")
    
    for port in PORTS_TO_PROXY:
        threading.Thread(target=start_listener, args=(port,), daemon=True).start()

if __name__ == "__main__":

    start_proxy() # Start-up got moved into a function so live_display can call it
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down proxy...")
