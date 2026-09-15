import socket
import time
from pathlib import Path
import rtde_control
import rtde_receive

# -----------------------------
# Robot connection
# -----------------------------
ROBOT_IP = "192.168.56.101" # "192.168.1.112"

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
rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
print("Connected\n")

HOME_POSE = rtde_r.getActualTCPPose()  # position the sim starts at
# returns a 6D pose representing 
# the actual Cartesian position (X, Y, Z) 
# and orientation \((R_x, R_y, R_z)\) of the TCP

HOME_JOINTS = rtde_r.getActualQ()
# returns the current positions of all six joint angles on the robotic arm in real time

# -----------------------------
# Safety limits
# Adjust only if your team verifies the workspace is safe
# -----------------------------
X_MIN = 0.000
X_MAX = 0.750

Y_MIN = -0.500
Y_MAX = 0.420

Z_MIN = 0.050
Z_MIN_PICK = 0.020
Z_MAX = 0.500

# =========================================================
# Pose helpers and safety
# =========================================================

def make_pose(x, y, z):
    return [float(x), float(y), float(z), RX, RY, RZ]

# =========================================================
# Exploring movel and movej
# =========================================================
# print("Start pose: ", HOME_POSE)

# Arguments: pose, speed, accel 
# Straight line in Cartesian space   
print("Testing MoveL...")
X_POSE = HOME_POSE.copy()
X_POSE[0] += 0.10

Y_POSE = HOME_POSE.copy()
Y_POSE[1] += 0.10

Z_POSE = HOME_POSE.copy()
Z_POSE[2] += 0.10 # move .1 meters in Z

# side to side 
print("MoveL in X axis...")
rtde_c.moveL(X_POSE, SPEED_L, ACCEL_L)
rtde_c.moveL(HOME_POSE, SPEED_L, ACCEL_L)
time.sleep(1)

# backwards
print("MoveL in Y axis...")
rtde_c.moveL(Y_POSE, SPEED_L, ACCEL_L)
# forwards
rtde_c.moveL(HOME_POSE, SPEED_L, ACCEL_L)
time.sleep(1)

# up
print("MoveL in Z axis...")
rtde_c.moveL(Z_POSE, SPEED_L, ACCEL_L)
#down 
rtde_c.moveL(HOME_POSE, SPEED_L, ACCEL_L)
time.sleep(1.5)
# 
# ==========================================
print("\nTesting MoveJ...")

# moveJ is in JOINT DEGREES
TEST_JOINTS = HOME_JOINTS.copy()
# [base, shoulder, elbow, wrist1, wrist2, wrist3]

# BASE ==================================================================================
TEST_JOINTS[0] += 0.26185   # 0.2618 radians = 15 degrees
print("MoveJ on base...")
rtde_c.moveJ(TEST_JOINTS, SPEED_J, ACCEL_J)
rtde_c.moveJ(HOME_JOINTS, SPEED_J, ACCEL_J)
time.sleep(1)

TEST_JOINTS[0] -= 0.2618 # don't move base again

# SHOULDER ========================================================================
TEST_JOINTS[1] += 0.2618
print("MoveJ on shoulder...")
rtde_c.moveJ(TEST_JOINTS, SPEED_J, ACCEL_J)
rtde_c.moveJ(HOME_JOINTS, SPEED_J, ACCEL_J)
time.sleep(1)

TEST_JOINTS[1] -= 0.2618 # don't move shoulder again

# ELBOW ============================================================================
TEST_JOINTS[2] += 0.2618
print("MoveJ on elbow...")
rtde_c.moveJ(TEST_JOINTS, SPEED_J, ACCEL_J)
rtde_c.moveJ(HOME_JOINTS, SPEED_J, ACCEL_J)
time.sleep(1)

TEST_JOINTS[2] -= 0.2618 # don't move elbow again

# WRIST1 ==========================================================
TEST_JOINTS[3] += 0.2618
print("MoveJ on wrist1...")
rtde_c.moveJ(TEST_JOINTS, SPEED_J, ACCEL_J)
time.sleep(1)

TEST_JOINTS[3] -= 0.2618 # don't move wrist1 again

# WRIST2 ==========================================================
TEST_JOINTS[4] += 0.2618
print("MoveJ on wrist2...")
rtde_c.moveJ(TEST_JOINTS, SPEED_J, ACCEL_J)
time.sleep(1)

TEST_JOINTS[4] -= 0.2618 # don't move wrist2 again

# WRIST3 ==========================================================
TEST_JOINTS[5] += 0.2618
print("MoveJ on wrist3...")
rtde_c.moveJ(TEST_JOINTS, SPEED_J, ACCEL_J)
time.sleep(1)

rtde_c.stopScript()
print("Done.")

