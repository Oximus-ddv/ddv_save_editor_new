This is a rework of : https://github.com/BenCG3/Ddv-Save-Editor/ big shootout to BenCG3 for his work !

# DDV Save Editor - Python Version

A modern, comprehensive save file editor for Disney Dreamlight Valley, rebuilt in Python with advanced features and enhanced functionality.

## What the app does (quick summary)

- Edit DDV save files safely (with automatic backups).
- Load a live item database from an Excel spreadsheet and organize items into friendly categories/subcategories.
- Add/remove items, adjust amounts, and fully edit pets (CustomName, FriendshipLevel, XP).
- Edit currencies and player info.
- Filter out problematic/debug items automatically.

## ✨ Key Features

### 🚀 **Smart Save Detection**
- **Automatic Detection**: Finds your latest save file automatically by timestamp
- **Multi-Platform Support**: Works with Steam and Windows Store versions  
- **Enhanced Logging**: Detailed file information and loading progress
- **Manual Override**: Option to select specific save files when needed

### 🔐 **Advanced Encryption Handling**
- **Auto-Decryption**: Uses known DDV encryption keys automatically
- **Custom Key Support**: Handles custom decryption keys
- **File Validation**: Robust encryption detection and error handling

### 📊 **Comprehensive Item Management**
- **16 Categories**: Detailed organization with granular subcategories
  - **Pets**: All companion animals
  - **Clothes**: Outfits, Tops, Bottoms, Helmets, Shoes, Accessories, Other
  - **Houses**: Skins, Wallpapers, Floors, NPC Houses
  - **Furniture**: All decorative items
  - **Tools**: Pickaxes, shovels, fishing rods, etc.
  - **Food & Materials**: Consumables and crafting components

### 🎨 **Smart Content Filtering**
- **Quality Control**: Automatically filters out debug/problematic items
- **Color-Coded Rules**: 
  - 🔴 Red cells = Filtered out (broken/test items)
  - 🟡 Yellow cells = Limited to 1 item maximum
  - 🔵 Blue cells = Completely hidden from interface
- **Excel Integration**: Loads complete item database from spreadsheet

### 💰 **Currency Editor**
- Edit all currencies: Star Coins, Dreamlight, Daisy Coins, Mist, Pixel Dust
- Player information editing (name, level)
- Quick max/reset buttons with validation

### 🎨 **Modern Interface**
- Clean, intuitive design
- Real-time progress indicators
- Comprehensive logging and status updates
- Image preview support for items

## 🛠️ Installation

### Quick Start
```bash
git clone https://github.com/Nassbrock/DDV-Save-Editor.git
cd DDV-Save-Editor
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

### Requirements
- Python 3.8 or higher
- Windows 10/11 (primary support)

## 📖 Usage

### Getting Started
1. **Launch**: Run `python main.py`
2. **Auto-Load**: Click "Auto-Load" - the app will find your latest save automatically
3. **Edit**: Use the category tabs to modify items, currencies, and player data
4. **Save**: Click "Save" to write changes back to your save file

### Advanced Features
- **Manual Loading**: Use "Manual Load" if auto-detection doesn't work
- **Detailed Logs**: Check console output for comprehensive operation details
- **Backup System**: Automatic timestamped backups before any changes

## 🔍 What's New in Python Version

### 🚀 **Enhanced Performance**
- Faster save file detection and loading
- Efficient Excel parsing with color detection
- Smart caching for images and data

### 🧠 **Intelligent Features**
- **Automatic Save Selection**: Finds most recent save across all game installations
- **Smart Item Filtering**: Removes test/debug items automatically
- **Quality Limits**: Respects game item limitations (1-max items, filtered categories)

### 📊 **Better Data Handling**
- **Live Excel Integration**: No hardcoded item lists
- **Category Intelligence**: Maps Excel categories to logical game groupings
- **Error Recovery**: Robust handling of corrupted or incomplete data

### 🔧 **Developer Improvements**
- **Modern Architecture**: Clean separation of concerns
- **Comprehensive Logging**: Every operation is logged for debugging
- **Type Safety**: Full type hints and validation
- **Extensible Design**: Easy to add new features and categories

## 📁 Project Structure

```
ddv_save_editor_python/
├── src/
│   ├── gui/              # UI components (main window, editors, dialogs)
│   ├── services/         # Core services (save, excel, image handling)  
│   └── models/           # Data models and validation
├── backups/              # Automatic save backups (created at runtime)
├── requirements.txt      # Python dependencies
├── main.py              # Application entry point
└── img.zip              # Item images (optional)
```

## 🚨 Safety Features

- **Automatic Backups**: Creates timestamped backups before any changes
- **Data Validation**: Ensures save file integrity using Pydantic models
- **Error Recovery**: Comprehensive error handling with detailed logging
- **Non-Destructive**: Original files are preserved

## 🆚 Advantages Over C# Version

### ✅ **User Experience**
- **Smarter**: Automatic save detection, intelligent filtering
- **Faster**: Optimized loading and processing
- **Safer**: Better error handling and recovery
- **More Informative**: Detailed logging and progress feedback

### ✅ **Technical Improvements**
- **Cross-Platform**: Works on Windows, Mac, Linux
- **Modern Libraries**: pandas, openpyxl, Pillow, cryptography
- **Better Architecture**: Clean, maintainable code structure
- **Type Safety**: Full type hints and validation

### ✅ **Feature Rich**
- **Dynamic Data**: Excel-driven item database
- **Smart Filtering**: Automatic problem item detection
- **Enhanced Categories**: 16 granular categories vs basic grouping
- **Quality Controls**: Respects game limitations and rules

## 🪟 Using the Windows .exe with the Excel file

The app needs your Excel data file to populate categories and items. When running the packaged `.exe`, place the Excel next to the executable or select it when prompted.

### Recommended folder layout

```
release/
  DDV_Save_Editor.exe
  Disney Dream Light ID List - Mainted by Rubyelf.xlsx   # or your own data file
  img.zip                                               # optional (item images)
```

### First run

- If the Excel is not found, the app will prompt you to select it. Pick your `.xlsx` and the categories will load.
- After selecting once, the app caches data in memory for the session; reloading Excel uses the same picker.

### Auto-Load save

1. Click "Auto-Load" to detect and load the latest DDV save.
2. If categories are empty, ensure the Excel file is available as described above, then use "Refresh Excel Data" or restart the app.

### Decryption key

- The standard DDV hex key is built in.

### Troubleshooting

- **Categories don’t load**: The Excel file is missing/not found. Place the `.xlsx` next to the `.exe` or select it when prompted.
- **Images not showing**: Ensure `img.zip` or an `img/` folder exists if you want item images (optional).
- **Auto-Load finds no save**: Use "Manual Load" and browse to your `profile.json` (Steam/Windows folders).

## 🤝 Contributing

Contributions welcome! The codebase is designed to be easily extensible:
- **Add Categories**: Extend the `ItemCategory` enum
- **New Features**: Clean service architecture makes additions straightforward  
- **Bug Fixes**: Comprehensive logging makes debugging easier

## ⚠️ Disclaimer

This tool modifies game save files. While it includes extensive safety features like automatic backups and validation, always backup your saves manually before use.

## 📜 License

MIT License - see LICENSE file for details.
