import logging
from config import TARGET_DIGITS, SPECIAL_DIGITS, HILL_WALL_VOLUME, MOUNTAIN_WALL_VOLUME, EPIC_WALL_VOLUME

logger = logging.getLogger(__name__)

# Globalna promenljiva za rokada status
rokada_status_global = "off"


def classify_wall_volume(volume):
    if volume >= EPIC_WALL_VOLUME:
        return "Planina"
    elif volume >= MOUNTAIN_WALL_VOLUME:
        return "Brdo"
    elif volume >= HILL_WALL_VOLUME:
        return "Brdašce"
    return "Zid"


def generate_signals(current_price, walls, trend, rokada_status=None):
    global rokada_status_global
    if rokada_status is not None:
        rokada_status_global = rokada_status
    price_str = f"{current_price:.5f}" if current_price is not None else "None"
    logger.info(
        f"Ulaz u generate_signals: current_price={price_str}, trend={trend}, rokada={rokada_status_global}, walls={walls}")
    signals = []

    # Proveri da li walls ima 'support' i 'resistance', ako ne, postavi prazne liste
    support_walls = sorted(walls.get('support', []), key=lambda x: x[1], reverse=True) if walls else []
    resistance_walls = sorted(walls.get('resistance', []), key=lambda x: x[1], reverse=True) if walls else []
    logger.debug(f"Support walls: {len(support_walls)}, Resistance walls: {len(resistance_walls)}")

    # Ako current_price nije None, generiši signale
    if current_price is None:
        logger.warning("current_price je None, preskačem generisanje signala")
        return signals

    for price, volume in support_walls:
        last_digit = int(str(round(price, 4))[-1])
        wall_type = classify_wall_volume(volume)
        logger.debug(f"Support: price={price:.5f}, last_digit={last_digit}, volume={volume:.2f}, wall_type={wall_type}")
        if last_digit in TARGET_DIGITS:
            if last_digit in [2, 3]:
                signal = {
                    'type': 'LONG',
                    'entry_price': price,
                    'stop_loss': round(price - 0.00005, 5),
                    'take_profit': round(price + 0.00010, 5),
                    'wall_type': wall_type,
                    'volume': volume
                }
                signals.append(signal)
                logger.info(f"Signal: {signal}")
        elif rokada_status_global == "on" and last_digit in SPECIAL_DIGITS and trend == 'DOWN':
            if last_digit == 1:
                signal = {
                    'type': 'SHORT',
                    'entry_price': round(price - 0.00002, 5),
                    'stop_loss': round(price + 0.00005, 5),
                    'take_profit': round(price - 0.00010, 5),
                    'wall_type': wall_type,
                    'volume': volume
                }
                signals.append(signal)
                logger.info(f"Signal: {signal}")

    for price, volume in resistance_walls:
        last_digit = int(str(round(price, 4))[-1])
        wall_type = classify_wall_volume(volume)
        logger.debug(
            f"Resistance: price={price:.5f}, last_digit={last_digit}, volume={volume:.2f}, wall_type={wall_type}")
        if last_digit in TARGET_DIGITS:
            if last_digit in [7, 8]:
                signal = {
                    'type': 'SHORT',
                    'entry_price': price,
                    'stop_loss': round(price + 0.00005, 5),
                    'take_profit': round(price - 0.00010, 5),
                    'wall_type': wall_type,
                    'volume': volume
                }
                signals.append(signal)
                logger.info(f"Signal: {signal}")
        elif rokada_status_global == "on" and last_digit in SPECIAL_DIGITS and trend == 'UP':
            if last_digit == 9:
                signal = {
                    'type': 'LONG',
                    'entry_price': round(price + 0.00002, 5),
                    'stop_loss': round(price - 0.00005, 5),
                    'take_profit': round(price + 0.00010, 5),
                    'wall_type': wall_type,
                    'volume': volume
                }
                signals.append(signal)
                logger.info(f"Signal: {signal}")

    logger.info(f"Generisano signala: {len(signals)}")
    return signals