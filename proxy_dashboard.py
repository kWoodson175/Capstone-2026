import sys
import threading
from datetime import datetime
from PyQt5 import QtWidgets, QtCore

# 1. Import your partner's UI class
from GUI_framework import Ui_MainWindow

# 2. Import your proxy engine, queue, and stop command
from display_proxy import start_proxy, security_event_queue, send_stop_command

# 3. Import the entire security policy module for direct variable access
import security_policy

class DashboardApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Set up the UI from your partner's file
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Pre-fill the static safety limits directly from your policy
        self.ui.value_vel_limit.setText(f"{security_policy.MAX_VELOCITY} m/s")
        self.ui.value_accel_limit.setText(f"{security_policy.MAX_ACCELERATION} m/s²")

        # Wire up the manual E-STOP button to your proxy's stop command
        self.ui.stop_button.clicked.connect(self.trigger_manual_stop)

        # Set up the Queue checking timer (Checks every 50ms)
        self.queue_timer = QtCore.QTimer()
        self.queue_timer.timeout.connect(self.process_queue)
        self.queue_timer.start(50)

    def trigger_manual_stop(self):
        """Fires when the E-STOP button is clicked."""
        send_stop_command()
        self.ui.violation_status.setText("🛑 MANUAL E-STOP TRIGGERED")
        self.ui.violation_status.setStyleSheet("color: red; font-weight: bold;")
        self.add_log_entry("STOP", "Manual E-Stop button pressed")

    def process_queue(self):
        """Pulls events from the background proxy thread."""
        while not security_event_queue.empty():
            event = security_event_queue.get()
            self.update_dashboard(event)
            security_event_queue.task_done()

    def update_dashboard(self, event):
        """Maps your proxy dictionary keys to your partner's PyQt labels."""
        
        # Handle Gripper Events
        if event.get("event_type") == "gripper":
            self.ui.value_gripper.setText(event.get("gripper"))
            self.ui.value_cmd.setText("Gripper Command")
            self.add_log_entry("Gripper", event.get("gripper"))
            return

        # Network Info Update
        self.ui.value_ip.setText(event.get("source_ip", "Unknown"))
        self.ui.value_port.setText(str(event.get("destination_port", "Unknown")))
        self.ui.value_authorize.setText("Authorized" if event.get("source_ip") == "127.0.0.1" else "Unknown")
        self.ui.value_authorize.setStyleSheet("color: green;" if event.get("source_ip") == "127.0.0.1" else "color: red;")

        # Kinematic Command Info Update
        self.ui.value_cmd.setText(event.get("command", "None"))
        speed = event.get("speed", 0.0)
        accel = event.get("acceleration", 0.0)
        
        self.ui.value_veloc.setText(f"{speed:.4f} m/s")
        self.ui.value_req_speed.setText(f"{speed:.4f} m/s")
        self.ui.value_accel.setText(f"{accel:.4f} m/s²")
        self.ui.value_req_accel.setText(f"{accel:.4f} m/s²")

        # Update Target Coordinates (Only if it's an RTDE packet with a valid list)
        target = event.get("target")
        if isinstance(target, list) and len(target) >= 6:
            self.ui.value_X.setText(f"X {target[0]*1000:.1f}")
            self.ui.value_Y.setText(f"Y {target[1]*1000:.1f}")
            self.ui.value_Z.setText(f"Z {target[2]*1000:.1f}")
            self.ui.value_Rx.setText(f"Rx {target[3]:.3f}")
            self.ui.value_Ry.setText(f"Ry {target[4]:.3f}")
            self.ui.value_Rz.setText(f"Rz {target[5]:.3f}")
        else:
            # Fallback for text commands where coordinates aren't extracted
            self.ui.value_X.setText("X N/A")
            self.ui.value_Y.setText("Y N/A")
            self.ui.value_Z.setText("Z N/A")
            self.ui.value_Rx.setText("Rx N/A")
            self.ui.value_Ry.setText("Ry N/A")
            self.ui.value_Rz.setText("Rz N/A")

        # Violation Interlock Update
        if event.get("allowed"):
            self.ui.violation_status.setText("✅ ALL CLEAR")
            self.ui.violation_status.setStyleSheet("color: green; font-weight: bold;")
            self.ui.violation_action.setText("Command forwarded to URSim safely.")
        else:
            self.ui.violation_status.setText("🚨 POLICY VIOLATION")
            self.ui.violation_status.setStyleSheet("color: red; font-weight: bold;")
            self.ui.violation_action.setText(f"BLOCKED: {event.get('reason')}")

        # Add event to the Audit Log table
        event_type = "Pass" if event.get("allowed") else "Block"
        self.add_log_entry(event_type, event.get("raw_command", "Binary Packet"))

    def add_log_entry(self, event_type, description):
        """Inserts a new row into the QTableWidget."""
        # Insert at the top (row 0) so newest events are always visible
        self.ui.tableEvents.insertRow(0)
        
        time_str = datetime.now().strftime("%H:%M:%S")
        self.ui.tableEvents.setItem(0, 0, QtWidgets.QTableWidgetItem(time_str))
        self.ui.tableEvents.setItem(0, 1, QtWidgets.QTableWidgetItem(event_type))
        self.ui.tableEvents.setItem(0, 2, QtWidgets.QTableWidgetItem(description))

if __name__ == "__main__":
    # Start your proxy firewall in a background thread
    threading.Thread(target=start_proxy, daemon=True).start()

    # Launch the PyQt Dashboard
    app = QtWidgets.QApplication(sys.argv)
    window = DashboardApp()
    window.show()
    sys.exit(app.exec_())
