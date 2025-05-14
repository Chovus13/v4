import logging
from fastapi import FastAPI
import requests
from orderbook import filter_walls, detect_trend
from levels import generate_signals
from fastapi.middleware.cors import CORSMiddleware


# Podešavanje logovanja
logging.basicConfig(
    filename='/app/logs/bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/get_data')
async def get_data():
    logger = logging.getLogger(__name__)
    logger.info("Ulaz u /get_data endpoint")
    try:
        url = "https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000"
        orderbook = requests.get(url).json()
        logger.debug(f"Orderbook dobijen: bids={len(orderbook['bids'])}, asks={len(orderbook['asks'])}")

        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        logger.debug(f"Current price: {current_price:.5f}")

        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend, rokada_status="on")

        response = {
            'price': round(current_price, 5),
            'support': len(walls['support']),
            'resistance': len(walls['resistance']),
            'trend': trend,
            'signals': signals,
            'balance': 65.00
        }
        logger.info(f"Podaci za GUI: {response}")
        return response
    except Exception as e:
        logger.error(f"Greška u /get_data: {str(e)}")
        return {'error': str(e)}