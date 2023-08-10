import socket
import sys
import os
import dotenv
from colorama import init, Fore
import signal

init(autoreset=True)

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 2052

CALC_ID = dotenv.get_key(key_to_get="CALC_ID", dotenv_path=".env")
USERNAME = dotenv.get_key(key_to_get="USERNAME", dotenv_path=".env")
TOKEN = dotenv.get_key(key_to_get="TOKEN", dotenv_path=".env")

if CALC_ID is None or USERNAME is None or TOKEN is None:
    print(Fore.RED + "Calc ID, username or token could not be loaded!")


def receive_response(sock):
    sock.settimeout(0.1)
    try:
        response = sock.recv(4096)
        try:
            decoded_response = response.decode('utf-8').strip()
            if decoded_response.startswith("RTC_CHAT:"):
                print(Fore.MAGENTA + "Received RTC_CHAT:", decoded_response[len("RTC_CHAT:"):])
            elif decoded_response == "SERVER_PONG":
                print(Fore.CYAN + "Received SERVER_PONG")
            else:
                print(Fore.GREEN + "Received:", decoded_response)
            return decoded_response
        except UnicodeDecodeError:
            print(Fore.YELLOW + "Received non-UTF-8 bytes:", response)
    except socket.timeout:
        return None


def command_help():
    print("Available commands:")
    print("? - Show a list of all available (local) commands.")
    print("exit - Quit the terminal.")
    print("clear - Clear the terminal screen.")


def sigint_handler(sig, frame):
    print(Fore.RED + "\nCommand cancelled.")
    raise KeyboardInterrupt


def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(Fore.LIGHTBLACK_EX + f"Connecting to {SERVER_ADDRESS}:{SERVER_PORT} ...")
        sock.connect((SERVER_ADDRESS, SERVER_PORT))
        print(Fore.GREEN + f"Connected to {SERVER_ADDRESS}:{SERVER_PORT} !")

        print(Fore.YELLOW + "Logging in..")
        sock.send("SERIAL_CONNECTED".encode())
        sock.recv(4096)

        sock.send(f"LOGIN:{CALC_ID}:{USERNAME}:{TOKEN}".encode())
        loggedIn = sock.recv(4096).decode().strip()

        if loggedIn != "LOGIN_SUCCESS":
            print(loggedIn)
            print(Fore.RED + "Login failed!")
            print(Fore.RED + loggedIn)
            sys.exit(1)
        print(Fore.GREEN + "Logged in as", USERNAME)

        print(Fore.CYAN + f"You are now connected to the socket server at {SERVER_ADDRESS}:{SERVER_PORT}.")
        print("Type your commands, and press Enter to send.")
        print("Type '?' to show a list of available commands.")

        signal.signal(signal.SIGINT, sigint_handler)

        while True:
            user_input = input(Fore.YELLOW + ">>> ")

            if not user_input.strip():
                print(Fore.YELLOW + "Please enter a command.")
                continue

            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "clear":
                os.system("cls" if os.name == "nt" else "clear")
            elif user_input == "?":
                command_help()
            else:
                sock.send(user_input.encode())  # Encode the user input as bytes
                receive_response(sock)

    except KeyboardInterrupt:
        print(Fore.RED + "CTRL-C received. Command cancelled.")
    finally:
        sock.close()
        print(Fore.CYAN + "Socket connection closed.")

if __name__ == "__main__":
    main()