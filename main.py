import logging
from fastapi import FastAPI, WebSocket
import requests
from orderbook import filter_walls, detect_trend
from levels import generate_signals, rokada_status_global
import json
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv
from datetime import datetime
from telegram import Bot

load_dotenv()

# Podešavanje logovanja
logging.basicConfig(
    filename='/app/logs/bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()
logger = logging.getLogger(__name__)

# Dodaj CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8888", "http://192.168.68.39:8888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RokadaState:
    def __init__(self):
        self._status = "off"

    def get_status(self):
        return self._status

    def set_status(self, status: str):
        if status.lower() in ["on", "off"]:
            self._status = status.lower()
            logger.info(f"Rokada status changed to: {self._status}")
            return True
        logger.warning(f"Invalid rokada status attempt: {status}")
        return False

load_dotenv()

# Inicijalizacija Binance exchange-a
exchange = ccxt.binance({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET'),
    'enableRateLimit': True,
})

load_dotenv()
# Inicijalizacija Telegram bota
telegram_bot=os.getenv('TELEGRAM_TOKEN')
telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID')

# Čuvanje aktivnih trejdova
active_trades = []

rokada_status_global = "off"
# Inicijalizacija
rokada_state = RokadaState()
# Korišćenje u endpointu
# Globalna promenljiva za rokada status
@app.get('/set_rokada/{status}')
async def set_rokada(status: str):
    logger.info(f"Received request to set rokada status to: {status}")
    success = set_rokada_status(status)
    if success:
        current_price, walls, trend = await fetch_current_data()
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())
        return {'status': get_rokada_status(), 'signals': signals}
    return {'error': 'Status mora biti "on" ili "off"'}

# Funkcije za upravljanje rokada statusom (kao što si ranije poslao)
def get_rokada_status():
    global rokada_status_global
    return rokada_status_global

def set_rokada_status(status: str):
    global rokada_status_global
    if status.lower() in ["on", "off"]:
        rokada_status_global = status.lower()
        logger.info(f"Rokada status changed to: {rokada_status_global}")
        return True
    logger.warning(f"Invalid rokada status attempt: {status}")
    return False

async def send_telegram_message(message):
    try:
        await telegram_bot.send_message(chat_id=telegram_chat_id, text=message)
        logging.getLogger(__name__).info(f"Telegram poruka poslata: {message}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Greška pri slanju Telegram poruke: {str(e)}")



@app.get('/update_data')
async def update_data():
    return await get_data()  # Pozovi isti kod kao za /get_data


# HTTP endpoint za dohvatanje podataka
@app.get('/get_data')
async def get_data_endpoint():
    return await get_data()

# HTTP endpoint za ažuriranje podataka (dodajemo ovde, odmah nakon /get_data)
@app.get('/update_data')
async def update_data():
    return await get_data()  # Pozovi isti kod kao za /get_data

@app.get('/start_trade/{signal_index}')
async def start_trade(signal_index: int):
    logger = logging.getLogger(__name__)
    try:
        # Dobij signale
        url = "https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000"
        orderbook = requests.get(url).json()
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend)

        if signal_index < 0 or signal_index >= len(signals):
            logger.error(f"Nevažeći indeks signala: {signal_index}")
            return {'error': 'Nevažeći indeks signala'}

        signal = signals[signal_index]
        # Pošalji order na Binance
        if signal['type'] == 'LONG':
            order = await exchange.create_limit_buy_order(
                'ETH/BTC',
                0.01,
                signal['entry_price']
            )
        else:  # SHORT
            order = await exchange.create_limit_sell_order(
                'ETH/BTC',
                0.01,
                signal['entry_price']
            )

        trade = {
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'entry_time': datetime.utcnow().isoformat(),
            'status': 'pending',
            'order': order
        }
        active_trades.append(trade)
        logger.info(f"Zapčet trejd: {trade}")

        # Pošalji Telegram poruku
        message = f"🔔 Novi trejd započet!\nType: {trade['type']}\nEntry Price: {trade['entry_price']}\nSL: {trade['stop_loss']}\nTP: {trade['take_profit']}\nTime: {trade['entry_time']}"
        await send_telegram_message(message)

        return {'message': 'Trejd započet', 'trade': trade}
    except Exception as e:
        logger.error(f"Greška pri startovanju trejda: {str(e)}")
        return {'error': str(e)}
    finally:
        await exchange.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger = logging.getLogger(__name__)
    logger.info("WebSocket povezan")
    try:
        while True:
            url = "https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000"
            orderbook = requests.get(url).json()
            current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
            walls = filter_walls(orderbook, current_price)
            trend = detect_trend(orderbook, current_price)
            signals = generate_signals(current_price, walls, trend)

            # Ažuriraj status trejdova
            updated_trades = []
            for trade in active_trades:
                trade['current_price'] = current_price
                if trade['type'] == 'LONG':
                    trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
                else:  # SHORT
                    trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
                updated_trades.append(trade)

            response = {
                'price': round(current_price, 5),
                'support': len(walls['support']),
                'resistance': len(walls['resistance']),
                'trend': trend,
                'signals': signals,
                'balance': 65.00,
                'rokada_status': rokada_status_global,
                'active_trades': updated_trades
            }
            await websocket.send_text(json.dumps(response))
            logger.info(f"Poslati podaci preko WebSocket-a: {response}")
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"WebSocket greška: {str(e)}")
    finally:
        await websocket.close()
        logger.info("WebSocket zatvoren")

# Helper funkcija za dohvatanje trenutnih podataka (primer)
async def fetch_current_data():
    url = "https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000"
    orderbook = requests.get(url).json()
    current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
    walls = filter_walls(orderbook, current_price)
    trend = detect_trend(orderbook, current_price)
    return current_price, walls, trend

async def get_data():
    try:
        url = "https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000"
        response = requests.get(url)
        response.raise_for_status()  # Proveri da li je zahtev uspešan
        orderbook = response.json()
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())
        return {
            "price": current_price,
            "support": walls.get("support", 0),
            "resistance": walls.get("resistance", 0),
            "trend": trend,
            "signals": signals,
            "balance": 65.0,
            "rokada_status": get_rokada_status(),
            "active_trades": [],
            "trade_attempts": []
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Binance: {e}")
        await asyncio.sleep(5)  # Čekaj 5 sekundi pre ponovnog pokušaja
        return {"error": "Failed to fetch data from Binance"}