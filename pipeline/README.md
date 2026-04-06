# pipeline — 번역·요약 (Ollama + Qwen 3.5)

외부 뉴스 원문을 **한국어 번역**과 **격식체·일상체 요약**으로 가공하는 로직입니다.  
예전에 쓰던 **KoBART / mBART / mT5 같은 Hugging Face 시퀀스 모델은 사용하지 않습니다.**  
로컬 LLM은 **[Ollama](https://ollama.com)** 로 띄운 **Qwen 3.5** 계열을 기본으로 씁니다.

## 스택

| 구분 | 내용 |
|------|------|
| 런타임 | Ollama (`ollama.chat`) |
| 기본 모델 | `qwen3.5:4b` (환경변수 `MODEL_NAME`으로 변경 가능) |
| 의존성 | `ollama`, `python-dotenv` (`requirements.txt` 기준) |

`think=False` 로 thinking 모드를 끄고, 일부 응답에서 남는 thinking 마커는 코드에서 잘라 씁니다.

## 파일 역할

| 파일 | 설명 |
|------|------|
| `translate_summarize.py` | **권장 메인 플로우**: 영어 기사 한 번에 **번역 + 격식체 요약 + 일상체 요약**을 JSON으로 받음. 문장 수 추정·재시도·배치 헬퍼 포함. |
| `translator.py` | 번역만 (격식체 / 일상체 `style` 선택). |
| `summarizer.py` | 한국어 **3줄 불릿** 요약 (시스템 프롬프트 규칙 고정). |

백엔드·`collect/`와 붙일 때는 팀 DB·API 스키마에 맞춰 입출력만 맞추면 됩니다.

## 설정

1. Ollama에 모델 설치 (예시는 기본 태그):

   ```bash
   ollama pull qwen3.5:4b
   ```

2. (선택) 다른 Qwen 3.5 태그를 쓰려면 환경 변수:

   ```bash
   set MODEL_NAME=qwen3.5:7b
   ```

3. 프로젝트 루트에서 의존성 설치 후 실행:

   ```bash
   pip install -r requirements.txt
   python pipeline/translate_summarize.py
   ```

## 참고

- **KoBART**는 과거 프로젝트에서 쓰이던 한국어 요약용 BART 계열 모델 이름입니다. **현재 이 디렉터리 코드 경로에는 없습니다.**
- GPU 옵션은 `options`에 `num_gpu` 등이 들어가 있으니, 실제 머신·Ollama 버전에 맞게 조정하세요.
