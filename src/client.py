"""
main client module
"""

import socket
import select
import threading
from sys import argv
from PyQt6 import QtCore, QtWidgets, QtGui
from log import log_ok, log_err
from client_popup import ClientPopup


class Client(QtWidgets.QWidget):
	"""
	main client class
	"""
	def __init__(self):
		super().__init__()
		self.server_ip, self.nickname = ClientPopup().exec()
		self.port = 2718
		self.messages = []
		self.client = connect_to_server(self.server_ip, 2718)
		# send out nickname to server with a setnickname message
		self.client.send(b'\x02' + bytes(self.nickname, encoding="utf-8"))
		self.shutdown_event = threading.Event()
		self.broadcast_thread = threading.Thread(target=self.handle_broadcast)
		self.broadcast_thread.start()
		# if we couldn't connect to server
		if not self.client:
			exit()
		self.init_ui()

	def init_ui(self):
		"""
		initializes client ui
		"""
		self.setFixedSize(800, 600)

		font = QtGui.QFont()
		font.setFamily("Source Code Pro")
		self.setFont(font)

		self.connected_to_label = QtWidgets.QLabel(parent=self)
		self.connected_to_label.setGeometry(QtCore.QRect(20, 0, 650, 71))
		font.setPointSize(30)
		self.connected_to_label.setFont(font)
		self.connected_to_label.setText(f"Connected to: {self.server_ip}")

		self.chat_list = QtWidgets.QListWidget(parent=self)
		self.chat_list.setGeometry(QtCore.QRect(20, 70, 761, 471))

		self.msg_input = QtWidgets.QLineEdit(parent=self)
		self.msg_input.setGeometry(QtCore.QRect(20, 550, 511, 32))
		font.setPointSize(14)
		self.msg_input.setFont(font)
		self.msg_input.setMaxLength(256)

		self.send_button = QtWidgets.QPushButton(parent=self)
		self.send_button.setGeometry(QtCore.QRect(640, 550, 141, 34))
		font.setPointSize(16)
		self.send_button.setFont(font)
		self.send_button.setText("SEND")
		self.send_button.clicked.connect(self.on_clicked)

		self.send_txt_button = QtWidgets.QPushButton(parent=self)
		self.send_txt_button.setGeometry(QtCore.QRect(535, 550, 101, 34))
		font.setPointSize(16)
		self.send_txt_button.setFont(font)
		self.send_txt_button.setText("SENDTXT")
		self.send_txt_button.clicked.connect(self.on_clicked)

		self.exit_button = QtWidgets.QPushButton(parent=self)
		self.exit_button.setGeometry(QtCore.QRect(650, 0, 131, 71))
		self.exit_button.setFont(font)
		self.exit_button.setText("QUIT")
		self.exit_button.clicked.connect(self.on_clicked)

	def on_clicked(self):
		"""
		when buttons are clicked
		"""
		match self.sender():
			case self.send_button:
				if self.msg_input.text() == "":
					return

				msg = self.msg_input.text()
				self.msg_input.clear()
				self.chat_list.addItem(f"{self.nickname}: {msg}")
				self.client.send(msg.encode(encoding="utf-8"))
			case self.send_txt_button:
				dialog = QtWidgets.QFileDialog(parent=self)
				dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
			case self.exit_button:
				self.close()

	def close(self):
		"""
		graceful closing of the client
		"""
		self.shutdown_event.set()
		self.broadcast_thread.join()
		self.client.close()
		QtWidgets.QApplication.instance().quit()

	def handle_broadcast(self):
		"""
		handles server sending back messages from other users
		"""
		while not self.shutdown_event.is_set():
			try:
				msg = self.client.recv(1024)
				if msg:
					print(msg[0])
					# if we received a shutdown message, server is dying and we need to leave
					if msg[0] == 3:
						self.close()
						break
					else:
						msg = msg.split(b'\x01')
						cl_addr = str(msg[0])[2:-1]
						decoded = msg[1].decode("utf-8")
						self.messages.append((cl_addr, decoded))
						self.chat_list.addItem(f"{cl_addr} : {decoded}")
						self.chat_list.scrollToBottom()
				else:
					break
			except TimeoutError:
				# we didn't get any data
				pass
			except UnicodeDecodeError:
				# got bad bytes from server
				log_err("got bad message from server")
				break


def connect_to_server(host: str, port: int) -> socket.socket:
	"""
	connects non-blocking client socket to server
	params:
		host - server ip
		port - server port
	"""
	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client.settimeout(0.5)

	try:
		client.connect((host, port))
	except TimeoutError:
		print(f"unable to connect to {host}:{port}")
		return None

	# wait until we're ready to send to server
	_, ready_to_write, _ = select.select([], [client], [])

	if ready_to_write:
		log_ok(f"successfully connected to {host}:{port}")
		return client
	else:
		# should never happen as we handled not connecting to the server
		# and select() hangs until we get a good socket
		log_err(f"unable to connect to {host}:{port}")
		return None


if __name__ == "__main__":
	app = QtWidgets.QApplication(argv)
	w = Client()
	w.show()
	exit(app.exec())
