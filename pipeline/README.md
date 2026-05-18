# pipeline — 번역·요약 (Ollama + Gemma 4 E4B)

외부 뉴스 원문을 **한국어 번역**과 **격식체·일상체 요약**으로 가공하는 모듈입니다.

## 핵심 플로우

**`translate_summarize.py`**가 전체 파이프라인의 중심입니다. **한 번의 LLM 호출**로 다음을 동시에 생성합니다.

- 한국어 본문 번역 (`translation`)
- 격식체 요약 (`summary_formal`)
- 일상체 요약 (`summary_casual`)
- (선택) 영문 제목이 있으면 한국어 제목 (`title_ko`)

모델 응답은 JSON 한 덩어리로 받고, `utils.extract_json`으로 필드를 안정적으로 파싱합니다.

## 스택

| 구분 | 내용 |
|------|------|
| 런타임 | [Ollama](https://ollama.com) (`ollama.chat`) |
| 기본 모델 | **`samsun-gemma4`** (환경변수 `MODEL_NAME`으로 태그 변경) |
| 의존성 | `ollama`, `python-dotenv` (`requirements.txt` 기준) |

- `think=False`로 thinking 모드를 끕니다. Ollama 태그가 다르면 `MODEL_NAME`만 교체합니다.
- `options`에 `num_gpu` 등이 설정되어 있으므로, 환경에 맞게 Ollama 설정을 조정하세요.

## 파일 역할

| 파일 | 설명 |
|------|------|
| **`translate_summarize.py`** | **권장 메인**: 번역 + 격식체/일상체 요약 + (선택) 한국어 제목을 단일 LLM 호출로 생성. 문장 수 추정(`estimate_sentences`)·재시도·배치 헬퍼·CLI 샘플 포함. |
| `summarizer.py` | 한국어 3줄 불릿 요약(별도 프롬프트). 향후 **부재중 요약 알림 파이프라인** 등 요약 단독 호출이 필요할 때 사용. |
| `utils.py` | 전처리·JSON 필드 추출 등 공통 유틸. |

> 과거에 함께 있던 `translator.py` 는 `translate_summarize.py` 의 번역 출력으로 완전 대체되어 2026-04-28 청소(이슈 #18) 때 삭제했습니다. `summarizer.py` 는 향후 알림 파이프라인 백본으로 보존(이슈 #19 복구).

운영 API(`backend/main.py`의 `/translate`, `/summarize`)는 `backend/llm_dispatch.py`를 통해 `translate_summarize.translate_and_summarize`를 호출합니다.

## 설정

1. Ollama에 모델 설치:

   ```bash
   ollama list
   ollama run samsun-gemma4
   ```

2. (선택) 다른 태그를 쓰려면 환경 변수:

   ```bash
   set MODEL_NAME=samsun-gemma4
   ```

3. 프로젝트 루트에서 의존성 설치 후 CLI 샘플 실행:

   ```bash
   pip install -r requirements.txt
   python pipeline/translate_summarize.py
   ```

## 요약 문장 수

`translate_and_summarize(..., summary_sentences=n)`으로 격식·일상 요약 각각의 문장 수를 맞춥니다. 배치 유틸 `batch_translate_summarize`는 동일한 `summary_sentences`를 반복 적용합니다.
