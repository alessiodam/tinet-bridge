import logging
import os
import serial
import socket
import sys
import threading
import time
from serial.tools import list_ports

# ---BRIDGE CONFIG---#
TCP_HOST = 'tinethub.tkbstudios.com'
TCP_PORT = 2052
DEBUG = True
RETRY_DEFAULT_PORT_FOREVER = False
# -END BRIDGE CONFIG-#

logging.basicConfig(level=logging.DEBUG)


def updateBridge():
    logging.debug("Pulling latest files...")
    os.system("git config pull.ff only")
    os.system("git pull")


def CleanExit(serial_connection, server_client_sock, reason):
    logging.debug(str(reason))
    logging.debug("Notifying client bridge got disconnected!")
    serial_connection.write("bridgeDisconnected".encode())
    serial_connection.write("internetDisconnected".encode())
    logging.debug("Notified client bridge got disconnected!")
    serial_connection.close()
    server_client_sock.close()
    sys.exit(0)


def serial_read(serial_connection, server_client_sock):
    while True:
        data = bytes()
        try:
            data = serial_connection.read(serial_connection.in_waiting)
        except serial.SerialException as e:
            CleanExit(serial_connection, server_client_sock, str(e))

        if data:
            decoded_data = data.decode().replace("/0", "").replace("\0", "")
            if DEBUG:
                logging.debug(f'R - serial - ED: {data}')
            logging.debug(f'R - serial: {decoded_data}')

            try:
                server_client_sock.send(decoded_data.encode())
            except socket.error as e:
                CleanExit(serial_connection, server_client_sock, str(e))
            logging.debug(f'W - server: {decoded_data}')


def server_read(serial_connection, server_client_sock):
    while True:
        try:
            server_response = server_client_sock.recv(4096)
        except socket.timeout:
            continue
        except socket.error as e:
            CleanExit(serial_connection, server_client_sock, str(e))

        decoded_server_response = server_response.decode()

        if DEBUG:
            logging.debug(f'R - server - ED: {server_response}')
        logging.debug(f'R - server: {decoded_server_response}')

        try:
            serial_connection.write(decoded_server_response.encode())
        except serial.SerialException as e:
            CleanExit(serial_connection, server_client_sock, str(e))
        logging.debug(f'W - serial: {decoded_server_response}')

        if decoded_server_response == "DISCONNECT":
            CleanExit(serial_connection, server_client_sock, f"Received {decoded_server_response} from server")


def list_serial_ports():
    ports = list_ports.comports()
    for i, port in enumerate(ports):
        logging.debug(f"{i + 1}. {port.device} - {port.description}")
    return ports


def select_serial_port(ports):
    while True:
        selected_index = input("Enter the number of the serial device you want to select: ")
        if selected_index == "":
            logging.debug("Please select a valid port!")
            sys.exit(1)
        if selected_index in [str(x + 1) for x in range(len(ports))]:
            port_number = int(selected_index) - 1
            logging.debug(port_number)
            return ports[port_number]
        else:
            logging.debug("Invalid selection. Please try again.")


if __name__ == "__main__":
    logging.debug("\rInitiating serial...\n")

    try:
        if RETRY_DEFAULT_PORT_FOREVER:
            while True:
                logging.debug("Trying default netbridge port...")
                try:
                    serial_connection = serial.Serial("/dev/ttyACM0", baudrate=9600, timeout=3)
                    if serial_connection.is_open:
                        break
                except serial.SerialException as err:
                    if err.errno == 13:
                        logging.debug("Missing USB permissions, please add them: ")
                        logging.debug("sudo groupadd dailout")
                        logging.debug("sudo usermod -a -G dialout $USER")
                        logging.debug("sudo chmod a+rw /dev/TTYACM0")
                        sys.exit(1)

        else:
            available_ports = list_serial_ports()

            try:
                while len(available_ports) == 0:
                    logging.debug("No devices detected! Is your calculator connected?")
                    available_ports = list_serial_ports()
                    time.sleep(1)
            except KeyboardInterrupt:
                sys.exit(0)

            selected_port_info = select_serial_port(available_ports)
            serial_connection = serial.Serial(selected_port_info.device, baudrate=9600, timeout=3)
            logging.debug(f"Connected to: {serial_connection.portstr}")

    except KeyboardInterrupt:
        CleanExit(serial_connection=serial_connection, server_client_sock=None,
                  reason="\nReceived CTRL+C! Exiting cleanly...")

    except serial.SerialException as err:
        if err.errno == 13:
            logging.debug("Missing USB permissions, please add them: ")
            logging.debug("sudo groupadd dailout")
            logging.debug("sudo usermod -a -G dialout $USER")
            logging.debug("sudo chmod a+rw /dev/TTYACM0")
            sys.exit(1)

    logging.debug("Serial started successfully!")

    while True:
        try:
            logging.debug("Connecting to server...")
            server_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_client_sock.connect((TCP_HOST, TCP_PORT))
            logging.debug("Connected to server!")
            break
        except socket.error as e:
            logging.debug(f"Failed to connect to server: {str(e)}")
            time.sleep(1)

    server_client_sock.settimeout(3)

    logging.debug("Starting read threads...")
    threading.Thread(target=serial_read, args=(serial_connection, server_client_sock), daemon=True).start()
    threading.Thread(target=server_read, args=(serial_connection, server_client_sock), daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        CleanExit(serial_connection=serial_connection, server_client_sock=server_client_sock,
                  reason="\nReceived CTRL+C! Exiting cleanly...")
