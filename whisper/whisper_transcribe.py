"""
Craig 봇 녹음 파일 → 참여자별 텍스트 변환 스크립트

[사용법]
    python whisper_transcribe.py --input ./craig_recording --output meeting.txt

    # 타임스탬프 포함
    python whisper_transcribe.py --input ./craig_recording --output meeting.txt --timestamp

[Craig 다운로드 파일 구조]
    Craig는 참여자별로 분리된 .flac 또는 .opus 파일을 ZIP으로 제공합니다.
    ZIP 압축 해제 후 폴더째로 --input에 지정하세요.

[출력 예시]
    [홍길동] 오늘 번역 데이터 300개 완료했어요.
    [김철수] 파인튜닝은 언제 시작하나요?

    타임스탬프 포함 시:
    [00:03] [홍길동] 오늘 번역 데이터 300개 완료했어요.
    [00:07] [김철수] 파인튜닝은 언제 시작하나요?

[설치 필요]
    pip install openai-whisper pydub
    ffmpeg 설치 필수 (https://ffmpeg.org)
"""

import whisper
import argparse
from pathlib import Path


SUPPORTED_EXT = {".flac", ".opus", ".mp3", ".wav", ".m4a", ".ogg"}


def get_speaker_name(filename: str) -> str:
    """파일명에서 참여자 이름 추출
    예: user_홍길동.flac  → 홍길동
        craig_홍길동_1234.flac → 홍길동
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    for part in reversed(parts):
        if part and not part.isdigit():
            return part
    return stem


def transcribe_speaker(model, audio_path: str, speaker: str, language: str) -> list:
    """참여자 한 명의 오디오를 텍스트로 변환, 타임스탬프 포함해서 반환"""
    print(f"  🎙️  [{speaker}] 변환 중...")
    result = model.transcribe(str(audio_path), language=language, verbose=False)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start":   seg["start"],
            "speaker": speaker,
            "text":    seg["text"].strip()
        })
    return segments


def format_time(seconds: float) -> str:
    """초 → MM:SS 형식"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def save_transcript(segments: list, output_file: str, show_timestamp: bool):
    """시간순 정렬 후 텍스트 파일로 저장"""
    sorted_segments = sorted(segments, key=lambda x: x["start"])

    with open(output_file, "w", encoding="utf-8") as f:
        for seg in sorted_segments:
            if show_timestamp:
                line = f"[{format_time(seg['start'])}] [{seg['speaker']}] {seg['text']}\n"
            else:
                line = f"[{seg['speaker']}] {seg['text']}\n"
            f.write(line)

    print(f"\n💾 저장 완료: {output_file}")
    print(f"   총 {len(sorted_segments)}개 발화 변환됨")
    return sorted_segments


def main():
    parser = argparse.ArgumentParser(description="Craig 녹음 파일 → 참여자별 텍스트 변환")
    parser.add_argument("--input",     required=True,         help="Craig 녹음 폴더 경로 (압축 해제 후)")
    parser.add_argument("--output",    default="meeting.txt", help="출력 텍스트 파일명 (기본: meeting.txt)")
    parser.add_argument("--model",     default="medium",      help="Whisper 모델 tiny/base/small/medium/large (기본: medium)")
    parser.add_argument("--language",  default="ko",          help="언어 코드 (기본: ko 한국어)")
    parser.add_argument("--timestamp", action="store_true",   help="타임스탬프 포함 출력 (예: [03:21])")
    args = parser.parse_args()

    # 오디오 파일 목록 수집
    files = sorted([
        f for f in Path(args.input).iterdir()
        if f.suffix.lower() in SUPPORTED_EXT
    ])

    if not files:
        print(f"❌ '{args.input}' 폴더에서 오디오 파일을 찾을 수 없습니다.")
        print(f"   지원 형식: {', '.join(SUPPORTED_EXT)}")
        return

    print(f"🎙️  참여자 {len(files)}명 발견:")
    for f in files:
        print(f"   - {get_speaker_name(f.name)} ({f.name})")

    # Whisper 모델 로드 (한 번만)
    print(f"\n🤖 Whisper 모델 로딩 중: {args.model}")
    model = whisper.load_model(args.model)

    # 참여자별 변환
    all_segments = []
    for f in files:
        speaker = get_speaker_name(f.name)
        segments = transcribe_speaker(model, f, speaker, args.language)
        all_segments.extend(segments)
        print(f"  ✅ [{speaker}] {len(segments)}개 발화 완료")

    # 저장 및 미리보기
    sorted_segments = save_transcript(all_segments, args.output, args.timestamp)

    print("\n✨ 미리보기 (앞 5줄):")
    print("─" * 40)
    for seg in sorted_segments[:5]:
        if args.timestamp:
            print(f"[{format_time(seg['start'])}] [{seg['speaker']}] {seg['text']}")
        else:
            print(f"[{seg['speaker']}] {seg['text']}")
    if len(sorted_segments) > 5:
        print(f"... 외 {len(sorted_segments) - 5}개")
    print("─" * 40)
    print("\n📋 텍스트 파일을 Claude에게 붙여넣어 회의록 요약을 요청하세요!")


if __name__ == "__main__":
    main()
