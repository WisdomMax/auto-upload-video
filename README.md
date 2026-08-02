# 🚀 엄마아빠 패션다이어리 (MomDad Fashion Diary)

> **인스타그램(Reels)과 유튜브(Shorts) 댓글을 단 3초 만에 1:1 직행 구매 매출로 전환하는 100% 자체 구축(Self-Hosted) 무인 마케팅 시스템**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Meta Graph API](https://img.shields.io/badge/Meta%20Graph%20API-v19.0-blue.svg)](https://developers.facebook.com/)
[![YouTube Data API](https://img.shields.io/badge/YouTube%20Data%20API-v3-red.svg)](https://developers.google.com/youtube/v3)
[![Self Hosted](https://img.shields.io/badge/100%25-Self--Hosted-orange.svg)]()

---

## 🌐 Global Languages (다국어 안내)
- 🇰🇷 [한국어 (Korean)](#-왜-이-시스템을-소유해야-하는가-why-self-host)
- 🇺🇸 [English Overview](#-english-overview)
- 🇨🇳 [中文 概述](#-中文-概述)
- 🇪🇸 [Español Resumen](#-español-resumen)

---

## 💡 왜 이 시스템을 소유해야 하는가? (Why Self-Host?)

매달 나가는 수백만 원의 비싼 해외 SaaS 구독료(ManyChat 등) 없이, **본 오픈소스 소스코드를 활용하여 자사 서버/맥미니에 100% 영구 무료 무인 마케팅 인프라를 직접 구축**하세요.

- 💰 **월 구독료 0원 (Zero Monthly Fees)**: 외부 플랫폼 결제 없이 100% 영구 무료 자체 소유
- ⚡ **3초 실시간 반응**: 구매 의사가 가장 뜨거운 순간 1:1 DM 및 대댓글로 매출 전환
- 🔒 **고객 데이터 100% 보존**: 외부 툴 유출 없이 자사 데이터베이스에 안전 보존

---

## 🏗️ 시스템 구조도 (Architecture)

```mermaid
flowchart TD
    subgraph SNS["📱 SNS 멀티 플랫폼"]
        IG[Instagram Reels]
        YT[YouTube Shorts]
    end

    subgraph Engine["⚡ 백엔드 자동화 엔진 (FastAPI + Python)"]
        WH[실시간 웹훅 & 5분 주기 스캐너]
        NLP[구매 의도 및 상품 코드 자동 분석]
        API_IG[Meta Graph API v19.0 Client]
        API_YT[YouTube Data API v3 & Studio Daemon]
    end

    subgraph Safety["🛡️ 안심 가디언 레이어"]
        QH[Quiet Hours: 23시~08시 야간 중지]
        LMT[1일 80건 안전 쿼터 보장]
    end

    subgraph Action["🛍️ 100% 자동 실행 결과"]
        DM[Instagram 4단계 PURE URL 카드 DM]
        REPLY[YouTube 3줄 접힘방지 대댓글]
        HEART[YouTube Studio 자동 하트❤️ / 좋아요👍]
    end

    IG --> WH
    YT --> WH
    WH --> NLP
    NLP --> Safety
    Safety --> API_IG
    Safety --> API_YT

    API_IG --> DM
    API_YT --> REPLY
    API_YT --> HEART
```

---

## 💥 기존 방식 vs 해결책 (Pain Points & Solutions)

| 구분 | ❌ 수동 운용 & 기존 SaaS 툴 | 🟢 엄마아빠 패션다이어리 엔진 |
| :--- | :--- | :--- |
| **비용 & 소유권** | 매달 결제되는 비싼 구독료 (ManyChat 등) | 💻 **본 소스코드로 자사 서버에 100% 영구 무료 구축** |
| **응답 속도** | 평균 3시간~12시간 (고객 이미 이탈) | ⚡ **단 3초 만에 24시간 실시간 1:1 직행 발송** |
| **인스타그램 DM** | 한글과 URL이 섞여 클릭 불가능한 깨진 링크 | 💌 **4단계 독립 PURE URL 카드 (100% 예쁜 미리보기)** |
| **DM 전송률** | 브라우저 타자 입력 방식으로 수신 누락 발생 | 📩 **Meta 오피셜 Graph API (200 OK) 수신함 100% 직행** |
| **유튜브 대댓글** | 5~6줄 장문으로 `...자세히 보기` 접혀 시선 차단 | 📱 **접힘 0%! 한눈에 들어오는 3줄 직관 쇼핑몰 안내 (`6080.piella.shop`)** |
| **팬덤 관리** | 일일이 하트 누르기 불가능 | ❤️ **채널주인 빨간 하트(❤️) + 좋아요(👍) 100% 자동 클릭** |
| **계정 안전성** | 야간 발송으로 스팸 신고 & 계정 정지 위험 | 🛡️ **야간 안심 시간대 (23시~08시 중지) & 1일 80건 안전 쿼터** |
| **구동 편의성** | 복잡한 설정 및 여러 터미널 띄우기 | 🚀 **`npm run dev` 1클릭 백엔드+터널+웹훅 자동 가동** |

---

## 🖼️ 실측 가동 증명 갤러리 (Live Proof)

### 1. 인스타그램 4단계 PURE URL 카드 DM 전송 증명
> 한글과 링크가 섞여 깨지는 현상을 완전 차단하고, 4개의 독립 말풍선으로 클릭 가능한 카드를 즉시 생성합니다.

![Instagram DM Proof](docs/images/instagram_dm_proof.png)

---

### 2. 유튜브 스튜디오 채널주인 빨간 하트(❤️) + 좋아요(👍) 자동 클릭 증명
> 신규 댓글이 달릴 때마다 채널주인 빨간 하트와 좋아요를 100% 자동 클릭하여 어머님 휴대폰으로 감동 푸시 알림을 발송합니다.

![YouTube Heart Proof](docs/images/youtube_heart_proof.png)

---

## 🌍 Global Translations (펼쳐보기 / Expand)

<details>
<summary><b>🇺🇸 English Overview (Click to expand)</b></summary>

<br/>

### 📌 Project Concept & Business Goals
**MomDad Fashion Diary** is an autonomous multi-platform SNS engagement & e-commerce marketing orchestration system designed for Instagram Reels and YouTube Shorts. Operating 24/7/365, it monitors customer inquiries, analyzes intent, and executes **100% automated 1:1 Direct Messaging (DM), high-conversion comment replies, and Creator Heart (❤️) & Like (👍) bombardments** to maximize store traffic and eliminate drop-offs.

### 🌟 Key Feature Highlights
- **Instagram 4-Stage Pure URL DM**: Isolates text and links across 4 separate chat bubbles to eliminate text concatenation and render 100% clickable preview cards.
- **Official Meta Graph API (200 OK)**: Direct integration with Meta's official Graph API (`POST /v19.0/me/messages`) ensuring guaranteed delivery to recipient inboxes.
- **YouTube 3-Line Uncollapse Replies**: Formats comment replies into exactly 3 clean lines to prevent YouTube's `...Read More` collapse while pointing users to `6080.piella.shop`.
- **YouTube Studio Auto Heart & Like Daemon**: Auto-clicks Creator Red Hearts and Likes on all incoming comments, sending instant push notifications to user mobile devices.
- **Quiet Hours & Quota Guard**: Automatically pauses DMs overnight (23:00~08:00) to prevent night spam reports, capping daily volume at 80 DMs/day.
- **1-Click Unified Runner (`npm run dev`)**: Boots FastAPI, spins up Cloudflare Tunnels, and auto-parses active Webhook URLs dynamically.

</details>

<details>
<summary><b>🇨🇳 中文 概述 (点击展开)</b></summary>

<br/>

### 📌 项目概述与商业目标
**爸爸妈妈时尚日记 (MomDad Fashion Diary)** 是一款专为 Instagram Reels 和 YouTube Shorts 打造的全自动社交媒体营销与客服自动化系统。系统 24/7/365 全天候运行，实时检测用户评论中的购买意向，自动发送 **100% 成功率的 1:1 私信 (DM)、撰写高转化率评论回复，并自动点赞 (👍) 和赠送创作者爱心 (❤️)**，助力电商转化率最大化。

### 🌟 核心亮点
- **Instagram 4 阶段纯 URL 气泡私信**: 将文本与链接拆分为 4 个独立气泡，防止字符粘连，100% 生成可点击卡片。
- **Meta 官方 API 直连**: 通过 Meta 官方 API 直投收件箱，彻底告别浏览器模拟发件的漏发率。
- **YouTube 3 行极简评论回复 (`6080.piella.shop`)**: 精准控制在 3 行以内，避免被 YouTube 折叠（`...展开全文`）。
- **YouTube Studio 自动红心与点赞**: 自动为评论点赞并赠送创作者红心，触发手机端实时推送通知。
- **夜间免打扰 (Quiet Hours: 23:00~08:00) 与配额保护**: 深夜自动暂停发送，设置每日 80 条安全上限。
- **一键整合启动 (`npm run dev`)**: 单条命令启动后端、Cloudflare 隧道并自动解析 Webhook 网址。

</details>

<details>
<summary><b>🇪🇸 Español Resumen (Haz clic para desplegar)</b></summary>

<br/>

### 📌 Visión General del Proyecto
**MomDad Fashion Diary** es un sistema autónomo de orquestación de marketing y automatización multi-plataforma diseñado para Instagram Reels y YouTube Shorts. Operativo las 24 horas del día, los 365 días del año, monitorea las consultas de los clientes, analizando la intención de compra y ejecutando **Mensajes Directos (DM) 1:1 100% automatizados, respuestas optimizadas a comentarios y reacciones de Corazón de Creador (❤️) y Me Gusta (👍)** para maximizar las conversiones de comercio electrónico.

</details>

---

## 🛠️ 빠른 시작 (Quick Start Guide)

```bash
# 1. 저장소 클론 (Clone Repository)
git clone https://github.com/WisdomMax/auto-upload-video.git
cd "20260605 momdad fashion diary"

# 2. 의존성 패키지 설치 (Install Dependencies)
npm install
pip3 install -r requirements.txt

# 3. 환경변수 (.env) 설정 후 1클릭 가동 (Launch Server)
npm run dev
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
