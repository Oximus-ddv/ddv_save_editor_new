#!/usr/bin/env python3
"""
Build script to create a standalone executable for DDV Save Editor
"""
import subprocess
import sys
import shutil
from pathlib import Path


def main():
    """Build the executable"""
    print("🔨 Building DDV Save Editor executable...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller"])
    
    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("🧹 Cleaned previous dist directory")
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("🧹 Cleaned previous build directory")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Create single file
        "--windowed",                   # Don't show console window
        "--name", "DDV_Save_Editor",    # Output name
        "--icon", "icon.ico",           # Icon (if exists)
        "--add-data", "README.md;.",    # Include README
        "--hidden-import", "PIL",       # Ensure PIL is included
        "--hidden-import", "pandas",    # Ensure pandas is included
        "--hidden-import", "openpyxl",  # Ensure openpyxl is included
        "main.py"
    ]
    
    # Remove icon parameter if icon doesn't exist
    if not Path("icon.ico").exists():
        cmd.remove("--icon")
        cmd.remove("icon.ico")
    
    try:
        # Run PyInstaller
        print("🚀 Running PyInstaller...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            exe_path = dist_dir / "DDV_Save_Editor.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"✅ Build successful!")
                print(f"📦 Executable: {exe_path}")
                print(f"📏 Size: {size_mb:.1f} MB")
                
                # Create distribution folder
                release_dir = Path("release")
                release_dir.mkdir(exist_ok=True)
                
                # Copy executable
                shutil.copy2(exe_path, release_dir / "DDV_Save_Editor.exe")
                
                # Copy example files
                example_files = [
                    "README.md",
                    "requirements.txt"
                ]
                
                for file in example_files:
                    if Path(file).exists():
                        shutil.copy2(file, release_dir)
                
                print(f"📁 Release files copied to: {release_dir}")
                print("\n🎉 Build complete! You can now distribute the 'release' folder.")
                
            else:
                print("❌ Executable not found after build")
                return False
        else:
            print(f"❌ PyInstaller failed with return code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error during build: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
