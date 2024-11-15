from sys import argv
from PyQt6 import QtWidgets
import server


class ServerGui(QtWidgets.QWidget):
	def __init__(self, host: str, port: int):
		super().__init__()
		self.server = server.Server(host, port)
		self.init_ui()

	def init_ui(self):
		"""
		initializes server ui
		"""
		self.setFixedSize(800, 600)

	def on_clicked(self):
		"""
		when buttons are clicked
		"""


if __name__ == "__main__":
	app = QtWidgets.QApplication(argv)

	# get ip and port from server.conf for now
	with open("src/server.conf", "r", encoding="utf-8") as f:
		h = f.readline().split("=")[1].strip()
		p = int(f.readline().split("=")[1])

	w = ServerGui(host=h, port=p)
	w.show()
	exit(app.exec())
