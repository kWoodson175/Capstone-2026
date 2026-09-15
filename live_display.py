from PyQt5 import QtCore, QtWidgets
from GUI_framework import Ui_MainWindow

from rtde_receive import RTDEReceiveInterface as RTDEReceive

import sys
import math


# ---------------------------------------------------------
# Robot connection
# ---------------------------------------------------------

ROBOT_IP = "192.168.56.101"   # URSim
# ROBOT_IP = "192.168.1.112"  # Physical robot, if applicable

UPDATE_INTERVAL_MS = 100

class SafetyDashboard(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        # Build interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Robot connection starts empty
        self.rtde_r = None

        # Attempt RTDE connection
        self.connect_robot()

        # Update display every 100 ms
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_robot_data)
        self.timer.start(UPDATE_INTERVAL_MS)

    # Connect to UR robot
    def connect_robot(self):

        try:
            print(f"Connecting to robot at {ROBOT_IP}...")

            self.rtde_r = RTDEReceive(ROBOT_IP)

            print("Connected.")

            #self.ui.value_ip.setText(ROBOT_IP)

            self.ui.value_authorize.setText("Authorized")
            self.ui.value_authorize.setStyleSheet(
                "background-color: lightgreen;"
                "border-radius: 10px;"
                "padding: 4px 10px;"
            )

            # may want to get rid of this
            self.ui.val_system_action.setText("System on")
            self.ui.val_system_action.setStyleSheet(
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

            self.ui.val_system_action.setText("System unavailable")
            self.ui.val_system_action.setStyleSheet(
                "background-color: #ffb3b3;"
                "border-radius: 10px;"
                "padding: 4px 10px;"
            )

            print("RTDE connection failed:", e)

    # Read live TCP pose and joint positions.
    def update_robot_data(self):

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

            self.ui.value_Rx.setText(f"Rx {rx:.3f}")
            self.ui.value_Ry.setText(f"Ry {ry:.3f}")
            self.ui.value_Rz.setText(f"Rz {rz:.3f}")

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


# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    window = SafetyDashboard()
    window.show()

    sys.exit(app.exec_())