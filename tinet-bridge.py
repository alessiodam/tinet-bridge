import serial
from serial.tools import list_ports
import socket
import sys
import time
import threading
import os

# ---BRIDGE CONFIG---#

TCP_HOST = 'tinethub.tkbstudios.com'  # TCP Server address. default: tinethub.tkbstudios.com
TCP_PORT = 2052  # Server port. default: 2052 for default address

DEBUG = True  # ENABLE DEBUG MODE, Shows more information in console, useful if staff asks for console log. default: True

# [DOES NOT WORK!!] Enable or disable server ping, disable to get a more clean console. default: True
PING_SERVER = False
PING_INTERVAL = 3  # Time between every server ping. default: 3
# If the ping is 0, then disconnect the serial device and clean exit the bridge. default: True
EXIT_IF_PING_IS_ZERO = True

# Retry the default rpi0W2 port (/dev/ttyACM0) forever if it fails. default: True
RETRY_DEFAULT_PORT_FOREVER = True

EXIT_SCRIPT = False

# -END BRIDGE CONFIG-#


def updateBridge():
    print("Pulling latest files...")
    os.system("git config pull.ff only")
    os.system("git pull")


updateBridge()

connected = False


def CleanExit(serial_connection, server_client_sock, reason):
    print(str(reason))
    print("Notifying client bridge got disconnected!                      ")
    serial_connection.write("bridgeDisconnected".encode())
    serial_connection.write("internetDisconnected".encode())
    print("Notified client bridge got disconnected!                      ")
    serial_connection.close()
    server_client_sock.close()
    sys.exit(0)


'''
def server_ping(server_client_sock, serial_connection):
    while True:
        start_time = time.time()
        server_client_sock.send("server_ping".encode())

        ping_response = server_client_sock.recv(16)
        end_time = time.time()
        elapsed_time = math.floor((end_time - start_time) * 1000)
        
#        ser.write(f"ping:{elapsed_time}\0".encode())
        print(f"Ping: {elapsed_time}ms")

        if elapsed_time >= 1000:
            CleanExit(serial_connection=serial_connection, server_client_sock=server_client_sock, reason="\nPing was higher than 1000, preventing lag! Exiting cleanly...")
            break

        if EXIT_IF_PING_IS_ZERO == True:
            if elapsed_time == 0:
                CleanExit(serial_connection=serial_connection, server_client_sock=server_client_sock, reason="\nPing was 0, disconnected from server! Exiting cleanly...")
                break

        time.sleep(PING_INTERVAL)
'''


def serial_read(serial_connection, server_client_sock):
    while True:
        data = bytes()
        try:
            data = serial_connection.read(serial_connection.in_waiting)
        except IOError:
            CleanExit(serial_connection, server_client_sock,
                      "Device disconnected!!")
        except Exception as e:
            CleanExit(serial_connection, server_client_sock, str(e))

        if data.decode() != "":
            decoded_data = data.decode().replace("/0", "").replace("\0", "")
            if DEBUG:
                print(f'R - serial - ED: {data}')
            print(f'R - serial: {decoded_data}')

            try:
                server_client_sock.send(decoded_data.encode())
            except TimeoutError:
                CleanExit(serial_connection, server_client_sock, "Timeout reaching server!")
            print(f'W - server: {decoded_data}')


def server_read(serial_connection, server_client_sock):
    while True:
        try:
            server_response = server_client_sock.recv(4096)
        except socket.timeout:
            continue
        except Exception:
            CleanExit(serial_connection, server_client_sock,
                      "Server read exception!")
        decoded_server_response = server_response.decode()

        if DEBUG:
            print(f'R - server - ED: {server_response}')
        print(f'R - server: {decoded_server_response}')

        serial_connection.write(decoded_server_response.encode())
        print(f'W - serial: {decoded_server_response}')
        if decoded_server_response == "DISCONNECT":
            CleanExit(serial_connection, server_client_sock, f"Received {decoded_server_response} from server")
            sys.exit(0)


def list_serial_ports():
    ports = list_ports.comports()
    for i, port in enumerate(ports):
        print(f"{i + 1}. {port.device} - {port.description}")
    return ports


def select_serial_port(ports):
    selected_index = int(
        input("Enter the number of the serial device you want to select: ")) - 1
    if 0 <= selected_index < len(ports):
        return ports[selected_index]
    else:
        print("Invalid selection. Please try again.")
        return select_serial_port(ports)


print("\rIniting serial...\n")

try:
    # deepcode ignore PythonSameEvalBinaryExpressiontrue: This is a config made by the user
    if RETRY_DEFAULT_PORT_FOREVER == True:
        while True:
            print("Trying default netbridge port...")
            serial_connection = serial.Serial(
                "/dev/ttyACM0", baudrate=9600, timeout=3)
            if serial_connection.is_open == True:
                break

except serial.SerialException:
    try:
        print("DEFAULT PORT FAILED!")
        available_ports = list_serial_ports()
        selected_port_info = select_serial_port(available_ports)
        serial_connection = serial.Serial(
            selected_port_info.device, baudrate=9600, timeout=3)
        print(f"Connected to: {serial_connection.portstr}")
    except serial.SerialException:
        print("FAILED CONNECTION!")
        print("Are you sure your calculator is in TINET program\nwith a valid key and connected to USB?")
        sys.exit(1)

print("\rCreating TCP socket...                      ", end="")

server_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_client_sock.settimeout(10)

print("\rConnecting to TCP socket...                      ", end="")

server_client_sock.connect((TCP_HOST, TCP_PORT))

print("\rNotifying serial client he is connected to the bridge...                      ", end="")

serial_connection.write("bridgeConnected\0".encode())
print("\rClient got notified he was connected to the bridge!                      ", end="")

# Add delay to prevent the client to not see the SERIAL_CONNECTED_CONFIRMED message
time.sleep(1)

print("\rReading data from serial device...                      ")
try:
    # Windows doesn't allow connection even when allowed through private and public networks firewall
    '''
    if PING_SERVER == True:
        ping_server_thread = threading.Thread(target=server_ping(server_client_sock=server_client_sock, serial_connection=serial_connection))
        ping_server_thread.name = "ping_server"
        ping_server_thread.daemon = True
        ping_server_thread.start()
    '''
    serial_read_thread = threading.Thread(
        target=serial_read, args=(serial_connection, server_client_sock))
    serial_read_thread.name = "SERIAL_READ_THREAD"
    serial_read_thread.start()
    server_read_thread = threading.Thread(
        target=server_read, args=(serial_connection, server_client_sock))
    server_read_thread.name = "SERVER_READ_THREAD"
    server_read_thread.start()

except KeyboardInterrupt:
    CleanExit(serial_connection=serial_connection, server_client_sock=server_client_sock,
              reason="\nRecieved CTRL+C! Exiting cleanly...")