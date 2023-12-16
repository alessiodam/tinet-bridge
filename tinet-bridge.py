import threading
import time
import serial
import serial.tools.list_ports
import socket
from queue import Queue

SERVER_ADDRESS = 'tinethub.tkbstudios.com'
SERVER_PORT = 2052


def find_serial_port():
    while True:
        time.sleep(0.2)
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if "USB Serial Device" in port.description or "TI-84" in port.description:
                return port


class SerialThread(threading.Thread):
    def __init__(self, serial_port, data_queue):
        threading.Thread.__init__(self)
        self.serial_port = serial_port
        self.data_queue = data_queue

    def run(self):
        if self.serial_port.is_open:
            self.serial_port.write("BRIDGE_CONNECTED\0".encode())

        while True:
            decoded_data = self.serial_port.readline().decode().strip()
            if decoded_data == "CONNECT_TCP\0":
                break  # Exit the loop after receiving "CONNECT_TCP"

        while True:
            data_to_send = "Hello, TCP server!"  # Modify this line with the data you want to send
            self.serial_port.write(data_to_send.encode())


class SocketThread(threading.Thread):
    def __init__(self, serial_port, data_queue):
        threading.Thread.__init__(self)
        self.serial_port = serial_port
        self.data_queue = data_queue

    def run(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((SERVER_ADDRESS, SERVER_PORT))
            print("Socket connection established")
            self.data_queue.put("TCP_CONNECTED\0")

            while True:
                data_received = self.serial_port.readline().decode().strip()
                if not data_received:
                    break
                print(f"Received from Serial: {data_received}")
                self.data_queue.put(data_received)

                # Send the received data to the TCP server
                server_socket.sendall(data_received.encode())
        except Exception as e:
            print(f"Error connecting to the server: {e}")
        finally:
            server_socket.close()


if __name__ == "__main__":
    data_queue = Queue()
    serial_port = find_serial_port()
    serial_conn = serial.Serial(serial_port.device, 115200)

    serial_thread = SerialThread(serial_conn, data_queue)
    socket_thread = SocketThread(serial_conn, data_queue)

    # Start serial thread first
    serial_thread.start()

    # Start socket thread
    socket_thread.start()

    try:
        # No user input needed, data is sent automatically in the threads
        time.sleep(10)  # Run for 10 seconds (adjust as needed)
    finally:
        data_queue.put("EXIT")  # Signal the threads to exit
        serial_thread.join()
        socket_thread.join()
