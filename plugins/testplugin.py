# this is a test plugin

class TINETBridgePlugin:
    def __init__(self):
        self.plugin_name = "TestPlugin"
        print(f"Successfully loaded {self.plugin_name}")

    def custom_print(self, message):
        print(f"[{self.plugin_name}]: {message}")

    def log_call(self, log_message):
        self.custom_print(log_message)
