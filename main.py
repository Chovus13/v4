import time
import logging
from fastapi import FastAPI, WebSocket
import aiohttp
from orderbook import filter_walls, detect_trend
from levels import generate_signals
import json
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv
from config import AMOUNT, LEVERAGE

load_dotenv()

logging.basicConfig(
    filename='/app/logs/bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8888", "http://192.168.68.39:8888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

exchange = ccxt.binance({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET'),
    'enableRateLimit': True,
    'test': True,  # Ako koristiš testnet
})

balance = await exchange.fetch_balance()
logger.info(f"Dostupne valute: {balance.keys()}")
eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0

rokada_status_global = "off"
active_trades = []
cached_data = None  # Keš za podatke

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

@app.get('/set_rokada/{status}')
async def set_rokada(status: str):
    logger.info(f"Received request to set rokada status to: {status}")
    success = set_rokada_status(status)
    if success:
        current_price, walls, trend = await fetch_current_data()
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())
        return {'status': get_rokada_status(), 'signals': signals}
    return {'error': 'Status mora biti "on" ili "off"'}

@app.get('/get_data')
async def get_data():
    global cached_data
    if cached_data and (time.time() - cached_data['timestamp'] < 10):
        logger.info("Vraćam keširane podatke")
        return cached_data['data']

    try:
        orderbook = await exchange.fetch_order_book('ETH/BTC', limit=1000)
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())
        exchange.options['defaultType'] = 'future'
        balance = await exchange.fetch_balance()
        eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0  # Promenjeno sa USDT na ETH

        data = {
            "price": current_price,
            "support": len(walls.get("support", [])),
            "resistance": len(walls.get("resistance", [])),
            "support_walls": walls.get("support", []),
            "resistance_walls": walls.get("resistance", []),
            "trend": trend,
            "signals": signals,
            "balance": eth_balance,  # Promenjeno sa usdt_balance na eth_balance
            "balance_currency": "ETH",  # Dodajemo valutu za frontend
            "rokada_status": get_rokada_status(),
            "active_trades": active_trades
        }
        cached_data = {'data': data, 'timestamp': time.time()}
        return data
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return {"error": "Failed to fetch data"}

@app.get('/start_trade/{signal_index}')
async def start_trade(signal_index: int):
    try:
        exchange.options['defaultType'] = 'future'
        await exchange.set_leverage(LEVERAGE, 'ETH/BTC')
        await exchange.set_margin_mode('isolated', 'ETH/BTC')

        balance = await exchange.fetch_balance()
        eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0  # Promenjeno sa USDT na ETH
        if eth_balance < 0.01:  # Minimum 0.01 ETH
            logger.error(f"Nedovoljan balans: {eth_balance} ETH")
            return {'error': f"Nedovoljan balans: {eth_balance} ETH"}

        orderbook = await exchange.fetch_order_book('ETH/BTC', limit=1000)
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend)

        if signal_index < 0 or signal_index >= len(signals):
            logger.error(f"Nevažeći indeks signala: {signal_index}")
            return {'error': 'Nevažeći indeks signala'}

        signal = signals[signal_index]
        if signal['type'] == 'LONG':
            order = await exchange.create_limit_buy_order(
                'ETH/BTC',
                AMOUNT,
                signal['entry_price'],
                params={'leverage': LEVERAGE}
            )
        else:
            order = await exchange.create_limit_sell_order(
                'ETH/BTC',
                AMOUNT,
                signal['entry_price'],
                params={'leverage': LEVERAGE}
            )

        trade = {
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'order': order
        }
        active_trades.append(trade)
        logger.info(f"Započet trejd: {trade}")
        return {'message': 'Trejd započet', 'trade': trade}
    except Exception as e:
        logger.error(f"Greška pri startovanju trejda: {str(e)}")
        return {'error': str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket povezan")
    try:
        exchange.options['defaultType'] = 'future'
        while True:
            orderbook = await exchange.watch_order_book('ETH/BTC', limit=1000)
            current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
            walls = filter_walls(orderbook, current_price)
            trend = detect_trend(orderbook, current_price)
            signals = generate_signals(current_price, walls, trend)

            balance = await exchange.fetch_balance()
            eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0  # Promenjeno sa USDT na ETH

            updated_trades = []
            for trade in active_trades:
                trade['current_price'] = current_price
                trade['status'] = 'winning' if (trade['type'] == 'LONG' and current_price > trade['entry_price']) else 'losing'
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
                'balance': eth_balance,  # Promenjeno sa usdt_balance na eth_balance
                'balance_currency': 'ETH',  # Dodajemo valutu za frontend
                'rokada_status': rokada_status_global,
                'active_trades': updated_trades
            }
            await websocket.send_text(json.dumps(response))
            logger.info(f"Poslati podaci preko WebSocket-a: {response}")
    except Exception as e:
        logger.error(f"WebSocket greška: {str(e)}")
        raise
    finally:
        await websocket.close()
        logger.info("WebSocket zatvoren")

async def fetch_current_data():
    orderbook = await exchange.fetch_order_book('ETH/BTC', limit=1000)
    current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
    walls = filter_walls(orderbook, current_price)
    trend = detect_trend(orderbook, current_price)
    return current_price, walls, trend

@app.on_event("shutdown")
async def shutdown_event():
    await exchange.close()
    logger.info("Exchange zatvoren prilikom gašenja aplikacije")