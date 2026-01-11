#!/usr/bin/env python3
"""
DDV Save Editor - Python Version
Main entry point for the application
"""
import sys
import logging
from pathlib import Path
import time
import traceback
import platform

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon
from PyQt6.QtCore import Qt


def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions, log them, and show a dialog to the user."""
    # Log the exception
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Create a crash report
    report = f"""--- CRASH REPORT ---
Date: {time.strftime('%Y-%m-%d %H:%M:%S')}
OS: {platform.system()} {platform.release()}
Python: {platform.python_version()}

--- TRACEBACK ---
{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}
"""
    with open("crash_report.txt", "w") as f:
        f.write(report)

    # Show a dialog to the user
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Application Crashed",
            "An unexpected error occurred and the application needs to close.\\n\\n"
            "A 'crash_report.txt' file has been created with details of the error."
        )
    except:
        # Fallback if GUI is not available
        print("Fatal error occurred. Crash report generated.")
        
    # Exit the application
    sys.exit(1)


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
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting DDV Save Editor - PyQt6 Version")
    
    # Install exception hook
    sys.excepthook = handle_exception
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    # Set application icon
    app.setWindowIcon(QIcon("images/logo.png"))
    
    # Create and show splash screen
    splash_image_png_path = Path("images/splash_screen.png")
    splash_image_jpg_path = Path("images/splash_screen.jpg")
    
    if splash_image_png_path.exists():
        logger.info("Loading splash screen from images/splash_screen.png")
        pixmap = QPixmap(str(splash_image_png_path))
    elif splash_image_jpg_path.exists():
        logger.info("Loading splash screen from images/splash_screen.jpg")
        pixmap = QPixmap(str(splash_image_jpg_path))
    else:
        logger.info("No splash screen image found, using fallback.")
        pixmap = QPixmap(400, 200)
        pixmap.fill(QColor("#2a2a2a"))
        painter = QPainter(pixmap)
        painter.setPen(QColor(Qt.GlobalColor.white))
        font = QFont()
        font.setPointSize(16)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Loading DDV Save Editor...")
        painter.end()

    splash = QSplashScreen(pixmap)
    splash.show()
    
    # Create and show the main window, passing the splash screen
    window = MainWindow(splash=splash)
    window.run()
    
    # Start the event loop
    result = app.exec()
    
    logger.info("Application closed successfully")
    return result

if __name__ == "__main__":
    sys.exit(main())
