"""
generate_dummy.py — AI/Tech 특화 더미 데이터 생성 & 업로드

카테고리: AI 연구 / AI 스타트업 / 테크전반 / 윤리-정책 / 반도체
실행:
    cd /Users/aiagent/Desktop/test/ss_Test
    python generate_dummy.py
"""

import os
import hashlib
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("backend/.env")

sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

from backend.embedder import make_embedding


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()

def fact_label(score: float) -> str:
    if score >= 0.8: return "FACT"
    if score < 0.4:  return "RUMOR"
    return "UNVERIFIED"


# ════════════════════════════════════════════════════════
# ARTICLES
# 카테고리 5종 × 각 5~6개 = 총 27개
# source 6종 / source_type 2종 / country 5종
# fact_label 3종 / credibility 전 구간
# ════════════════════════════════════════════════════════

RAW = [

    # ── AI 연구 (6개) ─────────────────────────────────────────
    {
        "url": "https://deepmind.google/research/gemini-ultra-2",
        "title": "Google DeepMind Releases Gemini Ultra 2.0 with 2M Token Context",
        "source": "MIT Technology Review", "source_type": "media",
        "category": "AI 연구", "country": "US",
        "keywords": ["Gemini", "멀티모달", "LLM", "DeepMind", "컨텍스트창"],
        "published_at": days_ago(1),
        "credibility_score": 0.93,
        "content": "Google DeepMind announced Gemini Ultra 2.0, achieving top scores on MMLU, HumanEval, and a new multimodal reasoning benchmark. The model supports a 2 million token context window and introduces native video understanding capabilities.",
        "translation": "구글 딥마인드가 MMLU·HumanEval 등 주요 벤치마크 1위를 기록한 제미나이 울트라 2.0을 공개했다. 200만 토큰 컨텍스트와 네이티브 영상 이해 기능을 지원한다.",
        "summary_formal": "구글 딥마인드가 200만 토큰 컨텍스트를 지원하는 제미나이 울트라 2.0을 공개하며 주요 벤치마크에서 최고 성능을 기록했다.",
        "summary_casual": "구글이 제미나이 2.0 냈어! 200만 토큰 컨텍스트에 영상도 이해하는 진짜 멀티모달이야.",
    },
    {
        "url": "https://arxiv.org/abs/2026.llama4-scout",
        "title": "Meta Releases Llama 4 Scout: 17B MoE Model Beats GPT-4o on Benchmarks",
        "source": "The Verge", "source_type": "media",
        "category": "AI 연구", "country": "US",
        "keywords": ["Llama 4", "MoE", "오픈소스", "Meta", "벤치마크"],
        "published_at": days_ago(3),
        "credibility_score": 0.91,
        "content": "Meta's Llama 4 Scout uses a Mixture-of-Experts architecture with 17 billion active parameters, outperforming GPT-4o on math and coding benchmarks while remaining open-source under a permissive license.",
        "translation": "메타의 라마 4 스카우트는 MoE 아키텍처로 170억 개의 활성 파라미터를 사용하며, 수학·코딩 벤치마크에서 GPT-4o를 뛰어넘으면서도 허용적 라이선스로 오픈소스 공개됐다.",
        "summary_formal": "메타가 MoE 구조의 라마 4 스카우트를 오픈소스로 공개하며 GPT-4o 대비 우수한 수학·코딩 성능을 달성했다.",
        "summary_casual": "메타 라마 4 나왔어! GPT-4o보다 수학·코딩 잘하는데 오픈소스야.",
    },
    {
        "url": "https://openai.com/research/o3-reasoning",
        "title": "OpenAI o3 Achieves 87% on ARC-AGI: Biggest Reasoning Leap Yet",
        "source": "MIT Technology Review", "source_type": "media",
        "category": "AI 연구", "country": "US",
        "keywords": ["o3", "추론", "ARC-AGI", "OpenAI", "AGI"],
        "published_at": days_ago(5),
        "credibility_score": 0.95,
        "content": "OpenAI's o3 model scored 87.5% on the ARC-AGI benchmark, a test designed to measure general reasoning that previous AI systems struggled with. The result reignited debates about the timeline to artificial general intelligence.",
        "translation": "오픈AI의 o3 모델이 일반 추론 능력을 측정하는 ARC-AGI 벤치마크에서 87.5%를 기록했다. 이 결과는 AGI 도달 시점 논쟁에 다시 불을 붙였다.",
        "summary_formal": "오픈AI o3가 ARC-AGI에서 87.5%를 달성하며 역대 최고의 AI 추론 성능을 보였고, AGI 논쟁이 재점화됐다.",
        "summary_casual": "오픈AI o3가 AGI 테스트에서 87% 찍었어. AGI 언제 오냐는 논쟁 다시 시작.",
    },
    {
        "url": "https://arxiv.org/abs/2026.chain-of-thought-scaling",
        "title": "Chain-of-Thought Scaling Laws: Longer Reasoning Chains Boost Accuracy Linearly",
        "source": "MIT Technology Review", "source_type": "media",
        "category": "AI 연구", "country": "US",
        "keywords": ["Chain-of-Thought", "스케일링 법칙", "추론", "LLM", "연구"],
        "published_at": days_ago(7),
        "credibility_score": 0.88,
        "content": "A new paper from Stanford shows that extending reasoning chain length in large language models improves accuracy linearly up to a point, with diminishing returns beyond 32 reasoning steps.",
        "translation": "스탠퍼드 연구팀이 LLM의 추론 체인 길이를 늘릴수록 정확도가 선형 향상되지만, 32단계 이상에서는 수확 체감이 나타남을 밝혔다.",
        "summary_formal": "스탠퍼드 연구에 따르면 LLM 추론 체인 확장은 32단계까지 정확도를 선형으로 향상시키나 이후 효과가 감소한다.",
        "summary_casual": "생각을 길게 할수록 AI가 똑똑해지는데, 32단계 넘으면 효과가 별로 없대.",
    },
    {
        "url": "https://anthropic.com/research/claude-4-release",
        "title": "Anthropic Releases Claude 4 Opus: Sets New Bar for Instruction Following",
        "source": "The Verge", "source_type": "media",
        "category": "AI 연구", "country": "US",
        "keywords": ["Claude 4", "Anthropic", "instruction following", "안전", "LLM"],
        "published_at": days_ago(2),
        "credibility_score": 0.92,
        "content": "Anthropic released Claude 4 Opus, claiming top performance on instruction-following and coding tasks. The model features improved Constitutional AI alignment and a 200K token context window.",
        "translation": "앤트로픽이 지시 수행·코딩 태스크에서 최고 성능을 주장하는 클로드 4 오퍼스를 출시했다. 향상된 Constitutional AI 정렬과 20만 토큰 컨텍스트를 제공한다.",
        "summary_formal": "앤트로픽이 Constitutional AI 정렬을 강화한 클로드 4 오퍼스를 출시하며 지시 수행·코딩 분야 최고 성능을 달성했다.",
        "summary_casual": "앤트로픽이 클로드 4 냈어! 지시 잘 따르고 코딩 잘한다고 하는데 20만 토큰 됨.",
    },
    {
        "url": "https://reddit.com/r/MachineLearning/llm-benchmark-debate",
        "title": "[토론] LLM 벤치마크는 이미 의미없다 — 오염된 테스트셋 문제",
        "source": "Reddit/ML", "source_type": "community",
        "category": "AI 연구", "country": "US",
        "keywords": ["벤치마크", "데이터오염", "LLM평가", "MMLU", "커뮤니티"],
        "published_at": days_ago(4),
        "credibility_score": 0.35,
        "content": "Community discussion alleges major LLM benchmarks like MMLU and HumanEval are contaminated with training data, making published scores unreliable. Several researchers posted evidence of test set leakage.",
        "translation": "커뮤니티에서 MMLU, HumanEval 등 주요 LLM 벤치마크가 학습 데이터에 오염돼 공개 점수를 신뢰할 수 없다는 논쟁이 벌어졌다. 일부 연구자들이 테스트셋 유출 증거를 제시했다.",
        "summary_formal": "LLM 벤치마크 데이터 오염 문제가 커뮤니티에서 제기되며 공개 성능 지표의 신뢰성 논란이 확산되고 있다.",
        "summary_casual": "LLM 성능 테스트가 다 조작됐다는 주장 나왔어. 학습 데이터에 시험 문제가 포함됐다는 증거도 있대.",
    },

    # ── AI 스타트업 (5개) ──────────────────────────────────────
    {
        "url": "https://techcrunch.com/openai-series-f-300b",
        "title": "OpenAI Raises $5B Series F at $300B Valuation Led by SoftBank",
        "source": "TechCrunch", "source_type": "media",
        "category": "AI 스타트업", "country": "US",
        "keywords": ["OpenAI", "투자", "밸류에이션", "소프트뱅크", "시리즈F"],
        "published_at": days_ago(2),
        "credibility_score": 0.94,
        "content": "OpenAI closed a $5 billion Series F funding round at a $300 billion valuation, led by SoftBank and Andreessen Horowitz. The company plans to invest in compute infrastructure and expand its enterprise sales team.",
        "translation": "오픈AI가 소프트뱅크와 a16z 주도로 3,000억 달러 기업가치에 50억 달러 시리즈F를 마감했다. 컴퓨팅 인프라 투자와 엔터프라이즈 영업팀 확대에 사용할 계획이다.",
        "summary_formal": "오픈AI가 3,000억 달러 밸류에이션으로 50억 달러 시리즈F를 유치하며 컴퓨팅 인프라 확장에 나선다.",
        "summary_casual": "오픈AI 기업가치 3000억 달러 됐어. 소프트뱅크가 50억 달러 넣었음.",
    },
    {
        "url": "https://techcrunch.com/mistral-funding-2b",
        "title": "Mistral AI Closes €2B Round, Valued at €10B Amid European AI Race",
        "source": "TechCrunch", "source_type": "media",
        "category": "AI 스타트업", "country": "EU",
        "keywords": ["Mistral", "유럽AI", "오픈소스", "투자", "스타트업"],
        "published_at": days_ago(6),
        "credibility_score": 0.90,
        "content": "French AI startup Mistral closed a €2 billion funding round valuing the company at €10 billion. Mistral has positioned itself as Europe's open-source AI champion, releasing models under permissive licenses.",
        "translation": "프랑스 AI 스타트업 미스트랄이 100억 유로 기업가치로 20억 유로 투자를 마감했다. 미스트랄은 유럽의 오픈소스 AI 대표주자로 자리매김하고 있다.",
        "summary_formal": "미스트랄 AI가 100억 유로 밸류에이션으로 20억 유로 투자를 유치하며 유럽 오픈소스 AI 경쟁을 주도하고 있다.",
        "summary_casual": "프랑스 AI 스타트업 미스트랄이 유럽판 오픈AI 됐어. 기업가치 10조 원 넘었음.",
    },
    {
        "url": "https://news.kr/startup/wrtn-korean-llm",
        "title": "뤼튼, 한국어 특화 70억 파라미터 LLM 오픈소스 공개",
        "source": "한겨레", "source_type": "media",
        "category": "AI 스타트업", "country": "KR",
        "keywords": ["뤼튼", "한국어LLM", "오픈소스", "AI스타트업", "파운데이션모델"],
        "published_at": days_ago(4),
        "credibility_score": 0.85,
        "content": "AI 스타트업 뤼튼이 한국어에 최적화된 70억 파라미터 규모 LLM을 오픈소스로 공개했다. 한국어 이해·생성 벤치마크에서 GPT-4o를 상회하는 성능을 기록했다.",
        "translation": "AI startup Wrtn released an open-source 7B parameter LLM optimized for Korean, outperforming GPT-4o on Korean language understanding and generation benchmarks.",
        "summary_formal": "뤼튼이 GPT-4o를 넘는 한국어 특화 LLM을 오픈소스로 공개하며 국내 AI 생태계 강화에 기여했다.",
        "summary_casual": "뤼튼이 한국어 전용 AI 모델 오픈소스로 풀었는데 GPT-4o보다 한국어 잘해.",
    },
    {
        "url": "https://techcrunch.com/perplexity-ai-series-d",
        "title": "Perplexity AI Hits $14B Valuation After $500M Series D",
        "source": "TechCrunch", "source_type": "media",
        "category": "AI 스타트업", "country": "US",
        "keywords": ["Perplexity", "AI검색", "밸류에이션", "투자", "Series D"],
        "published_at": days_ago(8),
        "credibility_score": 0.89,
        "content": "Perplexity AI raised $500 million in a Series D round, reaching a $14 billion valuation. The AI-powered search engine now handles over 100 million queries per day, challenging Google's search dominance.",
        "translation": "AI 검색 엔진 퍼플렉시티가 시리즈D로 5억 달러를 조달해 140억 달러 기업가치를 기록했다. 현재 일일 1억 건 이상의 검색을 처리하며 구글에 도전하고 있다.",
        "summary_formal": "퍼플렉시티 AI가 140억 달러 밸류에이션으로 5억 달러를 유치하며 AI 검색 시장에서 구글에 본격 도전한다.",
        "summary_casual": "퍼플렉시티 기업가치 14조 원 됐어. 하루에 1억 번 검색 처리하면서 구글 위협 중.",
    },
    {
        "url": "https://reddit.com/r/startups/ai-bubble-2026",
        "title": "[토론] AI 스타트업 버블인가? 수익 없이 밸류에이션만 폭등",
        "source": "Reddit/startups", "source_type": "community",
        "category": "AI 스타트업", "country": "US",
        "keywords": ["AI버블", "밸류에이션", "스타트업", "수익성", "투자"],
        "published_at": days_ago(3),
        "credibility_score": 0.30,
        "content": "Community debate erupts over whether AI startup valuations are sustainable. Critics point to OpenAI losing $5B annually despite $3B revenue, while bulls argue compute moats justify premium valuations.",
        "translation": "AI 스타트업 밸류에이션 지속 가능성에 대한 커뮤니티 논쟁이 격화됐다. 비판론자들은 오픈AI가 30억 달러 매출에도 50억 달러 적자라고 지적하고, 낙관론자들은 컴퓨팅 해자가 프리미엄을 정당화한다고 반박한다.",
        "summary_formal": "AI 스타트업 고밸류에이션의 지속 가능성을 둘러싼 논쟁이 확산되고 있으며, 수익성 부재가 핵심 쟁점이다.",
        "summary_casual": "AI 스타트업 버블이냐 아니냐 논쟁 중. 오픈AI도 매출 3배보다 적자가 더 크다는 말 있어.",
    },

    # ── 테크전반 (5개) ────────────────────────────────────────
    {
        "url": "https://theverge.com/apple-vision-pro-2",
        "title": "Apple Vision Pro 2 Unveiled: Lighter, Cheaper at $2,499",
        "source": "The Verge", "source_type": "media",
        "category": "테크전반", "country": "US",
        "keywords": ["Apple", "Vision Pro", "공간컴퓨팅", "AR", "하드웨어"],
        "published_at": days_ago(1),
        "credibility_score": 0.91,
        "content": "Apple announced Vision Pro 2 at $2,499, a 37% price cut from the original. The new headset is 40% lighter and features Apple's M4 chip with dedicated AI processing for real-time scene understanding.",
        "translation": "애플이 2,499달러로 37% 인하된 비전 프로 2를 발표했다. 새 헤드셋은 40% 가벼워졌고 실시간 장면 이해를 위한 전용 AI 처리 기능이 포함된 M4 칩을 탑재했다.",
        "summary_formal": "애플이 40% 경량화된 비전 프로 2를 2,499달러로 출시하며 공간 컴퓨팅 시장 대중화에 나섰다.",
        "summary_casual": "애플 비전 프로 2 나왔어! 가격 37% 내리고 훨씬 가벼워졌음.",
    },
    {
        "url": "https://news.kr/tech/samsung-galaxy-ai",
        "title": "삼성 갤럭시 S26, 온디바이스 AI로 실시간 통역 기능 탑재",
        "source": "연합뉴스", "source_type": "media",
        "category": "테크전반", "country": "KR",
        "keywords": ["삼성", "갤럭시S26", "온디바이스AI", "실시간통역", "스마트폰"],
        "published_at": days_ago(3),
        "credibility_score": 0.88,
        "content": "삼성전자가 갤럭시 S26에 온디바이스 AI 기반 실시간 통역 기능을 탑재한다고 발표했다. 인터넷 연결 없이 30개 언어 간 실시간 통역이 가능하며, Exynos 2500이 전용 NPU로 구동한다.",
        "translation": "Samsung announced Galaxy S26 will feature on-device AI real-time translation across 30 languages without internet, powered by Exynos 2500's dedicated NPU.",
        "summary_formal": "삼성이 갤럭시 S26에 온디바이스 AI 실시간 통역 기능을 탑재해 30개 언어를 인터넷 없이 지원한다.",
        "summary_casual": "갤럭시 S26 온디바이스 AI로 30개 국어 실시간 통역된대. 인터넷도 필요 없음.",
    },
    {
        "url": "https://theverge.com/microsoft-copilot-enterprise",
        "title": "Microsoft Copilot Enterprise Hits 10M Paid Users in 6 Months",
        "source": "The Verge", "source_type": "media",
        "category": "테크전반", "country": "US",
        "keywords": ["Microsoft", "Copilot", "기업AI", "생산성", "구독"],
        "published_at": days_ago(5),
        "credibility_score": 0.87,
        "content": "Microsoft's Copilot Enterprise surpassed 10 million paid subscribers six months after launch. The $30/month AI assistant is embedded in Microsoft 365 and can summarize meetings, draft emails, and generate presentations.",
        "translation": "마이크로소프트 코파일럿 엔터프라이즈가 출시 6개월 만에 유료 구독자 1,000만 명을 돌파했다. 월 30달러의 AI 어시스턴트는 회의 요약, 이메일 초안, 프레젠테이션 생성이 가능하다.",
        "summary_formal": "마이크로소프트 코파일럿 엔터프라이즈가 출시 6개월 만에 유료 구독자 1,000만 명을 달성하며 기업용 AI 시장을 선도하고 있다.",
        "summary_casual": "마이크로소프트 AI 어시스턴트 코파일럿, 6개월 만에 유료 구독자 1000만 명 돌파.",
    },
    {
        "url": "https://news.kr/tech/naver-hyperclova",
        "title": "네이버, HyperCLOVA X 2.0으로 기업용 AI 시장 공략",
        "source": "한겨레", "source_type": "media",
        "category": "테크전반", "country": "KR",
        "keywords": ["네이버", "HyperCLOVA", "기업AI", "클라우드", "한국어"],
        "published_at": days_ago(6),
        "credibility_score": 0.84,
        "content": "네이버가 HyperCLOVA X 2.0을 공개하며 기업용 AI 서비스 시장 공략을 본격화했다. 한국어 특화 성능과 네이버 클라우드 연동을 강점으로 내세운다.",
        "translation": "Naver unveiled HyperCLOVA X 2.0 targeting enterprise AI services, emphasizing Korean language capabilities and integration with Naver Cloud.",
        "summary_formal": "네이버가 한국어 특화 HyperCLOVA X 2.0으로 기업용 AI 시장에 본격 진입했다.",
        "summary_casual": "네이버도 기업용 AI 서비스 시작. 한국어 잘하고 네이버 클라우드랑 연동됨.",
    },
    {
        "url": "https://reddit.com/r/technology/apple-vision-hype",
        "title": "[후기] 비전 프로 2 써봤는데 여전히 킬러앱이 없다",
        "source": "Reddit/technology", "source_type": "community",
        "category": "테크전반", "country": "US",
        "keywords": ["비전프로2", "공간컴퓨팅", "킬러앱", "후기", "AR"],
        "published_at": days_ago(2),
        "credibility_score": 0.32,
        "content": "Early users of Apple Vision Pro 2 report the hardware improvements are real but the killer app problem persists. Most usage remains media consumption and video calls, with enterprise adoption still limited.",
        "translation": "비전 프로 2 얼리 어답터들은 하드웨어 개선은 실제라고 평가하지만 킬러앱 부재 문제는 여전하다고 지적한다. 사용처는 미디어 소비·화상통화 위주이며 기업 채택은 제한적이다.",
        "summary_formal": "비전 프로 2 사용자들은 하드웨어 개선을 인정하면서도 킬러앱 부재와 제한적인 기업 활용을 주요 문제로 지적하고 있다.",
        "summary_casual": "비전 프로 2 써봤는데 하드웨어는 좋아졌는데 결국 쓸 앱이 없어. 유튜브나 화상통화가 전부.",
    },

    # ── 윤리-정책 (5개) ───────────────────────────────────────
    {
        "url": "https://bbc.com/eu-ai-act-enforcement",
        "title": "EU AI Act First Fines: Two Firms Penalised for High-Risk AI Deployment",
        "source": "BBC코리아", "source_type": "media",
        "category": "윤리-정책", "country": "EU",
        "keywords": ["EU AI법", "규제", "벌금", "고위험AI", "거버넌스"],
        "published_at": days_ago(2),
        "credibility_score": 0.95,
        "content": "The EU issued its first enforcement actions under the AI Act, fining two companies for deploying high-risk AI systems without mandatory risk assessments. Penalties can reach up to 3% of global annual revenue.",
        "translation": "EU가 AI법에 따른 첫 제재로 의무 위험성 평가 없이 고위험 AI를 배포한 두 기업에 벌금을 부과했다. 벌금은 글로벌 연매출의 최대 3%에 달할 수 있다.",
        "summary_formal": "EU가 AI법 시행에 따른 첫 제재를 단행하며 고위험 AI 배포 기업 두 곳에 벌금을 부과했다.",
        "summary_casual": "EU AI법 실제로 집행 시작! 제대로 안 따른 회사들 벌금 맞았어.",
    },
    {
        "url": "https://reuters.com/g7-ai-safety-framework",
        "title": "G7 Agrees on Joint AI Safety Framework with Mandatory Pre-Deployment Testing",
        "source": "Reuters", "source_type": "media",
        "category": "윤리-정책", "country": "US",
        "keywords": ["G7", "AI안전", "국제협력", "사전테스트", "프런티어AI"],
        "published_at": days_ago(4),
        "credibility_score": 0.92,
        "content": "G7 leaders signed a joint AI safety framework requiring mandatory pre-deployment testing for frontier AI models. The framework also includes incident reporting obligations and red-teaming standards.",
        "translation": "G7 정상들이 프런티어 AI 모델의 의무 배포 전 테스트를 요구하는 공동 AI 안전 프레임워크에 서명했다. 사고 보고 의무와 레드팀 기준도 포함됐다.",
        "summary_formal": "G7이 프런티어 AI 사전 테스트 의무화와 사고 보고 체계를 담은 공동 AI 안전 프레임워크를 채택했다.",
        "summary_casual": "G7이 AI 안전 규칙 함께 만들기로 서명했어. 출시 전 테스트 의무화가 핵심.",
    },
    {
        "url": "https://news.kr/policy/ai-basic-law",
        "title": "국회, 인공지능 기본법 통과 — 개발사 안전 의무·이용자 보호 핵심",
        "source": "연합뉴스", "source_type": "media",
        "category": "윤리-정책", "country": "KR",
        "keywords": ["AI기본법", "국회", "입법", "AI규제", "안전의무"],
        "published_at": days_ago(1),
        "credibility_score": 0.93,
        "content": "국회가 인공지능 기본법을 재적 과반수 찬성으로 통과시켰다. 핵심 내용은 고위험 AI 개발사의 안전성 평가 의무화, 이용자 피해 구제 절차, AI 생성물 표시 의무다.",
        "translation": "South Korea's National Assembly passed the AI Basic Act. Key provisions include mandatory safety assessments for high-risk AI developers, user protection procedures, and disclosure requirements for AI-generated content.",
        "summary_formal": "한국 국회가 고위험 AI 안전 평가 의무와 AI 생성물 표시를 핵심으로 하는 AI 기본법을 통과시켰다.",
        "summary_casual": "드디어 한국도 AI법 통과! 위험한 AI 만들려면 안전 검사 필수, AI가 만든 콘텐츠도 표시해야 해.",
    },
    {
        "url": "https://techcrunch.com/deepfake-regulation-us",
        "title": "US Congress Passes Deepfake Accountability Act After Celebrity Scandal",
        "source": "TechCrunch", "source_type": "media",
        "category": "윤리-정책", "country": "US",
        "keywords": ["딥페이크", "규제", "미국의회", "AI윤리", "디지털성범죄"],
        "published_at": days_ago(9),
        "credibility_score": 0.90,
        "content": "The US Congress passed the Deepfake Accountability Act, making non-consensual deepfake creation a federal crime punishable by up to 10 years in prison. The bill passed with bipartisan support following high-profile celebrity incidents.",
        "translation": "미국 의회가 딥페이크 책임법을 통과시켜 비동의 딥페이크 생성을 최대 10년 징역에 처할 수 있는 연방 범죄로 규정했다. 유명인 사건 이후 초당적 지지로 통과됐다.",
        "summary_formal": "미국이 비동의 딥페이크 생성을 최대 10년 징역형으로 처벌하는 딥페이크 책임법을 제정했다.",
        "summary_casual": "미국이 딥페이크 연방법 만들었어. 동의 없이 딥페이크 만들면 최대 징역 10년.",
    },
    {
        "url": "https://reddit.com/r/privacy/ai-surveillance",
        "title": "[우려] AI 안면인식 공공장소 확산 — 우리는 항상 감시받는 중",
        "source": "Reddit/privacy", "source_type": "community",
        "category": "윤리-정책", "country": "KR",
        "keywords": ["안면인식", "감시", "프라이버시", "AI윤리", "빅브라더"],
        "published_at": days_ago(5),
        "credibility_score": 0.28,
        "content": "Community posts raise concerns about AI-powered facial recognition expanding to shopping malls and public transport. Some claim databases are being built without consent, though official sources have not confirmed.",
        "translation": "커뮤니티에서 AI 안면인식이 쇼핑몰·대중교통으로 확산되는 것에 우려의 목소리가 높아지고 있다. 일부는 동의 없이 데이터베이스가 구축되고 있다고 주장하지만 공식 확인은 없다.",
        "summary_formal": "AI 안면인식의 공공장소 확산에 대한 프라이버시 침해 우려가 커뮤니티에서 제기되고 있으나 공식 확인은 미흡하다.",
        "summary_casual": "마트·지하철에 AI 안면인식 카메라 퍼진다는 우려 나옴. 동의 없이 얼굴 DB 만든다는 주장도 있어.",
    },

    # ── 반도체 (6개) ──────────────────────────────────────────
    {
        "url": "https://reuters.com/tsmc-2nm-mass-production",
        "title": "TSMC Begins 2nm Mass Production, Apple and NVIDIA First Customers",
        "source": "Reuters", "source_type": "media",
        "category": "반도체", "country": "US",
        "keywords": ["TSMC", "2나노", "파운드리", "애플", "엔비디아"],
        "published_at": days_ago(2),
        "credibility_score": 0.94,
        "content": "TSMC officially began mass production of its 2nm process node. Apple's A20 chip for iPhone 18 and NVIDIA's next-generation Blackwell Ultra GPU are the first confirmed customers. Yield rates are reported above 60%.",
        "translation": "TSMC가 2나노 공정 양산을 공식 시작했다. 아이폰 18용 애플 A20 칩과 엔비디아 차세대 블랙웰 울트라 GPU가 첫 고객으로 확인됐다. 수율은 60% 이상으로 알려졌다.",
        "summary_formal": "TSMC가 2나노 양산에 돌입했으며, 애플과 엔비디아가 첫 고객으로 AI·모바일 반도체 경쟁이 본격화됐다.",
        "summary_casual": "TSMC 2나노 드디어 양산 시작! 애플 아이폰 18이랑 엔비디아 GPU가 처음 쓴대.",
    },
    {
        "url": "https://news.kr/semiconductor/samsung-hbm4",
        "title": "삼성전자 HBM4 양산 개시, SK하이닉스와 엔비디아 공급 경쟁",
        "source": "연합뉴스", "source_type": "media",
        "category": "반도체", "country": "KR",
        "keywords": ["삼성전자", "HBM4", "고대역폭메모리", "엔비디아", "AI반도체"],
        "published_at": days_ago(3),
        "credibility_score": 0.91,
        "content": "삼성전자가 HBM4 양산에 돌입하며 SK하이닉스와 엔비디아 납품 경쟁에 본격 뛰어들었다. HBM4는 HBM3E 대비 대역폭이 60% 향상됐으며, AI 학습 가속기 수요에 대응한다.",
        "translation": "Samsung Electronics began HBM4 mass production, entering direct competition with SK Hynix for NVIDIA supply. HBM4 offers 60% higher bandwidth than HBM3E to meet AI training accelerator demand.",
        "summary_formal": "삼성전자가 HBM4 양산을 시작하며 SK하이닉스와 엔비디아 AI 반도체 공급 경쟁에 합류했다.",
        "summary_casual": "삼성이 HBM4 양산 시작! SK하이닉스랑 엔비디아 납품 놓고 경쟁 시작됐어.",
    },
    {
        "url": "https://techcrunch.com/nvidia-blackwell-ultra-launch",
        "title": "NVIDIA Blackwell Ultra: 10x AI Inference vs H100, Ships Q3 2026",
        "source": "TechCrunch", "source_type": "media",
        "category": "반도체", "country": "US",
        "keywords": ["엔비디아", "블랙웰울트라", "AI가속기", "추론", "데이터센터"],
        "published_at": days_ago(1),
        "credibility_score": 0.92,
        "content": "NVIDIA announced Blackwell Ultra, claiming 10x AI inference performance versus H100 and 2x over the original Blackwell. The chip ships in Q3 2026 and features 288GB HBM4 memory with 8TB/s bandwidth.",
        "translation": "엔비디아가 H100 대비 AI 추론 성능 10배, 기존 블랙웰 대비 2배 향상된 블랙웰 울트라를 발표했다. 2026년 3분기 출하 예정이며 288GB HBM4와 8TB/s 대역폭을 갖췄다.",
        "summary_formal": "엔비디아 블랙웰 울트라가 H100 대비 10배 AI 추론 성능으로 2026년 3분기 출하를 앞두고 있다.",
        "summary_casual": "엔비디아 블랙웰 울트라 발표! H100보다 AI 추론 10배 빠르고 3분기에 나온대.",
    },
    {
        "url": "https://reuters.com/us-china-chip-export-ban",
        "title": "US Expands Semiconductor Export Controls Targeting Advanced AI Chips to China",
        "source": "Reuters", "source_type": "media",
        "category": "반도체", "country": "US",
        "keywords": ["수출통제", "미중반도체", "AI칩", "지정학", "무역규제"],
        "published_at": days_ago(4),
        "credibility_score": 0.93,
        "content": "The US expanded export controls to block shipment of AI chips with over 4.7 TFLOPS performance to China, closing loopholes exploited by previous regulations. The new rules also restrict chip design software exports.",
        "translation": "미국이 4.7 TFLOPS 이상 성능의 AI 칩의 중국 수출을 차단하도록 수출통제를 강화해 기존 규정의 허점을 막았다. 새 규정은 칩 설계 소프트웨어 수출도 제한한다.",
        "summary_formal": "미국이 AI 칩 수출통제를 강화해 고성능 칩 및 설계 소프트웨어의 중국 수출을 전면 차단했다.",
        "summary_casual": "미국이 중국에 AI 칩 수출 또 막았어. 이번엔 설계 소프트웨어도 같이 금지.",
    },
    {
        "url": "https://news.kr/semiconductor/sk-hynix-hbm-dominance",
        "title": "SK하이닉스, HBM3E 시장 점유율 70% 돌파 — 삼성·마이크론 추격",
        "source": "한겨레", "source_type": "media",
        "category": "반도체", "country": "KR",
        "keywords": ["SK하이닉스", "HBM3E", "점유율", "메모리", "AI반도체"],
        "published_at": days_ago(7),
        "credibility_score": 0.86,
        "content": "SK하이닉스가 HBM3E 시장에서 점유율 70%를 돌파한 것으로 집계됐다. 삼성전자와 마이크론이 추격에 나섰지만 기술 격차가 2~3분기 수준이라는 분석이 나온다.",
        "translation": "SK Hynix surpassed 70% market share in HBM3E, with Samsung and Micron trailing by an estimated 2-3 quarter technology gap.",
        "summary_formal": "SK하이닉스가 HBM3E 시장 점유율 70%를 달성했으며, 삼성·마이크론과의 기술 격차는 2~3분기 수준으로 분석된다.",
        "summary_casual": "SK하이닉스 HBM 시장 70% 점유! 삼성은 2~3분기 뒤처진 상태래.",
    },
    {
        "url": "https://reddit.com/r/hardware/nvidia-moat-discussion",
        "title": "[분석] 엔비디아 독점 언제까지? AMD·인텔·커스텀칩의 반격",
        "source": "Reddit/hardware", "source_type": "community",
        "category": "반도체", "country": "US",
        "keywords": ["엔비디아", "AMD", "커스텀칩", "AI반도체경쟁", "CUDA"],
        "published_at": days_ago(5),
        "credibility_score": 0.38,
        "content": "Community analysts debate NVIDIA's GPU monopoly durability. AMD's MI400 series, Google TPU v5, and Apple's M4 Ultra are cited as credible threats, but CUDA ecosystem lock-in remains NVIDIA's core moat.",
        "translation": "커뮤니티에서 엔비디아의 GPU 독점 지속 가능성을 논쟁한다. AMD MI400, 구글 TPU v5, 애플 M4 울트라가 실질적 경쟁자로 꼽히지만 CUDA 생태계 종속이 엔비디아의 핵심 해자로 남아있다.",
        "summary_formal": "엔비디아 AI 반도체 독점에 대한 경쟁사 위협이 증가하고 있으나, CUDA 생태계 의존성이 당분간 우위를 유지시킬 것으로 분석된다.",
        "summary_casual": "엔비디아 독점 깨질 수 있을까? AMD랑 구글이 도전 중인데 CUDA 때문에 쉽지 않다는 분석.",
    },
]


# ════════════════════════════════════════════════════════
# NEOLOGISMS (6개)
# ════════════════════════════════════════════════════════

NEOLOGISMS = [
    {
        "term": "Mixture-of-Experts",
        "explanation": "전체 파라미터 중 일부만 활성화해 추론하는 LLM 아키텍처. 동일 성능을 적은 연산 비용으로 달성한다.",
        "ko_suggestion": "전문가 혼합 아키텍처",
        "occurrence_count": 23, "confirmed": True,
    },
    {
        "term": "vibe coding",
        "explanation": "자연어로 AI에 지시해 코드를 직관적으로 생성하는 개발 방식. 전통적 코딩 지식 없이도 소프트웨어를 만들 수 있다.",
        "ko_suggestion": "감각 코딩",
        "occurrence_count": 11, "confirmed": False,
    },
    {
        "term": "agentic loop",
        "explanation": "AI 에이전트가 목표 달성을 위해 계획·실행·평가를 자율적으로 반복하는 순환 구조.",
        "ko_suggestion": "에이전트 루프",
        "occurrence_count": 7, "confirmed": False,
    },
    {
        "term": "HBM4",
        "explanation": "High Bandwidth Memory 4세대. AI 가속기에 사용되는 고대역폭 메모리의 최신 규격으로, HBM3E 대비 60% 이상 대역폭이 향상됐다.",
        "ko_suggestion": "고대역폭 메모리 4세대",
        "occurrence_count": 31, "confirmed": True,
    },
    {
        "term": "Constitutional AI",
        "explanation": "앤트로픽이 개발한 AI 정렬 기법. 명시적 원칙 집합으로 모델이 스스로 응답을 평가·수정하도록 훈련한다.",
        "ko_suggestion": "헌법적 AI 정렬",
        "occurrence_count": 14, "confirmed": True,
    },
    {
        "term": "token budget",
        "explanation": "LLM 추론 시 사용 가능한 최대 토큰 수를 사전에 할당하는 비용 관리 개념.",
        "ko_suggestion": "토큰 예산",
        "occurrence_count": 6, "confirmed": False,
    },
]


# ════════════════════════════════════════════════════════
# FACT_CHECKS (6개 — verdict 4종, checker 2종)
# ════════════════════════════════════════════════════════

FACT_CHECKS = [
    ("https://openai.com/research/o3-reasoning",
     "오픈AI o3가 ARC-AGI 벤치마크에서 87.5%를 기록했다",
     "FACT", 0.96, "ai"),
    ("https://reuters.com/tsmc-2nm-mass-production",
     "TSMC 2나노 공정 수율이 60% 이상이다",
     "FACT", 0.82, "human"),
    ("https://reddit.com/r/startups/ai-bubble-2026",
     "오픈AI의 연간 적자가 매출보다 크다",
     "UNVERIFIED", 0.61, "ai"),
    ("https://reddit.com/r/privacy/ai-surveillance",
     "공공장소 AI 안면인식 DB가 동의 없이 구축되고 있다",
     "RUMOR", 0.85, "ai"),
    ("https://reddit.com/r/hardware/nvidia-moat-discussion",
     "AMD MI400이 엔비디아 H100 대비 성능이 우월하다",
     "MISLEADING", 0.72, "human"),
    ("https://news.kr/policy/ai-basic-law",
     "AI 기본법이 국회 재적 과반수 찬성으로 통과됐다",
     "FACT", 0.97, "ai"),
]


# ════════════════════════════════════════════════════════
# EVAL_RESULTS (6개 — eval_type 2종 × model 3종)
# ════════════════════════════════════════════════════════

EVALS = [
    ("https://reuters.com/tsmc-2nm-mass-production",
     "qwen3-4b-base", "translation",
     {"bleu": 0.31, "comet": 0.69, "tpr": 0.65}),
    ("https://reuters.com/tsmc-2nm-mass-production",
     "qwen3-4b-ft-v1", "translation",
     {"bleu": 0.46, "comet": 0.82, "tpr": 0.88}),
    ("https://reuters.com/tsmc-2nm-mass-production",
     "gpt-4o", "translation",
     {"bleu": 0.53, "comet": 0.89, "tpr": 0.95}),
    ("https://techcrunch.com/nvidia-blackwell-ultra-launch",
     "qwen3-4b-base", "summary_formal",
     {"geval_faithfulness": 3.0, "geval_fluency": 3.4,
      "geval_conciseness": 3.1, "geval_relevance": 3.3}),
    ("https://techcrunch.com/nvidia-blackwell-ultra-launch",
     "qwen3-4b-ft-v1", "summary_formal",
     {"geval_faithfulness": 4.1, "geval_fluency": 4.3,
      "geval_conciseness": 4.2, "geval_relevance": 4.4}),
    ("https://techcrunch.com/nvidia-blackwell-ultra-launch",
     "gpt-4o", "summary_formal",
     {"geval_faithfulness": 4.8, "geval_fluency": 4.7,
      "geval_conciseness": 4.6, "geval_relevance": 4.8}),
]


# ════════════════════════════════════════════════════════
# 업로드
# ════════════════════════════════════════════════════════

def clear_all():
    print("[초기화] 기존 데이터 삭제 중...")
    sb.table("eval_results").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("fact_checks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("neologisms").delete().neq("term", "___never___").execute()
    sb.table("bookmarks").delete().neq("user_id", "___never___").execute()
    sb.table("user_logs").delete().neq("user_id", "___never___").execute()
    sb.table("articles").delete().neq("url_hash", "___never___").execute()
    print("  → 완료")


def upload_articles():
    print("\n[1/4] articles 업로드 중 (OpenRouter 임베딩)...")
    rows = []
    for i, a in enumerate(RAW):
        h = url_hash(a["url"])
        score = a["credibility_score"]
        emb = make_embedding(a["title"] + " " + a["content"])
        rows.append({
            "url_hash":          h,
            "url":               a["url"],
            "title":             a["title"],
            "source":            a["source"],
            "source_type":       a["source_type"],
            "category":          a["category"],
            "country":           a["country"],
            "keywords":          a["keywords"],
            "published_at":      a["published_at"],
            "content":           a["content"],
            "credibility_score": score,
            "fact_label":        fact_label(score),
            "translation":       a.get("translation"),
            "summary_formal":    a.get("summary_formal"),
            "summary_casual":    a.get("summary_casual"),
            "embedding":         emb,
        })
        print(f"  [{i+1}/{len(RAW)}] {a['category']} — {a['title'][:45]}...")
    sb.table("articles").upsert(rows).execute()
    print(f"  → {len(rows)}개 완료")
    return {a["url"]: url_hash(a["url"]) for a in RAW}


def upload_neologisms(u2h):
    print("\n[2/4] neologisms 업로드 중...")
    anchor = u2h.get("https://techcrunch.com/nvidia-blackwell-ultra-launch")
    rows = [{
        "term":                n["term"],
        "explanation":         n["explanation"],
        "ko_suggestion":       n["ko_suggestion"],
        "first_seen_url_hash": anchor,
        "occurrence_count":    n["occurrence_count"],
        "confirmed":           n["confirmed"],
        "created_at":          datetime.now(timezone.utc).isoformat(),
    } for n in NEOLOGISMS]
    sb.table("neologisms").upsert(rows, on_conflict="term").execute()
    print(f"  → {len(rows)}개 완료")


def upload_fact_checks(u2h):
    print("\n[3/4] fact_checks 업로드 중...")
    rows = []
    for (url, claim, verdict, conf, checker) in FACT_CHECKS:
        h = u2h.get(url)
        if not h:
            print(f"  [경고] URL 없음: {url}"); continue
        rows.append({
            "article_url_hash": h, "claim": claim, "verdict": verdict,
            "confidence": conf, "checker_type": checker,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })
    sb.table("fact_checks").insert(rows).execute()
    print(f"  → {len(rows)}개 완료")


def upload_evals(u2h):
    print("\n[4/4] eval_results 업로드 중...")
    rows = []
    for (url, model, etype, metrics) in EVALS:
        h = u2h.get(url)
        if not h:
            print(f"  [경고] URL 없음: {url}"); continue
        rows.append({
            "article_url_hash": h, "model_version": model,
            "eval_type": etype,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            **metrics,
        })
    sb.table("eval_results").insert(rows).execute()
    print(f"  → {len(rows)}개 완료")


if __name__ == "__main__":
    print("=" * 55)
    print("삼선뉴스 AI/Tech 더미 데이터 생성기")
    print("=" * 55)

    clear_all()
    u2h = upload_articles()
    upload_neologisms(u2h)
    upload_fact_checks(u2h)
    upload_evals(u2h)

    print("\n" + "=" * 55)
    print("완료! 커버된 속성:")
    print("  카테고리: AI연구(6) / AI스타트업(5) / 테크전반(5)")
    print("            윤리-정책(5) / 반도체(6)")
    print("  source:   MIT TR / TechCrunch / The Verge /")
    print("            Reuters / BBC코리아 / 연합뉴스 / 한겨레")
    print("  source_type: media / community")
    print("  country:  US / KR / EU")
    print("  fact_label: FACT / RUMOR / UNVERIFIED")
    print("  neologisms: confirmed T/F 혼합")
    print("  fact_checks: FACT/RUMOR/UNVERIFIED/MISLEADING + ai/human")
    print("  eval_results: translation/summary_formal × 3 models")
    print("=" * 55)
