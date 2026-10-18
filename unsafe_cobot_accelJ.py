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

# Full poses measured from the teach pendant.
FIRST_XYZ = [0.38540, -0.02418, 0.25258, 2.455, -2.425, 0.705]
SECOND_XYZ = [0.33117, 0.08715, 0.21997, 2.237, -2.211, 0.0]

print("Connecting to URSim...")
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)
print("Connected\n")


def unsafe_move_around():
    """
    1. Move to first position with moveJ
    2. Try to move to second position
    """    

    # moves with a SAFELY acceleration
    print("\nMoving SAFELY to first point...")
    FIRST_POSE = [0.444186, -1.629963, -1.818109, -1.179114, -4.894078, 0.309970]
    rtde_c.moveJ(FIRST_POSE, SPEED_J, ACCEL_J)
    time.sleep(1)

    # this shouldn't work
    print("\nMoving DANGEROUSLY to second point...")
    SECOND_POSE = [0.568977, -1.182635, -2.190563, -1.197819, -4.894078, 0.309970]
    rtde_c.moveJ(SECOND_POSE, SPEED_J, UNSAFE_ACCEL_J)
    rtde_c.stopScript()

if __name__ == "__main__":
    unsafe_move_around()
