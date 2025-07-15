import queue
import threading
import sounddevice as sd
from google.cloud import speech
from google.cloud.speech import (
    RecognitionConfig,
    StreamingRecognitionConfig,
    StreamingRecognizeRequest,
    SpeechRecognitionAlternative,
    SpeechRecognitionResult,
)
from google.oauth2.service_account import Credentials
from typing import Optional, Generator, Literal
from dataclasses import dataclass
from type_speech.logger import logger
from type_speech.config import config
from type_speech.utils import resolve_path
import time
import pyperclip
import win32api
import win32con


def press_ctrl_plus(key: Literal["V", "Z"]) -> None:
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(ord(key), 0, 0, 0)
    win32api.keybd_event(ord(key), 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    logger.debug(f"Pressed CTRL+{key}")


def get_google_credentials() -> Credentials:
    """Get Google Cloud credentials from JSON file"""
    try:
        credentials_path = resolve_path(config.credentials.google_cloud_path)
        logger.info(f"Loading credentials from: {credentials_path}")
        return Credentials.from_service_account_file(str(credentials_path))
    except Exception as e:
        logger.error(f"Failed to load credentials from file: {e}")
        raise ValueError(
            "Google Cloud credentials not found. Please check credentials file path."
        )


@dataclass(frozen=True)
class Phrase:
    text: str
    accuracy: float  # confidence for final or stability for interim
    is_final: bool  # final or interim


class SpeechToText:
    """Main speech recognition application class"""

    def __init__(self) -> None:
        self.audio_queue: queue.Queue = queue.Queue()
        self.transcription_text_queue: queue.Queue = queue.Queue()
        self.recording_lock: threading.Lock = threading.Lock()

        self._audio_stream: Optional[sd.InputStream] = None

        self.is_recording: bool = False
        self.is_transcribing: bool = False
        self.interim_phrase: Optional[Phrase] = None

    def generate_requests(
        self, audio_queue: queue.Queue
    ) -> Generator[StreamingRecognizeRequest, None, None]:
        """Generate requests for API streaming"""
        while True:
            data = audio_queue.get()
            if data is None:
                break
            yield StreamingRecognizeRequest(audio_content=data)

    def start_recording(self) -> None:
        """Start audio recording"""
        with self.recording_lock:
            if self.is_recording:
                logger.debug("Recording already in progress, ignoring start request")
                return
            self.is_recording = True

        logger.info("Initializing sounddevice for recording...")

        try:
            self._audio_stream = sd.InputStream(
                samplerate=config.audio.rate,
                channels=config.audio.channels,
                dtype=config.audio.dtype,
                blocksize=config.audio.chunk,
            )
            self._audio_stream.start()
            logger.info("Sounddevice stream opened for recording")
        except Exception as e:
            logger.error(f"Failed to open sounddevice stream: {e}")
            logger.error(
                "Make sure microphone is connected and selected in system, check permissions"
            )
            with self.recording_lock:
                self.is_recording = False
            return

        logger.info("Starting audio recording...")
        while self.is_recording:
            try:
                data, overflowed = self._audio_stream.read(config.audio.chunk)
                if overflowed:
                    logger.warning("Audio buffer overflow detected")
                # Convert numpy array to bytes for Google Speech API
                audio_bytes = data.tobytes()
                self.audio_queue.put(audio_bytes)
            except Exception as e:
                logger.error(f"Error reading audio from microphone: {e}")
                logger.error(
                    "Microphone may have disconnected or been captured by another application"
                )
                break
            time.sleep(0.001)

        if self._audio_stream:
            self._audio_stream.stop()
            self._audio_stream.close()

        with self.recording_lock:
            self.is_recording = False

        logger.info("Recording stopped")

    def stop_recording(self) -> None:
        """Stop audio recording"""
        with self.recording_lock:
            if not self.is_recording:
                logger.debug("Recording not in progress, ignoring stop request")
                return
            self.is_recording = False

        logger.info("Stop recording signal sent")
        self.audio_queue.put(None)

    @property
    def is_recording_active(self) -> bool:
        """Check if recording is currently active"""
        with self.recording_lock:
            return self.is_recording

    def transcribe_stream(
        self, audio_queue: queue.Queue, text_output_queue: queue.Queue
    ) -> None:
        """Transcribe audio stream using Google Speech-to-Text API"""
        with self.recording_lock:
            if self.is_transcribing:
                logger.debug("Transcription already in progress, ignoring")
                return
            self.is_transcribing = True

        try:
            client = speech.SpeechClient(credentials=get_google_credentials())  # type: ignore

            config_speech = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=config.audio.rate,
                language_code=config.speech.language_code,
                alternative_language_codes=config.speech.alternative_language_codes,
                model=config.speech.model,
                enable_automatic_punctuation=config.speech.enable_automatic_punctuation,
                use_enhanced=config.speech.use_enhanced,
                enable_word_time_offsets=False,  # Speeds up processing
                enable_word_confidence=False,  # Speeds up processing
                max_alternatives=1,  # Only best result
                speech_contexts=config.speech.speech_contexts,
            )
            streaming_config = StreamingRecognitionConfig(
                config=config_speech, interim_results=True
            )

            requests = self.generate_requests(audio_queue)
            logger.info("Starting streaming to Google Speech-to-Text API...")
            responses = client.streaming_recognize(streaming_config, requests)

            for response in responses:
                if not response.results:
                    continue

                for result in response.results:
                    if not result.alternatives:
                        continue
                    result: SpeechRecognitionResult
                    alternative: SpeechRecognitionAlternative = result.alternatives[
                        0
                    ]  # best

                    phrase = Phrase(
                        text=alternative.transcript.strip(),
                        is_final=result.is_final,
                        accuracy=round(
                            (
                                alternative.confidence
                                if result.is_final
                                else result.stability
                            ),
                            2,
                        ),
                    )
                    text_output_queue.put(phrase)

        except Exception as e:
            logger.critical(f"Critical error in transcription stream: {e}")

            # Special handling for stream duration limit error
            if "400" in str(e) and "maximum allowed stream duration" in str(e):
                # Reset recording state
                with self.recording_lock:
                    self.is_recording = False
                    self.is_transcribing = False
                # Clear audio queue
                while not audio_queue.empty():
                    try:
                        audio_queue.get_nowait()
                    except queue.Empty:
                        break
                logger.info(
                    "Recording stopped due to stream duration limit. Ready for new recording."
                )
            else:
                # For other errors also reset state
                with self.recording_lock:
                    self.is_recording = False
                    self.is_transcribing = False
                logger.error("Recording stopped due to error. Ready for new recording.")
        finally:
            with self.recording_lock:
                self.is_transcribing = False
            logger.info("Transcription stream completed")

    def type_text(self, phrase: Phrase) -> None:
        """Type text into active field"""

        logger.debug(f"{phrase}")

        if (not phrase.is_final) and (
            phrase.accuracy < config.speech.accuracy_threshold
        ):
            logger.debug("Low accuracy, skipping")
            return

        pyperclip.copy(phrase.text + " ")

        if self.interim_phrase is None:
            press_ctrl_plus("V")
        else:
            if self.interim_phrase.text.lower() == phrase.text.lower():
                logger.debug("Interim phrase is the same, skipping")
            else:
                press_ctrl_plus("Z")
                press_ctrl_plus("V")

        if phrase.is_final:
            self.interim_phrase = None
            logger.info(f"FINAL: {phrase.text}")
        else:
            self.interim_phrase = phrase

    def run(self) -> None:
        """Start the speech recognition process"""
        logger.info("Starting speech recognition...")

        # Start recording thread
        record_thread = threading.Thread(target=self.start_recording)
        record_thread.start()

        # Wait a bit for recording to initialize
        time.sleep(0.5)

        # Start transcription thread if recording is still active
        if record_thread.is_alive():
            transcribe_thread = threading.Thread(
                target=self.transcribe_stream,
                args=(self.audio_queue, self.transcription_text_queue),
            )
            transcribe_thread.start()

            # Start text input worker
            text_input_thread = threading.Thread(target=self._text_input_worker)
            text_input_thread.start()

            # Wait for threads to complete
            record_thread.join()
            transcribe_thread.join()

            # Signal text input worker to stop
            self.transcription_text_queue.put(None)
            text_input_thread.join()

        logger.info("Speech recognition completed")

    def _text_input_worker(self) -> None:
        """Worker for text input"""
        while True:
            item = self.transcription_text_queue.get()
            if item is None:
                break
            self.type_text(item)


if __name__ == "__main__":
    SpeechToText().run()
