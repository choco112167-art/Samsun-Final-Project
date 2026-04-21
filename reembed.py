"""
reembed.py — 기존 기사 재임베딩 스크립트

기존에 translation만으로 임베딩된 기사들을
title + translation 합산 방식으로 다시 임베딩해서 DB를 업데이트합니다.

실행 방법:
    python reembed.py            # 전체 재임베딩
    python reembed.py --dry-run  # 실제 저장 없이 테스트만
    python reembed.py --limit 50 # 50개만 처리 (테스트용)
"""

import argparse
import os
import time

from dotenv import load_dotenv
from supabase import create_client

from backend.embedder import make_embedding

load_dotenv()

sb = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_KEY", ""),
)

PAGE_SIZE = 50  # 한 번에 가져올 기사 수 (Ollama 메모리 고려)


def reembed_all(dry_run: bool = False, limit: int | None = None):
    print(f"{'[DRY-RUN] ' if dry_run else ''}재임베딩 시작\n")

    total_processed = 0
    total_skipped   = 0
    offset          = 0

    while True:
        # 페이지 단위로 기사 가져오기
        # title = 한국어 제목, translation = 한국어 번역 전문
        rows = (
            sb.table("articles")
            .select("url_hash, title, translation")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
        )

        if not rows:
            break  # 더 이상 기사 없음

        for row in rows:
            url_hash    = row["url_hash"]
            title       = row.get("title") or ""
            translation = row.get("translation") or ""

            # translation이 없으면 임베딩 품질이 낮으므로 건너뜀
            if not translation.strip():
                print(f"  SKIP {url_hash[:8]}... (translation 없음)")
                total_skipped += 1
                continue

            # 한국어 제목 + 한국어 번역 합산 임베딩
            combined   = f"{title}\n{translation}"
            new_vector = make_embedding(combined)

            if dry_run:
                print(f"  [DRY] {url_hash[:8]}... | {title[:40]!r} | 벡터 앞 3개={new_vector[:3]}")
            else:
                sb.table("articles").update(
                    {"embedding": new_vector}
                ).eq("url_hash", url_hash).execute()
                print(f"  OK  {url_hash[:8]}... | {title[:40]!r}")

            total_processed += 1

            # limit 옵션 처리
            if limit and total_processed >= limit:
                print(f"\n--limit {limit} 도달, 중단")
                _print_summary(total_processed, total_skipped, dry_run)
                return

            # Ollama 과부하 방지 (기사 사이 짧은 대기)
            time.sleep(0.1)

        offset += PAGE_SIZE
        print(f"  --- {offset}개 완료 ---\n")

    _print_summary(total_processed, total_skipped, dry_run)


def _print_summary(processed: int, skipped: int, dry_run: bool):
    print("\n" + "=" * 40)
    print(f"{'[DRY-RUN] ' if dry_run else ''}완료!")
    print(f"  재임베딩: {processed}개")
    print(f"  건너뜀:   {skipped}개 (translation 없음)")
    print("=" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기사 재임베딩 스크립트")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장 없이 테스트")
    parser.add_argument("--limit",   type=int,            help="처리할 최대 기사 수")
    args = parser.parse_args()

    reembed_all(dry_run=args.dry_run, limit=args.limit)
