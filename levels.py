import logging
from config import TARGET_DIGITS, SPECIAL_DIGITS, MIN_WALL_VOLUME, HILL_WALL_VOLUME, MOUNTAIN_WALL_VOLUME, EPIC_WALL_VOLUME

logger = logging.getLogger(__name__)

def classify_wall_volume(volume):
    if volume >= EPIC_WALL_VOLUME:
        return "Planina"
    elif volume >= MOUNTAIN_WALL_VOLUME:
        return "Brdo"
    elif volume >= HILL_WALL_VOLUME:
        return "Brdašce"
    return "Zid"

def generate_signals(current_price, walls, trend, rokada_status="off"):
    logger.info(f"Ulaz u generate_signals: current_price={current_price:.5f}, trend={trend}, rokada={rokada_status}, walls={walls}")
    signals = []
    support_walls = sorted(walls['support'], key=lambda x: x[1], reverse=True)
    resistance_walls = sorted(walls['resistance'], key=lambda x: x[1], reverse=True)
    logger.debug(f"Support walls: {len(support_walls)}, Resistance walls: {len(resistance_walls)}")

    for price, volume in support_walls:
        last_digit = int(str(round(price, 4))[-1])  # Smanjena preciznost
        wall_type = classify_wall_volume(volume)
        logger.debug(f"Support: price={price:.5f}, last_digit={last_digit}, volume={volume:.2f}, wall_type={wall_type}")
        if last_digit in TARGET_DIGITS or True:  # Privremeno uklonjen uslov
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

    for price, volume in resistance_walls:
        last_digit = int(str(round(price, 4))[-1])
        wall_type = classify_wall_volume(volume)
        logger.debug(f"Resistance: price={price:.5f}, last_digit={last_digit}, volume={volume:.2f}, wall_type={wall_type}")
        if last_digit in TARGET_DIGITS or True:  # Privremeno uklonjen uslov
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

    logger.info(f"Generisano signala: {len(signals)}")
    return signals