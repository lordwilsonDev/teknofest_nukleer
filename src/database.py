"""
database.py — TEKNOFEST Nükleer Enerji Simülasyonu Veritabanı Modülü
=====================================================================
SQLite tabanlı telemetri ve olay kaydı.
"""

import sqlite3
import json
import os
from datetime import datetime

class ReactorDatabase:
    def __init__(self, db_path: str = "reactor_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Telemetri tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_s REAL,
                    temperature_k REAL,
                    pressure_bar REAL,
                    power_mwth REAL,
                    neutron_flux REAL,
                    rod_pos REAL,
                    coolant_flow REAL,
                    xenon_pcm REAL,
                    burnup_mwdmt REAL
                )
            """)
            # Olay tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_iso TEXT,
                    level TEXT,
                    message TEXT
                )
            """)
            conn.commit()

    def save_state(self, state):
        """ReactorState nesnesini veya dict formatını kaydet."""
        if hasattr(state, 'to_dict'):
            d = state.to_dict()
        else:
            d = state

        # Reactivity pcm olarak değilse bile burada pcm olarak saklanabilir 
        # (ReactorState'de reactivity_pcm var zaten önceki geliştirmeden)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO telemetry (
                    timestamp_s, temperature_k, pressure_bar, power_mwth, 
                    neutron_flux, rod_pos, coolant_flow, xenon_pcm, burnup_mwdmt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d['timestamp'], d['temperature_k'], d['pressure_bar'], d['power_mwth'],
                d['neutron_flux'], d['control_rod_pos'], d['coolant_flow_pct'],
                d['reactivity_pcm'], d['burnup_mwdmt']
            ))
            conn.commit()

    def save_event(self, event):
        """ReactorEvent nesnesini kaydet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (timestamp_iso, level, message)
                VALUES (?, ?, ?)
            """, (event.timestamp_iso, event.level, event.message))
            conn.commit()
