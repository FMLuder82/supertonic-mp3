# Supertonic MP3

Converts chat TXT files in `Chats/` to MP3 using Supertonic.

## Structure

- `Chats/` - input TXT files.
- `Mp3/` - output MP3 files produced by GitHub Actions.
- `txt_to_wav.py` - Supertonic TXT -> WAV.
- `wav_to_mp3.py` - WAV -> MP3.
- `.github/workflows/convert.yml` - GitHub Actions workflow.

TXT files must use:

[USER]
Message from the user.

[ASSISTANT]
Message from the assistant.

## Run

Open **Actions → Convert chats to MP3 → Run workflow**.

The workflow processes every `*.txt` file in `Chats/`.

The resulting MP3 files are uploaded as a workflow artifact named `mp3`. WAV files are temporary and are not committed to the repository.

Default settings:

- USER voice: M4
- ASSISTANT voice: F1
- Supertonic: 3
- total steps: 8
- speed: 1.0
- silence between chunks: 0.4 s
- MP3 bitrate: 128k
