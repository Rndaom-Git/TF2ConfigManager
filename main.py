import os
import shutil
import customtkinter as ctk
import tkinter as tk  # Add this import for Listbox and Text
from tkinter import filedialog, messagebox, simpledialog
import configparser
import json
import hashlib

APP_NAME = "TF2 Config Manager"
CONFIG_FILE = "config.ini"
PROFILES_DIR = "profiles"

IGNORED_FILES = {
    "config.cfg",
    "motd_entries.txt",
    "sound.cache",
}

# Helper functions
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def get_tf2_dir(config):
    return config['DEFAULT'].get('tf2_dir', '')

def set_tf2_dir(config, path):
    config['DEFAULT']['tf2_dir'] = path
    save_config(config)

def backup_folders(tf2_dir, backup_dir):
    for folder in ['cfg', 'custom']:
        src = os.path.join(tf2_dir, folder)
        dst = os.path.join(backup_dir, folder)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

def restore_folders(profile_dir, tf2_dir):
    for folder in ['cfg', 'custom']:
        src = os.path.join(profile_dir, folder)
        dst = os.path.join(tf2_dir, folder)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        if os.path.exists(src):
            shutil.copytree(src, dst)

def delete_folders(tf2_dir):
    for folder in ['cfg', 'custom']:
        path = os.path.join(tf2_dir, folder)
        if os.path.exists(path):
            shutil.rmtree(path)

def save_profile_metadata(profile_path, name, desc, launch_options):
    meta = {
        'name': name,
        'description': desc,
        'launch_options': launch_options
    }
    with open(os.path.join(profile_path, 'profile.json'), 'w') as f:
        json.dump(meta, f)

def load_profile_metadata(profile_path):
    try:
        with open(os.path.join(profile_path, 'profile.json'), 'r') as f:
            return json.load(f)
    except Exception:
        return {'name': os.path.basename(profile_path), 'description': '', 'launch_options': ''}

def list_profiles():
    ensure_dir(PROFILES_DIR)
    return [os.path.join(PROFILES_DIR, d) for d in os.listdir(PROFILES_DIR) if os.path.isdir(os.path.join(PROFILES_DIR, d))]

def folder_hash(folder):
    """Make a hash of everything in a folder."""
    if not os.path.exists(folder):
        return None
    hash_md5 = hashlib.md5()
    for root, _, files in os.walk(folder):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, folder)
            hash_md5.update(relpath.encode())
            try:
                with open(fpath, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        hash_md5.update(chunk)
            except Exception:
                continue
    return hash_md5.hexdigest()

def folder_hash_subset(target_folder, reference_folder):
    """Hash files in target_folder that match files in reference_folder. Shows debug info for missing or different files."""
    import os, hashlib
    hash_md5 = hashlib.md5()
    any_files = False
    for root, _, files in os.walk(reference_folder):
        for fname in sorted(files):
            if fname in IGNORED_FILES:
                print(f"[DEBUG] IGNORING: {fname}")
                continue
            any_files = True
            ref_fpath = os.path.join(root, fname)
            relpath = os.path.relpath(ref_fpath, reference_folder)
            tgt_fpath = os.path.join(target_folder, relpath)
            print(f"[DEBUG] CHECKING: {relpath}")
            hash_md5.update(relpath.encode())
            if os.path.exists(tgt_fpath):
                try:
                    with open(tgt_fpath, 'rb') as f1, open(ref_fpath, 'rb') as f2:
                        t1 = f1.read()
                        t2 = f2.read()
                        if t1 != t2:
                            print(f"[DEBUG] MISMATCH: {relpath}")
                        hash_md5.update(t1)
                except Exception as e:
                    print(f"[DEBUG] ERROR reading {relpath}: {e}")
                    continue
            else:
                print(f"[DEBUG] MISSING: {relpath}")
                hash_md5.update(b'__MISSING__')
    if not any_files:
        return None  # Special value for empty reference
    return hash_md5.hexdigest()

def tolerant_profile_match(profile_path, tf2_dir):
    """Check if tf2_dir matches the profile, ignoring extra files in tf2_dir."""
    profile_cfg = os.path.join(profile_path, 'cfg')
    profile_custom = os.path.join(profile_path, 'custom')
    tf_cfg = os.path.join(tf2_dir, 'cfg')
    tf_custom = os.path.join(tf2_dir, 'custom')
    cfg_hash = folder_hash_subset(tf_cfg, profile_cfg)
    custom_hash = folder_hash_subset(tf_custom, profile_custom)
    profile_cfg_hash = folder_hash_subset(profile_cfg, profile_cfg)
    profile_custom_hash = folder_hash_subset(profile_custom, profile_custom)
    # If the profile's cfg/custom is empty, only match if tf2's is also empty
    cfg_match = (cfg_hash == profile_cfg_hash) and (cfg_hash is not None)
    custom_match = (custom_hash == profile_custom_hash) and (custom_hash is not None)
    # If profile's cfg/custom is empty, both hashes will be None
    if profile_cfg_hash is None:
        cfg_match = (cfg_hash is None)
    if profile_custom_hash is None:
        custom_match = (custom_hash is None)
    return cfg_match and custom_match

def profile_hash(profile_path):
    cfg_hash = folder_hash(os.path.join(profile_path, 'cfg'))
    custom_hash = folder_hash(os.path.join(profile_path, 'custom'))
    return (cfg_hash, custom_hash)

def current_tf_hash(tf2_dir):
    cfg_hash = folder_hash(os.path.join(tf2_dir, 'cfg'))
    custom_hash = folder_hash(os.path.join(tf2_dir, 'custom'))
    return (cfg_hash, custom_hash)

class ThemedInfoDialog(ctk.CTkToplevel):
    def __init__(self, master, message, title="Info"):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title(title)
        self.geometry("420x180")
        self.resizable(False, False)
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11), wraplength=380, justify='left', text_color="#FFFFFF").pack(padx=20, pady=(30,10))
        ctk.CTkButton(self, text="OK", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(pady=10)

class ThemedErrorDialog(ctk.CTkToplevel):
    def __init__(self, master, message, title="Error"):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title(title)
        self.geometry("420x180")
        self.resizable(False, False)
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11), wraplength=380, justify='left', text_color="#FF5555").pack(padx=20, pady=(30,10))
        ctk.CTkButton(self, text="OK", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(pady=10)

class InfoDialog(ctk.CTkToplevel):
    def __init__(self, master, on_close):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("Welcome to TF2 Config Manager")
        self.geometry("420x260")
        self.resizable(False, False)
        info = (
            "Welcome to TF2 Config Manager!\n\n"
            "This tool helps you backup, manage, and switch between different Team Fortress 2 config profiles.\n\n"
            "- Use the 'Change tf Folder' button to set or update your tf directory.\n"
            "- Create new profiles by importing your tf folder.\n"
            "- Apply profiles to quickly switch your cfg and custom folders.\n"
            "- Your Steam launch options can be saved with each profile.\n\n"
            "No files are changed until you apply or create a profile."
        )
        ctk.CTkTextbox(self, width=380, height=120, state='normal', font=("Segoe UI", 11), wrap='word', fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=20, pady=20)
        text_widget = self.winfo_children()[-1]
        text_widget.insert('1.0', info)
        text_widget.configure(state='disabled')
        ctk.CTkButton(self, text="OK", command=self.close, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(pady=10)
        self.on_close = on_close
    def close(self):
        self.on_close()
        self.destroy()

class EditProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, meta, on_save):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("Edit Profile")
        self.geometry("400x300")
        self.resizable(False, False)
        self.on_save = on_save
        ctk.CTkLabel(self, text="Profile Name:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=20, pady=(15,0))
        self.name_var = ctk.StringVar(value=meta.get('name', ''))
        ctk.CTkEntry(self, textvariable=self.name_var, width=320, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=20)
        ctk.CTkLabel(self, text="Description:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=20, pady=(10,0))
        self.desc_var = ctk.StringVar(value=meta.get('description', ''))
        ctk.CTkEntry(self, textvariable=self.desc_var, width=320, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=20)
        ctk.CTkLabel(self, text="Steam Launch Options:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=20, pady=(10,0))
        self.launch_var = ctk.StringVar(value=meta.get('launch_options', ''))
        ctk.CTkEntry(self, textvariable=self.launch_var, width=320, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=20)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="OK", command=self.save, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=10)
    def save(self):
        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()
        launch = self.launch_var.get().strip()
        if not name:
            ThemedErrorDialog(self, "Profile name cannot be empty.")
            return
        self.on_save(name, desc, launch)
        self.destroy()

class DeleteProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, profile_name, on_confirm):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("Delete Profile")
        self.geometry("380x160")
        self.resizable(False, False)
        self.result = False
        self.delete_tf_config = ctk.BooleanVar()
        msg = f"Are you sure you want to delete the profile '{profile_name}'? This cannot be undone."
        ctk.CTkLabel(self, text=msg, font=("Segoe UI", 11), wraplength=350, justify='left', text_color="#FFFFFF").pack(padx=20, pady=(20,10))
        ctk.CTkCheckBox(self, text="Delete config from tf directory?", variable=self.delete_tf_config, fg_color="#232323", border_color="#444444", text_color="#FFFFFF", hover_color="#FFA559", corner_radius=8).pack(pady=5)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Delete", command=self.confirm, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=10)
        self.on_confirm = on_confirm
    def confirm(self):
        self.on_confirm(self.delete_tf_config.get())
        self.destroy()

class NewProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, on_import_tf, on_import_custom):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("New Profile")
        self.geometry("350x160")
        self.resizable(False, False)
        ctk.CTkLabel(self, text="How would you like to import the new profile?", font=("Segoe UI", 11), wraplength=320, text_color="#FFFFFF").pack(pady=(20,10))
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Import from current tf folder", width=220, height=36, font=("Segoe UI", 11), command=lambda: self._choose(on_import_tf), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(pady=5)
        ctk.CTkButton(btn_frame, text="Import from cfg/custom folders", width=220, height=36, font=("Segoe UI", 11), command=lambda: self._choose(on_import_custom), fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(pady=5)
    def _choose(self, callback):
        self.destroy()
        callback()

class CustomImportProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, on_submit):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("New Profile from Folders")
        self.geometry("440x420")  # Reduced height
        self.resizable(False, False)
        self.on_submit = on_submit
        ctk.CTkLabel(self, text="Create New Profile", font=("Segoe UI", 14, "bold"), text_color="#FFFFFF").pack(pady=(18, 8))
        ctk.CTkLabel(self, text="Profile Name:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(0, 2))
        self.name_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.name_var, width=340, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=28)
        ctk.CTkLabel(self, text="Description:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(10, 2))
        self.desc_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.desc_var, width=340, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=28)
        ctk.CTkLabel(self, text="Steam Launch Options:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(10, 2))
        self.launch_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.launch_var, width=340, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=28)
        # Folder selection
        ctk.CTkLabel(self, text="Select cfg and custom folders:", font=("Segoe UI", 11, "bold"), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(16, 2))
        self.cfg_path_var = ctk.StringVar()
        self.custom_path_var = ctk.StringVar()
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(padx=28, pady=(0, 0), fill='x')
        ctk.CTkButton(folder_frame, text="Choose cfg folder", width=140, command=self.choose_cfg, fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").grid(row=0, column=0, padx=(0, 8), pady=4)
        ctk.CTkEntry(folder_frame, textvariable=self.cfg_path_var, width=170, state='readonly', fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).grid(row=0, column=1, pady=4)
        ctk.CTkButton(folder_frame, text="Choose custom folder", width=140, command=self.choose_custom, fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").grid(row=1, column=0, padx=(0, 8), pady=4)
        ctk.CTkEntry(folder_frame, textvariable=self.custom_path_var, width=170, state='readonly', fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).grid(row=1, column=1, pady=4)
        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent", width=380)
        btn_frame.pack(pady=(10, 2))
        ctk.CTkButton(btn_frame, text="OK", command=self.submit, width=160, height=40, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=160, height=40, font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=10)
    def choose_cfg(self):
        path = filedialog.askdirectory(title="Select your cfg folder")
        if path:
            if os.path.basename(os.path.normpath(path)).lower() != "cfg":
                ThemedErrorDialog(self, "Please select a folder named 'cfg'.")
                return
            self.cfg_path_var.set(path)
    def choose_custom(self):
        path = filedialog.askdirectory(title="Select your custom folder")
        if path:
            if os.path.basename(os.path.normpath(path)).lower() != "custom":
                ThemedErrorDialog(self, "Please select a folder named 'custom'.")
                return
            self.custom_path_var.set(path)
    def submit(self):
        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()
        launch = self.launch_var.get().strip()
        cfg = self.cfg_path_var.get().strip()
        custom = self.custom_path_var.get().strip()
        if not name:
            ThemedErrorDialog(self, "Profile name cannot be empty.")
            return
        if not cfg or not custom:
            ThemedErrorDialog(self, "Please select both cfg and custom folders.")
            return
        self.on_submit(name, desc, launch, cfg, custom)
        self.destroy()

class HelpTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind('<Enter>', self.show_tip)
        widget.bind('<Leave>', self.hide_tip)
    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, wraplength=300)
        label.pack(ipadx=1)
    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class HelpDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("TF2 Config Manager - Help & FAQ")
        self.geometry("540x480")
        self.resizable(False, False)
        text = (
            "TF2 Config Manager - Help & FAQ\n\n"
            "- Use the 'TF Folder' section to set or change your tf directory.\n"
            "- 'New Profile' lets you save your current tf folder or import from other cfg/custom folders.\n"
            "- 'Apply Profile' will always delete your current profile files and replace them with those from the selected profile. No extra confirmation is required.\n"
            "- 'Edit' lets you change a profile's name, description, or launch options.\n"
            "- 'Delete' removes a profile, and optionally deletes the config from your tf folder.\n"
            "- 'Fresh Install' will delete your entire tf folder (not just cfg/custom). This cannot be undone. You must verify integrity of your TF2 game files after.\n"
            "- The '[Current]' tag shows which profile (if any) matches your tf folder.\n"
            "- The program auto-detects changes to your tf/cfg and tf/custom folders."
        )
        ctk.CTkTextbox(self, wrap='word', height=22, width=64, state='normal', font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(fill='both', expand=True, padx=10, pady=10)
        text_widget = self.winfo_children()[-1]
        text_widget.insert('1.0', text)
        text_widget.configure(state='disabled')
        ctk.CTkButton(self, text="Close", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(pady=10)

class ApplyProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, on_apply):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("Apply Profile")
        self.geometry("400x180")
        self.resizable(False, False)
        msg = (
            "This will delete the current config and apply the new profile."
        )
        ctk.CTkLabel(self, text=msg, font=("Segoe UI", 11), wraplength=370, justify='left', text_color="#FFFFFF").pack(padx=20, pady=(20,10))
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Apply", width=120, height=36, font=("Segoe UI", 11), command=self.apply, fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=16)
        ctk.CTkButton(btn_frame, text="Cancel", width=120, height=36, font=("Segoe UI", 11), command=self.destroy, fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=16)
        self.on_apply = on_apply
    def apply(self):
        self.on_apply()
        self.destroy()

class NoProfileSelectedDialog(ctk.CTkToplevel):
    def __init__(self, master, message):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass
        self.configure(fg_color="#181818")
        self.title("No Profile Selected")
        self.geometry("340x140")
        self.resizable(False, False)
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11), wraplength=300, justify='left', text_color="#FFFFFF").pack(padx=20, pady=(25, 10))
        ctk.CTkButton(self, text="OK", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(pady=10)

class FreshInstallDialog(ctk.CTkToplevel):
    def __init__(self, master, on_confirm):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("Fresh Install Confirmation")
        self.geometry("420x200")
        self.resizable(False, False)
        msg = (
            "You are about to delete your entire 'tf' folder.\n\n"
            "This action cannot be undone."
        )
        ctk.CTkLabel(self, text=msg, font=("Segoe UI", 11), wraplength=380, justify='left', text_color="#FFFFFF").pack(padx=20, pady=(20,10))
        self.sure_var = ctk.BooleanVar()
        checkbox = ctk.CTkCheckBox(self, text="Are you sure?", variable=self.sure_var, fg_color="#232323", border_color="#444444", text_color="#FFFFFF", hover_color="#FFA559", corner_radius=8, command=self.toggle_ok)
        checkbox.pack(pady=5)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        self.ok_btn = ctk.CTkButton(btn_frame, text="OK", width=120, height=36, font=("Segoe UI", 11), command=self.confirm, fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877", state="disabled")
        self.ok_btn.pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=120, height=36, font=("Segoe UI", 11), command=self.destroy, fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=10)
        self.on_confirm = on_confirm
    def toggle_ok(self):
        if self.sure_var.get():
            self.ok_btn.configure(state="normal")
        else:
            self.ok_btn.configure(state="disabled")
    def confirm(self):
        self.on_confirm()
        self.destroy()

class ThemedNewProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, on_submit):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title("New Profile")
        self.geometry("420x340")
        self.resizable(False, False)
        ctk.CTkLabel(self, text="Create New Profile", font=("Segoe UI", 14, "bold"), text_color="#FFFFFF").pack(pady=(18, 8))
        ctk.CTkLabel(self, text="Profile Name:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(0, 2))
        self.name_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.name_var, width=320, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=28)
        ctk.CTkLabel(self, text="Description:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(10, 2))
        self.desc_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.desc_var, width=320, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=28)
        ctk.CTkLabel(self, text="Steam Launch Options:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(anchor='w', padx=28, pady=(10, 2))
        self.launch_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.launch_var, width=320, fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8).pack(padx=28)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=18)
        ctk.CTkButton(btn_frame, text="OK", command=self.submit, width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=10)
        self.on_submit = on_submit
    def submit(self):
        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()
        launch = self.launch_var.get().strip()
        if not name:
            ThemedErrorDialog(self, "Profile name cannot be empty.")
            return
        self.on_submit(name, desc, launch)
        self.destroy()

class ThemedConfirmDialog(ctk.CTkToplevel):
    def __init__(self, master, message, on_confirm, title="Confirm Delete"):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.focus()
        self.lift()
        self.iconbitmap("icon.ico")
        self.configure(fg_color="#181818")
        self.title(title)
        self.geometry("420x180")
        self.resizable(False, False)
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11), wraplength=380, justify='left', text_color="#FFA559").pack(padx=20, pady=(30,10))
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Delete", command=lambda: self._confirm(on_confirm), width=120, height=36, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120, height=36, font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", corner_radius=12, hover_color="#FFA559").pack(side='left', padx=10)
    def _confirm(self, on_confirm):
        on_confirm()
        self.destroy()

class ProfileManager(ctk.CTkFrame):
    def __init__(self, master, config, on_change_tf2_dir):
        super().__init__(master)
        self.config = config
        self.tf2_dir = get_tf2_dir(config)
        self.on_change_tf2_dir = on_change_tf2_dir
        self.launch_opts_var = ctk.StringVar()
        self.create_widgets()
        self.refresh_profiles()
        self._last_hash = current_tf_hash(self.tf2_dir)
        self._poll_tf_folder()  # Start polling with after()

    def destroy(self):
        if hasattr(self, '_after_id'):
            self.after_cancel(self._after_id)
        super().destroy()

    def _poll_tf_folder(self):
        new_hash = current_tf_hash(self.tf2_dir)
        if new_hash != self._last_hash:
            self._last_hash = new_hash
            self.event_generate('<<TFRefresh>>', when='tail')
        self._after_id = self.after(2000, self._poll_tf_folder)  # Poll every 2 seconds

    def create_widgets(self):
        # Top bar with tf folder label and entry (in rounded frame)
        top_frame = ctk.CTkFrame(self, fg_color="#232323", corner_radius=16, height=56, width=420)
        top_frame.pack(pady=(10, 10), padx=10, anchor="n")
        top_frame.pack_propagate(False)
        top_frame.grid_propagate(False)
        top_frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(top_frame, text="TF Folder:", font=("Segoe UI", 11), text_color="#FFFFFF").grid(row=0, column=0, padx=(12, 4), pady=12, sticky="w")
        self.tf2_dir_var = ctk.StringVar(value=self.tf2_dir)
        self.tf2_dir_entry = ctk.CTkEntry(top_frame, textvariable=self.tf2_dir_var, width=320, state='readonly', font=("Segoe UI", 11), fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8)
        self.tf2_dir_entry.grid(row=0, column=1, padx=2, pady=12, sticky="w")

        # Place the buttons outside the rounded frame, in a separate row
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(pady=(0, 10), padx=10, anchor="n")
        ctk.CTkButton(btn_bar, text="Change tf Folder", command=self.change_tf2_dir, width=140, height=32, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=5)
        ctk.CTkButton(btn_bar, text="Fresh Install", command=self.fresh_install, width=140, height=32, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=5)
        ctk.CTkButton(btn_bar, text="Refresh Profiles", command=self.refresh_profiles, width=140, height=32, font=("Segoe UI", 11), fg_color="#FFA559", text_color="#181818", corner_radius=12, hover_color="#FFB877").pack(side='left', padx=5)

        # Profile section as a contained card
        profile_section = ctk.CTkFrame(self, fg_color="#232323", corner_radius=16, width=420, height=340)
        profile_section.pack(pady=(0, 10), anchor='center')
        profile_section.pack_propagate(False)
        ctk.CTkLabel(profile_section, text="Profiles", font=("Segoe UI", 14, "bold"), text_color="#FFFFFF").pack(pady=(10, 4))

        # Profile listbox with modern style
        listbox_frame = ctk.CTkFrame(profile_section, fg_color="transparent")
        listbox_frame.pack(pady=(0, 8))
        # TODO: Replace tk.Listbox with a custom CTk widget for full theming
        self.profile_listbox = tk.Listbox(
            listbox_frame,
            width=32,
            height=7,
            bg="#232323",
            highlightthickness=0,
            selectbackground="#FFA559",
            selectforeground="#181818",
            relief="flat",
            font=("Segoe UI", 11),
            bd=0,
            fg="#ffffff",
            activestyle='none',
        )
        self.profile_listbox.pack(padx=8, pady=2)
        self.profile_listbox.bind('<<ListboxSelect>>', self.on_select)
        self.bind('<<TFRefresh>>', lambda e: self.refresh_profiles())

        # Description section
        ctk.CTkLabel(profile_section, text="Description", font=("Segoe UI", 11, "bold"), text_color="#FFFFFF").pack(pady=(0, 2))
        self.desc_text = ctk.CTkTextbox(
            profile_section,
            width=340,
            height=40,
            font=("Segoe UI", 10),
            wrap='word',
            fg_color="#232323",
            text_color="#FFFFFF",
            border_color="#444444",
            corner_radius=8,
            state='disabled'
        )
        self.desc_text.pack(padx=8, pady=(0, 4))

        # Steam launch options inside the card
        ctk.CTkLabel(profile_section, text="Steam Launch Options:", font=("Segoe UI", 11), text_color="#FFFFFF").pack(pady=(0, 0))
        self.launch_opts_entry = ctk.CTkEntry(profile_section, textvariable=self.launch_opts_var, width=340, height=40, state='readonly', font=("Segoe UI", 10), fg_color="#232323", text_color="#FFFFFF", border_color="#444444", corner_radius=8)
        self.launch_opts_entry.pack(pady=(0, 10))

        # Main action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))
        button_style = {"width": 120, "height": 36, "font": ("Segoe UI", 11), "fg_color": "#FFA559", "text_color": "#181818", "corner_radius": 12, "hover_color": "#FFB877"}
        ctk.CTkButton(btn_frame, text="Apply Profile", command=self.apply_profile, **button_style).pack(side='left', padx=6)
        ctk.CTkButton(btn_frame, text="New Profile", command=self.new_profile, **button_style).pack(side='left', padx=6)
        ctk.CTkButton(btn_frame, text="Delete", command=self.delete_profile, **button_style).pack(side='left', padx=6)
        ctk.CTkButton(btn_frame, text="Edit", command=self.edit_profile, **button_style).pack(side='left', padx=6)

        # Add help button in the bottom right
        help_btn = ctk.CTkButton(self, text="?", width=32, height=32, font=("Segoe UI", 14, "bold"), command=self.show_help, fg_color="#232323", text_color="#FFA559", corner_radius=12, hover_color="#FFA559")
        help_btn.place(relx=1.0, rely=1.0, x=-14, y=-14, anchor='se')
        HelpTooltip(help_btn, "Click for help and FAQ.\n\n- Set your tf folder\n- Create, apply, edit, or delete profiles\n- Use Fresh Install for a clean config\n- '[Current]' tag shows which profile is active\n- See full help for more!")

    def refresh_profiles(self):
        self.profile_listbox.delete(0, tk.END)
        self.profiles = list_profiles()
        tf2_dir = self.tf2_dir
        self.current_profile_idx = None
        for i, p in enumerate(self.profiles):
            meta = load_profile_metadata(p)
            is_current = tolerant_profile_match(p, tf2_dir)
            print(f"[DEBUG] profile {meta['name']} is_current: {is_current}")
            tag = ''
            display_name = meta['name']
            if is_current:
                tag = ' [Current]'
                self.current_profile_idx = i
            if tag:
                self.profile_listbox.insert(tk.END, f"{display_name}{tag}")
            else:
                self.profile_listbox.insert(tk.END, display_name)
        self.desc_text.configure(state='normal')
        self.desc_text.delete('1.0', 'end')
        self.desc_text.configure(state='disabled')
        self.launch_opts_var.set("")
        for i in range(self.profile_listbox.size()):
            text = self.profile_listbox.get(i)
            if '[Current]' in text:
                self.profile_listbox.itemconfig(i, {'fg': '#39ff14'})
            else:
                self.profile_listbox.itemconfig(i, {'fg': '#ffffff'})

    def on_select(self, event):
        idx = self.profile_listbox.curselection()
        if not idx:
            return
        profile_path = self.profiles[idx[0]]
        meta = load_profile_metadata(profile_path)
        self.desc_text.configure(state='normal')
        self.desc_text.delete('1.0', 'end')
        self.desc_text.insert('1.0', meta.get('description', ''))
        self.desc_text.configure(state='disabled')
        self.launch_opts_var.set(meta.get('launch_options', ''))

    def apply_profile(self):
        idx = self.profile_listbox.curselection()
        if not idx:
            NoProfileSelectedDialog(self, "Please select a profile to apply.")
            return
        profile_path = self.profiles[idx[0]]
        prev_profile_path = self.profiles[self.current_profile_idx] if self.current_profile_idx is not None else None
        def delete_matching_files(src_folder, dst_folder):
            if not os.path.exists(src_folder) or not os.path.exists(dst_folder):
                return
            for root, dirs, files in os.walk(src_folder):
                rel_root = os.path.relpath(root, src_folder)
                dst_root = os.path.join(dst_folder, rel_root) if rel_root != '.' else dst_folder
                for file in files:
                    dst_file = os.path.join(dst_root, file)
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
        def delete_cache_files(folder):
            if not os.path.exists(folder):
                return
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith('.cache'):
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception:
                            pass
        def do_apply():
            try:
                # Delete only files that exist in the previous [current] profile
                if prev_profile_path:
                    for folder in ['cfg', 'custom']:
                        prev_src = os.path.join(prev_profile_path, folder)
                        dst = os.path.join(self.tf2_dir, folder)
                        delete_matching_files(prev_src, dst)
                # Copy/merge files from new profile to tf2_dir
                for folder in ['cfg', 'custom']:
                    src = os.path.join(profile_path, folder)
                    dst = os.path.join(self.tf2_dir, folder)
                    if os.path.exists(src):
                        if not os.path.exists(dst):
                            shutil.copytree(src, dst)
                        else:
                            for root, dirs, files in os.walk(src):
                                rel_root = os.path.relpath(root, src)
                                dst_root = os.path.join(dst, rel_root) if rel_root != '.' else dst
                                if not os.path.exists(dst_root):
                                    os.makedirs(dst_root)
                                for file in files:
                                    shutil.copy2(os.path.join(root, file), os.path.join(dst_root, file))
                # Delete .cache files in tf/cfg and tf/custom AFTER copying
                for folder in ['cfg', 'custom']:
                    delete_cache_files(os.path.join(self.tf2_dir, folder))
                ThemedInfoDialog(self, "Profile applied successfully.", title="Success")
            except Exception as e:
                ThemedErrorDialog(self, f"Failed to apply profile: {e}")
        if self.current_profile_idx is not None:
            def on_apply():
                do_apply()
            ApplyProfileDialog(self, on_apply)
            return
        do_apply()

    def new_profile(self):
        def import_from_tf():
            tf_folder = self.tf2_dir
            if not tf_folder or not os.path.isdir(tf_folder):
                ThemedErrorDialog(self, "Please select a valid tf folder first.")
                return
            self._create_profile_from_folder(tf_folder)
        def import_from_custom():
            def on_submit(name, desc, launch_opts, cfg_folder, custom_folder):
                profile_id = name.replace(' ', '_')
                profile_path = os.path.join(PROFILES_DIR, profile_id)
                if os.path.exists(profile_path):
                    ThemedErrorDialog(self, "A profile with this name already exists.")
                    return
                try:
                    ensure_dir(profile_path)
                    dst_cfg = os.path.join(profile_path, 'cfg')
                    dst_custom = os.path.join(profile_path, 'custom')
                    shutil.copytree(cfg_folder, dst_cfg)
                    shutil.copytree(custom_folder, dst_custom)
                    save_profile_metadata(profile_path, name, desc, launch_opts or "")
                    ThemedInfoDialog(self, "Profile created.", title="Success")
                    self.refresh_profiles()
                except Exception as e:
                    ThemedErrorDialog(self, f"Failed to create profile: {e}")
            CustomImportProfileDialog(self, on_submit)
        NewProfileDialog(self, import_from_tf, import_from_custom)

    def _create_profile_from_folder(self, tf_folder):
        def on_submit(name, desc, launch_opts):
            profile_id = name.replace(' ', '_')
            profile_path = os.path.join(PROFILES_DIR, profile_id)
            if os.path.exists(profile_path):
                ThemedErrorDialog(self, "A profile with this name already exists.")
                return
            try:
                ensure_dir(profile_path)
                backup_folders(tf_folder, profile_path)
                save_profile_metadata(profile_path, name, desc, launch_opts or "")
                ThemedInfoDialog(self, "Profile created.", title="Success")
                self.refresh_profiles()
            except Exception as e:
                ThemedErrorDialog(self, f"Failed to create profile: {e}")
        ThemedNewProfileDialog(self, on_submit)

    def delete_profile(self):
        idx = self.profile_listbox.curselection()
        if not idx:
            NoProfileSelectedDialog(self, "Please select a profile to delete.")
            return
        profile_path = self.profiles[idx[0]]
        meta = load_profile_metadata(profile_path)
        is_current = (self.current_profile_idx == idx[0])
        def on_confirm(delete_tf):
            try:
                shutil.rmtree(profile_path)
                if delete_tf:
                    delete_folders(self.tf2_dir)
                msg = "Profile deleted."
                if delete_tf:
                    msg += "\nTF config deleted from tf directory."
                ThemedInfoDialog(self, msg, title="Deleted")
                self.refresh_profiles()
            except Exception as e:
                ThemedErrorDialog(self, f"Failed to delete profile: {e}")
        if is_current:
            DeleteProfileDialog(self, meta.get('name', os.path.basename(profile_path)), on_confirm)
        else:
            def confirm_delete():
                on_confirm(False)
            ThemedConfirmDialog(
                self,
                "This will delete the profile from your profiles folder. This cannot be undone. Continue?",
                confirm_delete,
                title="Delete Profile?"
            )

    def edit_profile(self):
        idx = self.profile_listbox.curselection()
        if not idx:
            NoProfileSelectedDialog(self, "Please select a profile to edit.")
            return
        profile_path = self.profiles[idx[0]]
        meta = load_profile_metadata(profile_path)
        def on_save(new_name, new_desc, new_launch_opts):
            save_profile_metadata(profile_path, new_name, new_desc, new_launch_opts)
            self.refresh_profiles()
            self.profile_listbox.selection_set(idx[0])
            self.on_select(None)
        EditProfileDialog(self, meta, on_save)

    def change_tf2_dir(self):
        path = filedialog.askdirectory(title="Select your tf folder (should contain cfg and custom)")
        if path:
            set_tf2_dir(self.config, path)
            self.tf2_dir = path
            self.tf2_dir_var.set(path)
            self.on_change_tf2_dir(path)

    def fresh_install(self):
        tf2_dir = self.tf2_dir
        if not tf2_dir or not os.path.isdir(tf2_dir):
            ThemedErrorDialog(self, "Please select a valid tf folder first.")
            return
        def do_delete():
            try:
                shutil.rmtree(tf2_dir)
                ThemedInfoDialog(self, "The entire 'tf' folder has been deleted.\n\nYou must now verify the integrity of game files for Team Fortress 2 in Steam before launching the game or applying any new profiles.", title="Fresh Install Complete")
            except Exception as e:
                ThemedErrorDialog(self, f"Failed to perform fresh install: {e}")
        FreshInstallDialog(self, do_delete)

    def show_help(self):
        HelpDialog(self)

class TF2ConfigManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("620x600")  # Increased window size
        self.resizable(True, True)  # Allow resizing
        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass
        self.font = ("Segoe UI", 10)
        self.configure(fg_color="#181818")
        ensure_dir(PROFILES_DIR)
        self.config_parser = load_config()
        if 'DEFAULT' not in self.config_parser:
            self.config_parser['DEFAULT'] = {}
        self.first_launch = not os.path.exists(CONFIG_FILE)
        self.after(100, self.startup_flow)

    def startup_flow(self):
        if self.first_launch:
            self.withdraw()
            def on_close():
                self.deiconify()
                self.show_main()
            InfoDialog(self, on_close)
        else:
            self.show_main()

    def show_main(self):
        for widget in self.winfo_children():
            widget.destroy()
        pm = ProfileManager(self, self.config_parser, self.on_change_tf2_dir)
        pm.pack(fill='both', expand=True)

    def on_change_tf2_dir(self, _):
        pass

def main():
    app = TF2ConfigManagerApp()
    app.mainloop()

if __name__ == "__main__":
    main() 