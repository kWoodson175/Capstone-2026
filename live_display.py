from PyQt5 import QtCore, QtWidgets
from GUI_framework import Ui_MainWindow
#from packet_capturer import RTDEPacketCapture
from proxy_translator import ProxyCommandSource
from rtde_receive import RTDEReceiveInterface as RTDEReceive

import sys
import math # for degrees
import time # for timers

# ---------------------------------------------------------
# Robot connection
# ---------------------------------------------------------

ROBOT_IP = "192.168.56.101"   # URSim
#ROBOT_IP = "192.168.1.112"  # Physical robot, if applicable

UPDATE_INTERVAL_MS = 100 #  100 ms = 0.1 sec

class SafetyDashboard(QtWidgets.QMainWindow):

    # Stop proxy when dashboard closes
    def closeEvent(self, event):
        if hasattr(self, "proxy_source"):
            self.proxy_source.stop()
        event.accept()

    def __init__(self):
        super().__init__()

        # Build interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ---------------------------------------------------------
        # URobot_proxy command source
        # ---------------------------------------------------------
        proxy_path = QtCore.QDir.current().absoluteFilePath("display_proxy.py")
        self.proxy_source = ProxyCommandSource(proxy_path, self)

        self.proxy_source.command_received.connect(self.update_command_inspector)
        self.proxy_source.network_received.connect(self.update_network_access)
        self.proxy_source.proxy_message.connect(
            lambda message: print("[PROXY]", message)
        )
        self.proxy_source.proxy_error.connect(print)

        self.proxy_source.start()
        
        # Robot connection starts empty
        self.rtde_r = None

        # Attempt RTDE connection
        self.connect_robot()

        # Update display every 100 ms
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_system_status)
        self.timer.timeout.connect(self.update_rtde_data)
        self.timer.start(UPDATE_INTERVAL_MS)

    # Connect to UR robot and authorization 
    def connect_robot(self):
        try:
            print(f"Connecting to robot at {ROBOT_IP}...")
            self.rtde_r = RTDEReceive(ROBOT_IP)
            print("Connected.")

            self.ui.value_authorize.setText("Authorized")
            self.ui.value_authorize.setStyleSheet(
                "background-color: lightgreen;"
                "border-radius: 10px;"
                "padding: 4px 10px;"
            )            

        except Exception as e:

            self.rtde_r = None

            self.ui.value_authorize.setText("Blocked")
            self.ui.value_authorize.setStyleSheet(
                "background-color: #ffb3b3;"
                "border-radius: 10px;"
                "padding: 4px 10px;"
            )

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
                self.ui.value_system_action.setText("System running")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: lightgreen;"
                    "    font-weight: bold;"                    
                )

            elif runtime_state == 4:
                self.ui.value_system_action.setText("System on hold")
                self.ui.value_system_action.setStyleSheet(
                    f"background-color: #ffe699;"
                    "    font-weight: bold;"
                )
            elif runtime_state == 1:
                self.ui.value_system_action.setText("System stopped")
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
            # Convert to millimeters for display.
            self.ui.value_X.setText(f"X {x * 1000:.1f}")
            self.ui.value_Y.setText(f"Y {y * 1000:.1f}")
            self.ui.value_Z.setText(f"Z {z * 1000:.1f}")

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

    # Read incoming command packet
    def update_command_inspector(self, data):

        command = data["command"] # moveL, moveJ
        command_id = data["command_id"] # code for move
            # X Y Z Rx Ry Rz for moveL
            #J1 2 3 4  5  6  for moveJ
        target = data["target"]
        speed = data["speed"]
        acceleration = data["acceleration"]

        # Active Command 
        self.ui.value_cmd.setText(command)
    
        # TARGET position
                    # moveL or moveL_FK
        if command_id == 3 or command_id == 4: # moveL uses cartesian positions
    
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
        elif command_id == 1 or command_id == 2: # moveJ uses joint positions
    
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

    # not every data includes gripper
    def update_gripper_command(self, data):
        gripper = data["gripper"]
        
        self.ui.value_gripper.setText(gripper)

    # Read network access control
    def update_network_access(self, data):

        source_IP = data["source_ip"]
        destination_port = data["destination_port"]
        
        # Network info 
        self.ui.value_ip.setText(source_IP)

        # https://www.universal-robots.com/articles/ur/interface-communication/remote-control-via-tcpip/ 

        if destination_port == 30001 or destination_port == 30011:
            self.ui.value_port.setText(str(destination_port) + " (Primary)")
        
        elif destination_port == 30002 or destination_port == 30012:
            self.ui.value_port.setText(str(destination_port) + " (Secondary)")

        elif destination_port == 30003 or destination_port == 30013:
            self.ui.value_port.setText(str(destination_port) + " (Real-time)")
        
        elif destination_port == 30004:
            self.ui.value_port.setText(str(destination_port) + " (RTDE)")

 
# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    window = SafetyDashboard()
    window.show()

    sys.exit(app.exec_())