import sys

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.suggester import SuggestFromList


import socket
import dotenv
from colorama import init
import signal

import time
from _thread import *

import queue


commands = ["RTC_CHAT:", "ACCOUNT_INFO", "clear", "quit", "exit", "?"]
messagequeue = queue.Queue()
messages = []


init(autoreset=True)

SERVER_ADDRESS = "tinethub.tkbstudios.com"
SERVER_PORT = 2052

CALC_ID = dotenv.get_key(key_to_get="CALC_ID", dotenv_path=".env")
USERNAME = dotenv.get_key(key_to_get="USERNAME", dotenv_path=".env")
TOKEN = dotenv.get_key(key_to_get="TOKEN", dotenv_path=".env")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)



class TiNet_Term(App):
    """TEST TUI APP"""
    
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]
    
    closing = False
    
    def command_help(self):
        messagequeue.put("Available commands:")
        messagequeue.put("? - Show a list of all available (local) commands.")
        # messagequeue.put("PING - ping the server  [Seems deprecated?]")
        messagequeue.put(
            "RTC_CHAT:[RECIPIENT]:[YOURMESSAGE] -  send a RTC message - Use recipient 'global' for global message")
        messagequeue.put("ACCOUNT_INFO - get current account information")
        messagequeue.put("exit - Quit the terminal.")
        messagequeue.put("clear - Clear the terminal screen.")
    
    @work(exclusive=True, thread=True)
    def thread_receive_response(self):
        sock.settimeout(0.1)
        while not self.closing:
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

    def sigint_handler(sig, frame):
        messagequeue.put("\nCommand cancelled.")
        raise KeyboardInterrupt

    @work(exclusive=True, thread=True)
    def outputhandler(self) -> None:
        """Update the chat messages"""
        while not self.closing:
            if not messagequeue.empty():
                message = messagequeue.get()  # take from queue
                try: 
                    message = message.decode()
                except:
                    pass
                messages.append(message)  # put in logs (for later usage.. not used rn)
                # output to window
                self.query_one(RichLog).write(message)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        
        yield Header()
        yield RichLog(wrap=True)
        yield Input(placeholder="Enter a command...",suggester=SuggestFromList(commands, case_sensitive=False))
        yield Footer()
        
        #self.startsocks()
        self.outputhandler()


    def on_mount(self) -> None:
        # SERVER LOGIN
        global sock
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
            messagequeue.put(logged_in) #DEBUG
        except Exception:
            pass

        if logged_in != "LOGIN_SUCCESS":
            messagequeue.put(logged_in)
            messagequeue.put("Login failed!")
            #self.closing = True
            #sys.exit(1)
        messagequeue.put(f"Logged in as {USERNAME}")

        messagequeue.put(f"You are now connected to the socket server at {SERVER_ADDRESS}:{SERVER_PORT}.")
        messagequeue.put("Type your commands, and press Enter to send.")
        messagequeue.put("Type '?' to show a list of available commands.")

        #signal.signal(signal.SIGINT, sigint_handler)
        # DONE SERVER LOGIN
        self.thread_receive_response()


    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value
        if text == "quit" or text == "exit":
            self.closing = True
            sys.exit(0)
        elif text == "clear":
            self.query_one(RichLog).clear()
        elif text == "?":
            self.command_help()
        else:
            sock.send(text.encode())
            #messagequeue.put(text.encode())
        self.query_one(Input).value = ""
        #self.query_one(RichLog).write(event.value) # write the inputted value to the log


    def action_toogle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
    def action_quit(self) -> None:
        """Quit."""
        self.closing = True
        sys.exit(0)


if __name__ == "__main__":
    app = TiNet_Term()
    app.run()
