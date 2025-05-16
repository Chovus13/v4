import os
from dotenv import load_dotenv

load_dotenv()

# Binance WebSocket
BINANCE_WS_URL = "wss://fstream.binance.com/ws"

# Trading par
PAR = os.getenv('ETH/BTC')
LEVERAGE_POSTAVI = 2  # napravi da bude promenljivo kroz UI (web stranica koja se prikzuje preko nginx)
SVOTA_U_ETH = 0.05   # napravi da bude promenljivo kroz UI (web stranica koja se prikzuje preko nginx)

# Postavke za zidove
WALL_RANGE_SPREAD = float(os.getenv('WALL_RANGE_SPREAD', 0.00002))  # Vratio na tvoju vrednost
MIN_WALL_VOLUME = float(os.getenv('MIN_WALL_VOLUME', 30))  # Vratio na tvoju vrednost
HILL_WALL_VOLUME = float(os.getenv('HILL_WALL_VOLUME', 50.0))
MOUNTAIN_WALL_VOLUME = float(os.getenv('MOUNTAIN_WALL_VOLUME', 100.0))
EPIC_WALL_VOLUME = float(os.getenv('EPIC_WALL_VOLUME', 500.0))

# Preciznost
PRICE_PRECISION = int(os.getenv('PRICE_PRECISION', 5))  # Ostaje 5 za 5. decimalu
VOLUME_PRECISION = int(os.getenv('VOLUME_PRECISION', 2))

# Strategija
TARGET_DIGITS = [int(d) for d in os.getenv('TARGET_DIGITS', '2,3,7,8').split(',')]
SPECIAL_DIGITS = [int(d) for d in os.getenv('SPECIAL_DIGITS', '1,9').split(',')]
PROFIT_TARGET = float(os.getenv('PROFIT_TARGET', 0.00010))

# Parametri za detect_trend
BUY_THRESHOLD = float(os.getenv('BUY_THRESHOLD', 0.99))
SELL_THRESHOLD = float(os.getenv('SELL_THRESHOLD', 1.01))