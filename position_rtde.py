import math

from rtde_control import RTDEControlInterface as RTDEControl
from rtde_receive import RTDEReceiveInterface as RTDEReceive

ROBOT_IP = "192.168.56.101" # change if Sim or actual

rtde_c = RTDEControl(ROBOT_IP)

print("Connecting to URSim...")

rtde_r = RTDEReceive(ROBOT_IP)
# Read live data from the robot

print("Connected")

# Move to a safe home position using moveJ (joint space)
# Arguments: joint positions [rad], speed [rad/s], acceleration [rad/s^2]
# home_q = [-np.pi/2, -np.pi/2, -np.pi/2, -np.pi/2, np.pi/2, 0.0]
# rtde_c.moveJ(home_q, 0.5, 0.5)

# Get current joint positions
joints = rtde_r.getActualQ()

print("Current joints:", joints)

# 0 = base
# 1 = shoulder
# 2 = elbow
# 3,4,5 = wrist 1,2,3 
# Move ONE joint by +100 degrees
joints[1] += math.radians(100)

# Move robot
# Arguments: joint positions [rad], speed [rad/s], acceleration [rad/s^2]
rtde_c.moveJ(joints, 0.2, 0.2)

joints[1] -= math.radians(150)
rtde_c.moveJ(joints, 0.2, 0.2)

rtde_c.stopScript()