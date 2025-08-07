# Testing Guide - DDV Save Editor Python

This guide explains how to test the Python version of the DDV Save Editor.

## Quick Start Testing

### 1. Environment Setup

```bash
# Clone/download the project
cd ddv_save_editor_python

# Install Python 3.8+ if not already installed
python --version  # Should be 3.8 or higher

# Install dependencies
pip install -r requirements.txt
```

### 2. Basic Test Run

```bash
# Run the application
python main.py
```

The application should start and show the main window with tabs for Currencies, and potentially other categories if Excel data is found.

## Test Scenarios

### Test 1: Basic Application Startup ✅
**Expected**: Application starts without errors
- Main window appears
- Menu bar is functional
- Tabs are visible
- Status bar shows "Ready"

### Test 2: Excel Data Loading ✅

**Without Excel file**:
- Application starts but shows no item categories
- Status shows "No Excel data found"

**With Excel file**:
```bash
# Copy your Excel file to the project directory
cp "Disney Dream Light ID List - Mainted by Rubyelf.xlsx" ./

# Restart application
python main.py
```
- Tabs should appear for each category (Pets, Clothes, etc.)
- Status shows "Excel data loaded successfully"
- Database stats appear in status bar

### Test 3: Image Loading ✅

**Setup test images**:
```bash
# Option A: Create test ZIP
mkdir -p temp_img/pets temp_img/clothes
# Add some test images like 120000001.png, 50000001.png
zip -r img.zip temp_img/*

# Option B: Create folder structure
mkdir -p img/pets img/clothes
# Copy test images
```

**Expected**:
- Items show thumbnail images
- Missing images show placeholder with "?" symbol
- No crashes when loading images

### Test 4: Save File Operations ✅

**Test with unencrypted save**:
1. File → Load Save File
2. Select a test JSON file
3. **Expected**: Currency values load, item counts update

**Test with encrypted save**:
1. File → Load Save File
2. Select encrypted save file
3. Enter hex key when prompted
4. **Expected**: Successful decryption and loading

**Test save operations**:
1. Make changes to currencies/items
2. File → Save
3. **Expected**: Backup created, file saved successfully

### Test 5: Currency Editing ✅

1. Load a save file
2. Go to Currencies tab
3. Edit Star Coins value
4. Click "Apply Changes"
5. **Expected**: Values update immediately

**Test bulk operations**:
- "Max All Currencies" sets all to maximum
- "Reset All Currencies" sets all to zero

### Test 6: Item Management ✅

**Prerequisites**: Excel data loaded with items

1. Go to any item category tab (e.g., Pets)
2. **Available Items panel**: Should show items from Excel
3. **Add items**: Double-click or use "Add Selected"
4. **Items in Save panel**: Should show added items
5. **Edit quantity**: Double-click item in save list
6. **Remove items**: Select and click "Remove Selected"

**Test search functionality**:
- Type in search boxes to filter items
- Search should work in both Available and Save panels

### Test 7: Settings and Configuration ✅

1. Edit → Settings
2. Test each tab:
   - **File Paths**: Browse for files
   - **Images**: Adjust cache settings
   - **Backups**: Configure backup options
3. **Expected**: Settings save and persist between sessions

## Performance Testing

### Memory Usage 📊
Monitor memory usage with:
```bash
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep python
```

**Expected memory usage**:
- Base application: ~50-100 MB
- With Excel data: +10-30 MB
- With image cache: +5-20 MB per 100 images

### Load Time Testing ⏱️
Measure startup and operation times:
- Application startup: < 5 seconds
- Excel data loading: < 10 seconds for large files
- Save file loading: < 5 seconds
- Image cache loading: < 15 seconds for 100+ images

## Error Testing

### Test Error Handling 🚨

**Missing files**:
- Start app without Excel file → Should show warning, continue
- Load non-existent save file → Should show error dialog
- Use invalid image ZIP → Should fall back gracefully

**Invalid data**:
- Load corrupted Excel file → Should show error, continue with empty data
- Load invalid save file → Should show descriptive error
- Enter invalid hex key → Should prompt for retry

**Memory limits**:
- Load very large Excel file (1000+ items) → Should handle gracefully
- Load many images → Should respect cache limits

## Integration Testing

### Test with Real Data 🎮

**Use actual game files**:
1. Copy real DDV save file
2. Use community-maintained Excel file
3. Use actual image ZIP from community
4. Test complete workflow:
   - Load save → Edit items → Edit currencies → Save

**Test backup system**:
1. Load save file
2. Check that backup was created in `backups/` folder
3. Make changes and save
4. Verify new backup created
5. Test backup restoration (when implemented)

## Platform Testing

### Windows Testing 🪟
```bash
# Test with different Python versions
python3.8 main.py
python3.9 main.py
python3.10 main.py
python3.11 main.py
```

### Cross-Platform Testing 🌐
If available, test on:
- Windows 10/11
- macOS
- Linux (Ubuntu/Debian)

**Expected**: Same functionality across all platforms

## Automated Testing

### Unit Tests 🧪
```bash
# Install pytest
pip install pytest

# Run tests (when implemented)
pytest tests/
```

### Integration Tests 🔧
```bash
# Test with sample data
python -m pytest tests/integration/
```

## Building and Distribution Testing

### Test Executable Creation 📦
```bash
# Build standalone executable
python build_executable.py

# Test the executable
./dist/DDV_Save_Editor.exe  # Windows
./dist/DDV_Save_Editor      # Linux/Mac
```

**Expected**:
- Executable runs without Python installation
- All features work identically
- File size reasonable (~50-150 MB)

### Test Package Installation 📋
```bash
# Test pip installation
pip install -e .

# Test command-line entry point
ddv-editor
```

## Regression Testing

### Test Against C# Version ⚖️

Compare functionality:
- [ ] Save file loading/saving works identically
- [ ] Currency editing produces same results
- [ ] Item management works the same way
- [ ] Backup creation behaves similarly
- [ ] Performance is comparable or better

## Troubleshooting Test Issues

### Common Test Problems

**"ModuleNotFoundError"**:
```bash
pip install -r requirements.txt
python -m pip install --upgrade pip
```

**"Excel file not found"**:
- Check file exists in project directory
- Verify filename matches exactly
- Try using absolute path

**"Images not displaying"**:
- Check img.zip exists OR img/ folder exists
- Verify image formats (PNG, JPG supported)
- Try clearing cache: Tools → Clear Image Cache

**"Slow performance"**:
- Reduce image cache size in settings
- Use smaller image files
- Close other applications

**"Save loading fails"**:
- Verify save file isn't corrupted
- Check hex key is correct for encrypted saves
- Try with unencrypted save first

### Debug Mode

Enable detailed logging:
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" main.py
```

Check the log file `ddv_editor.log` for detailed error information.

## Test Checklist

### Basic Functionality ✅
- [ ] Application starts without errors
- [ ] Excel data loads correctly
- [ ] Images display properly
- [ ] Save file loads successfully
- [ ] Currency editing works
- [ ] Item management works
- [ ] Settings save and load
- [ ] Backups are created

### Performance ✅
- [ ] Startup time < 5 seconds
- [ ] Memory usage reasonable
- [ ] No memory leaks during extended use
- [ ] Image loading doesn't freeze UI

### Error Handling ✅
- [ ] Graceful handling of missing files
- [ ] Clear error messages
- [ ] Application doesn't crash
- [ ] Recovery from errors possible

### Compatibility ✅
- [ ] Works with different Python versions
- [ ] Cross-platform compatibility
- [ ] Real game data compatibility
- [ ] Backward compatibility with C# saves

## Reporting Issues

When reporting test failures, include:
1. Python version (`python --version`)
2. Operating system
3. Exact error message
4. Steps to reproduce
5. Log file contents (`ddv_editor.log`)
6. Screenshots if applicable

## Success Criteria

The Python version is ready for release when:
- ✅ All basic functionality tests pass
- ✅ Performance meets or exceeds C# version
- ✅ Error handling is robust
- ✅ Cross-platform compatibility verified
- ✅ Real game data works correctly
- ✅ Executable builds successfully
- ✅ User experience is intuitive
