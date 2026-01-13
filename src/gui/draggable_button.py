from PyQt6.QtWidgets import QToolButton, QApplication
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QPixmap


class DraggableButton(QToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.draggable = False
        self.__mousePressPos = None

    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.MouseButton.LeftButton:
            self.__mousePressPos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self.draggable
            and event.buttons() == Qt.MouseButton.LeftButton
            and self.__mousePressPos is not None
        ):
            if (
                event.pos() - self.__mousePressPos
            ).manhattanLength() > QApplication.startDragDistance():
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.objectName())
                drag.setMimeData(mime_data)

                pixmap = QPixmap(self.size())
                self.render(pixmap)
                drag.setPixmap(pixmap)

                drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(event)
