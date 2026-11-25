# alarms/alarm_sound.py
"""Модуль для звукового оповещения о критическом времени тревог"""

from PyQt5.QtCore import QTimer
from utils.logger import logger

try:
    import winsound
    SOUND_AVAILABLE = True
    logger.info("✅ Звук доступен (winsound)")
except ImportError:
    SOUND_AVAILABLE = False
    logger.warning("❌ Модуль winsound не доступен (только Windows)")
except Exception as e:
    SOUND_AVAILABLE = False
    logger.error(f"❌ Ошибка инициализации звука: {e}")


class AlarmSoundManager:
    """Менеджер звуковых оповещений о критическом времени тревог"""
    
    INTERVAL_1_HOUR = 60
    INTERVAL_2_HOURS = 120
    
    def __init__(self):
        self._timer = None
        self._is_playing = False
        self._notified_1hour = set()
        self._notified_2hours = set()
        logger.info("AlarmSoundManager инициализирован")
    
    def check_and_play(self, alarms: list):
        if not SOUND_AVAILABLE:
            return
        
        active_alarms = [a for a in alarms 
                        if a.get("status") not in ["closed", "worked"]]
        
        if not active_alarms:
            return
        
        for alarm in active_alarms:
            timestamp = alarm.get("timestamp", "")
            if not timestamp:
                continue
            
            alarm_id = f"{alarm.get('vin', '')}_{alarm.get('contract', '')}_{timestamp}"
            
            try:
                from datetime import datetime
                opened_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                minutes_passed = (current_time - opened_time).total_seconds() / 60
                
                if minutes_passed >= self.INTERVAL_2_HOURS:
                    if alarm_id not in self._notified_2hours:
                        self._notified_2hours.add(alarm_id)
                        logger.info(f"🔴 КРИТИЧЕСКИЙ СИГНАЛ: тревога более 2 часов! VIN={alarm.get('vin')}")
                        self._play_sound(critical=True)
                        return
                elif minutes_passed >= self.INTERVAL_1_HOUR:
                    if alarm_id not in self._notified_1hour:
                        self._notified_1hour.add(alarm_id)
                        logger.info(f"🟡 ПРЕДУПРЕЖДЕНИЕ: тревога более 1 часа! VIN={alarm.get('vin')}")
                        self._play_sound(critical=False)
                        return
            except Exception as e:
                logger.error(f"Ошибка: {e}")
    
    def _play_sound(self, critical: bool = False):
        if self._is_playing or not SOUND_AVAILABLE:
            return
        
        try:
            if critical:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            else:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            self._is_playing = True
            self._start_stop_timer()
        except Exception as e:
            logger.error(f"Ошибка воспроизведения звука: {e}")
    
    def _start_stop_timer(self):
        if self._timer:
            self._timer.stop()
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._stop_sound)
        self._timer.start(5000)
    
    def _stop_sound(self):
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._is_playing = False
    
    def on_alarm_clicked(self):
        self._stop_sound()
    
    def reset(self):
        self._stop_sound()
        self._notified_1hour.clear()
        self._notified_2hours.clear()


alarm_sound_manager = AlarmSoundManager()