import socket
import time
from pathlib import Path

import rtde_control
import rtde_receive

# -----------------------------
# Robot connection
# -----------------------------
#ROBOT_IP = "192.168.56.101" # simulation
ROBOT_IP = "192.168.1.112" # actual cobot
PROXY_IP = "127.0.0.1"

# -----------------------------
# Motion settings
# -----------------------------
SPEED_L = 0.08             # normal linear speed
ACCEL_L = 0.19             # slow acceleration

# Poses
FIRST_XYZ = [0.38540, -0.02418, 0.25258, 2.455, -2.425, 0.705]
DANGER_XYZ = [0.099, 0.0, 0.25258, 2.455, -2.425, 0.705]

print("Connecting to URSim...")
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)
print("Connected\n")

def unsafe_move_around():
    """
    1. Move to first position with moveL
    2. Try to move to second position
    """    

    print("\nMoving SAFELY to first point...")
    rtde_c.moveL(FIRST_XYZ, SPEED_L, ACCEL_L)
    time.sleep(1)

    # Destination is a violation
    print("\nMoving DANGEROUSLY to second point...")

    # 11/3 for timing
    issued_ms = time.perf_counter_ns() // 1_000_000
    rtde_c.moveL(DANGER_XYZ, SPEED_L, ACCEL_L)
    print(f"[BAD COMMAND ISSUED] timestamp (ms) = {issued_ms}", flush=True)

    rtde_c.stopScript()

if __name__ == "__main__":
    unsafe_move_around()
