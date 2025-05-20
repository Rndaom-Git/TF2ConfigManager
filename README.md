# 🎮 TF2 Config Manager

**Easily manage, backup, and switch between Team Fortress 2 config profiles!**

![TF2 Logo](https://cdn.cloudflare.steamstatic.com/steam/apps/440/header.jpg)

---

## ✨ Features

- 🗂️ **Profile Management:** Create, edit, and delete multiple config profiles for TF2.
- 🔄 **One-Click Switching:** Instantly apply any profile to your TF2 directory.
- 🛡️ **Safe Backups:** Never lose your custom configs—profiles are stored safely.
- 🚀 **Steam Launch Options:** Save and recall your favorite launch options per profile.
- 🕵️ **Auto-Detect:** The app detects changes in your `cfg` and `custom` folders.
- 🧹 **Fresh Install:** Wipe your TF2 config for a clean start (with safety checks!).

---

## 🛠️ Installation

1. **Clone this repo:**
   ```bash
   git clone https://github.com/yourusername/TF2ConfigManager.git
   cd TF2ConfigManager
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   ```bash
   python main.py
   ```

---

## 🧑‍💻 Usage

1. **Set your TF2 folder:**  
   Click "Change tf Folder" and select your `tf` directory (should contain `cfg` and `custom`).

2. **Create a new profile:**  
   - Import from your current TF2 folder, or  
   - Import from any `cfg`/`custom` folders.

3. **Switch profiles:**  
   Select a profile and click "Apply Profile" to instantly swap configs.

4. **Edit or delete profiles:**  
   Use the "Edit" and "Delete" buttons for easy management.

5. **Fresh install:**  
   Use "Fresh Install" to wipe your TF2 config. You have to verify game files in Steam after.

6. **Need help?**  
   Click the `?` button for a full FAQ and help dialog.

---

## ⚠️ Warnings

- **Back up your configs!**  
  While this tool is designed to be safe, always keep backups of important files.
- **Fresh Install is destructive!**  
  This will delete your entire `tf` folder. You must verify your game files in Steam after using it.

---

## 💡 FAQ

- **Q: Where are profiles stored?**  
  A: In the `profiles/` folder inside the app directory.

- **Q: Does this modify my Steam or TF2 install?**  
  A: No, it only manages your `cfg` and `custom` folders.

- **Q: Can I use this for other Source games?**  
  A: It's designed for TF2, but may work for similar folder structures.

---

## 🧑‍🎨 Credits

- UI: [CustomTkinter](https://customtkinter.tomschimansky.com/)
- Made with ❤️ by Rndaom

---

## 📝 License

MIT License. See [LICENSE](LICENSE) for details.
