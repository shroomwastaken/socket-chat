"""
main server module
"""

import socket
import threading
from log import log_ok, log_err, log_info


class Server:
	"""
	main server class
	"""
	def __init__(self, host: str, port: int):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind((host, port))
		self.sock.listen(10)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.setblocking(False)  # non-blocking recv calls

		self.clients = []
		self.threads = []
		self.clients_lock = threading.Lock()
		self.shutdown_event = threading.Event()

	def run(self) -> None:
		"""
		the server's main loop
		"""
		while True:
			# other than the interrupt there should be no reason this ever fails :)
			try:
				(cl_sock, cl_addr) = self.sock.accept()
				log_ok(f"accepted connection from {cl_addr}")
				new_thread = threading.Thread(target=self.handle_client, args=(cl_sock, cl_addr))
				new_thread.start()
				self.clients.append((cl_sock, cl_addr))
				self.threads.append(new_thread)
			except BlockingIOError:
				# because we have a non-blocking socket every time we don't get a connection through accept()
				# it throws an error which we can just ignore here
				pass
			except KeyboardInterrupt:
				log_ok("received ctrl+c, exiting")
				break

	def close(self) -> None:
		"""
		when we've exited from the run() function
		"""
		self.shutdown_event.set()
		self.sock.close()
		for t in self.threads:
			t.join()
		log_info("closed server")

	def handle_client(self, cl: socket.socket, cl_addr) -> None:
		""".
		handles client connection and messages
		params:
			cl - client socket
			cl_addr - client address
		"""
		cl.setblocking(False)
		while not self.shutdown_event.is_set():
			try:
				msg = cl.recv(1024)
				decoded = msg.decode("utf-8")
				if msg:
					log_info(f"{cl_addr}: {decoded}")
					self.broadcast(msg, cl)
				else:
					break
			except BlockingIOError:
				# we didn't get any data
				pass
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
			self.clients.remove((cl, cl_addr))
		log_info(f"closing connection with client {cl_addr}")
		cl.close()

	def broadcast(self, msg: bytes, sender) -> None:
		"""
		broadcasts received message to all connected clients
		params:
			msg - message bytes
			sender - client who sent it
		"""
		with self.clients_lock:
			for client in self.clients:
				# don't return the message to sender
				if client == sender:
					continue

				client[0].send(msg)

if __name__ == "__main__":
	server = Server("127.0.0.1", 80)
	server.run()
	server.close()
