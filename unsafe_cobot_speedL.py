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
UNSAFE_SPEED_L = 0.51      # DANGER
SPEED_L = 0.08             # normal linear speed
ACCEL_L = 0.19             # slow acceleration

# Default tool orientation used for pick and drop poses.
RX = 2.2
RY = -2.2
RZ = 0

# Full poses measured from the teach pendant.
FIRST_XYZ = [0.38540, -0.02418, 0.25258, 2.455, -2.425, 0.705]
SECOND_XYZ = [0.33117, 0.08715, 0.21997, 2.237, -2.211, 0.0]

print("Connecting to URSim...")
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)
print("Connected\n")

def unsafe_move_around():
    """
    1. Move to first position with moveL
    2. Try to move to second position
    """    

    # speed is a violation
    print("\nMoving DANGEROUSLY to first point...")

    # 11/3 for timing
    issued_ms = time.perf_counter_ns() // 1_000_000
    rtde_c.moveL(FIRST_XYZ, UNSAFE_SPEED_L, ACCEL_L)
    print(f"[BAD COMMAND ISSUED] timestamp (ms) = {issued_ms}", flush=True)

    time.sleep(1)

    print("\nMoving SAFELY to second point...")
    rtde_c.moveL(SECOND_XYZ, SPEED_L, ACCEL_L)

    rtde_c.stopScript()

if __name__ == "__main__":
    unsafe_move_around()
