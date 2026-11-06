import socket
import time
from pathlib import Path
import rtde_control
import rtde_receive

# -----------------------------
# Robot connection
# -----------------------------
#ROBOT_IP = "192.168.56.101" 
ROBOT_IP = "192.168.1.112"
PROXY_IP = "127.0.0.1"

# -----------------------------
# Motion settings
# -----------------------------
SPEED_L = 0.08      # linear speed
ACCEL_L = 0.2       # acceleration

SPEED_J = 0.1       # joint speed
ACCEL_J = 0.2

# receive and control
print("Connecting to URSim...")
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)
print("Connected\n")

START_POSE = rtde_r.getActualTCPPose()  # position the sim starts at
# returns a 6D pose representing 
# the actual Cartesian position (X, Y, Z) 
# and orientation \((R_x, R_y, R_z)\) of the TCP

# -----------------------------
# Safety limits
# Adjust only if your team verifies the workspace is safe
# -----------------------------
X_MIN = 0.000
X_MAX = 0.750

Y_MIN = -0.500
Y_MAX = 0.420

# =========================================================
# Making a box parallel to XY plane
# =========================================================

# START_POSE = A
#  D_____C   ----> x
#  |     |   | y
#  |_____|   V
#  A     B

# 0.20 m = 20 cm

# Arguments: pose, speed, accel 
# Straight line in Cartesian space   
print("Drawing a box...")
B_POSE = START_POSE.copy() # A
B_POSE[0] += 0.20          # B ---->

C_POSE = B_POSE.copy()     #        C
C_POSE[1] -= 0.20          #        ^
                           #        |
                           #        B
D_POSE = C_POSE.copy()     
D_POSE[0] -= 0.20          # D <----

# side to side
print("Point A to B: moveL in X axis...")
rtde_c.moveL(B_POSE, SPEED_L, ACCEL_L)
time.sleep(1)

# forwards
print("Point B to C: moveL in Y axis...")
rtde_c.moveL(C_POSE, SPEED_L, ACCEL_L)
time.sleep(1)

print("Point C to D: moveL in X axis...")
rtde_c.moveL(D_POSE, SPEED_L, ACCEL_L)
time.sleep(1)

# backwards
print("Point D to A: moveL in Y axis...")
rtde_c.moveL(START_POSE, SPEED_L, ACCEL_L)
time.sleep(1)

rtde_c.stopScript()
print("Done.")