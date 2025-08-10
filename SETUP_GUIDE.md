# FRP Freedom Setup Guide

## 📋 Prerequisites

Before using FRP Freedom, you need to install and configure several tools and dependencies.

### 1. System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **USB Port**: Available USB port for device connection
- **Internet Connection**: For downloading tools and dependencies

### 2. Required Tools

#### Android SDK Platform Tools
The Android SDK Platform Tools include ADB (Android Debug Bridge) and Fastboot, which are essential for device communication.

**Download and Installation:**

1. **Download Platform Tools:**
   - Visit: https://developer.android.com/studio/releases/platform-tools
   - Download the appropriate version for your operating system

2. **Extract and Setup:**
   ```bash
   # Windows
   # Extract to C:\platform-tools
   # Add C:\platform-tools to your PATH environment variable
   
   # macOS/Linux
   unzip platform-tools-latest-*.zip
   sudo mv platform-tools /usr/local/
   echo 'export PATH="/usr/local/platform-tools:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Verify Installation:**
   ```bash
   adb version
   fastboot --version
   ```

#### Python Dependencies
Install the required Python packages:

```bash
# Navigate to the FRP Freedom directory
cd /path/to/FRP-Freedom

# Install dependencies
pip install -r requirements.txt
```

## 🔧 Device Preparation

### 1. Enable Developer Options

1. Go to **Settings** > **About Phone**
2. Tap **Build Number** 7 times
3. Developer Options will be enabled

### 2. Enable USB Debugging

1. Go to **Settings** > **Developer Options**
2. Enable **USB Debugging**
3. Enable **OEM Unlocking** (if available)

### 3. Install USB Drivers

#### Windows:
- Download and install the appropriate USB drivers for your device manufacturer
- Common drivers:
  - Samsung: Samsung USB Driver
  - LG: LG Mobile Switch
  - HTC: HTC Sync Manager
  - Universal: Google USB Driver

#### macOS/Linux:
- Most devices work out of the box
- For some devices, you may need to install manufacturer-specific drivers

## 🚀 Getting Started

### 1. Connect Your Device

1. Connect your Android device to your computer via USB
2. On your device, allow USB debugging when prompted
3. Verify connection:
   ```bash
   adb devices
   ```
   You should see your device listed

### 2. Launch FRP Freedom

1. **Run the Application:**
   ```bash
   python3 main.py
   ```

2. **Test Basic Functionality:**
   ```bash
   python3 test_app.py
   ```

### 3. Using the Application

1. **Device Detection:**
   - The application will automatically scan for connected devices
   - Your device should appear in the device list

2. **Select Bypass Method:**
   - Choose from available bypass methods based on your device
   - Methods are categorized by risk level and success rate

3. **Execute Bypass:**
   - Follow the on-screen instructions
   - Monitor the progress in real-time
   - Review results and logs

## 🛠️ Troubleshooting

### Common Issues

#### Device Not Detected
- **Check USB Connection:** Ensure cable is properly connected
- **Enable USB Debugging:** Make sure USB debugging is enabled
- **Install Drivers:** Install appropriate USB drivers for your device
- **Try Different Cable:** Use a different USB cable
- **Check ADB:** Run `adb devices` to verify ADB can see your device

#### ADB/Fastboot Not Found
- **Check PATH:** Ensure platform-tools are in your system PATH
- **Reinstall Platform Tools:** Download and reinstall Android SDK Platform Tools
- **Verify Installation:** Run `adb version` and `fastboot --version`

#### Permission Denied (Linux/macOS)
- **Add User to Group:**
  ```bash
  sudo usermod -a -G plugdev $USER
  ```
- **Create udev Rules:**
  ```bash
  sudo nano /etc/udev/rules.d/51-android.rules
  # Add: SUBSYSTEM=="usb", ATTR{idVendor}=="[VENDOR_ID]", MODE="0666", GROUP="plugdev"
  sudo udevadm control --reload-rules
  ```

#### Python Dependencies Issues
- **Update pip:**
  ```bash
  python3 -m pip install --upgrade pip
  ```
- **Install in Virtual Environment:**
  ```bash
  python3 -m venv frp_env
  source frp_env/bin/activate  # Linux/macOS
  # or
  frp_env\Scripts\activate  # Windows
  pip install -r requirements.txt
  ```

## 📱 Supported Devices

### Manufacturers
- Samsung (Galaxy series)
- LG (G series, V series)
- HTC (One series, Desire series)
- Huawei/Honor (P series, Mate series)
- Xiaomi/Redmi (Mi series, Redmi series)
- OnePlus (OnePlus series)
- Google (Pixel series)
- Motorola (Moto series)
- Sony (Xperia series)

### Android Versions
- Android 5.0 (API 21) through Android 15.0 (API 35)
- Various security patch levels supported

## ⚠️ Important Notes

### Legal Considerations
- **Only use on devices you own or have explicit permission to modify**
- **Comply with local laws and regulations**
- **This tool is for legitimate device recovery purposes only**

### Security
- **All activities are logged for audit purposes**
- **Logs are encrypted by default**
- **Review logs regularly for security monitoring**

### Backup
- **Always backup important data before proceeding**
- **Create a full device backup if possible**
- **Note down current firmware version and security patch level**

## 📞 Support

If you encounter issues:

1. **Check the logs** in the `logs/` directory
2. **Review the troubleshooting section** above
3. **Verify all prerequisites** are properly installed
4. **Test with a different device** if available

## 🔄 Updates

To update FRP Freedom:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Test the update
python3 test_app.py
```

---

**Remember: Use this tool responsibly and only on devices you own or have explicit permission to modify.**