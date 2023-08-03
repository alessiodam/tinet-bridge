import serial
from serial.tools import list_ports
import socket
import sys
import time
import threading
import os

# ---BRIDGE CONFIG---#

TCP_HOST = 'tinethub.tkbstudios.com'
TCP_PORT = 2052

DEBUG = True

# Retry the default rpi0W2 port (/dev/ttyACM0) forever if it fails.
RETRY_DEFAULT_PORT_FOREVER = False

# -END BRIDGE CONFIG-#


def CleanExit(serial_connection, server_client_sock, reason):
    print(str(reason))
    print("Notifying client bridge got disconnected!")
    serial_connection.write("bridgeDisconnected".encode())
    serial_connection.write("internetDisconnected".encode())
    print("Notified client bridge got disconnected!")
    serial_connection.close()
    server_client_sock.close()
    sys.exit(0)


def serial_read(serial_connection_srl_read, server_client_sock_srl_read):
    while True:
        data = bytes()
        try:
            data = serial_connection_srl_read.read(serial_connection_srl_read.in_waiting)
        except Exception as srl_read_exception:
            CleanExit(serial_connection, server_client_sock, str(srl_read_exception))

        if data:
            decoded_data = data.decode().replace("/0", "").replace("\0", "")
            if DEBUG:
                print(f'R - serial - ED: {data}')
            print(f'R - serial: {decoded_data}')

            try:
                server_client_sock_srl_read.send(decoded_data.encode())
            except Exception as e:
                CleanExit(serial_connection, server_client_sock_srl_read, str(e))
            print(f'W - server: {decoded_data}')


def server_read(serial_connection_server_read, server_client_sock_server_read):
    while True:
        server_response = bytes()
        try:
            server_response = server_client_sock_server_read.recv(4096)
        except socket.timeout:
            continue
        except Exception as server_read_exception:
            CleanExit(serial_connection, server_client_sock_server_read, str(server_read_exception))

        decoded_server_response = server_response.decode()

        if DEBUG:
            print(f'R - server - ED: {server_response}')
        print(f'R - server: {decoded_server_response}')

        try:
            serial_connection.write(decoded_server_response.encode())
        except Exception as e:
            CleanExit(serial_connection, server_client_sock, str(e))
        print(f'W - serial: {decoded_server_response}')

        if decoded_server_response == "DISCONNECT":
            CleanExit(serial_connection, server_client_sock, f"Received {decoded_server_response} from server")


def list_serial_ports():
    ports = list_ports.comports()
    for i, port in enumerate(ports):
        print(f"{i + 1}. {port.device} - {port.description}")
    return ports


def select_serial_port(ports):
    while True:
        selected_index = input("Enter the number of the serial device you want to select: ")
        if selected_index == "":
            print("Please select a valid port!")
            sys.exit(1)
        if selected_index in [str(x + 1) for x in range(len(ports))]:
            port_number = int(selected_index) - 1
            print(port_number)
            return ports[port_number]
        else:
            print("Invalid selection. Please try again.")


if __name__ == "__main__":
    print("\rInitiating serial...\n")

    try:
        if RETRY_DEFAULT_PORT_FOREVER:
            while True:
                print("Trying default netbridge port...")
                try:
                    serial_connection = serial.Serial("/dev/ttyACM0", baudrate=9600, timeout=3)
                    if serial_connection.is_open:
                        break
                except serial.SerialException as err:
                    if err.errno == 13:
                        print("Missing USB permissions, please add them: ")
                        print("sudo groupadd dailout")
                        print("sudo usermod -a -G dialout $USER")
                        print(f"sudo chmod a+rw /dev/ttyACM0")
                        user_response = input("Add the permissions autmatically? (y or n): ").lower()
                        if user_response == "y":
                            os.system("sudo groupadd dailout")
                            os.system("sudo usermod -a -G dialout $USER")
                            os.system("sudo chmod a+rw {serial_connection.portstr}")
                        sys.exit(1)

        else:
            available_ports = list_serial_ports()

            try:
                while len(available_ports) == 0:
                    print("No devices detected! Is your calculator connected?")
                    available_ports = list_serial_ports()
                    time.sleep(1)
            except KeyboardInterrupt:
                sys.exit(0)

            selected_port_info = select_serial_port(available_ports)
            serial_connection = serial.Serial(selected_port_info.device, baudrate=9600, timeout=3)
            print(f"Connected to: {serial_connection.portstr}")

    except KeyboardInterrupt:
        CleanExit(serial_connection=serial_connection, server_client_sock=None,
                  reason="\nReceived CTRL+C! Exiting cleanly...")

    except serial.SerialException as err:
        if err.errno == 13:
            print("Missing USB permissions, please add them: ")
            print("sudo groupadd dailout")
            print("sudo usermod -a -G dialout $USER")
            print(f"sudo chmod a+rw {serial_connection.portstr}")
            user_response = input("Add the permissions autmatically? (y or n): ").lower()
            if user_response == "y":
                os.system("sudo groupadd dailout")
                os.system("sudo usermod -a -G dialout $USER")
                os.system("sudo chmod a+rw {serial_connection.portstr}")
            sys.exit(1)

    print("\rCreating TCP socket...                      ", end="")

    server_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_client_sock.settimeout(10)

    print("\rConnecting to TCP socket...                      ", end="")

    try:
        server_client_sock.connect((TCP_HOST, TCP_PORT))
    except socket.error as e:
        CleanExit(serial_connection, server_client_sock, f"Failed to connect to the server: {e}")

    print("\rNotifying serial client he is connected to the bridge...                      ", end="")

    serial_connection.write("bridgeConnected\0".encode())
    print("\rClient got notified he was connected to the bridge!                      ", end="")

    # Add delay to prevent the client from not seeing the SERIAL_CONNECTED_CONFIRMED message
    time.sleep(1)

    print("\rReading data from serial device...                      ")
    try:
        serial_read_thread = threading.Thread(target=serial_read, args=(serial_connection, server_client_sock))
        serial_read_thread.name = "SERIAL_READ_THREAD"
        serial_read_thread.start()

        server_read_thread = threading.Thread(target=server_read, args=(serial_connection, server_client_sock))
        server_read_thread.name = "SERVER_READ_THREAD"
        server_read_thread.start()

        serial_read_thread.join()
        server_read_thread.join()

    except KeyboardInterrupt:
        CleanExit(serial_connection=serial_connection, server_client_sock=server_client_sock,
                  reason="\nReceived CTRL+C! Exiting cleanly...")
