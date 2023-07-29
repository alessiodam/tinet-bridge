import socket
import sys
import os
import dotenv
from colorama import init, Fore
import signal

init(autoreset=True)

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 2052

USERNAME = dotenv.get_key(key_to_get="USERNAME", dotenv_path=".env")
TOKEN = dotenv.get_key(key_to_get="TOKEN", dotenv_path=".env")

if USERNAME is None or TOKEN is None:
    print(Fore.RED + "Username or token could not be loaded!")


def receive_response(sock):
    # Set a timeout of 1 second for receiving data
    sock.settimeout(1.0)
    try:
        response = sock.recv(4096).decode().strip()
        if response == "SERVER_PONG":
            print(Fore.CYAN + "Received SERVER_PONG")
        else:
            print(Fore.GREEN + "Received:", response)
        return response
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

        sock.sendall("SERIAL_CONNECTED".encode())
        receive_response(sock)

        sock.sendall(f"USERNAME:{USERNAME}".encode())
        receive_response(sock)

        sock.sendall(f"TOKEN:{TOKEN}".encode())
        loggedIn = receive_response(sock)
        if loggedIn != "LOGIN_SUCCESS":
            print(Fore.RED + "Login failed!")
            print(Fore.RED + loggedIn)
            sys.exit(1)

        print(Fore.CYAN + f"You are now connected to the socket server at {SERVER_ADDRESS}:{SERVER_PORT}.")
        print("Type your commands, and press Enter to send.")
        print("Type '?' to show a list of available commands.")

        # Set the CTRL-C handler
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
                sock.send(user_input.encode())
                receive_response(sock)

    except KeyboardInterrupt:
        print(Fore.RED + "CTRL-C received. Command cancelled.")
    except Exception as e:
        print(Fore.RED + "An error occurred:", e)
    finally:
        sock.close()
        print(Fore.CYAN + "Socket connection closed.")


if __name__ == "__main__":
    main()
