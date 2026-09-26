import argparse
import time
from pathlib import Path

from supertonic import TTS

DEFAULT_STEPS = 8
DEFAULT_SPEED = 1.0
DEFAULT_MAX_CHUNK_LENGTH = 300
DEFAULT_SILENCE = 0.4
DEFAULT_USER_VOICE = "M4"
DEFAULT_ASSISTANT_VOICE = "F1"


def read_dialog(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    messages = []
    current_role = None
    current_lines = []

    def save_message():
        nonlocal current_role, current_lines
        if current_role is None:
            return
        message = "\n".join(current_lines).strip()
        if message:
            messages.append((current_role, message))
        current_lines = []

    for line in lines:
        if line == "[USER]":
            save_message()
            current_role = "user"
        elif line == "[ASSISTANT]":
            save_message()
            current_role = "assistant"
        else:
            current_lines.append(line)

    save_message()
    return messages


def sanitize_text(text):
    """Не изменяет нормальный Unicode-текст; оставляет буквы, й и ё."""
    return text


def format_time(seconds):
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:05.2f}"


def synthesize_with_fallback(tts, text, style, args):
    """Пробует всё более короткие чанки; если реплика не синтезируется, отдаёт ошибку вызывающему коду."""
    chunk_lengths = []
    for value in (args.max_chunk_length, 150, 75, 40):
        if value > 0 and value not in chunk_lengths:
            chunk_lengths.append(value)

    last_error = None
    for chunk_length in chunk_lengths:
        try:
            result = tts.synthesize(
                text=text,
                voice_style=style,
                total_steps=args.total_steps,
                speed=args.speed,
                max_chunk_length=chunk_length,
                silence_duration=args.silence_duration,
                lang=args.lang,
                verbose=args.verbose,
            )
            return result, chunk_length
        except Exception as exc:
            last_error = exc

    raise last_error


def main():
    parser = argparse.ArgumentParser(description="Supertonic TXT -> WAV")
    parser.add_argument("input", type=Path, help="TXT-файл диалога")
    parser.add_argument("--output-dir", type=Path, default=Path("wav"))
    parser.add_argument("--voice-user", default=DEFAULT_USER_VOICE)
    parser.add_argument("--voice-assistant", default=DEFAULT_ASSISTANT_VOICE)
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--model", default="supertonic-3")
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--no-auto-download", action="store_true")
    parser.add_argument("--intra-threads", type=int, default=None)
    parser.add_argument("--inter-threads", type=int, default=None)
    parser.add_argument("--total-steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--max-chunk-length", type=int, default=DEFAULT_MAX_CHUNK_LENGTH)
    parser.add_argument("--silence-duration", type=float, default=DEFAULT_SILENCE)
    parser.add_argument("--lang", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("Загрузка Supertonic")
    print("=" * 60)
    start = time.perf_counter()
    tts = TTS(
        model=args.model,
        model_dir=args.model_dir,
        auto_download=not args.no_auto_download,
        intra_op_num_threads=args.intra_threads,
        inter_op_num_threads=args.inter_threads,
    )
    load_time = time.perf_counter() - start
    print(f"Модель:      {tts.model_name}")
    print(f"Sample rate: {tts.sample_rate} Hz")
    print(f"Загрузка:    {load_time:.2f} сек")

    if args.list_voices:
        print("Доступные голоса:")
        for voice in tts.voice_style_names:
            print(f"  {voice}")
        return

    if not args.input.exists():
        raise FileNotFoundError(f"Файл не найден: {args.input}")

    available = set(tts.voice_style_names)
    if args.voice_user not in available:
        raise ValueError(f"Неизвестный голос USER: {args.voice_user}")
    if args.voice_assistant not in available:
        raise ValueError(f"Неизвестный голос ASSISTANT: {args.voice_assistant}")

    user_style = tts.get_voice_style(args.voice_user)
    assistant_style = tts.get_voice_style(args.voice_assistant)

    messages = read_dialog(args.input)
    if not messages:
        raise ValueError("В TXT не найдено ни одной реплики.")

    output_dir = args.output_dir / args.input.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"USER:      {args.voice_user}")
    print(f"ASSISTANT: {args.voice_assistant}")
    print(f"Реплик:    {len(messages)}")
    print(f"Вывод:     {output_dir.resolve()}")

    total_audio = 0.0
    total_compute = 0.0
    created = 0
    skipped = 0
    failed = 0
    overall_start = time.perf_counter()

    for index, (role, text) in enumerate(messages, start=1):
        if role == "user":
            style = user_style
            role_name = "user"
        else:
            style = assistant_style
            role_name = "assistant"

        output_path = output_dir / f"{index:06d}_{role_name}.wav"
        if output_path.exists():
            print(f"[{index}/{len(messages)}] {output_path.name} уже существует, пропускаю.")
            skipped += 1
            continue

        clean_text = sanitize_text(text)
        if not clean_text.strip():
            failed += 1
            continue

        print()
        print(f"[{index}/{len(messages)}] {role_name}: {clean_text[:80].replace(chr(10), ' ')}")

        start = time.perf_counter()
        try:
            (wav, _), used_chunk_length = synthesize_with_fallback(
                tts, clean_text, style, args
            )
        except Exception:
            failed += 1
            print("  Не удалось озвучить реплику, переходим к следующей.")
            continue

        elapsed = time.perf_counter() - start
        tts.save_audio(wav, output_path)
        samples = wav.shape[0] if wav.ndim == 1 else wav.shape[-1]
        audio_seconds = samples / tts.sample_rate
        total_audio += audio_seconds
        total_compute += elapsed
        created += 1
        print(f"  chunk:   {used_chunk_length}")
        print(f"  аудио:   {audio_seconds:.2f} сек")
        print(f"  время:   {elapsed:.2f} сек")
        print(f"  RTF:     {elapsed / audio_seconds:.3f}")

    overall_time = time.perf_counter() - overall_start
    print()
    print("=" * 60)
    print("ГОТОВО")
    print("=" * 60)
    print(f"Новых WAV:       {created}")
    print(f"Пропущено:       {skipped}")
    print(f"Не озвучено:     {failed}")
    print(f"Аудио:           {format_time(total_audio)}")
    print(f"Время синтеза:   {format_time(total_compute)}")
    print(f"Общее время:     {format_time(overall_time)}")
    if total_audio > 0:
        print(f"Realtime factor: {total_compute / total_audio:.3f}")
    print(f"Папка:           {output_dir.resolve()}")


if __name__ == "__main__":
    main()
