import requests
import logging
from orderbook import filter_walls, detect_trend
from levels import generate_signals

logging.basicConfig(
    filename='/logs/bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

url = "https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000"
orderbook = requests.get(url).json()
current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
walls = filter_walls(orderbook, current_price)
trend = detect_trend(orderbook, current_price)
signals = generate_signals(current_price, walls, trend, rokada_status="on")

print("Zidovi:", walls)
print("Trend:", trend)
print("Signali:", signals)