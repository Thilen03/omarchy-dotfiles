#!/usr/bin/env python3
import json
import psutil
import subprocess
import os
import re
import time
import shutil
import glob

# ---------------------------
# CONFIG / ICONS
# ---------------------------
CPU_ICON = "󰻠"  # nf-md-cpu_64_bit
GPU_ICON = "󰢮"  # nf-md-expansion_card
MEM_ICON = "󰍛"  # nf-md-memory
SSD_ICON = "󰋊"  # nf-md-harddisk
HDD_ICON = "󰋊"  # nf-md-harddisk
PINK = "#f5c2e7"

COLOR_TABLE = [
    {"color": "#8caaee", "cpu_gpu_temp": (0, 25),  "cpu_power": (0.0, 20),   "gpu_power": (0.0, 50),   "mem_storage": (0.0, 10)},
    {"color": "#99d1db", "cpu_gpu_temp": (26, 30), "cpu_power": (21.0, 40),  "gpu_power": (51.0, 100), "mem_storage": (10.0, 20)},
    {"color": "#81c8be", "cpu_gpu_temp": (31, 45), "cpu_power": (41.0, 60),  "gpu_power": (101.0,200), "mem_storage": (20.0, 40)},
    {"color": "#e5c890", "cpu_gpu_temp": (46, 60), "cpu_power": (61.0, 80),  "gpu_power": (201.0,300), "mem_storage": (40.0, 60)},
    {"color": "#ef9f76", "cpu_gpu_temp": (61, 75), "cpu_power": (81.0, 100), "gpu_power": (301.0,400), "mem_storage": (60.0, 80)},
    {"color": "#ea999c", "cpu_gpu_temp": (76, 85), "cpu_power": (101.0,120), "gpu_power": (401.0,450), "mem_storage": (80.0, 90)},
    {"color": "#e78284", "cpu_gpu_temp": (86,999), "cpu_power": (121.0,999), "gpu_power": (451.0,999), "mem_storage": (90.0,100)}
]

def get_color(value, metric_type):
    try:
        value = float(value)
    except:
        return "#ffffff"
    for entry in COLOR_TABLE:
        low, high = entry.get(metric_type, (0, 0))
        if low <= value <= high:
            return entry["color"]
    return COLOR_TABLE[-1]["color"]

def color_text(value, metric_type):
    return f"<span foreground='{get_color(value, metric_type)}'>{value}</span>"

# ---------------------------
# CPU STATS
# ---------------------------
cpu_percent = psutil.cpu_percent(interval=0.5)
cpu_freq = psutil.cpu_freq()
cpu_current = cpu_freq.current if cpu_freq else 0
cpu_max = cpu_freq.max if cpu_freq else 0

max_cpu_temp = 0
try:
    temps = psutil.sensors_temperatures()
    k10 = temps.get("k10temp", []) or []
    
    # Collect all available temperature readings
    temp_readings = []
    for t in k10:
        if t.current and t.current > 0:
            temp_readings.append(t.current)
    
    # Use average of all sensors (like btop does)
    if temp_readings:
        max_cpu_temp = sum(temp_readings) / len(temp_readings)
except:
    max_cpu_temp = 0

# CPU Power - AMD Ryzen power monitoring
cpu_power = 0.0

# Method 1: Try nct6687 Super I/O chip (common on AMD motherboards)
try:
    for hwmon in os.listdir("/sys/class/hwmon"):
        hwmon_dir = os.path.join("/sys/class/hwmon", hwmon)
        name_file = os.path.join(hwmon_dir, "name")
        if os.path.exists(name_file):
            with open(name_file) as f:
                name = f.read().strip()
            if "nct66" in name.lower():  # nct6687, nct6683, etc.
                # Look for CPU power in voltage/current readings
                power_files = glob.glob(os.path.join(hwmon_dir, "power*_input"))
                if power_files:
                    for pf in power_files:
                        try:
                            with open(pf) as f:
                                power_val = float(f.read().strip()) / 1000000  # microwatts to watts
                                # CPU power is usually 50-150W, filter out unrealistic values
                                if 10 < power_val < 300:
                                    cpu_power = power_val
                                    break
                        except:
                            pass
                if cpu_power > 0:
                    break
except:
    pass

# Method 2: Try AMD RAPL through sysfs energy counters
if cpu_power == 0.0:
    try:
        # Check for AMD CPU energy counter in hwmon
        for hwmon in os.listdir("/sys/class/hwmon"):
            hwmon_dir = os.path.join("/sys/class/hwmon", hwmon)
            name_file = os.path.join(hwmon_dir, "name")
            if os.path.exists(name_file):
                with open(name_file) as f:
                    name = f.read().strip()
                if name in ["k10temp", "zenpower"]:
                    energy_file = os.path.join(hwmon_dir, "energy1_input")
                    if os.path.exists(energy_file):
                        with open(energy_file) as f:
                            e1 = int(f.read().strip())
                        time.sleep(0.5)
                        with open(energy_file) as f:
                            e2 = int(f.read().strip())
                        cpu_power = ((e2 - e1) / 1000000) / 0.5  # microjoules to watts
                        break
    except:
        pass

# Method 3: Try Intel RAPL (your system has it, though it's an AMD CPU)
if cpu_power == 0.0:
    try:
        energy_file = "/sys/class/powercap/intel-rapl:0/energy_uj"
        if os.path.exists(energy_file):
            with open(energy_file) as f:
                e1 = int(f.read().strip())
            time.sleep(0.5)
            with open(energy_file) as f:
                e2 = int(f.read().strip())
            cpu_power = ((e2 - e1) / 1e6) / 0.5
    except:
        pass

# ---------------------------
# GPU STATS (AMD)
# ---------------------------
gpu_util = 0
gpu_temp = 0
gpu_power = 0.0
gpu_freq = 0
gpu_max_freq = 0
gpu_name = "PowerColor RX 6900 XT"

# Try rocm-smi first (most reliable for AMD)
try:
    out = subprocess.check_output(
        ["rocm-smi", "--showuse", "--showpower", "--showtemp", "--showclocks"],
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=2
    )
    
    # Don't parse GPU name from rocm-smi, keep hardcoded name
    
    # Parse utilization (GPU use %)
    match_util = re.search(r'GPU use \(%\)\s*:\s*(\d+)', out)
    if match_util:
        gpu_util = int(match_util.group(1))
    
    # Parse power (Average Graphics Package Power)
    match_power = re.search(r'Average Graphics Package Power \(W\)\s*:\s*([\d\.]+)', out)
    if match_power:
        gpu_power = float(match_power.group(1))
    
    # Parse temperature (Temperature - edge)
    match_temp = re.search(r'Temperature \(Sensor edge\) \(C\)\s*:\s*([\d\.]+)', out)
    if match_temp:
        gpu_temp = int(float(match_temp.group(1)))
    
    # Parse current clock - multiple methods to find active clock
    # Method 1: Look for lines with asterisk (active state marker)
    for line in out.split('\n'):
        if '*' in line and 'Mhz' in line.lower():
            match = re.search(r'(\d+)\s*Mhz', line, re.IGNORECASE)
            if match:
                gpu_freq = int(match.group(1))
                break
    
    # Method 2: If still 0, try sclk pattern
    if gpu_freq == 0:
        match_clock = re.search(r'sclk.*?(\d+)\s*Mhz', out, re.IGNORECASE | re.DOTALL)
        if match_clock:
            gpu_freq = int(match_clock.group(1))
    
    # Parse max clock - look for highest clock value
    all_clocks = re.findall(r'(\d+)\s*Mhz', out, re.IGNORECASE)
    if all_clocks:
        gpu_max_freq = max(int(c) for c in all_clocks)

except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
    # Fallback to sysfs for AMD GPU
    try:
        # Find AMD GPU card
        drm_base = "/sys/class/drm"
        card_path = None
        
        for card in ["card0", "card1", "card2"]:
            card_dir = os.path.join(drm_base, card, "device")
            if os.path.exists(card_dir):
                vendor_file = os.path.join(card_dir, "vendor")
                if os.path.exists(vendor_file):
                    with open(vendor_file) as f:
                        vendor = f.read().strip()
                    if vendor == "0x1002":  # AMD vendor ID
                        card_path = card_dir
                        break
        
        if card_path:
            # Don't parse GPU name from sysfs, keep hardcoded name
            
            # Get hwmon path
            hwmon_dir = os.path.join(card_path, "hwmon")
            if os.path.exists(hwmon_dir):
                hwmons = os.listdir(hwmon_dir)
                if hwmons:
                    hwmon_path = os.path.join(hwmon_dir, hwmons[0])
                    
                    # Temperature
                    temp_path = os.path.join(hwmon_path, "temp1_input")
                    if os.path.exists(temp_path):
                        with open(temp_path) as f:
                            gpu_temp = int(f.read().strip()) // 1000
                    
                    # Power (in microwatts)
                    power_path = os.path.join(hwmon_path, "power1_average")
                    if os.path.exists(power_path):
                        with open(power_path) as f:
                            gpu_power = float(f.read().strip()) / 1000000
            
            # GPU utilization
            busy_path = os.path.join(card_path, "gpu_busy_percent")
            if os.path.exists(busy_path):
                with open(busy_path) as f:
                    gpu_util = int(f.read().strip())
            
            # GPU clock frequency
            sclk_path = os.path.join(card_path, "pp_dpm_sclk")
            if os.path.exists(sclk_path):
                with open(sclk_path) as f:
                    lines = f.readlines()
                    for line in lines:
                        if '*' in line:  # Current clock marked with *
                            match = re.search(r'(\d+)Mhz', line)
                            if match:
                                gpu_freq = int(match.group(1))
                        # Get last line for max freq
                        match = re.search(r'(\d+)Mhz', lines[-1])
                        if match:
                            gpu_max_freq = int(match.group(1))
    except:
        pass

# Try NVIDIA as final fallback
if gpu_temp == 0 and gpu_name == "Unknown GPU":
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,power.draw,utilization.gpu,clocks.gr,clocks.max.gr",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2
        )
        parts = out.strip().split(", ")
        if len(parts) >= 6:
            gpu_name = parts[0]
            gpu_temp = int(parts[1])
            gpu_power = float(parts[2])
            gpu_util = int(parts[3])
            gpu_freq = int(parts[4])
            gpu_max_freq = int(parts[5])
    except:
        pass

# ---------------------------
# MEMORY STATS
# ---------------------------
mem = psutil.virtual_memory()
mem_used = mem.used / (1024**3)
mem_total = mem.total / (1024**3)
mem_percent = mem.percent

ram_temps = []
hwmon_dir = "/sys/class/hwmon"
if os.path.exists(hwmon_dir):
    for hw in os.listdir(hwmon_dir):
        name_file = os.path.join(hwmon_dir, hw, "name")
        if os.path.exists(name_file):
            try:
                with open(name_file) as f:
                    name = f.read().strip()
                # Look for memory thermal sensors
                if "dimm" in name.lower() or "mem" in name.lower():
                    temp_file = os.path.join(hwmon_dir, hw, "temp1_input")
                    if os.path.exists(temp_file):
                        with open(temp_file) as f:
                            t = int(f.read().strip()) / 1000
                            ram_temps.append(t)
            except:
                pass

# ---------------------------
# STORAGE STATS
# ---------------------------
EXCLUDE = {"pkg", "log", "boot"}
partitions = [p for p in psutil.disk_partitions(all=False)
              if 'rw' in p.opts and p.fstype and os.path.basename(p.mountpoint) not in EXCLUDE]

# Map drives by size to custom names (avoid duplicates)
storage_entries = []
seen_labels = set()

for p in partitions:
    try:
        usage_info = psutil.disk_usage(p.mountpoint)
        usage = usage_info.percent
        total_gb = usage_info.total / (1024**3)
        
        # Identify drives by size
        if 1800 < total_gb < 2200:  # 2TB drive
            label = "Omarchy Linux"
            icon = SSD_ICON
        elif 900 < total_gb < 1200:  # 1TB drive
            label = "Linux Games"
            icon = SSD_ICON
        else:
            label = os.path.basename(p.mountpoint) or "Unknown"
            icon = HDD_ICON
        
        # Skip if we've already added this label
        if label not in seen_labels:
            storage_entries.append((icon, label, usage))
            seen_labels.add(label)
    except:
        pass

# ---------------------------
# TOP BAR TEXT (CPU temp, GPU temp, RAM usage only)
# ---------------------------
top_text = (
    f"{CPU_ICON} {color_text(f'{max_cpu_temp:.0f}' if max_cpu_temp else '0','cpu_gpu_temp')}°C  "
    f"{GPU_ICON} {color_text(f'{gpu_temp}','cpu_gpu_temp')}°C  "
    f"{MEM_ICON} {color_text(f'{mem_percent:.0f}','mem_storage')}%"
)

# ---------------------------
# TOOLTIP
# ---------------------------
tooltip_lines = []

# CPU
tooltip_lines.append(f"<span foreground='{PINK}'>{CPU_ICON} CPU:</span>")
tooltip_lines.append(f"Type: AMD Ryzen 7 5800X3D")
tooltip_lines.append(f"Freq: {color_text(f'{cpu_current:.0f}','cpu_power')} / {cpu_max:.0f} MHz")
tooltip_lines.append(f"Temp: {color_text(f'{max_cpu_temp:.1f}' if max_cpu_temp else '0','cpu_gpu_temp')}°C")
tooltip_lines.append(f"Power: {color_text(f'{cpu_power:.1f}','cpu_power')} W")
tooltip_lines.append(f"Util: {color_text(f'{cpu_percent:.0f}','cpu_power')}%")
tooltip_lines.append("─"*30)

# GPU
tooltip_lines.append(f"<span foreground='{PINK}'>{GPU_ICON} GPU:</span>")
tooltip_lines.append(f"Type: {gpu_name}")
tooltip_lines.append(f"Freq: {color_text(f'{gpu_freq}','gpu_power')} / {gpu_max_freq} MHz")
tooltip_lines.append(f"Temp: {color_text(f'{gpu_temp}','cpu_gpu_temp')}°C")
tooltip_lines.append(f"Power: {color_text(f'{gpu_power:.1f}','gpu_power')} W")
tooltip_lines.append(f"Util: {color_text(f'{gpu_util}','gpu_power')}%")
tooltip_lines.append("─"*30)

# RAM
tooltip_lines.append(f"<span foreground='{PINK}'>{MEM_ICON} RAM:</span>")
tooltip_lines.append(f"Usage: {mem_used:.1f}/{mem_total:.1f} GB ({color_text(f'{mem_percent:.0f}','mem_storage')}%)")
if ram_temps:
    for i, t in enumerate(ram_temps[:4]):  # Limit to 4 slots
        tooltip_lines.append(f"Slot {i+1}: Temp {color_text(f'{t:.0f}','cpu_gpu_temp')}°C")
tooltip_lines.append("─"*30)

# Storage
tooltip_lines.append(f"<span foreground='{PINK}'>{SSD_ICON} Storage:</span>")
for icon, name, usage in storage_entries:
    if usage is not None:
        tooltip_lines.append(f"{icon} {name}: {color_text(f'{usage:.0f}','mem_storage')}%")
tooltip_lines.append("─"*30)

# Click hints
tooltip_lines.append("🖱️ LMB: Btop | 🖱️ RMB: CoolerControl")

# ---------------------------
# OUTPUT
# ---------------------------
TERMINAL = os.environ.get("TERMINAL") or shutil.which("alacritty") or shutil.which("kitty") or "xterm"
click_type = os.environ.get("WAYBAR_CLICK_TYPE")

if click_type == "left":
    subprocess.Popen([TERMINAL, "-e", "btop"])
elif click_type == "right":
    subprocess.Popen(["coolercontrol"])

output = {
    "text": top_text,
    "tooltip": "\n".join(tooltip_lines),
    "class": "custom-system-monitor",
    "percentage": int(max(cpu_percent, gpu_util, mem_percent))
}

print(json.dumps(output))