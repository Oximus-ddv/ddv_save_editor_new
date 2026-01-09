# DDV Save Editor

This is a save file editor for Disney Dreamlight Valley. It allows you to modify your save files to get more items, edit currencies, and customize your game.

## ✨ Features

- **Edit Your Inventory**: Add or remove items from your inventory, including clothes, furniture, and more.
- **Edit Currencies**: Change the amount of Star Coins, Dreamlight, and other in-game currencies.
- **Pet Editor**: Customize your companions' names and friendship levels.
- **Automatic Backups**: Your original save file is automatically backed up before any changes are made, so you can always revert if something goes wrong.
- **Easy to Use**: A user-friendly interface that makes editing your save file simple and intuitive.
- **Multi-platform**: Works with saves from Steam, Epic Games, and Microsoft Store versions of the game.

## 💾 How to use the editor

1.  **Download the editor**: You can find the latest version of the editor on the [releases page](https://github.com/Oximus-ddv/DDV-Save-Editor/releases). Download the `.exe` file.
2.  **Prepare your files**:
    *   Place the `DDV_Save_Editor.exe` file in a folder.
    *   You will need a data source for the items. You can either use an Excel file (`Disney Dream Light ID List - Mainted by Rubyelf.xlsx`) or the `Dict` folder. Place one or both of these in the same folder as the `.exe` file.
    *   If you want to see images of the items, you can also place `img.zip` or an `img` folder in the same directory.
    *   Your folder should look like this:

    ```
    release/
    ├── DDV_Save_Editor.exe
    ├── Disney Dream Light ID List - Mainted by Rubyelf.xlsx   # Excel data source
    └── Dict/                                                  # Dict data source
    ```

3.  **Launch the editor**: Double-click on `DDV_Save_Editor.exe` to run it.
4.  **Load your save file**:
    *   Click the **"Auto-Load"** button. The editor will automatically find your most recent Disney Dreamlight Valley save file.
    *   If the editor cannot find your save file, you can use the **"Manual Load"** button to select your `profile.json` file yourself.
5.  **Edit your save**:
    *   Use the tabs at the top to navigate between different categories like **Clothes**, **Furniture**, **Currencies**, etc.
    *   Select items from the list to add them to your inventory. You can also change the quantity of items.
6.  **Save your changes**:
    *   Once you are done editing, click the **"Save"** button. Your changes will be saved to your game.

## 🚨 Safety

This tool automatically creates a backup of your save file before making any changes. The backup will have a timestamp in its name and will be placed in a `backups` folder. If you want to restore a backup, you will need to rename the backup file and replace your current save file with it.

## ❓ Troubleshooting

-   **The categories are empty**: Make sure you have the Excel file or the `Dict` folder in the same directory as the `.exe` file. In the editor's toolbar, select the correct data source (Excel or Dict).
-   **Images are not showing**: Make sure `img.zip` or the `img` folder is in the same directory as the `.exe` file.
-   **The editor can't find my save file**: Use the "Manual Load" button to locate your save file manually.
-   **The application shows an error**: Please create an issue on the [GitHub issues page](https://github.com/Oximus-ddv/DDV-Save-Editor/issues) and describe what you were doing when the error occurred. Include the `ddv_editor.log` file if possible.

## ⚠️ Disclaimer

This tool modifies your game's save files. While it is designed to be safe, there is always a risk of corrupting your save file. It is highly recommended that you make a manual backup of your save files before using this editor. The creator of this tool is not responsible for any damage to your save files.
