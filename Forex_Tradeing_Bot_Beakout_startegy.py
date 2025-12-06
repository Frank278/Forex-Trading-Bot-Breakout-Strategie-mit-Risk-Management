"""
Interactive Brokers Forex Trading Bot
Breakout-Strategie mit Risk Management
"""

import time
from datetime import datetime, timezone
from ib_insync import IB, Forex, MarketOrder, Order
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import logging

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ForexBreakoutBot:
    """
    Forex Trading Bot mit Breakout-Strategie
    Features:
    - Breakout-Erkennung (Long/Short)
    - Risk Management (% vom Kapital)
    - Trailing Stop & Take Profit
    - Session-Filter (Sydney, Tokyo, London, NY)
    """
    
    def __init__(self, config: Dict):
        """
        Initialisierung des Bots
        
        Args:
            config: Dictionary mit Konfiguration
        """
        self.ib = IB()
        self.config = config
        
        # Trading Parameter
        self.symbol = config.get('symbol', 'EURUSD')
        self.lookback_period = config.get('lookback_period', 20)
        self.risk_percent = config.get('risk_percent', 10.0)
        self.take_profit_pips = config.get('take_profit_pips', 40)
        self.trailing_stop_pips = config.get('trailing_stop_pips', 20)
        self.leverage = config.get('leverage', 100)
        
        # Session Filter
        self.sessions = config.get('sessions', {
            'sydney': True,
            'tokyo': True,
            'london': True,
            'new_york': True
        })
        
        # Daten
        self.bars: List = []
        self.current_position = None
        
    def connect(self, host='127.0.0.1', port=7497, client_id=1):
        """
        Verbindung zu Interactive Brokers TWS/Gateway
        
        Args:
            host: TWS Host (Standard: localhost)
            port: TWS Port (7497=Paper, 7496=Live)
            client_id: Client ID
        """
        try:
            self.ib.connect(host, port, clientId=client_id)
            logger.info(f"✅ Verbunden mit IB auf {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"❌ Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        """Trennt Verbindung zu IB"""
        self.ib.disconnect()
        logger.info("Verbindung getrennt")
    
    def get_account_info(self) -> Dict:
        """
        Holt Account-Informationen
        
        Returns:
            Dictionary mit Account-Daten
        """
        account_values = self.ib.accountValues()
        info = {}
        
        for av in account_values:
            if av.tag == 'NetLiquidation':
                info['equity'] = float(av.value)
            elif av.tag == 'TotalCashValue':
                info['cash'] = float(av.value)
        
        logger.info(f"💰 Account Equity: ${info.get('equity', 0):.2f}")
        return info
    
    def in_trading_session(self) -> bool:
        """
        Prüft ob aktuelle Zeit in einer aktiven Trading-Session ist
        
        Returns:
            True wenn in Trading-Session
        """
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour
        
        # Sydney: 22:00-07:00 UTC
        if self.sessions.get('sydney') and (hour >= 22 or hour < 7):
            return True
        
        # Tokyo: 00:00-09:00 UTC
        if self.sessions.get('tokyo') and (0 <= hour < 9):
            return True
        
        # London: 08:00-17:00 UTC
        if self.sessions.get('london') and (8 <= hour < 17):
            return True
        
        # New York: 13:00-22:00 UTC
        if self.sessions.get('new_york') and (13 <= hour < 22):
            return True
        
        return False
    
    def get_historical_data(self, duration='1 D', bar_size='5 mins'):
        """
        Holt historische Daten von IB
        
        Args:
            duration: Zeitraum (z.B. '1 D', '1 W')
            bar_size: Bar-Größe (z.B. '5 mins', '1 hour')
        """
        contract = Forex(self.symbol)
        
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow='MIDPOINT',
            useRTH=False,
            formatDate=1
        )
        
        # Konvertiere zu DataFrame
        df = pd.DataFrame(bars)
        self.bars = df
        
        logger.info(f"📊 {len(df)} Bars geladen für {self.symbol}")
        return df
    
    def calculate_breakout_signals(self) -> Dict:
        """
        Berechnet Breakout-Signale
        
        Returns:
            Dictionary mit 'long_breakout' und 'short_breakout'
        """
        if len(self.bars) < self.lookback_period + 1:
            return {'long_breakout': False, 'short_breakout': False}
        
        df = self.bars.copy()
        
        # Höchst- und Tiefstwerte der letzten N Perioden
        df['highest_high'] = df['high'].rolling(self.lookback_period).max()
        df['lowest_low'] = df['low'].rolling(self.lookback_period).min()
        
        # Letzter Breakout
        last_close = df['close'].iloc[-1]
        prev_highest = df['highest_high'].iloc[-2]
        prev_lowest = df['lowest_low'].iloc[-2]
        
        long_breakout = last_close > prev_highest
        short_breakout = last_close < prev_lowest
        
        if long_breakout:
            logger.info(f"🚀 LONG Breakout erkannt bei {last_close}")
        if short_breakout:
            logger.info(f"📉 SHORT Breakout erkannt bei {last_close}")
        
        return {
            'long_breakout': long_breakout,
            'short_breakout': short_breakout,
            'current_price': last_close
        }
    
    def calculate_position_size(self, entry_price: float) -> int:
        """
        Berechnet Positionsgröße basierend auf Risiko
        
        Args:
            entry_price: Einstiegspreis
            
        Returns:
            Anzahl der Kontrakte/Einheiten
        """
        account_info = self.get_account_info()
        equity = account_info.get('equity', 10000)
        
        risk_amount = equity * (self.risk_percent / 100)
        
        # Pip-Wert berechnen
        if 'JPY' in self.symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        # Stop Loss Distanz
        stop_loss_distance = self.trailing_stop_pips * pip_value
        
        # Positionsgröße berechnen
        # Einheiten = Risiko / (SL Distanz * Pip Wert pro Einheit)
        units_needed = risk_amount / (stop_loss_distance)
        
        # Für Forex: 1 Lot = 100.000 Einheiten
        # Wir runden auf Mini-Lots (10.000 Einheiten)
        contracts = int(units_needed / 10000)
        
        logger.info(f"📐 Positionsgröße: {contracts} Mini-Lots (Risiko: ${risk_amount:.2f})")
        
        return max(1, contracts)  # Mindestens 1 Kontrakt
    
    def place_order(self, action: str, quantity: int, entry_price: float):
        """
        Platziert Order mit Trailing Stop und Take Profit
        
        Args:
            action: 'BUY' oder 'SELL'
            quantity: Anzahl Kontrakte
            entry_price: Einstiegspreis
        """
        contract = Forex(self.symbol)
        
        # Haupt-Order
        parent_order = MarketOrder(action, quantity)
        
        # Pip-Wert
        if 'JPY' in self.symbol:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        # Take Profit berechnen
        if action == 'BUY':
            take_profit_price = entry_price + (self.take_profit_pips * pip_value)
            trailing_stop_price = entry_price - (self.trailing_stop_pips * pip_value)
        else:
            take_profit_price = entry_price - (self.take_profit_pips * pip_value)
            trailing_stop_price = entry_price + (self.trailing_stop_pips * pip_value)
        
        # Take Profit Order (Bracket)
        take_profit = Order()
        take_profit.action = 'SELL' if action == 'BUY' else 'BUY'
        take_profit.totalQuantity = quantity
        take_profit.orderType = 'LMT'
        take_profit.lmtPrice = round(take_profit_price, 5)
        
        # Trailing Stop Order
        trailing_stop = Order()
        trailing_stop.action = 'SELL' if action == 'BUY' else 'BUY'
        trailing_stop.totalQuantity = quantity
        trailing_stop.orderType = 'TRAIL'
        trailing_stop.trailStopPrice = round(trailing_stop_price, 5)
        trailing_stop.auxPrice = self.trailing_stop_pips * pip_value
        
        # Bracket Order erstellen
        bracket = self.ib.bracketOrder(
            action=action,
            quantity=quantity,
            limitPrice=take_profit_price,
            takeProfitPrice=take_profit_price,
            stopLossPrice=trailing_stop_price
        )
        
        # Order platzieren
        trades = self.ib.placeOrder(contract, bracket[0])
        
        logger.info(f"✅ {action} Order platziert: {quantity} Lots")
        logger.info(f"   Entry: {entry_price:.5f}")
        logger.info(f"   TP: {take_profit_price:.5f} (+{self.take_profit_pips} pips)")
        logger.info(f"   SL: {trailing_stop_price:.5f} (-{self.trailing_stop_pips} pips)")
        
        return trades
    
    def check_positions(self):
        """Prüft offene Positionen"""
        positions = self.ib.positions()
        
        for pos in positions:
            if pos.contract.symbol == self.symbol.replace('USD', ''):
                self.current_position = pos
                logger.info(f"📍 Offene Position: {pos.position} @ {pos.avgCost}")
                return pos
        
        self.current_position = None
        return None
    
    def run(self, check_interval=300):
        """
        Haupt-Loop des Bots
        
        Args:
            check_interval: Sekunden zwischen Checks (Standard: 5 Min)
        """
        logger.info("🤖 Bot gestartet...")
        
        try:
            while True:
                # Prüfe Trading-Session
                if not self.in_trading_session():
                    logger.info("⏰ Außerhalb der Trading-Sessions, warte...")
                    time.sleep(60)
                    continue
                
                # Prüfe offene Positionen
                self.check_positions()
                
                if self.current_position is not None:
                    logger.info("Position bereits offen, warte auf Exit...")
                    time.sleep(check_interval)
                    continue
                
                # Hole aktuelle Daten
                self.get_historical_data()
                
                # Berechne Signale
                signals = self.calculate_breakout_signals()
                current_price = signals['current_price']
                
                # Long Signal
                if signals['long_breakout']:
                    quantity = self.calculate_position_size(current_price)
                    self.place_order('BUY', quantity, current_price)
                
                # Short Signal
                elif signals['short_breakout']:
                    quantity = self.calculate_position_size(current_price)
                    self.place_order('SELL', quantity, current_price)
                
                # Warte bis nächster Check
                logger.info(f"💤 Warte {check_interval}s bis nächster Check...")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Bot gestoppt durch Benutzer")
        except Exception as e:
            logger.error(f"❌ Fehler: {e}")
        finally:
            self.disconnect()


# ============================================
# KONFIGURATION & START
# ============================================

if __name__ == "__main__":
    # Bot-Konfiguration
    config = {
        'symbol': 'EURUSD',
        'lookback_period': 20,
        'risk_percent': 10.0,
        'take_profit_pips': 40,
        'trailing_stop_pips': 20,
        'leverage': 100,
        'sessions': {
            'sydney': True,
            'tokyo': True,
            'london': True,
            'new_york': True
        }
    }
    
    # Bot erstellen
    bot = ForexBreakoutBot(config)
    
    # Verbinden (Port 7497 = Paper Trading, 7496 = Live)
    if bot.connect(host='127.0.0.1', port=7497):
        # Bot starten
        bot.run(check_interval=300)  # Check alle 5 Minuten
