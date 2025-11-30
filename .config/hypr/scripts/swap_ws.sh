#!/usr/bin/env bash
# swap_ws.sh - move/swap workspaces so that calling workspace X
# will appear on the focused monitor; if it already exists on another
# monitor, swap the two workspaces.

set -e

WS="$1"
if [ -z "$WS" ]; then
  echo "Usage: $0 <workspace-id>" >&2
  exit 2
fi

# Get all monitor info
MONITORS_JSON=$(hyprctl -j monitors)

# Get focused monitor name
FOCUSED_MONITOR=$(echo "$MONITORS_JSON" | jq -r '.[] | select(.focused==true).name')

if [ -z "$FOCUSED_MONITOR" ]; then
    echo "Error: Could not determine focused monitor" >&2
    exit 1
fi

# Get the current active workspace on the focused monitor
CURRENT_WS_ON_FOCUSED=$(echo "$MONITORS_JSON" | jq -r --arg fm "$FOCUSED_MONITOR" '.[] | select(.name==$fm).activeWorkspace.id')

# Check if the target workspace is currently visible on any monitor
TARGET_MONITOR=$(echo "$MONITORS_JSON" | jq -r --arg ws "$WS" '.[] | select(.activeWorkspace.id==($ws|tonumber)).name')

# Case 1: Workspace is already on the focused monitor - just switch to it
if [ "$TARGET_MONITOR" = "$FOCUSED_MONITOR" ]; then
    hyprctl dispatch workspace "$WS"
    exit 0
fi

# Case 2: Workspace is on another monitor - swap them
if [ -n "$TARGET_MONITOR" ] && [ "$TARGET_MONITOR" != "null" ]; then
    # First, move the target workspace to focused monitor
    hyprctl dispatch moveworkspacetomonitor "$WS" "$FOCUSED_MONITOR"
    sleep 0.1
    
    # Then move the current workspace from focused monitor to target monitor
    hyprctl dispatch moveworkspacetomonitor "$CURRENT_WS_ON_FOCUSED" "$TARGET_MONITOR"
    sleep 0.05
    
    # Finally, focus the workspace we wanted
    hyprctl dispatch workspace "$WS"
    exit 0
fi

# Case 3: Workspace doesn't exist or isn't visible anywhere - summon it
hyprctl dispatch moveworkspacetomonitor "$WS" "$FOCUSED_MONITOR"
sleep 0.05
hyprctl dispatch workspace "$WS"
exit 0