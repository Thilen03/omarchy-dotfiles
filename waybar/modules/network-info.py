#!/usr/bin/env python3
import json
import time
import subprocess
import requests
import sys
from pathlib import Path

# Configuration
INTERFACE = "enp42s0"  # Change to your network interface (e.g., eth0, enp0s3, wlp2s0)
CACHE_FILE = "/tmp/waybar_net_cache"
CACHE_DURATION = 300  # Cache external IP for 5 minutes

def get_bytes(interface):
    """Get current transmitted and received bytes for interface"""
    try:
        rx_bytes = int(Path(f"/sys/class/net/{interface}/statistics/rx_bytes").read_text())
        tx_bytes = int(Path(f"/sys/class/net/{interface}/statistics/tx_bytes").read_text())
        return rx_bytes, tx_bytes
    except:
        return 0, 0

def get_local_ip(interface):
    """Get local IPv4 address"""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", interface],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if 'inet ' in line:
                return line.strip().split()[1].split('/')[0]
    except:
        pass
    return "N/A"

def get_external_ip():
    """Get external IP with caching"""
    try:
        cache_path = Path(CACHE_FILE)
        if cache_path.exists():
            cache_time = cache_path.stat().st_mtime
            if time.time() - cache_time < CACHE_DURATION:
                return cache_path.read_text().strip()
        
        # Fetch new external IP
        response = requests.get("https://api.ipify.org", timeout=3)
        external_ip = response.text.strip()
        
        # Cache the result
        cache_path.write_text(external_ip)
        return external_ip
    except:
        return "N/A"

def get_speed_color(bytes_per_sec):
    """Get color based on speed"""
    if bytes_per_sec < 1024 * 100:  # < 100 KB/s
        return "#61d261"  # green
    elif bytes_per_sec < 1024 * 1024:  # < 1 MB/s
        return "#5fd7ff"  # light blue
    elif bytes_per_sec < 1024 * 1024 * 10:  # < 10 MB/s
        return "#ffaf00"  # orange
    else:  # >= 10 MB/s
        return "#ff5f5f"  # red

def format_speed(bytes_per_sec):
    """Format bytes per second to human readable format with color"""
    color = get_speed_color(bytes_per_sec)
    if bytes_per_sec < 1024:
        return f'<span color="{color}">{bytes_per_sec:.0f} B/s</span>'
    elif bytes_per_sec < 1024 * 1024:
        return f'<span color="{color}">{bytes_per_sec / 1024:.1f} KB/s</span>'
    else:
        return f'<span color="{color}">{bytes_per_sec / (1024 * 1024):.1f} MB/s</span>'

def main():
    # Handle special arguments for copying IPs
    if len(sys.argv) > 1:
        if sys.argv[1] == "--local-ip":
            print(get_local_ip(INTERFACE))
            return
        elif sys.argv[1] == "--external-ip":
            print(get_external_ip())
            return
    
    # Get previous values
    try:
        with open("/tmp/waybar_net_prev", "r") as f:
            data = json.load(f)
            prev_rx, prev_tx, prev_time = data["rx"], data["tx"], data["time"]
    except:
        prev_rx, prev_tx = get_bytes(INTERFACE)
        prev_time = time.time()
        # Save and output zero speeds on first run
        with open("/tmp/waybar_net_prev", "w") as f:
            json.dump({"rx": prev_rx, "tx": prev_tx, "time": prev_time}, f)
        
        output = {
            "text": f"󰈀 ↑ 0 B/s ↓ 0 B/s",
            "tooltip": f"<span color='#6acda2'>Local IP:</span> {get_local_ip(INTERFACE)}\n<span color='#6acda2'>External IP:</span> {get_external_ip()}\n\n🖱️ <span color='#6acda2'>LMB:</span> Copy Local IP\n🖱️ <span color='#6acda2'>RMB:</span> Copy External IP"
        }
        print(json.dumps(output))
        return

    # Get current values
    curr_rx, curr_tx = get_bytes(INTERFACE)
    curr_time = time.time()
    
    # Calculate time difference
    time_diff = curr_time - prev_time
    if time_diff < 0.1:
        time_diff = 1  # Prevent division by zero
    
    # Calculate speeds
    rx_speed = (curr_rx - prev_rx) / time_diff
    tx_speed = (curr_tx - prev_tx) / time_diff
    
    # Ensure non-negative speeds
    rx_speed = max(0, rx_speed)
    tx_speed = max(0, tx_speed)
    
    # Save current values for next run
    with open("/tmp/waybar_net_prev", "w") as f:
        json.dump({"rx": curr_rx, "tx": curr_tx, "time": curr_time}, f)
    
    # Get IP addresses
    local_ip = get_local_ip(INTERFACE)
    external_ip = get_external_ip()
    
    # Format output
    output = {
        "text": f"󰈀 ↑ {format_speed(tx_speed)} ↓ {format_speed(rx_speed)}",
        "tooltip": f"<span color='#6acda2'>Local IP:</span> {local_ip}\n<span color='#6acda2'>External IP:</span> {external_ip}\n\n🖱️ <span color='#6acda2'>LMB:</span> Copy Local IP\n🖱️ <span color='#6acda2'>RMB:</span> Copy External IP"
    }
    
    print(json.dumps(output))

if __name__ == "__main__":
    main()