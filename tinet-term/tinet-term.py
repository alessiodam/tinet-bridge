import socket
import sys
import dotenv
from colorama import init
import signal

import time
from _thread import *

import curses
from curses import wrapper
from curses.textpad import rectangle

import queue

init(autoreset=True)

SERVER_ADDRESS = "tinethub.tkbstudios.com"
SERVER_PORT = 2052

CALC_ID = dotenv.get_key(key_to_get="CALC_ID", dotenv_path=".env")
USERNAME = dotenv.get_key(key_to_get="USERNAME", dotenv_path=".env")
TOKEN = dotenv.get_key(key_to_get="TOKEN", dotenv_path=".env")

messagequeue = queue.Queue()

if CALC_ID is None or USERNAME is None or TOKEN is None:
    messagequeue.put("Calc ID, username or token could not be loaded!")

def thread_receive_response(sock):
    sock.settimeout(0.1)
    while True:
        try:
            response = sock.recv(4096)
            try:
                decoded_response = response.decode('utf-8').strip()
                if decoded_response.startswith("RTC_CHAT:"):
                    a = decoded_response[len("RTC_CHAT:"):]
                    messagequeue.put(f"Received RTC_CHAT:{a}")
                elif decoded_response == "SERVER_PONG":
                    messagequeue.put(f"Received SERVER_PONG")
                else:
                    messagequeue.put(f"Received: {decoded_response}")
            except UnicodeDecodeError:
                messagequeue.put(f"Received non-UTF-8 bytes:{response}")

        except socket.timeout:
            pass
        time.sleep(1)


def command_help():
    messagequeue.put("Available commands:")
    messagequeue.put("? - Show a list of all available (local) commands.")
    # messagequeue.put("PING - ping the server  [Seems deprecated?]")
    messagequeue.put(
        "RTC_CHAT:[RECIPIENT]:[YOURMESSAGE] -  send a RTC message - Use recipient 'global' for global message")
    messagequeue.put("ACCOUNT_INFO - get current account information")
    messagequeue.put("exit - Quit the terminal.")
    messagequeue.put("clear - Clear the terminal screen.")


def sigint_handler(sig, frame):
    messagequeue.put("\nCommand cancelled.")
    raise KeyboardInterrupt

messages = []
rows = 0
cols = 0


def outputhandler(chatwin):
    global messages
    global messagequeue
    while True:
        if not messagequeue.empty():
            message = messagequeue.get()  # take from queue
            messages.append(message)  # put in logs (for later usage.. not used rn)
            # output to window
            chatwin.addstr(message + "\n")


def handle_input(message, chatwin, sock):
    if not message.strip():
        messagequeue.put("Please enter a command.")
        pass
    if message.lower() == "exit":
        sys.exit(0)
    elif message.lower() == "clear":
        chatwin.clear()
        chatwin.refresh()
    elif message == "?":
        command_help()
    else:
        sock.send(message.encode())  # Encode the user input as bytes


# TODO:
# - auto-adjust the TUI when console size is changed
# - Add scrollbar to chatwin and let user can scroll back in chat log
# - autocomplete/suggestion 
# - Use arrow keys to Scroll up/down through commands sent previously by user
def main(stdscr):
    global rows
    global cols
    rows, cols = stdscr.getmaxyx()

    # INIT THE TUI
    stdscr.nodelay(True)
    stdscr.addstr(1, 1, f"Rows: {rows}, Cols: {cols}")
    current_input = ""

    messagelen = cols - 5
    messagewin = curses.newwin(1, messagelen, rows - 3, 3)
    messagewin.nodelay(True)
    messagewin.scrollok(True)

    rectangle(stdscr, rows - 4, 0, rows - 2, cols - 1)  # input chat textbox
    rectangle(stdscr, 1, 0, rows - 5, cols - 1)

    stdscr.addstr(rows - 1, 5, f"Ctrl+D or Ctrl+C to exit")
    stdscr.addstr(0, 0, f"TiNet Terminal")

    stdscr.refresh()

    chatwin = curses.newwin(rows - 7, cols - 4, 2, 2)
    chatwin.immedok(True)
    chatwin.refresh()
    chatwin.scrollok(True)
    # DONE TUI INIT

    # SERVER LOGIN
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    messagequeue.put(f"Connecting to {SERVER_ADDRESS}:{SERVER_PORT} ...")
    sock.connect((SERVER_ADDRESS, SERVER_PORT))
    messagequeue.put(f"Connected to {SERVER_ADDRESS}:{SERVER_PORT} !")

    messagequeue.put("Logging in..")
    sock.send("SERIAL_CONNECTED".encode())
    sock.recv(4096)
    sock.send(f"LOGIN:{CALC_ID}:{USERNAME}:{TOKEN}".encode())
    logged_in = ""
    try:
        logged_in = sock.recv(4096).decode().strip()
        print(logged_in) #DEBUG
    except Exception:
        pass

    if logged_in != "LOGIN_SUCCESS":
        print(logged_in)
        print("Login failed!")
        sys.exit(1)
    messagequeue.put(f"Logged in as {USERNAME}")

    messagequeue.put(f"You are now connected to the socket server at {SERVER_ADDRESS}:{SERVER_PORT}.")
    messagequeue.put("Type your commands, and press Enter to send.")
    messagequeue.put("Type '?' to show a list of available commands.")

    signal.signal(signal.SIGINT, sigint_handler)

    start_new_thread(thread_receive_response, (sock,))
    # DONE SERVER LOGIN

    # PUSH MESSAGES TO CHATWIN
    start_new_thread(outputhandler, (chatwin,))

    while True:

        try:
            key = messagewin.getch()
            if key == 4 or key == 3:
                raise KeyboardInterrupt
            if key < 0:
                # messagewin.addstr(0, 0, f"Command: {key}")
                pass
            if 31 < key < 128:
                current_input += chr(key)
                messagewin.clear()
                messagewin.refresh()
                messagewin.addstr(f"Command: {current_input}")
            elif key == 8:
                current_input = current_input[:-1]
                messagewin.clear()
                messagewin.refresh()
                messagewin.addstr(f"Command: {current_input}")
            elif key == 10:
                handle_input(current_input, chatwin, sock)
                current_input = ""
                messagewin.clear()
                messagewin.refresh()
                messagewin.addstr(f"Command: {current_input}")
        except KeyboardInterrupt:
            pass
            break

        messagewin.refresh()


wrapper(main)

# if __name__ == "__main__":
#    main()
