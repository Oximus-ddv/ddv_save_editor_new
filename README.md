# DDV Save Editor - Python Version

A modern, Python-based save editor for Disney Dreamlight Valley with dynamic Excel data loading and enhanced image support.

## Features

### 🎮 Save File Support
- ✅ Load and save encrypted DDV save files
- ✅ Automatic decryption with hex key input
- ✅ Automatic backup creation before changes
- ✅ Save file validation and integrity checking

### 📊 Dynamic Data Loading
- ✅ Load item data from Excel files (no hardcoded lists!)
- ✅ Automatic category detection from worksheet names
- ✅ Real-time data refresh when Excel file changes
- ✅ Support for custom item properties and metadata

### 🖼️ Enhanced Image Support
- ✅ Load images from ZIP files or folder structure
- ✅ Smart image fallback with placeholder generation
- ✅ Multiple image format support (PNG, JPG, etc.)
- ✅ Image caching for improved performance

### 💰 Currency Editing
- ✅ Edit all game currencies (Star Coins, Dreamlight, etc.)
- ✅ Quick max/reset buttons for each currency
- ✅ Player name and level editing

### 🎁 Item Management
- ✅ Add/remove items by category (Pets, Clothes, Houses, etc.)
- ✅ Bulk operations (add all, clear all)
- ✅ Item quantity editing
- ✅ Search and filter functionality

### 🔧 Modern UI
- ✅ Clean, intuitive interface built with tkinter
- ✅ Tabbed interface for different item categories
- ✅ Real-time search across all items
- ✅ Settings dialog for configuration
- ✅ Progress indicators for long operations

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Install from Source

1. **Clone or download the project**
```bash
git clone https://github.com/yourusername/ddv-save-editor-python.git
cd ddv-save-editor-python
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python main.py
```

### Install as Package

```bash
pip install -e .
ddv-editor
```

### Create Executable (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

## Setup Guide

### 1. Prepare Data Files

#### Excel File
- Copy your `Disney Dream Light ID List - Mainted by Rubyelf.xlsx` to the project directory
- Or use File → Load Excel Data to browse for it
- The file should have worksheets named: `pets`, `clothes`, `houses`, etc.
- Required columns: `ID` (or `ItemID`) and `Name` (or `ItemName`)

#### Images
Choose one of these options:

**Option A: ZIP File (Recommended)**
- Place `img.zip` in the project directory
- Organize images by category: `pets/12345.png`, `clothes/54321.png`

**Option B: Folder Structure**
- Create `img/` folder in project directory
- Create subfolders: `img/pets/`, `img/clothes/`, etc.
- Place images with item ID as filename: `12345.png`

### 2. Run the Application

1. **Start the application**: `python main.py`
2. **Load Excel data**: The app will automatically load the Excel file
3. **Load a save file**: File → Load Save File (or auto-detect common locations)
4. **Enter decryption key** if prompted (for encrypted saves)
5. **Edit items and currencies** using the tabbed interface
6. **Save changes**: File → Save

## Usage Guide

### Loading a Save File

1. **Automatic Detection**: The app will try to find your save file in common locations
2. **Manual Selection**: Use File → Load Save File to browse
3. **Encrypted Files**: Enter the hex decryption key when prompted
4. **Backup**: A backup is automatically created before loading

### Editing Items

1. **Select Category**: Click on tabs (Pets, Clothes, Houses, etc.)
2. **Add Items**: 
   - Double-click items in the "Available Items" list
   - Or select items and click "Add Selected"
   - Or click "Add All" to add everything
3. **Edit Quantities**: Double-click items in "Items in Save" list
4. **Remove Items**: Select items and click "Remove Selected"
5. **Search**: Use search boxes to filter items

### Editing Currencies

1. **Go to Currencies tab**
2. **Edit values** directly in the number fields
3. **Use Quick Buttons**: "Max" to set maximum, "Reset" to set zero
4. **Apply Changes**: Click "Apply Changes" to update save data

### Settings

Access via Edit → Settings:

- **File Paths**: Configure Excel and image file locations
- **Images**: Adjust cache size and image quality settings
- **Backups**: Configure automatic backup behavior

## File Structure

```
ddv_save_editor_python/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup script
├── README.md              # This file
│
├── src/
│   ├── models/
│   │   └── game_item.py   # Data models (GameItem, SaveData, etc.)
│   │
│   ├── services/
│   │   ├── excel_service.py    # Excel file reading
│   │   ├── image_service.py    # Image loading and caching
│   │   └── save_service.py     # Save file handling
│   │
│   └── gui/
│       ├── main_window.py      # Main application window
│       ├── item_editor.py      # Item editing interface
│       ├── currency_editor.py  # Currency editing interface
│       └── settings_dialog.py  # Settings configuration
│
├── backups/               # Automatic save backups (created at runtime)
├── img/                   # Image folder (optional)
├── img.zip               # Image ZIP file (optional)
└── Disney Dream Light ID List - Mainted by Rubyelf.xlsx
```

## Advantages Over C# Version

### ✅ Development Benefits
- **Simpler Setup**: No Visual Studio or .NET Framework required
- **Cross-Platform**: Works on Windows, Mac, and Linux
- **Better Libraries**: Pandas for Excel, PIL for images, cryptography for security
- **Easier Distribution**: Single executable with PyInstaller

### ✅ User Benefits
- **Dynamic Data**: No recompilation needed for new items
- **Better Performance**: Efficient caching and async operations
- **Modern UI**: Clean, responsive interface
- **Enhanced Features**: Advanced search, better error handling

### ✅ Maintenance Benefits
- **Cleaner Code**: Better separation of concerns
- **Easier Testing**: Built-in testing frameworks
- **Better Error Handling**: Comprehensive exception handling
- **Logging**: Built-in logging for troubleshooting

## Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
pip install -r requirements.txt
```

#### "Excel file not found"
- Check if the file exists in the project directory
- Use File → Load Excel Data to browse for it
- Verify the file isn't corrupted

#### "Images not loading"
- Check if `img.zip` exists OR `img/` folder exists
- Verify image filenames match item IDs
- Try clearing image cache: Tools → Clear Image Cache

#### "Decryption failed"
- Verify the hex key is correct
- Check that the save file isn't corrupted
- Try using an unencrypted save file first

### Debug Mode

Run with debug logging:
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" main.py
```

Check `ddv_editor.log` for detailed error information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original C# version contributors
- Disney Dreamlight Valley community
- EPPlus and other library maintainers
- Beta testers and feedback providers

## Support

- Create an issue on GitHub for bugs or feature requests
- Check the log file (`ddv_editor.log`) for error details
- Include your Python version and OS when reporting issues
#   D D V - S a v e - E d i t o r  
 