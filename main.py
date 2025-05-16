import logging
from fastapi import FastAPI, WebSocket
import aiohttp
from orderbook import filter_walls, detect_trend
from levels import generate_signals # rokada_status_global
import json
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv
from datetime import datetime
from telegram import Bot
import psutil

# Učitaj env promenljive samo jednom
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

# Inicijalizacija Binance exchange-a
exchange = ccxt.binance({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET'),
    'enableRateLimit': True,
})

# Inicijalizacija Telegram bota
telegram_token = os.getenv('TELEGRAM_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
telegram_bot = Bot(token=telegram_token)

# Čuvanje aktivnih trejdova
active_trades = []

# Globalna promenljiva za čuvanje istorije zidova
wall_history = {'support': [], 'resistance': []}

# Globalna promenljiva
rokada_status_global = "off"


# Funkcije za upravljanje rokada statusom
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
        logger.info(f"Telegram poruka poslata: {message}")
    except Exception as e:
        logger.error(f"Greška pri slanju Telegram poruke: {str(e)}")

@app.get('/set_rokada/{status}')
async def set_rokada(status: str):
    logger.info(f"Received request to set rokada status to: {status}")
    success = set_rokada_status(status)
    if success:
        current_price, walls, trend = await fetch_current_data()
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())
        return {'status': get_rokada_status(), 'signals': signals}
    return {'error': 'Status mora biti "on" ili "off"'}

@app.get('/update_data')
async def update_data():
    return await get_data()

@app.get('/get_data')
async def get_data_endpoint():
    return await get_data()

@app.get('/start_trade/{signal_index}')
async def start_trade(signal_index: int):
    logger = logging.getLogger(__name__)
    try:
        # Postavi futures market
        exchange.options['defaultType'] = 'future'

        # Postavi leverage i margin mod
        symbol = 'ETH/BTC'
        leverage = 2  # Možeš ovo učiniti konfigurabilnim preko env promenljive
        await exchange.set_leverage(leverage, symbol)
        await exchange.set_margin_mode('isolated', symbol)

        # Proveri balans pre trejda
        balance = await exchange.fetch_balance()
        usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
        if usdt_balance < 10:  # Minimalni balans za trejd
            logger.error(f"Nedovoljan balans za trejd: {usdt_balance} USDT")
            return {'error': f"Nedovoljan balans: {usdt_balance} USDT"}

        # Dobij signale
        orderbook = await exchange.fetch_order_book(symbol, limit=1000)
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend)

        if signal_index < 0 or signal_index >= len(signals):
            logger.error(f"Nevažeći indeks signala: {signal_index}")
            return {'error': 'Nevažeći indeks signala'}

        signal = signals[signal_index]
        amount = 0.05  # Možeš ovo učiniti konfigurabilnim

        # Pošalji order na Binance
        if signal['type'] == 'LONG':
            order = await exchange.create_limit_buy_order(
                symbol,
                amount,
                signal['entry_price'],
                params={'leverage': leverage}
            )
        else:  # SHORT
            order = await exchange.create_limit_sell_order(
                symbol,
                amount,
                signal['entry_price'],
                params={'leverage': leverage}
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
        logger.info(f"Započet trejd: {trade}")

        # Pošalji Telegram poruku
        message = f"🔔 Novi trejd započet!\nType: {trade['type']}\nEntry Price: {trade['entry_price']}\nSL: {trade['stop_loss']}\nTP: {trade['take_profit']}\nTime: {trade['entry_time']}"
        await send_telegram_message(message)

        return {'message': 'Trejd započet', 'trade': trade}
    except Exception as e:
        logger.error(f"Greška pri startovanju trejda: {str(e)}")
        return {'error': str(e)}


async def fetch_current_data():
    orderbook = await exchange.fetch_order_book('ETH/BTC', limit=1000)
    current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
    walls = filter_walls(orderbook, current_price)
    trend = detect_trend(orderbook, current_price)
    return current_price, walls, trend


async def get_data():
    try:
        orderbook = await exchange.fetch_order_book('ETH/BTC', limit=1000)
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())

        # Dohvati balans sa Binance Futures-a
        exchange.options['defaultType'] = 'future'
        balance = await exchange.fetch_balance()
        usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0

        return {
            "price": current_price,
            "support": walls.get("support", 0),
            "resistance": walls.get("resistance", 0),
            "support_walls": walls.get("support", []),
            "resistance_walls": walls.get("resistance", []),
            "trend": trend,
            "signals": signals,
            "balance": usdt_balance,
            "rokada_status": get_rokada_status(),
            "active_trades": [],
            "trade_attempts": []
        }
    except Exception as e:
        logger.error(f"Error fetching data from Binance: {e}")
        await asyncio.sleep(5)
        return {"error": "Failed to fetch data from Binance"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger = logging.getLogger(__name__)
    logger.info("WebSocket povezan")
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                # Praćenje CPU i memorije
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                logger.info(f"CPU: {cpu_percent}% | Memorija: {memory.percent}%")

                await websocket.send_text(json.dumps({'type': 'ping'}))
                async with session.get("https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000") as response:
                    response.raise_for_status()
                    orderbook = await response.json()
                  ### # response_size = len(json.dumps(response).encode('utf-8'))           #
                  ### # logger.info(f"Veličina WebSocket poruke: {response_size} bajtova")  # ovde sam stavio
                current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
                walls = filter_walls(orderbook, current_price)
                trend = detect_trend(orderbook, current_price)
                signals = generate_signals(current_price, walls, trend)

                wall_movement = {'support_speed': 0, 'resistance_speed': 0}
                if wall_history['support'] and walls['support']:
                    last_support_price = wall_history['support'][-1][0] if wall_history['support'] else walls['support'][0][0]
                    current_support_price = walls['support'][0][0] if walls['support'] else last_support_price
                    wall_movement['support_speed'] = abs(current_support_price - last_support_price)
                if wall_history['resistance'] and walls['resistance']:
                    last_resistance_price = wall_history['resistance'][-1][0] if wall_history['resistance'] else walls['resistance'][0][0]
                    current_resistance_price = walls['resistance'][0][0] if walls['resistance'] else last_resistance_price
                    wall_movement['resistance_speed'] = abs(current_resistance_price - last_resistance_price)

                wall_history['support'] = walls['support']
                wall_history['resistance'] = walls['resistance']

                exchange.options['defaultType'] = 'future'
                balance = await exchange.fetch_balance()
                usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0

                updated_trades = []
                for trade in active_trades:
                    trade['current_price'] = current_price
                    if trade['type'] == 'LONG':
                        trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
                    else:
                        trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
                    updated_trades.append(trade)

                response = {
                    'type': 'data',
                    'price': round(current_price, 5),
                    'support': len(walls['support']),
                    'resistance': len(walls['resistance']),
                    'support_walls': walls['support'],
                    'resistance_walls': walls['resistance'],
                    'trend': trend,
                    'signals': signals,
                    'balance': usdt_balance,
                    'rokada_status': rokada_status_global,
                    'active_trades': updated_trades,
                    'wall_movement': wall_movement,
                    'system_stats': {'cpu_percent': cpu_percent, 'memory_percent': memory.percent}
                }
                await websocket.send_text(json.dumps(response))
                logger.info(f"Poslati podaci preko WebSocket-a: {response}")
                await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"WebSocket greška: {str(e)}")
        raise
    finally:
        await websocket.close()
        logger.info("WebSocket zatvoren")

@app.on_event("shutdown")
async def shutdown_event():
    await exchange.close()
    logger.info("Exchange zatvoren prilikom gašenja aplikacije")