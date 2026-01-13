
import sys
import logging
from unittest.mock import Mock, patch
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QSplashScreen

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gui.main_window import MainWindow
from main import SplashLogHandler

# Pytest fixture for QApplication instance
@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_splash_screen_logging(qapp, monkeypatch):
    """Test that logs are displayed on the splash screen."""
    # Mock QSplashScreen to avoid actual GUI operations
    mock_splash = Mock(spec=QSplashScreen)
    mock_splash.isVisible.return_value = True
    
    # Patch QTimer to avoid actual timers
    monkeypatch.setattr("PyQt6.QtCore.QTimer.singleShot", Mock())

    # Create the log handler with the mocked splash
    handler = SplashLogHandler(mock_splash)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(handler)
    
    # Log a message
    test_message = "Testing splash screen log"
    logging.info(test_message)
    
    # Assert that showMessage was called on the splash screen
    mock_splash.showMessage.assert_called_with(test_message, 
                                               pytest.approx(3, 0), # Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
                                               pytest.approx(7, 0)) # Qt.GlobalColor.white

    logging.getLogger().removeHandler(handler)


@patch('gui.main_window.QTimer')
@patch('gui.main_window.MainWindow._close_splash_and_show')
def test_splash_closes_on_load_failure_with_delay(mock_close_splash, mock_qtimer, qapp):
    """Test that the splash screen closes with a delay on save load failure."""
    
    # Mock the main window and its dependencies
    mock_splash = Mock(spec=QSplashScreen)
    mock_handler = Mock()
    window = MainWindow(splash=mock_splash, splash_handler=mock_handler)
    
    # Simulate a failed save load
    window.on_save_loaded(success=False, message="File not found")
    
    # Assert that QTimer.singleShot was called with the correct delay and callback
    mock_qtimer.singleShot.assert_called_once_with(5000, mock_close_splash)


@patch('gui.main_window.MainWindow._close_splash_and_show')
def test_splash_closes_on_load_success(mock_close_splash, qapp):
    """Test that the splash screen closes immediately on save load success."""
    
    # Mock the main window and its dependencies
    mock_splash = Mock(spec=QSplashScreen)
    mock_handler = Mock()
    window = MainWindow(splash=mock_splash, splash_handler=mock_handler)
    
    # Simulate a successful save load
    window.on_save_loaded(success=True, message="Success")
    
    # Assert that _close_splash_and_show was called directly
    mock_close_splash.assert_called_once()
