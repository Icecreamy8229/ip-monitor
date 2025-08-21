# External IP Monitor with EZOutlet Integration

A lightweight Python tool to monitor your external IP address.  
If your IP address changes from your configured primary address, the tool can take automated actions — such as notifying via webhook/API, or resetting an outlet on an **EZOutlet** device.  

This is especially useful for self-healing network setups where you need your modem or router to reboot automatically when connectivity changes.

---

## ✨ Features
- Monitor your external/public IP address at custom intervals  
- **Test mode** available to safely test without triggering real resets  
- Supports **multiple DNS providers** for resilient IP detection  
- Send notifications via **webhooks** or **custom APIs**  
- Define a **primary IP address** and multiple **secondary IPs** with descriptions  
- Tag each monitored site with a friendly **location name**  
- Automatic reset support for **EZOutlet** devices with configurable limits  
- Optional logging to track activity  
- Lightweight and works on Linux, macOS, and Windows (with included `run.bat`)

---

## ⚙️ Configuration

All settings are managed in `config.yaml`.