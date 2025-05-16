# @app.websocket("/ws")
#   -----ovo je sa brzinom u HTML ali fali jos putil

# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     logger = logging.getLogger(__name__)
#     logger.info("WebSocket povezan")
#     try:
#         async with aiohttp.ClientSession() as session:
#             while True:
#                 logger.info("Povlačenje orderbook-a...")
#                 await websocket.send_text(json.dumps({'type': 'ping'}))
#
#                 async with session.get("https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000") as response:
#                     response.raise_for_status()
#                     orderbook = await response.json()
#                 current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
#                 walls = filter_walls(orderbook, current_price)
#                 trend = detect_trend(orderbook, current_price)
#                 signals = generate_signals(current_price, walls, trend)
#
#                 # Izračunavanje brzine kretanja zidova
#                 wall_movement = {'support_speed': 0, 'resistance_speed': 0}
#                 if wall_history['support'] and walls['support']:
#                     last_support_price = wall_history['support'][-1][0] if wall_history['support'] else \
#                     walls['support'][0][0]
#                     current_support_price = walls['support'][0][0] if walls['support'] else last_support_price
#                     wall_movement['support_speed'] = abs(current_support_price - last_support_price)
#                 if wall_history['resistance'] and walls['resistance']:
#                     last_resistance_price = wall_history['resistance'][-1][0] if wall_history['resistance'] else \
#                     walls['resistance'][0][0]
#                     current_resistance_price = walls['resistance'][0][0] if walls[
#                         'resistance'] else last_resistance_price
#                     wall_movement['resistance_speed'] = abs(current_resistance_price - last_resistance_price)
#
#                 # Ažuriraj istoriju zidova
#                 wall_history['support'] = walls['support']
#                 wall_history['resistance'] = walls['resistance']
#
#                 logger.info("Dohvatanje balansa...")
#                 exchange.options['defaultType'] = 'future'
#                 balance = await exchange.fetch_balance()
#                 usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
#
#                 updated_trades = []
#                 for trade in active_trades:
#                     trade['current_price'] = current_price
#                     if trade['type'] == 'LONG':
#                         trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
#                     else:
#                         trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
#                     updated_trades.append(trade)
#
#                 response = {
#                     'type': 'data',
#                     'price': round(current_price, 5),
#                     'support': len(walls['support']),
#                     'resistance': len(walls['resistance']),
#                     'support_walls': walls['support'],
#                     'resistance_walls': walls['resistance'],
#                     'trend': trend,
#                     'signals': signals,
#                     'balance': usdt_balance,
#                     'rokada_status': rokada_status_global,
#                     'active_trades': updated_trades,
#                     'wall_movement': wall_movement  # Dodaj brzinu kretanja zidova
#                 }
#                 await websocket.send_text(json.dumps(response))
#                 logger.info(f"Poslati podaci preko WebSocket-a: {response}")
#                 await asyncio.sleep(5)
#     except Exception as e:
#         logger.error(f"WebSocket greška: {str(e)}")
#         raise
#     finally:
#         await websocket.close()
#         logger.info("WebSocket zatvoren")

#####################################################################
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     logger = logging.getLogger(__name__)
#     logger.info("WebSocket povezan")
#     try:
#         # Koristi CCXT Pro WebSocket
#         exchange.options['defaultType'] = 'future'
#         while True:
#             orderbook = await exchange.watch_order_book('ETH/BTC', limit=1000)
#             current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
#             walls = filter_walls(orderbook, current_price)
#             trend = detect_trend(orderbook, current_price)
#             signals = generate_signals(current_price, walls, trend)
#
#             balance = await exchange.fetch_balance()
#             usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
#
#             updated_trades = []
#             for trade in active_trades:
#                 trade['current_price'] = current_price
#                 if trade['type'] == 'LONG':
#                     trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
#                 else:
#                     trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
#                 updated_trades.append(trade)
#
#             response = {
#                 'type': 'data',
#                 'price': round(current_price, 5),
#                 'support': len(walls['support']),
#                 'resistance': len(walls['resistance']),
#                 'support_walls': walls['support'],
#                 'resistance_walls': walls['resistance'],
#                 'trend': trend,
#                 'signals': signals,
#                 'balance': usdt_balance,
#                 'rokada_status': rokada_status_global,
#                 'active_trades': updated_trades
#             }
#             await websocket.send_text(json.dumps(response))
#             logger.info(f"Poslati podaci preko WebSocket-a: {response}")
#     except Exception as e:
#         logger.error(f"WebSocket greška: {str(e)}")
#     finally:
#         await websocket.close()
#         logger.info("WebSocket zatvoren")
###############################################################################
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     logger = logging.getLogger(__name__)
#     logger.info("WebSocket povezan")
#     try:
#         async with aiohttp.ClientSession() as session:
#             while True:
#                 await websocket.send_text(json.dumps({'type': 'ping'}))
#
#                 async with session.get("https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000") as response:
#                     response.raise_for_status()
#                     orderbook = await response.json()
#                 current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
#                 walls = filter_walls(orderbook, current_price)
#                 trend = detect_trend(orderbook, current_price)
#                 signals = generate_signals(current_price, walls, trend)
#
#                 # Dohvati balans
#                 exchange.options['defaultType'] = 'future'
#                 balance = await exchange.fetch_balance()
#                 usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
#
#                 updated_trades = []
#                 for trade in active_trades:
#                     trade['current_price'] = current_price
#                     if trade['type'] == 'LONG':
#                         trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
#                     else:
#                         trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
#                     updated_trades.append(trade)
#
#                 response = {
#                     'type': 'data',
#                     'price': round(current_price, 5),
#                     'support': len(walls['support']),
#                     'resistance': len(walls['resistance']),
#                     'support_walls': walls['support'],
#                     'resistance_walls': walls['resistance'],
#                     'trend': trend,
#                     'signals': signals,
#                     'balance': usdt_balance,
#                     'rokada_status': rokada_status_global,
#                     'active_trades': updated_trades
#                 }
#                 await websocket.send_text(json.dumps(response))
#                 logger.info(f"Poslati podaci preko WebSocket-a: {response}")
#                 await asyncio.sleep(5)
#     except Exception as e:
#         logger.error(f"WebSocket greška: {str(e)}")
#     finally:
#         await websocket.close()
#         logger.info("WebSocket zatvoren")
#################################################################################

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     logger = logging.getLogger(__name__)
#     logger.info("WebSocket povezan")
#     try:
#         async with aiohttp.ClientSession() as session:
#             while True:
#                 async with session.get("https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000") as response:
#                     response.raise_for_status()
#                     orderbook = await response.json()
#                 current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
#                 walls = filter_walls(orderbook, current_price)
#                 trend = detect_trend(orderbook, current_price)
#                 signals = generate_signals(current_price, walls, trend)
#
#                 updated_trades = []
#                 for trade in active_trades:
#                     trade['current_price'] = current_price
#                     if trade['type'] == 'LONG':
#                         trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
#                     else:  # SHORT
#                         trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
#                     updated_trades.append(trade)
#
#                 response = {
#                     'price': round(current_price, 5),
#                     'support': len(walls['support']),
#                     'resistance': len(walls['resistance']),
#                     'trend': trend,
#                     'signals': signals,
#                     'balance': 65.00,
#                     'rokada_status': rokada_status_global,
#                     'active_trades': updated_trades
#                 }
#                 await websocket.send_text(json.dumps(response))
#                 logger.info(f"Poslati podaci preko WebSocket-a: {response}")
#                 await asyncio.sleep(5)
#     except Exception as e:
#         logger.error(f"WebSocket greška: {str(e)}")
#     finally:
#         await websocket.close()
#         logger.info("WebSocket zatvoren")

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     logger = logging.getLogger(__name__)
#     logger.info("WebSocket povezan")
#     try:
#         async with aiohttp.ClientSession() as session:
#             while True:
#                 # Ping poruka
#                 await websocket.send_text(json.dumps({'type': 'ping'}))
#
#                 async with session.get("https://fapi.binance.com/fapi/v1/depth?symbol=ETHBTC&limit=1000") as response:
#                     response.raise_for_status()
#                     orderbook = await response.json()
#                 current_price = (float(orderbook['bids'][0][0]) + float(orderbook['asks'][0][0])) / 2
#                 walls = filter_walls(orderbook, current_price)
#                 trend = detect_trend(orderbook, current_price)
#                 signals = generate_signals(current_price, walls, trend)
#
#                 updated_trades = []
#                 for trade in active_trades:
#                     trade['current_price'] = current_price
#                     if trade['type'] == 'LONG':
#                         trade['status'] = 'winning' if current_price > trade['entry_price'] else 'losing'
#                     else:
#                         trade['status'] = 'winning' if current_price < trade['entry_price'] else 'losing'
#                     updated_trades.append(trade)
#
#                 response = {
#                     'type': 'data',
#                     'price': round(current_price, 5),
#                     'support': len(walls['support']),
#                     'resistance': len(walls['resistance']),
#                     'support_walls': walls['support'],
#                     'resistance_walls': walls['resistance'],
#                     'trend': trend,
#                     'signals': signals,
#                     'balance': 65.00,
#                     'rokada_status': rokada_status_global,
#                     'active_trades': updated_trades
#                 }
#                 await websocket.send_text(json.dumps(response))
#                 logger.info(f"Poslati podaci preko WebSocket-a: {response}")
#                 await asyncio.sleep(5)
#     except Exception as e:
#         logger.error(f"WebSocket greška: {str(e)}")
#     finally:
#         await websocket.close()
#         logger.info("WebSocket zatvoren")
###############################################################



