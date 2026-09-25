# CMD Toolbox

A small Windows desktop app for saving and launching CMD commands.

## Run
1. Install Python 3.10+ from https://www.python.org/downloads/ (enable "Add Python to PATH").
2. Double-click `run_cmd_toolbox.bat` or run `py cmd_toolbox.py` in this folder.
3. Optional: install Pillow for better custom image support: `py -m pip install pillow`.

## Features
- Square tiles with title, description, optional reference URL, command, and icon.
- Built-in icon selector and custom image upload.
- Persistent local storage; tools are saved in `%LOCALAPPDATA%\\CmdToolbox\\tools.json`.
- Custom icons are copied into `%LOCALAPPDATA%\\CmdToolbox\\Icons`.
- Right-click a tile to edit or delete it.
- Embedded interactive CMD terminal inside the app; type commands and press Enter.
- Clicking a tile asks for confirmation, then runs its command in the embedded terminal session.
- Terminal session is reused so commands such as `cd` can affect subsequent commands.

## Safety
Commands run with your Windows user permissions. Only add and run commands you understand and trust.
