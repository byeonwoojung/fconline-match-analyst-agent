"""
Bronze 데이터 동기화
- 소스 데이터를 data/bronze/로 복사
- 모든 날짜 폴더의 데이터를 통합
- 중복 제거 후 정렬
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

from config import (
    SOURCE_DATA,
    BRONZE_DATA,
    OUTPUT_FILES,
    META_FILES,
)


def sync_meta():
    """
    메타데이터 동기화
    - 가장 최신 날짜 폴더의 메타데이터를 data/bronze/meta/로 복사
    """
    source_meta = SOURCE_DATA["meta"]
    target_meta = BRONZE_DATA["meta"]

    # 날짜 폴더 찾기 (YY-MM-DD 형식)
    date_folders = sorted(
        [d for d in source_meta.iterdir() if d.is_dir() and d.name[0].isdigit()],
        reverse=True,  # 최신순
    )

    if not date_folders:
        print("❌ 메타데이터 날짜 폴더가 없습니다.")
        return

    latest_folder = date_folders[0]
    print(f"📁 메타데이터 소스: {latest_folder.name}")

    # 메타데이터 파일 복사
    target_meta.mkdir(parents=True, exist_ok=True)

    for meta_file in META_FILES:
        src = latest_folder / meta_file
        dst = target_meta / meta_file

        if src.exists():
            shutil.copy2(src, dst)
            print(f"  ✅ {meta_file} 복사 완료")
        else:
            print(f"  ⚠️ {meta_file} 없음")


def sync_match_detail():
    """
    matchDetail 동기화
    - 모든 날짜 폴더의 JSONL 파일 통합
    - matchId 기준 중복 제거
    - matchDate 내림차순 정렬
    """
    source_dir = SOURCE_DATA["matchDetail"]
    target_dir = BRONZE_DATA["matchDetail"]
    output_file = target_dir / OUTPUT_FILES["matchDetail"]

    target_dir.mkdir(parents=True, exist_ok=True)

    # 모든 날짜 폴더에서 데이터 수집
    all_matches = {}  # matchId -> match_data

    date_folders = [
        d for d in source_dir.iterdir() if d.is_dir() and d.name[0].isdigit()
    ]

    for date_folder in date_folders:
        for jsonl_file in date_folder.glob("*.jsonl"):
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        match = json.loads(line)
                        match_id = match.get("matchId")
                        if match_id and match_id not in all_matches:
                            all_matches[match_id] = match
                    except json.JSONDecodeError:
                        continue

    # matchDate 내림차순 정렬
    sorted_matches = sorted(
        all_matches.values(), key=lambda x: x.get("matchDate", ""), reverse=True
    )

    # JSONL로 저장
    with open(output_file, "w", encoding="utf-8") as f:
        for match in sorted_matches:
            f.write(json.dumps(match, ensure_ascii=False) + "\n")

    print(f"✅ matchDetail 동기화 완료: {len(sorted_matches)}개 경기")


def sync_community():
    """
    커뮤니티 데이터 동기화
    - 모든 날짜 폴더의 posts.jsonl 통합
    - article_no 기준 중복 제거
    - article_no 내림차순 정렬
    """
    source_dir = SOURCE_DATA["community"]
    target_dir = BRONZE_DATA["community"]
    output_file = target_dir / OUTPUT_FILES["community"]

    target_dir.mkdir(parents=True, exist_ok=True)

    # 모든 날짜 폴더에서 데이터 수집
    all_posts = {}  # article_no -> post_data

    date_folders = [
        d for d in source_dir.iterdir() if d.is_dir() and d.name[0].isdigit()
    ]

    for date_folder in date_folders:
        posts_file = date_folder / "posts.jsonl"
        if not posts_file.exists():
            continue

        with open(posts_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    post = json.loads(line)
                    article_no = post.get("article_no")
                    if article_no and article_no not in all_posts:
                        all_posts[article_no] = post
                except json.JSONDecodeError:
                    continue

    # article_no 내림차순 정렬
    sorted_posts = sorted(
        all_posts.values(), key=lambda x: x.get("article_no", 0), reverse=True
    )

    # JSONL로 저장
    with open(output_file, "w", encoding="utf-8") as f:
        for post in sorted_posts:
            f.write(json.dumps(post, ensure_ascii=False) + "\n")

    print(f"✅ community 동기화 완료: {len(sorted_posts)}개 게시글")


def sync_server_maintenance():
    """
    서버 점검 공지 동기화
    - 모든 날짜 폴더의 maintenance.jsonl 통합
    - article_no 기준 중복 제거
    - article_no 내림차순 정렬
    """
    source_dir = SOURCE_DATA["server-maintenance"]
    target_dir = BRONZE_DATA["server-maintenance"]
    output_file = target_dir / OUTPUT_FILES["server-maintenance"]

    target_dir.mkdir(parents=True, exist_ok=True)

    # 모든 날짜 폴더에서 데이터 수집
    all_notices = {}  # article_no -> notice_data

    date_folders = [
        d for d in source_dir.iterdir() if d.is_dir() and d.name[0].isdigit()
    ]

    for date_folder in date_folders:
        maintenance_file = date_folder / "maintenance.jsonl"
        if not maintenance_file.exists():
            continue

        with open(maintenance_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    notice = json.loads(line)
                    article_no = notice.get("article_no")
                    if article_no and article_no not in all_notices:
                        all_notices[article_no] = notice
                except json.JSONDecodeError:
                    continue

    # article_no 내림차순 정렬
    sorted_notices = sorted(
        all_notices.values(), key=lambda x: x.get("article_no", 0), reverse=True
    )

    # JSONL로 저장
    with open(output_file, "w", encoding="utf-8") as f:
        for notice in sorted_notices:
            f.write(json.dumps(notice, ensure_ascii=False) + "\n")

    print(f"✅ server-maintenance 동기화 완료: {len(sorted_notices)}개 공지")


def sync_all():
    """모든 Bronze 데이터 동기화"""
    print("🚀 Bronze 데이터 동기화 시작\n")

    print("=" * 50)
    print("📦 메타데이터 동기화")
    print("=" * 50)
    sync_meta()

    print("\n" + "=" * 50)
    print("📦 matchDetail 동기화")
    print("=" * 50)
    sync_match_detail()

    print("\n" + "=" * 50)
    print("📦 community 동기화")
    print("=" * 50)
    sync_community()

    print("\n" + "=" * 50)
    print("📦 server-maintenance 동기화")
    print("=" * 50)
    sync_server_maintenance()

    print("\n🎉 Bronze 데이터 동기화 완료!")


if __name__ == "__main__":
    sync_all()
