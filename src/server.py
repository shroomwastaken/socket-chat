"""
main server module
"""

import socket
import threading
from time import sleep
from base64 import b64encode, b64decode
from sys import argv
from PyQt6 import QtCore, QtWidgets, QtGui
from log import log_ok, log_err, log_info
import sqlite3


class Server(QtWidgets.QWidget):
	"""
	main server class
	"""
	def __init__(self, host: str, port: int):
		super().__init__()

		# server setup
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind((host, port))
		self.sock.listen(10)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.setblocking(False)  # non-blocking recv calls

		self.clients = []
		self.threads = []
		# for thread-safe access to the clients list
		self.clients_lock = threading.Lock()
		# to know when we're shutting everything down
		self.shutdown_event = threading.Event()

		# controlling the uptime timer
		self.time_thread = threading.Thread(target=self.update_timer)
		self.time_thread.start()
		self.seconds_elapsed = 0

		# make sure table exists in db
		self._db = sqlite3.connect("msgs.db")
		self._db.execute(
			"""CREATE TABLE IF NOT EXISTS msgs(
				id INTEGER PRIMARY KEY,
				name TEXT,
				msg TEXT
			)""")
		self._db.close()

		self.init_ui()

	def run(self) -> None:
		"""
		the server's main loop
		"""
		while not self.shutdown_event.is_set():
			# there should be no reason this ever fails :)
			try:
				(cl_sock, cl_addr) = self.sock.accept()
				log_ok(f"accepted connection from {cl_addr}")
				new_thread = threading.Thread(
					target=self.handle_client, args=(cl_sock, cl_addr)
				)
				self.clients_list.addItem(f"{cl_addr}")
				self.clients.append((cl_sock, cl_addr))
				self.threads.append(new_thread)
				new_thread.start()
				self.clients_count.setText(str(len(self.clients)))
			except BlockingIOError:
				# every time we don't get a connection
				# it throws an error which we can just ignore here
				sleep(0.5)  # manual timeout so we don't get 90% cpu usage kekw

	def close(self) -> None:
		"""
		when we've exited from the run() function
		"""
		self.send_shutdown_msg()
		self.shutdown_event.set()
		self.sock.close()
		for t in self.threads:
			t.join()
		self.time_thread.join()
		log_info("closed server")

	def handle_client(self, cl: socket.socket, cl_addr) -> None:
		""".
		handles client connection and messages
		params:
			cl - client socket
			cl_addr - client address
		"""
		cl.setblocking(False)
		conn = sqlite3.connect("msgs.db")
		nickname = "anonymous"  # default for if we don't get a nickname
		# make sure clients list has nickname
		with self.clients_lock:
			self.clients_list.takeItem(self.clients.index((cl, cl_addr)))
			self.clients_list.addItem(f"{cl_addr} : {nickname}")
		# send at most the last 50 messages to client as history
		history = conn.execute("""SELECT * FROM msgs ORDER BY id DESC LIMIT 50;""").fetchall()[::-1]
		for item in history:
			cl.send(
				bytes(f"{item[1]}", encoding="utf-8") +
				b'\x01' +
				bytes(f"{str(b64decode(item[2]))[2:-1]}", encoding="utf-8")
			)
			# small delay for the client receiver to not count all of these sends as one
			sleep(0.005)
		while not self.shutdown_event.is_set():
			try:
				msg = cl.recv(1024)
				if msg:
					# if we received a setnickname message from a client
					# (this is the first message every client will send)
					if msg[0] == 2:
						# update nickname in client list
						nickname = msg[1:].decode("utf-8")
						with self.clients_lock:
							self.clients_list.takeItem(self.clients.index((cl, cl_addr)))
							self.clients_list.addItem(f"{cl_addr} : {nickname}")
					else:
						decoded = msg.decode("utf-8")
						self.chat_list.addItem(f"{nickname} : {decoded}")
						self.chat_list.scrollToBottom()
						conn.execute(
							f"""INSERT INTO msgs (name, msg)
								VALUES ('{nickname}', '{str(b64encode(msg))[2:-1]}')"""
						)
						conn.commit()
						self.broadcast(msg, cl, cl_addr, nickname)
				else:
					break
			except BlockingIOError:
				# we didn't get any data
				sleep(0.5)  # manual timeout so we don't get 90% cpu usage kekw
			except ConnectionError:
				# client exited while the server was recv()ing, which resulted in an error
				# might come up later so i'll keep this here
				# log_err(f"connection refused by peer error from client {cl_addr}")
				break
			except UnicodeDecodeError:
				# got bad bytes from client
				log_err(f"got bad message from client {cl_addr}")
				break

		with self.clients_lock:
			self.clients_list.takeItem(self.clients.index((cl, cl_addr)))
			self.clients.remove((cl, cl_addr))
			self.clients_count.setText(str(len(self.clients)))
			conn.close()
		log_info(f"closing connection with client {cl_addr}")
		cl.close()

	def broadcast(
		self,
		msg: bytes,
		sender: socket.socket,
		sender_addr,
		nickname: str
	) -> None:
		"""
		broadcasts received message to all connected clients
		params:
			msg - message bytes
			sender - client who sent it
			sender_addr - client address
			nickname - client nickname
		"""
		with self.clients_lock:
			for client in self.clients:
				# don't return the message to sender
				if client == (sender, sender_addr):
					continue

				client[0].send(bytes(nickname, encoding="utf-8") + b'\x01' + msg)

	def send_shutdown_msg(self):
		"""
		we are shutting down and telling everyone about it
		"""
		with self.clients_lock:
			for client in self.clients:
				# 0x03 is the special shutdown message (patent pending)
				client[0].send(b'\x03')

	def init_ui(self):
		"""
		initializes server ui
		"""
		aligns = QtCore.Qt.AlignmentFlag
		self.setFixedSize(800, 600)
		self.uptime_label = QtWidgets.QLabel(parent=self)
		self.uptime_label.setGeometry(QtCore.QRect(540, 10, 251, 41))
		font = QtGui.QFont()
		font.setFamily("Source Code Pro")
		font.setPointSize(24)
		font.setBold(True)
		self.uptime_label.setFont(font)
		self.uptime_label.setText("Server uptime:")

		self.uptime_clock = QtWidgets.QLabel(parent=self)
		self.uptime_clock.setGeometry(QtCore.QRect(600, 60, 181, 31))
		font.setPointSize(24)
		self.uptime_clock.setFont(font)
		self.uptime_clock.setAlignment(
			aligns.AlignRight | aligns.AlignTrailing | aligns.AlignVCenter)
		self.uptime_clock.setText("00:00:00")

		self.clients_label = QtWidgets.QLabel(parent=self)
		self.clients_label.setGeometry(QtCore.QRect(450, 100, 341, 41))
		font.setPointSize(24)
		font.setBold(True)
		self.clients_label.setFont(font)
		self.clients_label.setText("Connected clients:")

		self.clients_count = QtWidgets.QLabel(parent=self)
		self.clients_count.setGeometry(QtCore.QRect(600, 140, 181, 31))
		font.setPointSize(24)
		self.clients_count.setFont(font)
		self.clients_count.setAlignment(
			aligns.AlignRight | aligns.AlignTrailing | aligns.AlignVCenter)
		self.clients_count.setText("0")

		self.close_button = QtWidgets.QPushButton(parent=self)
		self.close_button.setGeometry(QtCore.QRect(10, 10, 161, 51))
		font.setPointSize(15)
		self.close_button.setFont(font)
		self.close_button.setText("Close server")
		self.close_button.clicked.connect(self.on_clicked)

		self.chat_list = QtWidgets.QListWidget(parent=self)
		self.chat_list.setGeometry(QtCore.QRect(10, 120, 421, 471))
		self.chat_list.setFont(font)

		self.chat_label = QtWidgets.QLabel(parent=self)
		self.chat_label.setGeometry(QtCore.QRect(10, 70, 251, 41))
		font.setPointSize(24)
		font.setBold(True)
		self.chat_label.setFont(font)
		self.chat_label.setText("Chat")

		self.clients_list = QtWidgets.QListWidget(parent=self)
		self.clients_list.setGeometry(QtCore.QRect(450, 240, 341, 351))
		font.setPointSize(10)
		self.clients_list.setFont(font)

		self.clients_list_label = QtWidgets.QLabel(parent=self)
		self.clients_list_label.setGeometry(QtCore.QRect(450, 190, 341, 41))
		font.setPointSize(24)
		font.setBold(True)
		self.clients_list_label.setFont(font)
		self.clients_list_label.setText("Clients list:")

	def on_clicked(self):
		"""
		when buttons are clicked
		"""
		if self.sender() == self.close_button:
			self.shutdown_event.set()
			QtWidgets.QApplication.instance().quit()

	def update_timer(self):
		"""
		updates the server uptime timer every second
		"""
		while not self.shutdown_event.is_set():
			sleep(1)
			self.seconds_elapsed += 1
			seconds = self.seconds_elapsed % 60
			minutes = (self.seconds_elapsed // 60) % 60
			hours = self.seconds_elapsed // (60 * 24)
			self.uptime_clock.setText(f"{hours:02}:{minutes:02}:{seconds:02}")


if __name__ == "__main__":
	app = QtWidgets.QApplication(argv)
	server = Server("127.0.0.1", 2718)
	# the server and the gui run on different threads
	server_thread = threading.Thread(target=server.run, args=())
	server_thread.start()
	server.show()
	app.exec()
	server_thread.join()
	server.close()
