import asyncio
import importlib
import os
import time
from pathlib import Path

import serial.tools.list_ports
import serial.serialutil
from serial_asyncio import open_serial_connection

# --- bridge config --- #
AUTO_RECONNECT = True

# --- end bridge config --- #

plugin_instances = []


def find_serial_port():
    while True:
        time.sleep(0.2)
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if "USB Serial Device" in port.description or "TI-84" in port.description:
                return port


def clean_logging_message(message_to_clean: str):
    clean_message = message_to_clean
    if message_to_clean.startswith("LOGIN:"):
        login_data = message_to_clean.replace("LOGIN:", "").split(":", 2)
        login_data[0] = login_data[0][:4] + ("*" * 10) + login_data[0][-4:]
        login_data[2] = login_data[2][:4] + ("*" * 50) + login_data[2][-4:]
        clean_message = f"LOGIN:{login_data[0]}:{login_data[1]}:{login_data[2]}"
    clean_message = clean_message.strip()

    for plugin_instance in plugin_instances:
        if hasattr(plugin_instance, 'log_call'):
            plugin_instance.log_call(clean_message)

    return clean_message


async def bridge(serial_device):
    serial_reader, serial_writer = await open_serial_connection(url=serial_device, baudrate=115200)

    serial_writer.write("BRIDGE_CONNECTED\n".encode())
    await serial_writer.drain()
    print("sent BRIDGE_CONNECTED")

    while True:
        line = await serial_reader.readline()
        message = str(line, 'utf-8').strip()
        print(message)
        if message == "CONNECT_TCP":
            print("received CONNECT_TCP")
            break

    tcp_reader, tcp_writer = await asyncio.open_connection('localhost', 2052)

    serial_writer.write("TCP_CONNECTED\n".encode())
    await serial_writer.drain()
    print("sent TCP_CONNECTED")

    while True:
        try:
            serial_data = await serial_reader.readline()
        except serial.serialutil.SerialException:
            print("Calculator disconnected")
            break

        serial_message = str(serial_data, 'utf-8')
        cleaned_message = clean_logging_message(serial_message)
        print(f"receive from calculator: {cleaned_message}")

        tcp_writer.write(serial_message.encode())
        await tcp_writer.drain()
        print(f"transfer to TINET: {clean_logging_message(serial_message)}")

        tcp_data = await tcp_reader.readline()
        tcp_message = tcp_data.decode()
        print(f"receive from TINET: {clean_logging_message(tcp_message)}")

        serial_writer.write(tcp_message.encode())
        await serial_writer.drain()
        print(f"transfer to calculator: {clean_logging_message(tcp_message)}")

    print("Exiting bridge..")


if __name__ == "__main__":
    os.makedirs("plugins", exist_ok=True)

    for file_path in Path("plugins").glob('*.py'):
        plugin_name = os.path.basename(file_path)[:-3]
        print(f"Loading {plugin_name}")
        try:
            module = importlib.import_module(f'plugins.{plugin_name}')
            new_plugin_instance = module.TINETBridgePlugin()
            plugin_instances.append(new_plugin_instance)
        except Exception as e:
            print(f"Error loading plugin from {plugin_name}: {e}")

    while True:
        loop = asyncio.new_event_loop()
        print("Waiting for a calculator..")
        serial_port = find_serial_port()
        print(serial_port)
        time.sleep(2)
        loop.run_until_complete(bridge(serial_port.device))
        if AUTO_RECONNECT is False:
            break
