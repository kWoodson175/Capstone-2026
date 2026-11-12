import socket
import time
from pathlib import Path


import rtde_control
import rtde_receive

# True = CLOSED else OPEN
def set_gripper(closed):
    command = b"CLOSE\n" if closed else b"OPEN\n"

    with socket.create_connection((PROXY_IP, 30005), timeout=5) as client:
        client.sendall(command)
        with client.makefile("rb") as reader:
            response = reader.readline(256)

    if response != b"OK\n":
        raise RuntimeError(
            f"Gripper request failed: {response.decode().strip()}"
        )

# -----------------------------
# Gripper script settings
# -----------------------------
SCRIPT_FOLDER = Path(__file__).resolve().parent
GRIPPER_SCRIPT = "Gripper.script"
GRIPPER_PORT = 30002                 # for gripper motion NOT status
GRIPPER_SPEED = 150
GRIPPER_FORCE = 150

GRIPPER_ALREADY_ACTIVATED = False

def _strip_block(script_text, start_marker, end_marker):
    """
    Removes everything between (and including) two marker comment lines.
    Used to skip the one-time reset/activation section on routine calls.
    """
    start_index = script_text.find(start_marker)
    end_index = script_text.find(end_marker)

    if start_index < 0 or end_index < 0 or start_index >= end_index:
        raise RuntimeError(
            f"Could not find markers {start_marker!r}/{end_marker!r} in Gripper.script."
        )

    end_index += len(end_marker)
    return script_text[:start_index] + script_text[end_index:]


def build_gripper_program(action=None, full_reset=False):
    """
    Builds a Robotiq gripper program from Gripper.script.

    action: "open", "close", or None to only (re)connect/activate with no
        open/close motion (used for the one-time startup init).
    full_reset: if True, includes the reset block AND the activation
        re-check. Both cause the gripper to physically cycle, so they are
        skipped for routine open/close calls and should only run once per
        session, at startup.
    """
    script_path = SCRIPT_FOLDER / GRIPPER_SCRIPT

    if not script_path.exists():
        raise FileNotFoundError(
            f"Could not find gripper script: {script_path}. "
            "Put the script file in the same folder as simple_pick_and_place.py."
        )

    script_text = script_path.read_text()

    if not full_reset:
        script_text = _strip_block(
            script_text,
            "  # RESET_BLOCK_START",
            "  # RESET_BLOCK_END",
        )
        script_text = _strip_block(
            script_text,
            "  # ACTIVATE_BLOCK_START",
            "  # ACTIVATE_BLOCK_END",
        )

    marker = "  # Set speed and force"
    marker_index = script_text.find(marker)
    end_index = script_text.rfind("\nend")

    if marker_index < 0 or end_index < 0 or marker_index >= end_index:
        raise RuntimeError(
            "Could not find the final gripper command section in Gripper.script."
        )

    if action is None:
        action_block = (
            "  # Set speed and force\n"
            f"  rq_set_speed({GRIPPER_SPEED})\n"
            f"  rq_set_force({GRIPPER_FORCE})\n"
        )
    elif action == "close":
        action_block = (
            "  # Set speed and force\n"
            f"  rq_set_speed({GRIPPER_SPEED})\n"
            f"  rq_set_force({GRIPPER_FORCE})\n\n"
            "  # Close gripper\n"
            "  rq_close_and_wait()\n"
            "  sleep(0.5)\n"
        )
    elif action == "open":
        action_block = (
            "  # Set speed and force\n"
            f"  rq_set_speed({GRIPPER_SPEED})\n"
            f"  rq_set_force({GRIPPER_FORCE})\n\n"
            "  # Open gripper\n"
            "  rq_open_and_wait()\n"
            "  sleep(0.5)\n"
        )
    else:
        raise ValueError(f"Unknown gripper action: {action}")

    return script_text[:marker_index] + action_block + script_text[end_index:]


def send_gripper_program(action=None, full_reset=False):
    """
    Sends a generated URScript gripper program to the robot primary client.
    """
    program = build_gripper_program(action=action, full_reset=full_reset).encode("utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ROBOT_IP, GRIPPER_PORT))
        time.sleep(0.5)
        sock.sendall(program)
        time.sleep(0.5)


def initialize_gripper():
    """
    One-time startup call: reconnects, resets, and activates the gripper.
    Call this once at program startup, before any pick/place commands.
    """
    global GRIPPER_ALREADY_ACTIVATED
    print("\nGRIPPER INITIALIZE (one-time reset + activate)")
    send_gripper_program(action=None, full_reset=True)
    GRIPPER_ALREADY_ACTIVATED = True


def send_gripper_action(action):
    if not GRIPPER_ALREADY_ACTIVATED:
        print("Gripper not yet initialized this session - initializing now.")
        initialize_gripper()

    send_gripper_program(action=action, full_reset=False)


def close_gripper():
    print("\nGRIPPER CLOSE")
    send_gripper_action("close")


def open_gripper():
    print("\nGRIPPER OPEN")
    send_gripper_action("open")


# -----------------------------
# Robot connection
# -----------------------------
#ROBOT_IP = "192.168.56.101" 
ROBOT_IP = "192.168.1.112"
PROXY_IP = "127.0.0.1"

# -----------------------------
# Motion settings
# -----------------------------
SPEED_L = 0.08      # normal linear speed
ACCEL_L = 0.19      # slow acceleration

SPEED_J = 0.1       # joint speed
ACCEL_J = 0.2

DANGER_PICK_SPEED = 0.51   # DANGER  
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
    rtde_c.moveJ(HOME_JOINTS, SPEED_J, ACCEL_J)
    time.sleep(1)

    print("Moving to pick-up...")
    PICKUP_JOINTS = get_joint_target(PICKUP_XYZ)
    rtde_c.moveJ(PICKUP_JOINTS, SPEED_J, ACCEL_J)
    time.sleep(1)

    print("Making sure gripper is open...")
    open_gripper()
    set_gripper(False)

    print("Moving straight down to pickup height...")

    # 11/3 for timing
    # issued_ms = time.perf_counter_ns() // 1_000_000
    rtde_c.moveL(PICKUP_DOWN, DANGER_PICK_SPEED, PICK_ACCEL)
    # print(f"[BAD COMMAND ISSUED] timestamp (ms) = {issued_ms}", flush=True)

    #print("Pause to close gripper...")
    #time.sleep(1.5)

    print("Closing gripper...")
    close_gripper()
    set_gripper(True)

    print("Moving straight back up...")
    rtde_c.moveL(PICKUP_XYZ, DANGER_PICK_SPEED, ACCEL_L)
    time.sleep(.5)

    print("Moving to drop...")
    DROP_JOINTS = get_joint_target(DROP_XYZ)
    rtde_c.moveJ(DROP_JOINTS, SPEED_J, ACCEL_J)
    time.sleep(1)

    print("Moving down to drop height...")
    rtde_c.moveL(DROP_DOWN, DANGER_PICK_SPEED, PICK_ACCEL)
    print("Pause to open gripper...")
    time.sleep(1.5)
    
    print("Opening gripper...")
    open_gripper()
    set_gripper(False)

    print("Moving back up...")
    rtde_c.moveL(DROP_XYZ, DANGER_PICK_SPEED, ACCEL_L)
    time.sleep(.5)

    if return_home:
        print("Returning home...")
        rtde_c.moveJ(HOME_JOINTS, SPEED_J, ACCEL_J)

    print("\nPick-and-place complete.")
    rtde_c.stopScript()


if __name__ == "__main__":
    # One-time gripper wake-up (reset + activate) before any motion.
    initialize_gripper()

    # Set actually_move=True when you are ready for the robot to move.
    pick_place(actually_move=True, return_home=True)
