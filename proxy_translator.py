from PyQt5 import QtCore
import re
import sys

class ProxyCommandSource(QtCore.QObject):
    command_received = QtCore.pyqtSignal(dict)
    network_received = QtCore.pyqtSignal(dict)
    proxy_message = QtCore.pyqtSignal(str)
    proxy_error = QtCore.pyqtSignal(str)

    def __init__(self, proxy_path="display_proxy.py", parent=None):
        super().__init__(parent)
        self.proxy_path = proxy_path
        self._stdout_buffer = ""

        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_proxy_output)
        self.process.errorOccurred.connect(self._process_error)
        self.process.finished.connect(self._process_finished)

    def start(self):
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-u", self.proxy_path])
        self.process.start()

    def stop(self):
        if self.process.state() != QtCore.QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1000)

    def _read_proxy_output(self):
        raw = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += raw

        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split("\n", 1)
            self._parse_proxy_line(line.strip())

    def _process_error(self, error):
        self.proxy_error.emit(f"URobot_proxy process error: {error}")

    def _process_finished(self, exit_code, exit_status):
        self.proxy_message.emit(
            f"URobot_proxy stopped: exit_code={exit_code}, exit_status={exit_status}"
        )

    def _parse_proxy_line(self, line):
        if not line:
            return

        self.proxy_message.emit(line)

        text_match = re.match(r"^\[TEXT (ALLOWED|BLOCKED)\]\s+(.+)$", line)
        if text_match:
            data = self._parse_text_command(text_match.group(2).strip())
            if data is not None:
                data["allowed"] = text_match.group(1) == "ALLOWED"
                data["source_ip"] = "127.0.0.1"
                data["destination_port"] = 30002
                self.command_received.emit(data)
                self.network_received.emit(data)
            return

        binary_match = re.match(r"^\[BINARY (ALLOWED|BLOCKED)\]\s+(.+)$", line)
        if binary_match:
            data = self._parse_binary_command(binary_match.group(2).strip())
            if data is not None:
                data["allowed"] = binary_match.group(1) == "ALLOWED"
                data["source_ip"] = "127.0.0.1"
                data["destination_port"] = 30004
                self.command_received.emit(data)
                self.network_received.emit(data)

    def _parse_text_command(self, command_text):
        name_match = re.match(r"^\s*(movel|movej|speedl)\s*\(", command_text, re.IGNORECASE)
        if not name_match:
            return None

        command_map = {
            "movej": ("moveJ", 1),
            "movel": ("moveL", 3),
            "speedl": ("speedL", 11),
        }
        command, command_id = command_map[name_match.group(1).lower()]

        vector_match = re.search(r"(?:p\s*)?\[\s*([^\]]+)\]", command_text, re.IGNORECASE)
        if vector_match is None:
            return None

        try:
            target = [float(v.strip()) for v in vector_match.group(1).split(",")]
        except ValueError:
            return None

        v_match = re.search(r"\bv\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)", command_text, re.IGNORECASE)
        a_match = re.search(r"\ba\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)", command_text, re.IGNORECASE)

        if v_match is None or a_match is None:
            return None

        return {
            "command": command,
            "command_id": command_id,
            "target": target,
            "speed": float(v_match.group(1)),
            "acceleration": float(a_match.group(1)),
        }

    def _parse_binary_command(self, command_text):
        match = re.match(
            r"^\s*(moveL|moveJ|speedL)\s*"
            r"\(\s*\[\s*([^\]]+)\]\s*,\s*"
            r"a\s*=\s*([-+0-9.eE]+)\s*,\s*"
            r"v\s*=\s*([-+0-9.eE]+)\s*\)\s*$",
            command_text,
            re.IGNORECASE,
        )
        if match is None:
            return None

        command_map = {
            "movej": ("moveJ", 1),
            "movel": ("moveL", 3),
            "speedl": ("speedL", 11),
        }
        command, command_id = command_map[match.group(1).lower()]

        try:
            target = [float(v.strip()) for v in match.group(2).split(",")]
            acceleration = float(match.group(3))
            speed = float(match.group(4))
        except ValueError:
            return None

        return {
            "command": command,
            "command_id": command_id,
            "target": target,
            "speed": speed,
            "acceleration": acceleration,
        }
