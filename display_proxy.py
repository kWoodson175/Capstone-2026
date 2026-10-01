import socket
import threading
import time
import struct # imports struct to translate raw binary bytes into python numbers
import re  # imports regex to hunt for numbers inside text strings
from security_policy import check_motion_limits #imports the motion limits 

URSIM_IP = "192.168.56.101"
LOCAL_HOST = "127.0.0.1"
PORTS_TO_PROXY = [29999, 30002, 30003, 30004] # Dashboard, Secondary, RTDE

def forward_traffic(source, destination, port, direction):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            
            allow_packet = True  
            
            # -------------------------------------------------------------
            # Parse cleartext URScript and enforce policy (Port 30002)
            # Uses regex to get text from strings and checks for both lowercase and uppercase commands
            # -------------------------------------------------------------
            if port == 30002 and direction == "to_robot":
                try:
                    text_cmd = data.decode("utf-8").strip()
                    for line in text_cmd.split('\n'):
                        clean_line = line.strip()
                        cmd_lower = clean_line.lower()
                        
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
                                    
                except UnicodeDecodeError:
                    pass
                    
            # -------------------------------------------------------------
            # Parse binary RTDE packets and enforce policy (Port 30004)
            # -------------------------------------------------------------
            elif port == 30004 and direction == "to_robot":
                try:
                    if len(data) >= 8:

                        packet_size = struct.unpack(">H", data[0:2])[0]
                        packet_type = data[2]

                        if packet_type == 85:
                            recipe_id = data[3]
                            cmd_id = struct.unpack(">i", data[4:8])[0]

                            cmd_name = None
                            if cmd_id == 1: cmd_name = "moveJ"
                            elif cmd_id == 2: cmd_name = "moveJ" #movej_ik
                            elif cmd_id == 3: cmd_name = "moveL"
                            elif cmd_id == 4: cmd_name = "moveL" #movel_fk
                            elif cmd_id == 11: cmd_name = "speedL"

                            if cmd_id in (1, 2, 3, 4) and len(data) >= 76:

                                values = struct.unpack(
                                    ">8d",
                                    data[8:72]
                                )

                                target = list(values[0:6])
                                """
                                x, y, z = payload[1], payload[2], payload[3]
                                rx, ry, rz = payload[4], payload[5], payload[6]
                                """
                                v, a = values[6], values[7]

                                async_flag = struct.unpack(
                                    ">i",
                                    data[72:76]
                                )[0]

                                # -----------------------------------------
                                # Safety check
                                # -----------------------------------------

                                if cmd_id in (3, 4):
                                    # Cartesian moveL target
                                    x = target[0]
                                    y = target[1]
                                    z = target[2]

                                    is_safe, reason = check_motion_limits(x, y, z, v, a)

                                else:
                                    # moveJ contains joint angles, not XYZ.
                                    #
                                    # For now only apply your velocity /
                                    # acceleration test using safe dummy XYZ.
                                    is_safe, reason = check_motion_limits(
                                        0.1, 0.1, 0.1, v, a
                                    )


                                formatted_cmd = (
                                    f"{cmd_name}("
                                    f"[{', '.join(f'{value:.4f}' for value in target)}], "
                                    f"a={a:.4f}, "
                                    f"v={v:.4f})"
                                )


                                if is_safe:
                                    print(f"[BINARY ALLOWED] {formatted_cmd}")
                                else:
                                    print(f"[BINARY BLOCKED] {formatted_cmd}")
                                    print(f"    -> Reason: {reason}")
                                    allow_packet = False

                except Exception as e:
                    print(f"PARSE ERROR: {e}")
                    
            # Packet Forwarding Decision
            if allow_packet:
                destination.sendall(data)
            
    except ConnectionResetError:
        pass 
    except ConnectionAbortedError:
        pass
    except Exception as e:
        print(f"THREAD ERROR: {e}")
    finally:
        source.close()
        destination.close()

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
        threading.Thread(target=handle_connection, args=(local_socket, port), daemon=True).start()

if __name__ == "__main__":
    print(f"Starting proxy bridge to URSim at {URSIM_IP}...")
    for port in PORTS_TO_PROXY:
        threading.Thread(target=start_listener, args=(port,), daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down proxy...")