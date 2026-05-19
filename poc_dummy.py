"""
poc_dummy.py — 더미 데이터 Supabase 저장 스크립트

실행:
    cd Samsun-Final-Project
    python poc_dummy.py

결과:
    articles 테이블에 5개 더미 기사 저장
    (임베딩 포함 — Ollama qwen3-embedding:4b 필요)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.save_articles import save_articles

DUMMY_ARTICLES = [
    {
        "url":               "https://techcrunch.com/2026/04/13/nvidia-blackwell-ultra",
        "title":             "NVIDIA Unveils Blackwell Ultra GPU for AI Inference",
        "source":            "TechCrunch",
        "source_type":       "media",
        "category":          "AI/반도체",
        "country":           "US",
        "keywords":          ["NVIDIA", "Blackwell Ultra", "GPU", "AI inference"],
        "published_at":      "2026-04-13T09:00:00Z",
        "content":           "NVIDIA today announced the Blackwell Ultra GPU, designed specifically for large-scale AI inference workloads. The new chip offers 2x the memory bandwidth of its predecessor and supports up to 192GB of HBM3e memory. Major cloud providers including AWS, Google Cloud, and Microsoft Azure have already committed to deploying the new hardware.",
        "credibility_score": 0.95,
        "translation":       "엔비디아가 오늘 대규모 AI 추론 워크로드를 위해 특별히 설계된 블랙웰 울트라 GPU를 발표했습니다. 새 칩은 전작 대비 2배의 메모리 대역폭을 제공하며 최대 192GB HBM3e 메모리를 지원합니다. AWS, 구글 클라우드, 마이크로소프트 애저 등 주요 클라우드 제공업체들이 이미 새 하드웨어 도입을 약속했습니다.",
        "summary_formal":    "엔비디아가 AI 추론 특화 블랙웰 울트라 GPU를 발표하였습니다.\n전작 대비 메모리 대역폭이 2배 향상되었습니다.\n주요 클라우드 업체들이 즉시 도입 계획을 밝혔습니다.",
        "summary_casual":    "엔비디아에서 AI 추론 전용 블랙웰 울트라 GPU가 나왔어요!\n이전 것보다 메모리 대역폭이 2배나 빠르다고 해요.\nAWS, 구글, MS 애저 모두 바로 쓴다고 했어요.",
    },
    {
        "url":               "https://www.technologyreview.com/2026/04/12/openai-gpt5-release",
        "title":             "OpenAI Quietly Releases GPT-5 with Improved Reasoning",
        "source":            "MIT Technology Review",
        "source_type":       "media",
        "category":          "AI 일반",
        "country":           "US",
        "keywords":          ["OpenAI", "GPT-5", "reasoning", "LLM"],
        "published_at":      "2026-04-12T14:30:00Z",
        "content":           "OpenAI has released GPT-5, its latest flagship language model, with significant improvements in multi-step reasoning and mathematical problem solving. The model scores 92% on MATH benchmark, up from 78% with GPT-4. OpenAI also introduced a new pricing tier at $0.01 per 1K tokens for API access.",
        "credibility_score": 0.92,
        "translation":       "OpenAI가 다단계 추론과 수학 문제 풀이에서 크게 향상된 최신 플래그십 언어 모델 GPT-5를 출시했습니다. 이 모델은 MATH 벤치마크에서 92%를 기록해 GPT-4의 78%에서 올랐습니다. OpenAI는 또한 API 접근을 위해 1K 토큰당 0.01달러의 새로운 가격 티어를 도입했습니다.",
        "summary_formal":    "OpenAI가 추론 능력이 향상된 GPT-5를 출시하였습니다.\nMATH 벤치마크에서 92%를 달성하였습니다.\nAPI 가격이 1K 토큰당 0.01달러로 책정되었습니다.",
        "summary_casual":    "OpenAI에서 GPT-5를 조용히 출시했어요!\n수학 문제 풀이가 GPT-4보다 훨씬 좋아졌대요.\nAPI 가격도 꽤 착하게 나왔어요.",
    },
    {
        "url":               "https://theverge.com/2026/04/11/anthropic-claude-enterprise",
        "title":             "Anthropic Launches Claude Enterprise with 500K Context Window",
        "source":            "The Verge",
        "source_type":       "media",
        "category":          "AI 비즈니스",
        "country":           "US",
        "keywords":          ["Anthropic", "Claude", "enterprise", "context window"],
        "published_at":      "2026-04-11T10:00:00Z",
        "content":           "Anthropic has launched Claude Enterprise, a new tier of its AI assistant aimed at large corporations. The enterprise version features a 500,000 token context window, custom fine-tuning options, and dedicated infrastructure. Early customers include Goldman Sachs and Pfizer, who are using the model for document analysis and drug discovery respectively.",
        "credibility_score": 0.88,
        "translation":       "앤트로픽이 대기업을 대상으로 한 AI 어시스턴트의 새로운 등급인 클로드 엔터프라이즈를 출시했습니다. 엔터프라이즈 버전은 50만 토큰 컨텍스트 창, 맞춤형 파인튜닝 옵션, 전용 인프라를 갖추고 있습니다. 초기 고객으로는 골드만삭스와 화이자가 있으며 각각 문서 분석과 신약 개발에 활용하고 있습니다.",
        "summary_formal":    "앤트로픽이 기업용 클로드 엔터프라이즈를 출시하였습니다.\n50만 토큰 컨텍스트와 파인튜닝 기능을 제공합니다.\n골드만삭스, 화이자 등이 초기 고객으로 참여하였습니다.",
        "summary_casual":    "앤트로픽에서 기업용 클로드를 새로 내놨어요!\n무려 50만 토큰 컨텍스트 창이라고 해요.\n골드만삭스랑 화이자가 이미 쓰고 있대요.",
    },
    {
        "url":               "https://venturebeat.com/ai/2026/04/10/eu-ai-act-enforcement",
        "title":             "EU AI Act Enforcement Begins: What Tech Companies Need to Know",
        "source":            "VentureBeat AI",
        "source_type":       "media",
        "category":          "AI 윤리",
        "country":           "EU",
        "keywords":          ["EU AI Act", "regulation", "compliance", "policy"],
        "published_at":      "2026-04-10T08:00:00Z",
        "content":           "The EU AI Act has officially entered its enforcement phase, requiring all AI systems deployed in the European Union to comply with new transparency and safety standards. High-risk AI applications face fines of up to 30 million euros or 6% of global annual revenue. Companies have 6 months to achieve compliance or face penalties.",
        "credibility_score": 0.90,
        "translation":       "EU AI법이 공식적으로 집행 단계에 들어서며 유럽연합에 배포되는 모든 AI 시스템이 새로운 투명성 및 안전 기준을 준수해야 합니다. 고위험 AI 애플리케이션은 최대 3천만 유로 또는 전 세계 연간 매출의 6%에 달하는 벌금에 직면합니다. 기업들은 6개월 내에 규정 준수를 달성하지 않으면 제재를 받게 됩니다.",
        "summary_formal":    "EU AI법 집행이 공식적으로 시작되었습니다.\n고위험 AI에는 최대 3천만 유로의 벌금이 부과됩니다.\n기업들은 6개월 내 규정을 준수해야 합니다.",
        "summary_casual":    "EU에서 AI법 집행이 드디어 시작됐어요!\n규정 안 지키면 벌금이 어마어마하대요.\n6개월 안에 맞춰야 한다고 하네요.",
    },
    {
        "url":               "https://ieee.org/spectrum/2026/04/09/tsmc-2nm-yield",
        "title":             "TSMC Reports 70% Yield Rate for 2nm Process Node",
        "source":            "IEEE Spectrum",
        "source_type":       "media",
        "category":          "AI/반도체",
        "country":           "TW",
        "keywords":          ["TSMC", "2nm", "semiconductor", "yield rate"],
        "published_at":      "2026-04-09T06:00:00Z",
        "content":           "TSMC has achieved a 70% yield rate for its 2nm process node, well above the industry threshold for mass production. The breakthrough means AI chips manufactured on the 2nm process will be available at scale by Q3 2026. Apple and NVIDIA are among the first customers to secure production capacity for the new node.",
        "credibility_score": 0.93,
        "translation":       "TSMC가 2나노 공정 노드에서 70%의 수율을 달성해 양산 기준을 크게 웃돌고 있습니다. 이 성과로 2나노 공정에서 제조된 AI 칩이 2026년 3분기부터 대규모로 공급될 예정입니다. 애플과 엔비디아가 새 노드의 생산 능력을 확보한 첫 번째 고객 중 하나입니다.",
        "summary_formal":    "TSMC가 2나노 공정에서 70% 수율을 달성하였습니다.\n2026년 3분기부터 대량 생산이 가능할 것으로 전망됩니다.\n애플, 엔비디아가 첫 번째 고객으로 생산 물량을 확보하였습니다.",
        "summary_casual":    "TSMC 2나노 공정 수율이 70%나 됐대요!\n올 3분기면 AI 칩 대량 공급이 가능하다고 해요.\n애플이랑 엔비디아가 이미 물량 확보했다고 하네요.",
    },
]

if __name__ == "__main__":
    print("=" * 50)
    print("삼선뉴스 더미 데이터 업로드 시작")
    print("=" * 50)

    print("\n[1/2] Ollama 임베딩 모델 확인 중...")
    print("      (qwen3-embedding:4b 모델이 필요합니다)")
    print("      설치 안 돼있으면: ollama pull qwen3-embedding:4b\n")

    try:
        count = save_articles(DUMMY_ARTICLES)
        print(f"\n[2/2] 완료! {count}개 기사가 Supabase에 저장됐어요.")
        print("\n다음 단계:")
        print("  uvicorn backend.main:app --reload --port 8000")
        print("  curl http://localhost:8000/articles")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("\n확인 사항:")
        print("  1. .env 파일에 SUPABASE_URL, SUPABASE_KEY 설정됐는지")
        print("  2. Ollama 실행 중인지 (ollama serve)")
        print("  3. qwen3-embedding:4b 모델 설치됐는지")
