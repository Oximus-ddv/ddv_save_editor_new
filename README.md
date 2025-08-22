This is a rework of : https://github.com/BenCG3/Ddv-Save-Editor/ big shootout to BenCG3 for his work !

# If you have ideas to add to the editor, please share them here : https://github.com/Oximus-ddv/ddv_save_editor_new/discussions/7

# DDV Save Editor - Python Version

A modern, comprehensive save file editor for Disney Dreamlight Valley, rebuilt in Python with advanced features and enhanced functionality.

## What the app does (quick summary)

- Edit DDV save files safely (with automatic backups).
- Load a live item database from an Excel spreadsheet or Dict folder.
- Add/remove items, adjust amounts, and fully edit pets (CustomName, FriendshipLevel, XP).
- Edit currencies and player info.
- Filter out problematic/debug items automatically.
- Full JSON editor for advanced editing.

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
 
  Select which data source to load:
  - **Excel**: Load from the Excel spreadsheet
  - **Dict**: Load from the Dict folder structure
  Make sure either or both are located in the same folder as the .exe.

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
- Full JSON editor for advanced users

### 🔍 **Advanced Editing Tools**
- **Full Editor**: View and edit any value in the save file directly
- **JSON Viewer**: Examine the raw save file structure
- **Search**: Fast search functionality across all data
- **Batch Operations**: Add all items, clear categories

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
- **Full Editor**: Access the full save file editor for advanced editing
- **Detailed Logs**: Check console output for comprehensive operation details
- **Backup System**: Automatic timestamped backups before any changes

## 🔍 What's New in Python Version

### 🚀 **Enhanced Performance**
- Faster save file detection and loading
- Efficient data parsing with both Excel and Dict support
- Smart caching for images and data
- Optimized search functionality

### 🧠 **Intelligent Features**
- **Automatic Save Selection**: Finds most recent save across all game installations
- **Smart Item Filtering**: Removes test/debug items automatically
- **Quality Limits**: Respects game item limitations (1-max items, filtered categories)
- **Full Editor**: Direct access to all save file values

### 📊 **Better Data Handling**
- **Dual Data Sources**: Excel or Dict folder support
- **Category Intelligence**: Maps categories to logical game groupings
- **Error Recovery**: Robust handling of corrupted or incomplete data
- **Fast Search**: Efficient searching across all data

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
│   ├── services/         # Core services (save, excel, dict, image handling)  
│   └── models/           # Data models and validation
├── Dict/                 # Dictionary-based item data (optional)
├── backups/             # Automatic save backups (created at runtime)
├── requirements.txt     # Python dependencies
├── main.py             # Application entry point
└── img.zip             # Item images (optional)
```

## 🚨 Safety Features

- **Automatic Backups**: Creates timestamped backups before any changes
- **Data Validation**: Ensures save file integrity using Pydantic models
- **Error Recovery**: Comprehensive error handling with detailed logging
- **Non-Destructive**: Original files are preserved

## 🪟 Using the Windows .exe

The app can use either an Excel file or Dict folder for item data. Place either (or both) next to the executable.

### Recommended folder layout

```
release/
  DDV_Save_Editor.exe
  Disney Dream Light ID List - Mainted by Rubyelf.xlsx   # Excel data source
  Dict/                                                  # Dict data source
  img.zip                                               # optional (item images)
```

### First run

- Choose your data source (Excel or Dict) in the toolbar
- If using Excel and it's not found, you'll be prompted to select it
- If using Dict, ensure the Dict folder is present with the correct structure

### Auto-Load save

1. Click "Auto-Load" to detect and load the latest DDV save.
2. If categories are empty, check your data source settings and files.

### Decryption key

- The standard DDV hex key is built in.

### Troubleshooting

- **Categories don't load**: Check your data source selection and ensure files are present
- **Images not showing**: Ensure `img.zip` or an `img/` folder exists if you want item images (optional)
- **Auto-Load finds no save**: Use "Manual Load" and browse to your `profile.json`
- **Full Editor slow**: Large save files may take a moment to process

## 🤝 Contributing

Contributions welcome! The codebase is designed to be easily extensible:
- **Add Categories**: Extend the `ItemCategory` enum
- **New Features**: Clean service architecture makes additions straightforward  
- **Bug Fixes**: Comprehensive logging makes debugging easier

## ⚠️ Disclaimer

This tool modifies game save files. While it includes extensive safety features like automatic backups and validation, always backup your saves manually before use.

## 📜 License

MIT License - see LICENSE file for details.