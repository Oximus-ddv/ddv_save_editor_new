#!/usr/bin/env python3
"""
DDV Save Editor - Python Version
Main entry point for the application
"""
import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gui.main_window import MainWindow


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ddv_editor.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting DDV Save Editor - Python Version")
        
        # Create and run the main window
        app = MainWindow()
        app.run()
        
        logger.info("Application closed successfully")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        
        # Show error dialog if GUI is available
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide main window
            messagebox.showerror(
                "Fatal Error",
                f"An unexpected error occurred:\n\n{e}\n\nCheck ddv_editor.log for details."
            )
        except:
            print(f"Fatal error: {e}")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
