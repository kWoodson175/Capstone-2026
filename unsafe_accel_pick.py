import socket
import time
from pathlib import Path


import rtde_control
import rtde_receive


# -----------------------------
# Robot connection
# -----------------------------
ROBOT_IP = "192.168.56.101" # "192.168.1.112"
PROXY_IP = "127.0.0.1"

# -----------------------------
# Motion settings
# -----------------------------
SPEED_L = 0.08      # normal linear speed
ACCEL_L = 0.19      # slow acceleration

SPEED_J = 0.1       # joint speed
DANGER_ACCEL_J = 2.1       # DANGER

PICK_SPEED = 0.05   # very slow vertical pickup/drop speed
PICK_ACCEL = 0.05

# 28 mm from the pendant is 0.028 m.
Z_PICK = 0.050
Z_DROP = 0.080

# Default tool orientation used for pick and drop poses.
RX = 2.2
RY = -2.2
RZ = 0

# receive and control
print("Connecting to URSim...")
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)
print("Connected\n")

# Full poses measured from the teach pendant.
              # gotten from simulation -- get_joints.py   
HOME_XYZ = [0.2060313432789112, -0.4356200608107538, 0.2, RX, RY, RZ]
#HOME_JOINTS = [-1.5904201961032314, -1.7288431042924293, -2.225574532512576, -0.7361100588514411, 1.5497813839884034, -1.5906499201251876]

# --------------------------------------
# Pick up and drop poses 
# 0.20 m = 20 cm
PICKUP_XYZ = HOME_XYZ.copy()
PICKUP_XYZ[0] -= 0.20          # left
#PICKUP_JOINTS = [-1.994655360899399, -1.9230480056455805, -1.9593107054284973, -0.8016666286147291, 1.560072151396804, -1.9948074606816277]

DROP_XYZ = HOME_XYZ.copy()
DROP_XYZ[0] += 0.20            # right
#DROP_JOINTS = [-1.1277058117583714, -1.6855616897581776, -2.27382713607562, -0.7428191758862965, 1.5422332549765643, -1.1278512227115876]

# -------------------------------------
# Poses to go down 
PICKUP_DOWN = PICKUP_XYZ.copy()
PICKUP_DOWN[2] = Z_PICK

DROP_DOWN = DROP_XYZ.copy()
DROP_DOWN[2] = Z_DROP

def get_joint_target(pose):
    q_near = rtde_r.getActualQ()
    joints = rtde_c.getInverseKinematics(pose, q_near)

    if joints is None or len(joints) != 6:
        raise RuntimeError(f"Could not find inverse-kinematics solution for {pose}")

    return joints

# =========================================================
# Simple pick and place
# =========================================================

def pick_place(actually_move=True, return_home=True):
    """
    Fixed-coordinate pick and place:
    1. Move to home pose (joint)
    2. Move to pickup pose (joint)
    3. Go straight down to pickup height
    4. Close gripper
    5. Go straight back up to safe height
    6. Move to drop pose (joint)
    7. Lower to drop height
    8. Open gripper
    9. Return to safe height 
    10. Return home
    """

    if not actually_move:
        print("\nPREVIEW ONLY. Robot did not move.")
        return

    # Start from a safe height above wherever the robot currently is.
    print("\nMoving home first...")
    HOME_JOINTS = get_joint_target(HOME_XYZ)

    # 11/3 for timing
    issued_ms = time.perf_counter_ns() // 1_000_000
    rtde_c.moveJ(HOME_JOINTS, SPEED_J, DANGER_ACCEL_J)
    print(f"[BAD COMMAND ISSUED] timestamp (ms) = {issued_ms}", flush=True)

    time.sleep(1)

    print("Moving to pick-up...")
    PICKUP_JOINTS = get_joint_target(PICKUP_XYZ)
    rtde_c.moveJ(PICKUP_JOINTS, SPEED_J, DANGER_ACCEL_J)
    time.sleep(1)

    #print("Making sure gripper is open...")
    #open_gripper()

    print("Moving straight down to pickup height...")
    rtde_c.moveL(PICKUP_DOWN, PICK_SPEED, PICK_ACCEL)
    print("Pause to close gripper...")
    time.sleep(1.5)

    #print("Closing gripper...")
    #close_gripper()

    print("Moving straight back up...")
    rtde_c.moveL(PICKUP_XYZ, PICK_SPEED, ACCEL_L)
    time.sleep(.5)

    print("Moving to drop...")
    DROP_JOINTS = get_joint_target(DROP_XYZ)
    rtde_c.moveJ(DROP_JOINTS, SPEED_J, DANGER_ACCEL_J)
    time.sleep(1)

    print("Moving down to drop height...")
    rtde_c.moveL(DROP_DOWN, PICK_SPEED, PICK_ACCEL)
    print("Pause to open gripper...")
    time.sleep(1.5)
    
    #print("Opening gripper...")
    #open_gripper()

    print("Moving back up...")
    rtde_c.moveL(DROP_XYZ, PICK_SPEED, ACCEL_L)
    time.sleep(.5)

    if return_home:
        print("Returning home...")
        rtde_c.moveJ(HOME_JOINTS, SPEED_J, DANGER_ACCEL_J)

    print("\nPick-and-place complete.")
    rtde_c.stopScript()


if __name__ == "__main__":
    # One-time gripper wake-up (reset + activate) before any motion.
    # initialize_gripper()

    # Set actually_move=True when you are ready for the robot to move.
    pick_place(actually_move=True, return_home=True)
