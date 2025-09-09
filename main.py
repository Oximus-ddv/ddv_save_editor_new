#!/usr/bin/env python3
"""
DDV Save Editor - Python Version
Main entry point for the application
"""
import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, QObject, pyqtSignal

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gui.main_window import MainWindow, set_dark_mode
from src.gui.toast_notification import ToastNotification
from src.services.settings_service import SettingsService
from src.services.update_service import UpdateService


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

class UpdateWorker(QObject):
    finished = pyqtSignal(bool)

    def __init__(self, settings_service, dict_root):
        super().__init__()
        self.update_service = UpdateService(settings_service, dict_root)

    def run(self):
        """Long-running task."""
        result = self.update_service.check_and_update()
        self.finished.emit(result)


def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting DDV Save Editor - Python Version")
        
        app = QApplication(sys.argv)
        set_dark_mode(app)
        
        main_window = MainWindow()
        main_window.show()

        # Run update check in a separate thread
        thread = QThread()
        settings_service = SettingsService()
        worker = UpdateWorker(settings_service, "Dict")
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        def on_update_finished(success):
            if success:
                ToastNotification(main_window, "Dictionary updated successfully!")

        worker.finished.connect(on_update_finished)

        thread.start()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        
        # Show error dialog
        app = QApplication(sys.argv)
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setText("A fatal error occurred.")
        error_dialog.setInformativeText(f"{e}\n\nCheck ddv_editor.log for details.")
        error_dialog.setWindowTitle("Fatal Error")
        error_dialog.exec()
        
        sys.exit(1)



if __name__ == "__main__":
    main()
