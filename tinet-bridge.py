import serial
import serial.tools.list_ports
import time


def find_serial_port():
    while True:
        time.sleep(0.2)
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if "USB Serial Device" in port.description or "TI-84" in port.description:
                return port


def main():
    print("Searching port..")
    port = find_serial_port()
    print(port)

    if port:
        print("Connecting to serial port")
        ser = serial.Serial(port.device, baudrate=115200, timeout=3)
        if ser.is_open:
            print("Connected to serial port")

        try:
            ser.write(b'BRIDGE_CONNECTED\0')
            data = ser.read(1024)
            ser.flush()
            print(f"Received data: {data.decode('utf-8')}")

            while True:
                user_input = input("Enter data to send: ")
                written_bytes = ser.write(user_input.encode())
                print(f"wrote {written_bytes} bytes")

                data = ser.read(1024)
                print(f"Received data: {data}")

        except serial.SerialTimeoutException:
            print("Timeout occurred while waiting for data.")
        finally:
            ser.close()
    else:
        print("No suitable port found.")


if __name__ == "__main__":
    main()
