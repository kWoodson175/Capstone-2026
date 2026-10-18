from PyQt5 import QtCore, QtWidgets
from GUI_framework import Ui_MainWindow
from rtde_receive import RTDEReceiveInterface as RTDEReceive
import display_proxy as robot_proxy
from security_policy import(MAX_VELOCITY, MAX_ACCELERATION)
import re # for regex

import sys
import math # for degrees
import time # for timers

rejectCount = 0 # + 1 when a movement or IP violation happens

# for converting radians to match the teach pendant
def normalize_rotation_vector(rx, ry, rz):
    angle = math.sqrt(rx**2 + ry**2 + rz**2)

    if angle < 1e-9:
        return rx, ry, rz

    if angle <= math.pi:
        scale = 1 - (2 * math.pi / angle)
        return rx * scale, ry * scale, rz * scale

    return rx, ry, rz

# ---------------------------------------------------------
# Robot connection
# ---------------------------------------------------------

ROBOT_IP = "192.168.56.101"   # URSim
#ROBOT_IP = "192.168.1.112"  # Physical robot, if applicable

UPDATE_INTERVAL_MS = 100 #  100 ms = 0.1 sec

class SafetyDashboard(QtWidgets.QMainWindow):

    # proxy thread emits to this signal
    proxy_event = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # Build interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Preset Safety parameters
        self.ui.value_vel_limit.setText(f"{MAX_VELOCITY:.2f} m/s")
        self.ui.value_accel_limit.setText(f"{MAX_ACCELERATION:.2f} m/s²") 

        # ---------------------------------------------------------
        # URobot_proxy
        # ---------------------------------------------------------
        self.proxy_event.connect(self.handle_proxy_event)

        robot_proxy.set_event_callback(self.proxy_event.emit)

        robot_proxy.start_proxy()

        # Stop button is functional
        self.ui.stop_button.clicked.connect(robot_proxy.send_stop_command)
        #self.ui.stop_button.clicked.connect(robot_proxy.start_stop_thread)

        # resume button functional
        self.ui.resume_button.clicked.connect(robot_proxy.resume)
        
        # Robot connection starts empty
        self.rtde_r = None

        # Attempt RTDE connection
        self.connect_robot()

        # Update display every 100 ms
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_system_status)
        self.timer.timeout.connect(self.update_rtde_data)
        self.timer.start(UPDATE_INTERVAL_MS)

    # Proxy event
    def handle_proxy_event(self, data):

        if data.get("event_type") == "connection":
            self.update_network_access(data)
            
        elif data.get("command") is not None:
            self.update_command_inspector(data)
            self.update_safety_interlock(data)

    # Connect to UR robot 
    def connect_robot(self):
        try:
            print(f"Connecting to robot at {ROBOT_IP}...")
            self.rtde_r = RTDEReceive(ROBOT_IP)
            print("Connected.")            

        except Exception as e:

            self.rtde_r = None

            print("RTDE connection failed:", e)

    # Read live system status / action
    def update_system_status(self):
        try:
            if self.rtde_r.isConnected():
                self.ui.value_system_action.setText("System on")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: lightgreen;"
                    "    font-weight: bold;"                    
                )
            elif self.rtde_r is None or not self.rtde_r.isConnected():
                #if not self.rtde_r.isConnected():
                self.ui.value_system_action.setText("System off")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: #D3D3D3;"
                    "    font-weight: bold;"                    
                    )
                return

            runtime_state = self.rtde_r.getRuntimeState()
            """
            runtime values
            0 = STOPPING
            1 = STOPPED
            2 = PLAYING
            3 = PAUSING
            4 = PAUSED
            5 = RESUMING
            """
            
            if runtime_state == 2:
                self.ui.value_system_action.setText("▶ System running")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: lightgreen;"
                    "    font-weight: bold;"                    
                )

            elif runtime_state == 4:
                self.ui.value_system_action.setText("|| System on hold")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: #ffe699;"
                    "    font-weight: bold;"
                )
            elif runtime_state == 1:
                self.ui.value_system_action.setText("🛑 System stopped")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: #ffb3b3;"
                    "    font-weight: bold;"
                )
            
        except Exception as e:
    
            self.rtde_r = None
    
            #if not self.rtde_r.isConnected():
            self.ui.value_system_action.setText("System off")
            self.ui.value_system_action.setStyleSheet(
             f"background-color: #D3D3D3;"
             "    font-weight: bold;"                    
            )

    # Read live TCP pose and joint positions.
    def update_rtde_data(self):

        if self.rtde_r is None:
            return

        try:
            # GRIPPER
            output_bits = self.rtde_r.getActualDigitalOutputBits()

            # check digital_out[0]
            digital_out_0 = bool(output_bits & (1 << 0))

            if digital_out_0: 
                self.ui.value_gripper.setText("CLOSED") # High signal
            else:
                self.ui.value_gripper.setText("OPEN") # low signal
            
            # -------------------------------------------------
            # TCP pose
            # [X, Y, Z, Rx, Ry, Rz]
            # [0, 1, 2,  3,  4,  5]
            # -------------------------------------------------

            CARTESIAN_POSE = self.rtde_r.getActualTCPPose()

            x = CARTESIAN_POSE[0]
            y = CARTESIAN_POSE[1]
            z = CARTESIAN_POSE[2]

            rx = CARTESIAN_POSE[3]
            ry = CARTESIAN_POSE[4]
            rz = CARTESIAN_POSE[5]

            # XYZ returned in meters.
            # Convert to meters for display.
            self.ui.value_X.setText(f"X {x * 1000:.1f}")
            self.ui.value_Y.setText(f"Y {y * 1000:.1f}")
            self.ui.value_Z.setText(f"Z {z * 1000:.1f}")

            rx, ry, rz = normalize_rotation_vector(rx, ry, rz)

            self.ui.value_Rx.setText(f"Rx {rx:.2f}")
            self.ui.value_Ry.setText(f"Ry {ry:.2f}")
            self.ui.value_Rz.setText(f"Rz {rz:.2f}")
            
            # -------------------------------------------------
            # Joint positions
            # [base, shoulder, elbow, wrist1, wrist2, wrist3]
            # [   0,        1,     2,      3,      4,      5]
            # -------------------------------------------------

            joints = self.rtde_r.getActualQ()

            self.ui.value_J1.setText(
                f"J1 {math.degrees(joints[0]):.0f}°"
            )

            self.ui.value_J2.setText(
                f"J2 {math.degrees(joints[1]):.0f}°"
            )

            self.ui.value_J3.setText(
                f"J3 {math.degrees(joints[2]):.0f}°"
            )

            self.ui.value_J4.setText(
                f"J4 {math.degrees(joints[3]):.0f}°"
            )

            self.ui.value_J5.setText(
                f"J5 {math.degrees(joints[4]):.0f}°"
            )

            self.ui.value_J6.setText(
                f"J6 {math.degrees(joints[5]):.0f}°"
            )

        except Exception as e:
            print("RTDE read error:", e)

    # Read incoming command packet and live Safety speed
    def update_command_inspector(self, data):

        command = data.get("command") # moveL, moveJ
        #command_id = data.get("command_id") # code for move
            # X Y Z Rx Ry Rz for moveL
            #J1 2 3 4  5  6  for moveJ
        target = data.get("target")
        speed = data.get("speed")
        acceleration = data.get("acceleration")

        # Active Command 
        self.ui.value_cmd.setText(command)
    
        # TARGET position
                    # moveL or moveL_FK
        if command == "moveL": # moveL uses cartesian positions
    
            x = target[0] * 1000
            y = target[1] * 1000
            z = target[2] * 1000
    
            self.ui.value_position.setText(
                f"[{x:.1f}, {y:.1f}, {z:.1f}]"
            )
    
            self.ui.value_veloc.setText(
                f"{speed:.2f} m/s"
            )

            self.ui.value_accel.setText(
                f"{acceleration:.2f} m/s²"
            )

        # moveJ or  moveJ_IK
        elif command == "moveJ": # moveJ uses joint positions
    
            joints_deg = [
                math.degrees(q)
                for q in target
            ]
    
            self.ui.value_position.setText(
                "[" + ", ".join(f"{q:.0f}°"
                    for q in joints_deg
                ) +"]"
            )
    
            self.ui.value_veloc.setText(
                f"{speed:.2f} rad/s"
            )
    
            self.ui.value_accel.setText(
                f"{acceleration:.2f} rad/s²"
            )


    # Not every data packet includes gripper
    #def update_gripper_command(self, data):
    #    gripper = data["gripper"]
    #    
    #    self.ui.value_gripper.setText(gripper)

    # Read network access control and authorization 
    def update_network_access(self, data):
        global rejectCount # for IP violation and also displaying 

        client_IP = data.get("client_ip") # moveL, moveJ

        destination_port = data.get("port")
        ip_decision = data.get("ip_decision")
        
        # Network info 
        self.ui.value_ip.setText(client_IP)

        # https://www.universal-robots.com/articles/ur/interface-communication/remote-control-via-tcpip/ 

        if destination_port == 30001 or destination_port == 30011:
            self.ui.value_port.setText(str(destination_port) + " (Primary)")
        
        elif destination_port == 30002 or destination_port == 30012:
            self.ui.value_port.setText(str(destination_port) + " (Secondary)")

        elif destination_port == 30003 or destination_port == 30013:
            self.ui.value_port.setText(str(destination_port) + " (Real-time)")
        
        elif destination_port == 30004:
            self.ui.value_port.setText(str(destination_port) + " (RTDE)")

        if ip_decision == True:
            self.ui.value_authorize.setText("Authorized")
            self.ui.value_authorize.setStyleSheet(
                "background-color: lightgreen;"
                "border-radius: 10px;"
                "border: none;"
                "padding: 4px 10px;"
            )
        else:
            rejectCount += 1
            self.ui.value_authorize.setText("Blocked")
            self.ui.value_authorize.setStyleSheet(
                "background-color: #ffb3b3;"
                "border-radius: 10px;"
                "border: none;"
                "padding: 4px 10px;"
            )

        self.ui.value_packets.setText(str(rejectCount))
    

    # Read Safety Parameter Interlock
    def update_safety_interlock(self, data):
        global rejectCount # for when movement violation detected

        command = data.get("command")
        speed = data.get("speed")
        accel = data.get("acceleration")
        allowed = data.get("allowed")
        reason = data.get("reason")

        if command == "moveL":
            self.ui.value_req_speed.setText(f"{speed:.2f} m/s")
            self.ui.value_req_accel.setText(f"{accel:.2f} m/s²")
        elif command == "moveJ":
            self.ui.value_req_speed.setText(f"{speed:.2f} rad/s")
            self.ui.value_req_accel.setText(f"{accel:.2f} rad/s²")

        # reset after a violation happened
        self.ui.value_req_speed.setStyleSheet("QLabel {\n"
            "    border: none;\n"
            "    color: black;\n"
            "    font-weight: normal;\n"
            "}")
        self.ui.value_req_accel.setStyleSheet("QLabel {\n"
            "    border: none;\n"
            "    color: black;\n"
            "    font-weight: normal;\n"
            "}")

        if allowed:
            self.ui.violation_status.setText(f"No violation detected")
            self.ui.violation_status.setStyleSheet("QLabel {\n"
                "    font-weight: bold;\n"
                "    border: none;\n"
                "    color: black;\n"
                "}")            
            self.ui.violation_action.setText(f"Command forwarded and robot in motion")
            self.ui.violation_action.setStyleSheet("QLabel {\n"
                "    border: none;\n"
                "    color: black;\n"
                "}")
            self.ui.fraViolation.setStyleSheet("QFrame {\n"
                "    background-color: lightgreen;\n"
                "    border: 1px solid #AFCFEB;\n"
                "    border-radius: 8px;\n"
                "}")
            self.ui.LBL_INTERLO.setText(f"Safety Parameter Interlock")
            self.ui.fraSafety.setStyleSheet("QFrame {\n"
                "    background-color: white;\n"
                "    border: none;\n"
                "}")
        else:
            rejectCount += 1
            self.ui.value_packets.setText(str(rejectCount))

            self.ui.LBL_INTERLO.setText(f"⚠️ Safety Parameter Interlock")
            self.ui.fraSafety.setStyleSheet("QFrame {\n"
                "    background-color: white;\n"
                "    border: 3px solid #FF0000;\n"
                "    border-radius: 8px;\n"
                "}")
            self.ui.fraViolation.setStyleSheet("QFrame {\n"
                "    background-color: #FFD180;\n"
                "    border: none;\n"
                "}")
            self.ui.violation_status.setText(f"Violation detected")
            self.ui.violation_status.setStyleSheet("QLabel {\n"
                "    font-weight: bold;"
                "    border: none;\n"
                "    color: #8B0000;\n"
                "}")
            self.ui.violation_action.setText(f"Command blocked and robot placed on hold")
            self.ui.violation_action.setStyleSheet("QLabel {\n"
                "    border: none;\n"
                "    color: #8B0000;\n"
                "}")

            # if speed was the violation
            # if no match is found, re.search returns None
            if re.search(r'^Velocity', reason):
                if command == "moveL":
                    self.ui.value_req_speed.setText(f"{speed:.2f} m/s ⚠️")
                else: # "moveJ"
                    self.ui.value_req_speed.setText(f"{speed:.2f} rad/s ⚠️")
                
                self.ui.value_req_speed.setStyleSheet("QLabel {\n"
                    "    border: none;\n"
                    "    color: #8B0000;\n"
                    "    font-weight: bold;\n"
                    "}")
            
            else: # Acceleration is reason
                if command == "moveL":
                    self.ui.value_req_accel.setText(f"{accel:.2f} m/s² ⚠️")
                else: # "moveJ"
                    self.ui.value_req_accel.setText(f"{accel:.2f} rad/s² ⚠️")
                
                self.ui.value_req_accel.setStyleSheet("QLabel {\n"
                    "    border: none;\n"
                    "    color: #8B0000;\n"
                    "    font-weight: bold;\n"
                    "}")


        
# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    window = SafetyDashboard()
    window.show()

    sys.exit(app.exec_())