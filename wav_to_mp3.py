import argparse
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Собирает WAV-файлы в один MP3")
    parser.add_argument("input", type=Path, help="Папка с WAV-файлами")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--bitrate", default="128k")
    args = parser.parse_args()

    input_dir = args.input
    if not input_dir.exists():
        raise FileNotFoundError(f"Папка не найдена: {input_dir}")

    wav_files = sorted(input_dir.glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"В папке нет WAV-файлов: {input_dir}")

    output_file = input_dir.parent / f"{input_dir.name}.mp3" if args.output is None else args.output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("WAV -> MP3")
    print("=" * 60)
    print(f"Найдено WAV: {len(wav_files)}")
    print(f"Битрейт:     {args.bitrate}")
    print(f"Выход:       {output_file.resolve()}")
    print("Собираю MP3...")

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
        concat_file = Path(f.name)
        for wav in wav_files:
            path = wav.resolve().as_posix()
            f.write(f"file {path!r}\n")

    try:
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-vn",
            "-codec:a", "libmp3lame",
            "-b:a", args.bitrate,
            str(output_file),
        ]
        subprocess.run(command, check=True)
    finally:
        concat_file.unlink(missing_ok=True)

    print("=" * 60)
    print("ГОТОВО")
    print("=" * 60)
    print(f"MP3: {output_file.resolve()}")


if __name__ == "__main__":
    main()
