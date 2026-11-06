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
SPEED_J = 0.1       # joint speed
ACCEL_J = 0.2
UNSAFE_ACCEL_J = 2.01      # DANGER

# Default tool orientation used for pick and drop poses.
RX = 2.2
RY = -2.2
RZ = 0

print("Connecting to URSim...")
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)
print("Connected\n")

FIRST_POSE = rtde_r.getActualQ()
FIRST_POSE[0] += 0.1
SECOND_POSE = FIRST_POSE.copy()
SECOND_POSE[0] -= 0.1 

def unsafe_move_around():
    """
    1. Move to first position with moveJ
    2. Try to move to second position
    """    

    # moves with a SAFE acceleration
    print("\nMoving SAFELY to first point...")
    rtde_c.moveJ(FIRST_POSE, SPEED_J, ACCEL_J)
    time.sleep(1)

    # Acceleration is the problem
    print("\nMoving DANGEROUSLY to second point...")
    
    # 11/3 for timing
    #issued_ms = time.perf_counter_ns() // 1_000_000
    rtde_c.moveJ(SECOND_POSE, SPEED_J, UNSAFE_ACCEL_J)
    #print(f"[BAD COMMAND ISSUED] timestamp (ms) = {issued_ms}", flush=True)
    
    rtde_c.stopScript()

if __name__ == "__main__":
    unsafe_move_around()
