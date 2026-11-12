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
# Robot connection
# -----------------------------
# ROBOT_IP = "192.168.56.101"
ROBOT_IP = "192.168.1.112"
PROXY_IP = "127.0.0.1"

# -----------------------------
# Motion settings
# -----------------------------
SPEED_L = 0.08      # normal linear speed
ACCEL_L = 0.19      # slow acceleration

PICK_SPEED = 0.05   # very slow vertical pickup/drop speed
PICK_ACCEL = 0.05

Z_HOVER = 0.200     # safe hover height in meters
Z_BIN_HOVER = 0.200 # safe hover height above bins in meters

# 28 mm from the pendant is 0.028 m.
Z_PICK = 0.028
Z_DROP = 0.080

# Default tool orientation used for pick and drop poses.
RX = 2.2
RY = -2.2
RZ = 0

# Full poses measured from the teach pendant.
HOME_POSE = [0.38540, -0.02418, 0.25258, 2.455, -2.425, 0.705]
PICTURE_POSE = [0.33117, 0.08715, 0.21997, 2.237, -2.211, 0.0]

# The block is picked straight down from the picture-taking pose,
# so the pick X/Y is simply the picture pose X/Y.
PICK_X = PICTURE_POSE[0]
PICK_Y = PICTURE_POSE[1]


# -----------------------------
# Fixed bin locations
# -----------------------------
BINS = {
    "bin 1": {"x": 0.67606, "y": -0.37488},
    "bin 2": {"x": 0.53407, "y": -0.37488},
    "bin 3": {"x": 0.39170, "y": -0.37488},
    "bin 4": {"x": 0.24880, "y": -0.37488},
    "bin 5": {"x": 0.10519, "y": -0.37488},
}

# Which bin the block gets carried to.
DROP_BIN = "bin 5"


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


# -----------------------------
# Gripper script settings
# -----------------------------
SCRIPT_FOLDER = Path(__file__).resolve().parent
GRIPPER_SCRIPT = "Gripper.script"
GRIPPER_PORT = 30002                 # for gripper motion NOT status
GRIPPER_SPEED = 150
GRIPPER_FORCE = 150

GRIPPER_ALREADY_ACTIVATED = False


# =========================================================
# Pose helpers and safety
# =========================================================

def make_pose(x, y, z):
    return [float(x), float(y), float(z), RX, RY, RZ]


def check_pose_limits(pose, allow_low_z=False):
    x, y, z, rx, ry, rz = pose
    min_z = Z_MIN_PICK if allow_low_z else Z_MIN

    if not (X_MIN <= x <= X_MAX):
        raise ValueError(f"Unsafe X value: {x}")

    if not (Y_MIN <= y <= Y_MAX):
        raise ValueError(f"Unsafe Y value: {y}")

    if not (min_z <= z <= Z_MAX):
        raise ValueError(f"Unsafe Z value: {z}")


def safe_movel(pose, speed=SPEED_L, accel=ACCEL_L, allow_low_z=False):
    """
    Sends one blocking RTDE move, then closes the RTDE script.

    This is important because the gripper command is sent as a separate
    URScript through port 30002. Keeping one RTDE script open while sending
    gripper scripts can interrupt the remaining robot moves.
    """
    check_pose_limits(pose, allow_low_z=allow_low_z)

    rtde_c = rtde_control.RTDEControlInterface(PROXY_IP) # gateway

    try:
        rtde_c.moveL(pose, speed, accel)
    finally:
        rtde_c.stopScript()

def safe_movej(pose, speed=1.0, accel=1.4, allow_low_z=False):
    """
    Sends one blocking RTDE joint move, then closes the RTDE script.

    This is important because the gripper command is sent as a separate
    URScript through port 30002. Keeping one RTDE script open while sending
    gripper scripts can interrupt the remaining robot moves.
    """
    check_pose_limits(pose, allow_low_z=allow_low_z)

    rtde_c = rtde_control.RTDEControlInterface(PROXY_IP)

    try:
        rtde_c.moveJ(pose, speed, accel)
    finally:
        rtde_c.stopScript()

# =========================================================
# Gripper control (unchanged from robot_workspace_mover)
# =========================================================

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


# =========================================================
# Simple pick and place
# =========================================================

def simple_pick_and_place(bin_name=DROP_BIN, actually_move=True, return_home=True):
    """
    Simple fixed-coordinate pick and place:
    1. Move to the picture-taking pose
    2. Go straight down to pickup height
    3. Close gripper
    4. Go straight back up to the picture-taking pose
    5. Move above the selected bin
    6. Lower to drop height
    7. Open gripper
    8. Return to safe height above the bin
    9. Optionally return home
    """
    if bin_name not in BINS:
        raise ValueError(f"Unknown bin: {bin_name}")

    pick_pose = make_pose(PICK_X, PICK_Y, Z_PICK)

    bin_info = BINS[bin_name]
    above_bin_pose = make_pose(bin_info["x"], bin_info["y"], Z_BIN_HOVER)
    drop_pose = make_pose(bin_info["x"], bin_info["y"], Z_DROP)

    check_pose_limits(PICTURE_POSE)
    check_pose_limits(pick_pose, allow_low_z=True)
    check_pose_limits(above_bin_pose)
    check_pose_limits(drop_pose)

    print("\nPlanned simple pick-and-place path:")
    print("1. Picture-taking pose:", PICTURE_POSE)
    print("2. Straight down to pickup height:", pick_pose)
    print("3. Back up to picture-taking pose:", PICTURE_POSE)
    print(f"4. Above {bin_name}:", above_bin_pose)
    print("5. Down to drop height:", drop_pose)
    print(f"6. Back up above {bin_name}:", above_bin_pose)

    if not actually_move:
        print("\nPREVIEW ONLY. Robot did not move.")
        return

    # Start from a safe height above wherever the robot currently is.
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    current = rtde_r.getActualTCPPose()
    current_safe = make_pose(current[0], current[1], Z_HOVER)
    check_pose_limits(current_safe)

    print("\nMoving to safe Z first...")
    safe_movel(current_safe, SPEED_L, ACCEL_L)
    # try this following line. uncomment. 
    #safe_movej(current_safe, speed=1.0, accel=1.4)

    print("Moving to picture-taking pose...")
    safe_movel(PICTURE_POSE, SPEED_L, ACCEL_L)

    print("Making sure gripper is open...")
    open_gripper()
    # Set digital output 0 to LOW (False)
    set_gripper(False)

    print("Moving straight down to pickup height...")
    safe_movel(pick_pose, PICK_SPEED, PICK_ACCEL, allow_low_z=True)

    print("Closing gripper...")
    close_gripper()
    # Set digital output 0 to HIGH (True)
    set_gripper(True)

    print("Moving straight back up...")
    safe_movel(PICTURE_POSE, SPEED_L, ACCEL_L)

    print(f"Moving above {bin_name}...")
    safe_movel(above_bin_pose, SPEED_L, ACCEL_L)

    print("Moving down to drop height...")
    safe_movel(drop_pose, PICK_SPEED, PICK_ACCEL)

    print("Opening gripper...")
    open_gripper()
    # Set digital output 0 to LOW (False)
    set_gripper(False)

    print("Moving back up above the bin...")
    safe_movel(above_bin_pose, SPEED_L, ACCEL_L)

    if return_home:
        print("Returning home...")
        safe_movel(HOME_POSE, SPEED_L, ACCEL_L)

    print("\nSimple pick-and-place complete.")


if __name__ == "__main__":
    # One-time gripper wake-up (reset + activate) before any motion.
    initialize_gripper()

    # Set actually_move=True when you are ready for the robot to move.
    simple_pick_and_place(bin_name=DROP_BIN, actually_move=True)
