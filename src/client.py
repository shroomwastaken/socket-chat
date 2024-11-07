"""
main client module
"""

import socket
import select
from log import log_ok, log_err

def connect_to_server(host: str, port: int):
	"""
	connects non-blocking client socket to server
	params:
		host - server ip
		port - server port
	"""
	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client.settimeout(2)

	try:
		client.connect((host, port))
	except TimeoutError:
		pass

	_, ready_to_write, _ = select.select([], [client], [])

	if ready_to_write:
		log_ok(f"successfully connected to {host}:{port}")
		return client
	else:
		log_err(f"unable to connect to {host}:{port}")
		return None

sock = connect_to_server("127.0.0.1", 80)
while True and sock:
	try:
		msg = input()
		if msg == "/ex":
			sock.close()
			break
		sock.sendall(bytes(msg, "utf-8"))
	except:
		sock.close()
		break
sock.close()