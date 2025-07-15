import pystray
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import threading
import signal
import sys
import os
import queue
from type_speech.engine import SpeechToText
from type_speech.logger import logger
from type_speech.config import config
from typing import Any, Optional
import time
import keyboard


def create_square_icon(
    size: int = 40,
    color: str = "gray",
    border_color: Optional[str] = None,
    border_width: int = 5,
) -> Image.Image:
    """Create square icon with optional border"""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if border_color:
        draw.rectangle([0, 0, size - 1, size - 1], fill=border_color)
        draw.rectangle(
            [
                border_width,
                border_width,
                size - border_width - 1,
                size - border_width - 1,
            ],
            fill=color,
        )
    else:
        draw.rectangle([0, 0, size - 1, size - 1], fill=color)
    return image


def get_assets_path(filename: str) -> str:
    """Get path to assets file, works both in development and exe"""
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", "")  # Running as exe
    else:
        base_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )  # Running in development
    return os.path.join(base_path, "assets", filename)


class TraySpeechApp:
    def __init__(self) -> None:
        self.app: SpeechToText = SpeechToText()
        self.should_exit: bool = False
        self._register_hotkeys()

        # Setup signal handlers for shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.waiting_mode_icon = create_square_icon(50, "gray", "green")
        self.listening_mode_icon = create_square_icon(50, "green")

        self.menu: Menu = Menu(MenuItem("Exit", self.stop_app))
        self.icon = pystray.Icon(
            "speech_recognition",
            self.waiting_mode_icon,
            f"TypeSpeech \n\n"
            f"Start: {config.hotkeys.start_recording.upper()}\n"
            f"Stop: {config.hotkeys.stop_recording.upper()}\n"
            f"Exit: {config.hotkeys.exit_app.upper()}",
            self.menu,
        )

    def _register_hotkeys(self) -> None:
        if config.hotkeys.start_recording == config.hotkeys.stop_recording:
            keyboard.add_hotkey(
                config.hotkeys.start_recording, self._on_start_stop_hotkey
            )
        else:
            keyboard.add_hotkey(config.hotkeys.start_recording, self._on_start_hotkey)
            keyboard.add_hotkey(config.hotkeys.stop_recording, self._on_stop_hotkey)
        keyboard.add_hotkey(config.hotkeys.exit_app, self._on_exit_hotkey)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Signal handler for shutdown"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_app()

    def _update_icon(self, image: Image.Image) -> None:
        """Update tray icon"""
        self.icon.icon = image
        self.icon.update_menu()

    def _on_start_hotkey(self) -> None:
        if not self.app.is_recording_active:
            logger.info("Starting recording")
            self._update_icon(self.listening_mode_icon)
            record_thread = threading.Thread(target=self.app.start_recording)
            record_thread.start()

            transcribe_thread = threading.Thread(
                target=self.app.transcribe_stream,
                args=(self.app.audio_queue, self.app.transcription_text_queue),
            )
            transcribe_thread.daemon = True
            transcribe_thread.start()

    def _on_stop_hotkey(self) -> None:
        if self.app.is_recording_active:
            logger.info("Stopping recording")
            self.app.stop_recording()
            self._update_icon(self.waiting_mode_icon)

    def _on_start_stop_hotkey(self) -> None:
        if self.app.is_recording_active:
            self._on_stop_hotkey()
        else:
            self._on_start_hotkey()

    def _on_exit_hotkey(self) -> None:
        """Exit application hotkey handler"""
        logger.info("Exiting application")
        self.stop_app()

    def start_text_worker(self) -> None:
        def text_worker() -> None:
            while not self.should_exit:
                try:
                    item = self.app.transcription_text_queue.get(timeout=0.1)
                    if item is None:
                        break
                    self.app.type_text(item)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in text processing: {e}")
                    continue

        text_thread = threading.Thread(target=text_worker)
        text_thread.daemon = True
        text_thread.start()

    def start_recording_monitor(self) -> None:
        """Monitor recording state and update icon accordingly"""

        def monitor_worker() -> None:
            while not self.should_exit:
                try:
                    # Check if recording is active and update icon if needed
                    if not self.app.is_recording_active:
                        # If not recording but icon shows listening, update to waiting
                        if self.icon.icon == self.listening_mode_icon:
                            self._update_icon(self.waiting_mode_icon)
                            logger.debug(
                                "Recording stopped, updated icon to waiting mode"
                            )
                except Exception as e:
                    logger.error(f"Error in recording monitor: {e}")

                time.sleep(0.5)

        monitor_thread = threading.Thread(target=monitor_worker)
        monitor_thread.daemon = True
        monitor_thread.start()

    def stop_app(self, icon=None, item=None) -> None:
        """Stop application"""
        logger.info("Shutting down application")
        self.should_exit = True
        self.app.stop_recording()

        keyboard.remove_all_hotkeys()
        self.icon.stop()

    def run(self) -> None:
        """Run tray application"""
        logger.info("Starting speech recognition application")
        logger.info(
            f"Hotkeys: {config.hotkeys.start_recording} (start), {config.hotkeys.stop_recording} (stop), {config.hotkeys.exit_app} (exit)"
        )

        self.start_text_worker()
        self.start_recording_monitor()

        hotkey_thread = threading.Thread(target=keyboard.wait)
        hotkey_thread.daemon = True
        hotkey_thread.start()

        self.icon.run()


if __name__ == "__main__":
    TraySpeechApp().run()
