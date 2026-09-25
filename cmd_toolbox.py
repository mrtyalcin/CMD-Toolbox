import json
import os
import shutil
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

APP_NAME = "CMD Toolbox"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CmdToolbox"
DATA_FILE = APP_DIR / "tools.json"
ICON_DIR = APP_DIR / "Icons"

BUILTIN_ICONS = {
    "Activity": "📈",
    "Monitor": "🖥",
    "Shield": "🛡",
    "Chart": "📊",
    "Terminal": "⌨",
    "Gauge": "⏱",
    "Settings": "⚙",
    "Wrench": "🔧",
    "Folder": "📁",
    "Search": "🔎",
    "Network": "🌐",
    "Disk": "💽",
    "Tools": "🧰",
    "Star": "⭐",
    "Windows": "⊞",
}

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def ensure_storage():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    ICON_DIR.mkdir(parents=True, exist_ok=True)


def load_tools():
    ensure_storage()
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        messagebox.showwarning(APP_NAME, "The saved tools file could not be read. Starting with an empty list.")
        return []


def save_tools(tools):
    ensure_storage()
    temp_file = DATA_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)
    temp_file.replace(DATA_FILE)


class ToolDialog(tk.Toplevel):
    def __init__(self, parent, existing=None):
        super().__init__(parent)
        self.parent = parent
        self.existing = existing
        self.custom_icon_source = None
        self.icon_kind = tk.StringVar(value=(existing or {}).get("icon_kind", "builtin"))
        self.icon_value = tk.StringVar(value=(existing or {}).get("icon", "Activity"))
        self.title("Edit tool" if existing else "Add tool")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Title").grid(row=0, column=0, sticky="w", pady=5)
        self.title_var = tk.StringVar(value=(existing or {}).get("title", ""))
        ttk.Entry(frame, textvariable=self.title_var, width=46).grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Description").grid(row=1, column=0, sticky="nw", pady=5)
        self.desc_text = tk.Text(frame, width=46, height=4, wrap="word")
        self.desc_text.grid(row=1, column=1, sticky="ew", pady=5)
        self.desc_text.insert("1.0", (existing or {}).get("description", ""))

        ttk.Label(frame, text="Reference URL").grid(row=2, column=0, sticky="w", pady=5)
        self.ref_var = tk.StringVar(value=(existing or {}).get("reference", ""))
        ttk.Entry(frame, textvariable=self.ref_var, width=46).grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="CMD command").grid(row=3, column=0, sticky="w", pady=5)
        self.command_var = tk.StringVar(value=(existing or {}).get("command", ""))
        ttk.Entry(frame, textvariable=self.command_var, width=46).grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Icon").grid(row=4, column=0, sticky="w", pady=5)
        icon_frame = ttk.Frame(frame)
        icon_frame.grid(row=4, column=1, sticky="ew", pady=5)
        self.icon_combo = ttk.Combobox(icon_frame, textvariable=self.icon_value,
                                       values=list(BUILTIN_ICONS.keys()), state="readonly", width=22)
        self.icon_combo.pack(side="left")
        self.icon_combo.bind("<<ComboboxSelected>>", lambda _e: self.icon_kind.set("builtin"))
        ttk.Button(icon_frame, text="Upload image…", command=self.upload_icon).pack(side="left", padx=8)
        self.icon_status = ttk.Label(frame, text=self._icon_status_text())
        self.icon_status.grid(row=5, column=1, sticky="w")

        if existing and existing.get("icon_kind") == "custom":
            self.custom_icon_source = existing.get("icon_path")
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save tool", command=self.save).pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+60}+{parent.winfo_rooty()+60}")

    def _icon_status_text(self):
        if self.icon_kind.get() == "custom" and self.custom_icon_source:
            return f"Custom image: {Path(self.custom_icon_source).name}"
        return "Using built-in icon"

    def upload_icon(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose an icon image",
            filetypes=[("Image files", "*.png *.gif *.ppm *.pgm *.jpg *.jpeg *.bmp *.ico"), ("All files", "*.*")]
        )
        if not path:
            return
        ext = Path(path).suffix.lower()
        if ext not in {".png", ".gif", ".ppm", ".pgm", ".jpg", ".jpeg", ".bmp", ".ico"}:
            messagebox.showerror("Unsupported image", "Choose a PNG, GIF, PPM, PGM, JPG, BMP, or ICO image.")
            return
        if ext in {".jpg", ".jpeg", ".bmp", ".ico"} and not PIL_AVAILABLE:
            messagebox.showerror("Pillow required", "For JPG, BMP, and ICO images, install Pillow with:\n\npy -m pip install pillow\n\nPNG and GIF work without Pillow.")
            return
        self.custom_icon_source = path
        self.icon_kind.set("custom")
        self.icon_status.config(text=self._icon_status_text())

    def save(self):
        title = self.title_var.get().strip()
        command = self.command_var.get().strip()
        if not title or not command:
            messagebox.showerror("Missing information", "Please enter both a title and a CMD command.", parent=self)
            return
        reference = self.ref_var.get().strip()
        if reference and urlparse(reference).scheme not in ("http", "https"):
            messagebox.showerror("Invalid reference", "Reference must be an http:// or https:// URL.", parent=self)
            return

        record = {
            "id": (self.existing or {}).get("id") or __import__("uuid").uuid4().hex,
            "title": title,
            "description": self.desc_text.get("1.0", "end").strip(),
            "reference": reference,
            "command": command,
            "icon_kind": self.icon_kind.get(),
            "icon": self.icon_value.get() or "Activity",
            "icon_path": None,
        }
        if self.icon_kind.get() == "custom":
            if not self.custom_icon_source or not Path(self.custom_icon_source).exists():
                messagebox.showerror("Missing icon", "Choose an image file that still exists.", parent=self)
                return
            ensure_storage()
            src = Path(self.custom_icon_source)
            if self.existing and self.existing.get("icon_path") and Path(self.existing["icon_path"]).resolve() == src.resolve():
                record["icon_path"] = str(src)
            else:
                dest = ICON_DIR / f"{record['id']}{src.suffix.lower()}"
                try:
                    shutil.copy2(src, dest)
                except OSError as exc:
                    messagebox.showerror("Could not save icon", str(exc), parent=self)
                    return
                record["icon_path"] = str(dest)
        self.result = record
        self.destroy()


class CmdToolbox(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x720")
        self.minsize(650, 480)
        self.configure(bg="#f3f5f8")
        self.tools = load_tools()
        self.photo_refs = []
        self.terminal_process = None
        self.terminal_queue = queue.Queue()
        self.terminal_visible = True
        self._build_ui()
        self.render_tiles()

    def _build_ui(self):
        top = tk.Frame(self, bg="#f3f5f8")
        top.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(top, text="CMD TOOLBOX", font=("Segoe UI", 23, "bold"),
                 bg="#f3f5f8", fg="#172033").pack(side="left")
        tk.Label(top, text="Your personal Windows command launcher",
                 font=("Segoe UI", 10), bg="#f3f5f8", fg="#5b6475").pack(side="left", padx=16, pady=(8, 0))
        ttk.Button(top, text="Hide terminal", command=self.toggle_terminal).pack(side="right", padx=(8, 0))
        self.count_label = tk.Label(self, text="", font=("Segoe UI", 9),
                                    bg="#f3f5f8", fg="#697386")
        self.count_label.pack(anchor="w", padx=26, pady=(0, 8))

        outer = tk.Frame(self, bg="#f3f5f8")
        outer.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.canvas = tk.Canvas(outer, bg="#f3f5f8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.canvas, bg="#f3f5f8")
        self.window_id = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.terminal_frame = tk.Frame(self, bg="#172033")
        self.terminal_frame.pack(fill="x", padx=18, pady=(0, 10))
        terminal_header = tk.Frame(self.terminal_frame, bg="#172033")
        terminal_header.pack(fill="x", padx=10, pady=(7, 3))
        tk.Label(terminal_header, text="EMBEDDED CMD TERMINAL", font=("Segoe UI", 9, "bold"),
                 bg="#172033", fg="#dbeafe").pack(side="left")
        ttk.Button(terminal_header, text="Clear", command=self.clear_terminal).pack(side="right")
        self.terminal_output = tk.Text(self.terminal_frame, height=8, bg="#0b1020", fg="#d1fae5",
                                       insertbackground="white", font=("Consolas", 10),
                                       relief="flat", wrap="word", state="disabled")
        self.terminal_output.pack(fill="x", padx=10, pady=(0, 6))
        self.terminal_input = ttk.Entry(self.terminal_frame)
        self.terminal_input.pack(fill="x", padx=10, pady=(0, 10))
        self.terminal_input.insert(0, "Type a command and press Enter…")
        self.terminal_input.bind("<FocusIn>", self._clear_input_placeholder)
        self.terminal_input.bind("<Return>", self._terminal_enter)
        self._append_terminal("CMD Toolbox terminal ready. Click a tool or type a command below.")
        self.after(100, self._drain_terminal_queue)

        footer = tk.Label(self, text=f"Saved locally in: {DATA_FILE}",
                          font=("Segoe UI", 8), bg="#f3f5f8", fg="#8a93a3")
        footer.pack(anchor="w", padx=25, pady=(0, 10))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)
        self.render_tiles()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _icon_widget(self, parent, tool):
        if tool.get("icon_kind") == "custom" and tool.get("icon_path"):
            path = Path(tool["icon_path"])
            if path.exists():
                try:
                    if PIL_AVAILABLE:
                        img = Image.open(path).convert("RGBA")
                        img.thumbnail((66, 66))
                        photo = ImageTk.PhotoImage(img)
                    else:
                        photo = tk.PhotoImage(file=str(path))
                        factor = max(1, photo.width() // 72, photo.height() // 72)
                        if factor > 1:
                            photo = photo.subsample(factor, factor)
                    self.photo_refs.append(photo)
                    return tk.Label(parent, image=photo, bg="white")
                except Exception:
                    pass
        symbol = BUILTIN_ICONS.get(tool.get("icon", "Activity"), "🧰")
        return tk.Label(parent, text=symbol, font=("Segoe UI Emoji", 34),
                        bg="white", fg="#243b53")

    def render_tiles(self):
        if not hasattr(self, "grid_frame"):
            return
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.photo_refs = []
        width = max(self.canvas.winfo_width(), 500)
        tile_size = 205
        gap = 14
        columns = max(1, min(5, (width - 24) // (tile_size + gap)))
        for col in range(6):
            self.grid_frame.grid_columnconfigure(col, weight=1 if col < columns else 0)
        for index, tool in enumerate(self.tools):
            row, col = divmod(index, columns)
            self._make_tile(tool, row, col, tile_size)
        row, col = divmod(len(self.tools), columns)
        self._make_add_tile(row, col, tile_size)
        self.count_label.config(text=f"{len(self.tools)} saved tool{'s' if len(self.tools) != 1 else ''}  •  Click a tile to run its command")

    def _make_tile(self, tool, row, col, size):
        tile = tk.Frame(self.grid_frame, bg="white", highlightbackground="#dce2eb",
                        highlightthickness=1, width=size, height=size)
        tile.grid(row=row, column=col, padx=7, pady=7, sticky="n")
        tile.grid_propagate(False)
        icon = self._icon_widget(tile, tool)
        icon.pack(pady=(12, 2))
        title = tk.Label(tile, text=tool.get("title", "Untitled").upper(),
                         font=("Segoe UI", 11, "bold"), bg="white", fg="#172033",
                         wraplength=size-22, justify="center")
        title.pack(padx=8, pady=(0, 5))
        desc = tk.Label(tile, text=tool.get("description", ""), font=("Segoe UI", 8),
                        bg="white", fg="#5b6475", wraplength=size-24,
                        justify="center", height=3)
        desc.pack(padx=10, fill="x")
        if tool.get("reference"):
            ref = tk.Label(tile, text="Reference ↗", font=("Segoe UI", 8, "underline"),
                           bg="white", fg="#2563eb", cursor="hand2")
            ref.pack(side="bottom", pady=(0, 8))
            ref.bind("<Button-1>", lambda _e, url=tool["reference"]: webbrowser.open(url))
        else:
            tk.Label(tile, text="", bg="white").pack(side="bottom", pady=(0, 8))
        for widget in (tile, icon, title, desc):
            widget.bind("<Button-1>", lambda _e, t=tool: self.run_tool(t))
            widget.bind("<Button-3>", lambda _e, t=tool: self.show_context_menu(_e, t))
            widget.configure(cursor="hand2")

    def _make_add_tile(self, row, col, size):
        tile = tk.Frame(self.grid_frame, bg="#eaf0f8", highlightbackground="#c7d3e3",
                        highlightthickness=1, width=size, height=size, cursor="hand2")
        tile.grid(row=row, column=col, padx=7, pady=7, sticky="n")
        tile.grid_propagate(False)
        tk.Label(tile, text="+", font=("Segoe UI", 48), bg="#eaf0f8", fg="#315b91").pack(pady=(35, 5))
        tk.Label(tile, text="ADD BUTTON", font=("Segoe UI", 12, "bold"),
                 bg="#eaf0f8", fg="#315b91").pack()
        tk.Label(tile, text="Create a new command tile", font=("Segoe UI", 8),
                 bg="#eaf0f8", fg="#60758f", wraplength=size-25).pack(pady=8)
        tile.bind("<Button-1>", lambda _e: self.add_tool())
        for child in tile.winfo_children():
            child.bind("<Button-1>", lambda _e: self.add_tool())

    def add_tool(self):
        dialog = ToolDialog(self)
        self.wait_window(dialog)
        if getattr(dialog, "result", None):
            self.tools.append(dialog.result)
            self._persist_and_render()

    def edit_tool(self, tool):
        dialog = ToolDialog(self, existing=tool)
        self.wait_window(dialog)
        if getattr(dialog, "result", None):
            for i, item in enumerate(self.tools):
                if item.get("id") == tool.get("id"):
                    self.tools[i] = dialog.result
                    break
            self._persist_and_render()

    def delete_tool(self, tool):
        if not messagebox.askyesno("Delete tool", f"Delete '{tool.get('title')}'?", parent=self):
            return
        self.tools = [item for item in self.tools if item.get("id") != tool.get("id")]
        self._persist_and_render()

    def _persist_and_render(self):
        try:
            save_tools(self.tools)
            self.render_tiles()
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save your tools:\n{exc}", parent=self)

    def _append_terminal(self, text):
        self.terminal_output.configure(state="normal")
        self.terminal_output.insert("end", text if text.endswith("\n") else text + "\n")
        self.terminal_output.see("end")
        self.terminal_output.configure(state="disabled")

    def clear_terminal(self):
        self.terminal_output.configure(state="normal")
        self.terminal_output.delete("1.0", "end")
        self.terminal_output.configure(state="disabled")

    def toggle_terminal(self):
        if self.terminal_visible:
            self.terminal_frame.pack_forget()
            self.terminal_visible = False
        else:
            self.terminal_frame.pack(fill="x", padx=18, pady=(0, 10), before=self.winfo_children()[-1])
            self.terminal_visible = True

    def _clear_input_placeholder(self, _event=None):
        if self.terminal_input.get() == "Type a command and press Enter…":
            self.terminal_input.delete(0, "end")

    def _ensure_terminal(self):
        if self.terminal_process and self.terminal_process.poll() is None:
            return
        try:
            self.terminal_process = subprocess.Popen(
                ["cmd.exe", "/Q", "/D"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW
            )
            threading.Thread(target=self._read_terminal, daemon=True).start()
            self._append_terminal("Started cmd.exe. Commands run in this session.")
        except Exception as exc:
            messagebox.showerror("Could not start terminal", str(exc), parent=self)
            self.terminal_process = None

    def _read_terminal(self):
        proc = self.terminal_process
        try:
            for line in proc.stdout:
                self.terminal_queue.put(line)
        except (OSError, ValueError):
            pass
        self.terminal_queue.put("\n[Terminal process ended.]\n")

    def _drain_terminal_queue(self):
        try:
            while True:
                line = self.terminal_queue.get_nowait()
                self.terminal_output.configure(state="normal")
                self.terminal_output.insert("end", line)
                self.terminal_output.see("end")
                self.terminal_output.configure(state="disabled")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._drain_terminal_queue)

    def _send_terminal_command(self, command):
        self._ensure_terminal()
        if not self.terminal_process or self.terminal_process.poll() is not None:
            return
        try:
            self._append_terminal(f"> {command}")
            self.terminal_process.stdin.write(command + "\n")
            self.terminal_process.stdin.flush()
        except (OSError, ValueError) as exc:
            self._append_terminal(f"[Could not send command: {exc}]")

    def _terminal_enter(self, _event=None):
        command = self.terminal_input.get().strip()
        self.terminal_input.delete(0, "end")
        if command and command != "Type a command and press Enter…":
            self._send_terminal_command(command)
        return "break"

    def run_tool(self, tool):
        command = tool.get("command", "").strip()
        if not command:
            return
        if not messagebox.askyesno("Run command", f"Run this command in the embedded terminal?\n\n{command}\n\nOnly run commands you trust.", parent=self):
            return
        if not self.terminal_visible:
            self.toggle_terminal()
        self._send_terminal_command(command)

    def destroy(self):
        if self.terminal_process and self.terminal_process.poll() is None:
            try:
                self.terminal_process.terminate()
            except OSError:
                pass
        super().destroy()

    def show_context_menu(self, event, tool):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Run command", command=lambda: self.run_tool(tool))
        menu.add_command(label="Edit tool", command=lambda: self.edit_tool(tool))
        menu.add_command(label="Delete tool", command=lambda: self.delete_tool(tool))
        menu.tk_popup(event.x_root, event.y_root)


if __name__ == "__main__":
    ensure_storage()
    app = CmdToolbox()
    app.mainloop()
