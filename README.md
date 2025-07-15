# TypeSpeech

Real-time speech recognition application using Google Speech-to-Text API with automatic text input.

## Features

- Real-time audio recording from microphone
- Speech recognition via Google Speech-to-Text API
- Automatic text input to active field
- Configurable hotkey controls
- System tray interface

## Requirements

- Python 3.10+
- Google Cloud Speech-to-Text API
- Microphone
- Internet connection

## Installation

1. Clone the repository:
```bash
git clone git@github.com:closeup24/type-speech.git
cd type-speech
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up Google Cloud credentials:

   - Create a project in Google Cloud Console
   - Enable Speech-to-Text API
   - Create a Service Account and download JSON key
   - Place the JSON file in `credentials/` folder
   - Update `config/default.yaml` with the correct filename:

     ```yaml
     credentials:
       google_cloud_path: "credentials/your-service-account-key.json"
     ```

## Usage

1. Run the application:
```bash
python -m app.tray_app
```

2. Press the configured hotkey to start recording
3. Speak into microphone
4. Press the configured hotkey to stop recording

## Building Executable

```bash
python build_exe.py
```

### Setting up credentials for EXE

After building the executable:

1. **Copy your JSON credentials file** to the `build/TypeSpeech/credentials/` folder
2. **Update the config** in `build/TypeSpeech/config/default.yaml`:
   ```yaml
   credentials:
     google_cloud_path: "credentials/your-service-account-key.json"
   ```
3. **Run the executable** from `build/TypeSpeech/TypeSpeech.exe`

## Configuration

All settings can be configured in `config/default.yaml` and `config/user.yaml`. `user.yaml` will overwrite default settings.

## License

MIT License 