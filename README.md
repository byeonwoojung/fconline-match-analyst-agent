# fconline-match-analyst-agent

FC Online 경기 분석 RAG 에이전트

> 🚧 **구현 중**

## 프로젝트 개요

내 FC Online 경기 데이터와 커뮤니티 글을 분석하여 질문에 답변하는 RAG 에이전트입니다.

**예시 질문:**
- "내가 골 많이 먹힌 장면에 대해 말해줘"
- "후반 막판에 실점이 많은데 왜 그런지 분석해줘"
- "요즘 메타가 뭐야?"

## 폴더 구조

```
fconline-match-analyst-agent/
├── backend/                    # 데이터 수집
│   ├── api-fconline/           # Nexon Open API 크롤러
│   └── crawler-fconline-community/  # 커뮤니티 크롤러
│
├── agent/                      # RAG 에이전트 코어
│   ├── config.py               # LLM, VectorDB 설정
│   ├── embeddings/             # 임베딩 모듈
│   │   ├── match_embedder.py   # 경기 데이터 → 텍스트 → 임베딩
│   │   └── community_embedder.py  # 커뮤니티 글 임베딩
│   ├── vectorstore/            # 벡터DB
│   │   ├── indexer.py          # ChromaDB 인덱싱
│   │   └── retriever.py        # 유사 문서 검색
│   ├── chains/                 # LangChain 체인
│   │   ├── match_analyzer.py   # 경기 분석 체인
│   │   ├── community_analyzer.py  # 커뮤니티 분석 체인
│   │   └── rag_chain.py        # 통합 RAG 체인
│   └── prompts/                # 프롬프트 템플릿
│
├── app/                        # Streamlit UI
│   ├── main.py                 # 엔트리포인트
│   ├── pages/                  # 페이지
│   │   ├── 1_chat.py           # 채팅 (RAG 에이전트)
│   │   ├── 2_match_history.py  # 경기 기록 조회
│   │   └── 3_community.py      # 커뮤니티 트렌드
│   ├── components/             # UI 컴포넌트
│   └── utils/                  # 유틸리티
│
├── data/                       # 데이터 저장소
│   └── vectordb/               # 벡터DB 파일
│
├── scripts/                    # 실행 스크립트
│   ├── index_matches.py        # 경기 데이터 인덱싱
│   └── index_community.py      # 커뮤니티 데이터 인덱싱
│
├── .env                        # API 키 (OpenAI 등)
└── requirements.txt            # Python 의존성
```

## 데이터 수집

### API 데이터
- **출처**: [Nexon Open API - FC Online](https://openapi.nexon.com/ko/game/fconline/)
- **수집 항목**: 유저 OUID, 매치 기록, 선수/시즌/스펠 메타데이터

### 커뮤니티 데이터
- **출처**: [FC Online 자유게시판](https://fconline.nexon.com/community/free)
- **수집 항목**: 게시글 제목, 내용, 스쿼드 메이커 정보

## 기술 스택

- **Frontend**: Streamlit
- **RAG Framework**: LangChain
- **Vector DB**: ChromaDB
- **Embedding**: OpenAI text-embedding-3-small
- **LLM**: GPT-4o / Claude

## 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 설정

# 3. 데이터 인덱싱
python scripts/index_matches.py
python scripts/index_community.py

# 4. Streamlit 앱 실행
streamlit run app/main.py
```