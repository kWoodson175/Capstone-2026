import socket
import threading
import time
import struct # imports struct to translate raw binary bytes into python numbers
import re  # imports regex to hunt for numbers inside text strings
from security_policy import check_motion_limits #imports the motion limits 

URSIM_IP = "192.168.107.128"
LOCAL_HOST = "127.0.0.1"
PORTS_TO_PROXY = [30002, 30004]

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
                    if len(data) >= 3:
                        packet_type = data[2]
                        if packet_type == 8 and len(data) >= 72:
                            payload = struct.unpack(">i8d", data[4:72])
                            cmd_id = payload[0]
                            
                            cmd_name = None
                            if cmd_id == 2: cmd_name = "moveL"
                            elif cmd_id == 11: cmd_name = "speedL"
                            elif cmd_id == 1: cmd_name = "moveJ"
                            
                            if cmd_name:
                                x, y, z = payload[1], payload[2], payload[3]
                                rx, ry, rz = payload[4], payload[5], payload[6]
                                v, a = payload[7], payload[8]
                                
                                # Firewall Intervention
                                is_safe, reason = check_motion_limits(x, y, z, v, a)
                                formatted_cmd = f"{cmd_name}([{x:.4f}, {y:.4f}, {z:.4f}, {rx:.4f}, {ry:.4f}, {rz:.4f}], a={a:.4f}, v={v:.4f})"
                                
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