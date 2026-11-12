import math
import time
from rtde_control import RTDEControlInterface as RTDEControl
from rtde_receive import RTDEReceiveInterface as RTDEReceive

#ROBOT_IP = "192.168.56.101" # change if Sim or actual
ROBOT_IP = "192.168.1.112"
PROXY_IP = "127.0.0.1"

rtde_c = RTDEControl(PROXY_IP)

print("Connecting to URSim...")

rtde_r = RTDEReceive(ROBOT_IP)
# Read live data from the robot

print("Connected")

# base, shoulder, elbow, wrist1, wrist2, wrist3
joints = [
    [0.1, 0, 0, 0, 0, 0],
    [0, 0.1, 0, 0, 0, 0],
    [0, 0, 0.1, 0, 0, 0],
    [0, 0, 0, 0.1, 0, 0],
    [0, 0, 0, 0, 0.1, 0],
    [0, 0, 0, 0, 0, 0.1]
]

OPPjoints = [
    [-0.1, 0, 0, 0, 0, 0],
    [0, -0.1, 0, 0, 0, 0],
    [0, 0, -0.1, 0, 0, 0],
    [0, 0, 0, -0.1, 0, 0],
    [0, 0, 0, 0, -0.1, 0],
    [0, 0, 0, 0, 0, -0.1]
]

dt = 1.0/500 # each cycle is 2ms

print("Going this way")
# Move ONE joint clockwise
# Arguments: joint speed [rad/s], acceleration [rad/s^2], time
for i in range(2500): # 2500 * 2ms = 5s
    t_start = rtde_c.initPeriod() 
    rtde_c.speedJ(joints[2], 0.2, dt)
    rtde_c.waitPeriod(t_start)

rtde_c.speedStop()
time.sleep(1)

print("Going the other way")
# Move ONE joint counter-clockwise
for i in range(2500):
    t_start = rtde_c.initPeriod()
    rtde_c.speedJ(OPPjoints[2], 0.2, dt)
    rtde_c.waitPeriod(t_start)

rtde_c.speedStop()
rtde_c.stopScript()