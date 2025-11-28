# Osaka Jade

Osaka Jade config for Hyprland, Waybar, and Ghostty terminal.

![Preview](preview.png)

## Features

- Waybar
  - Color scheme for Osaka Jade
  - Spotify integration
  - System monitor 
  - Weather widget 
  - Pill containers for widgets
- Hyprland
  - Customized layouts
  - Transparent panels

- Ghostty Terminal
  - Terminal color scheme matching Osaka Jade

  Might need some tweaks for it to work on your system.

---

## Installation Instructions (Safe Method for Beginners)

# 1. Choose a folder to clone the repo into
# Replace <desired_clone_location> with the path where you want to store the repo
cd <desired_clone_location>
git clone -b osaka-jade https://github.com/Thilen03/omarchy-dotfiles.git

# Navigate into the repo
cd omarchy-dotfiles

# 2. Back Up Your Existing .config
# Replace <backup_location> with the path where you want to store your current .config
mkdir -p <backup_location>
cp -r ~/.config/* <backup_location>/

# 3. Copy Osaka Jade .config to Your System
# Replace <destination_config> with the path to your .config (usually ~/.config)
cp -r .config/* <destination_config>/

# Confirm overwrites if prompted — your backup is safe

# 4. Reload Hyprland and Waybar to apply changes
hyprctl reload
pkill waybar && waybar &

# 5. Restore Old Config (Optional)
# If you want to roll back to your previous setup
cp -r <backup_location>/* <destination_config>/
hyprctl reload
