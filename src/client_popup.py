from sys import argv
from PyQt6 import QtCore, QtWidgets, QtGui


class ClientPopup(QtWidgets.QDialog):
	"""
	class for popup that appears upon client startup
	"""
	def __init__(self):
		super().__init__()
		self.init_ui()

	def init_ui(self):
		"""
		initializes popup ui
		"""
		self.setFixedSize(300, 300)

		font = QtGui.QFont()
		font.setFamily("Source Code Pro")

		self.ip_label = QtWidgets.QLabel(parent=self)
		self.ip_label.setGeometry(QtCore.QRect(60, 20, 181, 31))
		font.setPointSize(24)
		self.ip_label.setFont(font)
		self.ip_label.setText("Server IP")

		self.ip_input = QtWidgets.QLineEdit(parent=self)
		self.ip_input.setGeometry(QtCore.QRect(50, 70, 191, 30))
		font.setPointSize(11)
		self.ip_input.setFont(font)

		self.name_input = QtWidgets.QLineEdit(parent=self)
		self.name_input.setGeometry(QtCore.QRect(50, 180, 191, 30))
		font.setPointSize(11)
		self.name_input.setFont(font)
		self.name_input.setMaxLength(16)

		self.name_label = QtWidgets.QLabel(parent=self)
		self.name_label.setGeometry(QtCore.QRect(0, 130, 301, 31))
		font.setPointSize(12)
		self.name_label.setFont(font)
		self.name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
		self.name_label.setText("Nickname (default=anonymous)")

		self.join_button = QtWidgets.QPushButton(parent=self)
		self.join_button.setGeometry(QtCore.QRect(100, 230, 90, 34))
		font.setPointSize(14)
		self.join_button.setFont(font)
		self.join_button.clicked.connect(self.on_clicked)
		self.join_button.setText("JOIN")

		self.setWindowTitle("Joining server...")

	def exec(self):
		super().exec()
		return self.ip_input.text(), self.name_input.text()

	def on_clicked(self):
		self.close()


if __name__ == "__main__":
	app = QtWidgets.QApplication(argv)
	popup = ClientPopup()
	popup.show()
	app.exec()
