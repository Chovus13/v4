import logging
import logging.handlers
import os
import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket
import json
import ccxt.async_support as ccxt
from typing import List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from config import AMOUNT, LEVERAGE
from orderbook import filter_walls, detect_trend
from levels import generate_signals
import time
#import telegram

app = FastAPI()

load_dotenv()

exchange = ccxt.binance({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET'),
    'enableRateLimit': True,
})

async def main():
    bot = telegram.Bot("TOKEN")
    async with bot:
        print(await bot.get_me())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8888", "http://192.168.68.39:8888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Globalne promenljive
ws_clients: List[WebSocket] = []  # Lista aktivnih WebSocket klijenata
active_trades = []
rokada_status_global = "off"
cached_data = None
bot_running = False
leverage = 2
trade_amount = 0.06

# Podešavanje logger-a
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Funkcija za slanje logova klijentima
async def send_logs_to_clients(message, level):
    if not ws_clients:  # Provera da li je lista prazna
        return
    log_message = {'type': 'log', 'message': f"{level}: {message}"}
    for client in ws_clients[:]:  # Kopija liste da izbegnemo greške pri iteraciji
        try:
            await client.send_text(json.dumps(log_message))
        except Exception as e:
            logger.error(f"Greška pri slanju logova klijentu: {str(e)}")
            ws_clients.remove(client)  # Uklanjamo klijenta ako je diskonektovan

# WebSocket logging handler
class WebSocketLoggingHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        level = record.levelname
        asyncio.create_task(send_logs_to_clients(log_entry, level))

ws_handler = WebSocketLoggingHandler()
ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(ws_handler)

# WebSocket konekcija sa Binance-om
async def connect_binance_ws():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect('wss://fstream.binance.com/ws/ethbtc@depth@100ms') as ws:
                    logger.info("Povezan na Binance WebSocket")
                    while True:
                        try:
                            msg = await asyncio.wait_for(ws.receive_json(), timeout=60.0)
                            if ws.closed:
                                logger.warning("Binance WebSocket zatvoren, pokušavam ponovno povezivanje")
                                break
                            yield msg
                        except asyncio.TimeoutError:
                            logger.info("Šaljem ping poruku Binance WebSocket-u")
                            await ws.ping()
        except Exception as e:
            logger.error(f"Greška u Binance WebSocket konekciji: {str(e)}")
            await asyncio.sleep(5)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info("Klijentski WebSocket povezan")
    last_send_time = 0
    try:
        async for msg in connect_binance_ws():
            current_time = time.time()
            if current_time - last_send_time < 0.2:  # Smanjujemo interval na 200ms
                continue

            if 'bids' in msg and 'asks' in msg:
                bids = msg['bids']
                asks = msg['asks']
            elif 'b' in msg and 'a' in msg:
                bids = msg['b']
                asks = msg['a']
            else:
                logger.warning(f"Nepoznat format WebSocket poruke: {msg}")
                continue

            if not bids or not asks:
                logger.warning(f"Prazni bids ili asks u WebSocket poruci: {msg}")
                continue

            orderbook = {
                'bids': [[float(bid[0]), float(bid[1])] for bid in bids],
                'asks': [[float(ask[0]), float(ask[1])] for ask in asks]
            }

            if not orderbook['bids'] or not orderbook['asks']:
                logger.warning(f"Prazan orderbook nakon konverzije: {orderbook}")
                continue

            try:
                current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
            except (IndexError, ValueError) as e:
                logger.error(f"Greška pri izračunavanju cene: {str(e)}, orderbook: {orderbook}")
                continue

            walls = filter_walls(orderbook, current_price)
            trend = detect_trend(orderbook, current_price)
            signals = generate_signals(current_price, walls, trend, rokada_status=rokada_status_global)

            exchange.options['defaultType'] = 'future'
            try:
                balance = await exchange.fetch_balance()
                eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0
                btc_balance = balance['BTC']['free'] if 'BTC' in balance else 0
                usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
                logger.info(f"Dohvaćen balans: ETH={eth_balance}, BTC={btc_balance}, USDT={usdt_balance}")
            except Exception as e:
                logger.error(f"Greška pri dohvatanju balansa: {str(e)}")
                eth_balance = 0
                btc_balance = 0
                usdt_balance = 0

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
                'balance': eth_balance,
                'balance_currency': 'ETH',
                'extra_balances': {'BTC': btc_balance, 'USDT': usdt_balance},
                'rokada_status': rokada_status_global,
                'active_trades': updated_trades,
                'latency': round((time.time() - current_time) * 1000, 2)
            }
            logger.info(f"Šaljem podatke preko WebSocket-a: {response}")
            await websocket.send_text(json.dumps(response))
            last_send_time = current_time
    except Exception as e:
        logger.error(f"Klijentski WebSocket greška: {str(e)}")
        raise
    finally:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        await websocket.close()
        logger.info("Klijentski WebSocket zatvoren")



@app.post('/start_bot')
async def start_bot(data: dict):
    global bot_running, leverage, trade_amount
    leverage = data.get('leverage', 3)
    trade_amount = data.get('amount', 0.06)
    if trade_amount < 0.05:  # Smanjujemo minimum na 0.05 ETH
        return {'status': 'error', 'message': 'Amount must be at least 0.05 ETH'}
    if bot_running:
        return {'status': 'error', 'message': 'Bot is already running'}
    bot_running = True
    logger.info(f"Bot started with leverage={leverage}, amount={trade_amount}")
    return {'status': 'success'}


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
    if cached_data and (time.time() - cached_data['timestamp'] < 15):  # Povećavamo keširanje na 15 sekundi
        logger.info("Vraćam keširane podatke")
        return cached_data['data']

    try:
        orderbook = await exchange.fetch_order_book('ETH/BTC', limit=50)  # Smanjujemo limit na 50
        current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
        walls = filter_walls(orderbook, current_price)
        trend = detect_trend(orderbook, current_price)
        signals = generate_signals(current_price, walls, trend, rokada_status=get_rokada_status())
        exchange.options['defaultType'] = 'future'
        balance = await exchange.fetch_balance()
        eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0
        btc_balance = balance['BTC']['free'] if 'BTC' in balance else 0
        usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0

        data = {
            "price": current_price,
            "support": len(walls.get("support", [])),
            "resistance": len(walls.get("resistance", [])),
            "support_walls": walls.get("support", []),
            "resistance_walls": walls.get("resistance", []),
            "trend": trend,
            "signals": signals,
            "balance": eth_balance,
            "balance_currency": "ETH",
            "extra_balances": {"BTC": btc_balance, "USDT": usdt_balance},
            "rokada_status": get_rokada_status(),
            "active_trades": active_trades
        }
        cached_data = {'data': data, 'timestamp': time.time()}
        return data
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return {"error": "Failed to fetch data"}

async def fetch_current_data():
    orderbook = await exchange.fetch_order_book('ETH/BTC', limit=100)
    current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
    walls = filter_walls(orderbook, current_price)
    trend = detect_trend(orderbook, current_price)
    return current_price, walls, trend

@app.get('/start_trade/{signal_index}')
async def start_trade(signal_index: int):
    try:
        exchange.options['defaultType'] = 'future'
        await exchange.set_leverage(LEVERAGE, 'ETH/BTC')
        await exchange.set_margin_mode('isolated', 'ETH/BTC')

        balance = await exchange.fetch_balance()
        eth_balance = balance['ETH']['free'] if 'ETH' in balance else 0
        if eth_balance < 0.01:
            logger.error(f"Nedovoljan balans: {eth_balance} ETH")
            return {'error': f"Nedovoljan balans: {eth_balance} ETH"}

        orderbook = await exchange.fetch_order_book('ETH/BTC', limit=100)
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




@app.post('/stop_bot')
async def stop_bot():
    global bot_running
    if not bot_running:
        return {'status': 'error', 'message': 'Bot is not running'}
    bot_running = False
    logger.info("Bot stopped")
    return {'status': 'success'}




@app.on_event("shutdown")
async def shutdown_event():
    await exchange.close()
    logger.info("Exchange zatvoren prilikom gašenja aplikacije")