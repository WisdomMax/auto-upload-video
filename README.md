# 📱 Momdad Fashion Diary - SNS Auto Upload Dashboard

숏폼(유튜브 쇼츠, 틱톡, 인스타 릴스) 영상의 **일괄 자동 업로드** 및 **상품/댓글 관리**를 위한 로컬 올인원 마케팅 대시보드입니다.

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📦 상품 등록 | 쿠팡 링크, 영상, 설명 등록 |
| 🤖 AI 홍보 문구 생성 | Gemini API로 유튜브/틱톡/릴스용 캡션 자동 작성 |
| ☁️ R2 자동 업로드 | Cloudflare R2 버킷에 영상 자동 업로드 |
| 🚀 3사 일괄 배포 | YouTube Shorts, TikTok, Instagram Reels 동시 배포 (Buffer API) |
| 💬 유튜브 댓글 모니터링 | 채널 실시간 댓글 확인 + 네이버 검색 유도 답변 원클릭 복사 |
| 📊 인기 제목 벤치마킹 | 키워드 기반 인기 영상 분석, 기여도(🔥 그레이트/👍 굿) 배지 표시 |

## 🛠️ 기술 스택

- **Backend**: Python 3 + FastAPI + SQLite
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **APIs**: YouTube Data API v3, Buffer GraphQL API, Cloudflare R2, ManyChat, Gemini AI

## 🚀 시작하기

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
```
`.env` 파일을 열어 각 API 키를 입력합니다.

### 3. 서버 실행
```bash
python3 main.py
```

브라우저에서 `http://localhost:18888` 접속 ✅

## 📁 프로젝트 구조
```
.
├── main.py              # FastAPI 백엔드 서버
├── database.py          # SQLite DB 관리
├── requirements.txt     # Python 패키지 목록
├── .env.example         # 환경 변수 설정 예시 (실제 키는 .env에 별도 저장)
├── templates/
│   └── index.html       # 대시보드 UI
└── static/
    ├── app.js           # 프론트엔드 JS 로직
    └── index.css        # 스타일시트
```

## 🔒 보안 주의사항

> `.env` 파일에는 실제 API 키가 저장됩니다. **절대 GitHub에 업로드하지 마세요.**
> `.gitignore`를 통해 자동으로 커밋 제외 처리되어 있습니다.

## 📋 필요한 API 키

| 키 | 용도 | 필수 여부 |
|----|------|----------|
| `BUFFER_ACCESS_TOKEN` | SNS 3사 자동 배포 | ✅ 필수 |
| `CLOUDFLARE_ACCOUNT_ID` | R2 영상 업로드 | ✅ 필수 |
| `CLOUDFLARE_API_TOKEN` | R2 영상 업로드 | ✅ 필수 |
| `CLOUDFLARE_PUBLIC_URL` | R2 퍼블릭 URL | ✅ 필수 |
| `YOUTUBE_API_KEY` | 댓글/트렌드 분석 | ⭐ 권장 |
| `YOUTUBE_CHANNEL_ID` | 채널 댓글 수집 | ⭐ 권장 |
| `GEMINI_API_KEY` | AI 홍보 문구 생성 | 선택 |
| `MANYCHAT_API_TOKEN` | DM 자동화 연동 | 선택 |
| `COUPANG_ACCESS_KEY` | 단축 링크 발급 | 선택 |
| `COUPANG_SECRET_KEY` | 단축 링크 발급 | 선택 |
