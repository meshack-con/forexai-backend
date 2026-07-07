import os
from dotenv import load_dotenv

load_dotenv()

MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
MT5_PATH = os.getenv("MT5_PATH")


class MT5Client:
    def __init__(self):
        self.login = int(MT5_LOGIN) if MT5_LOGIN is not None else None
        self.password = MT5_PASSWORD
        self.server = MT5_SERVER
        self.path = MT5_PATH
        self.connection = None

    def connect(self):
        import MetaTrader5 as mt5

        if self.path:
            mt5.initialize(self.path)
        else:
            mt5.initialize()

        if self.login and self.password and self.server:
            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if not authorized:
                raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")
        self.connection = mt5
        return mt5

    def disconnect(self):
        if self.connection is not None:
            self.connection.shutdown()
            self.connection = None

    def is_connected(self) -> bool:
        return self.connection is not None and self.connection.version() is not None


mt5_client = MT5Client()
