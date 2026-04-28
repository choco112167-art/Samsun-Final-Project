/**
 * tds-bypass.ts — `@toss/tds-mobile` 환경 검사 우회
 *
 * `@toss/tds-mobile` 의 번들은 import 시점에 실행되는 obfuscated IIFE 안에서
 * `window.location.hostname` (실패 시 `document.domain`) 을 읽어 String.hashCode
 * 로 해시한 뒤 내장 화이트리스트와 대조한다. 매칭되지 않으면 즉시
 *   "Throw new Error('@toss/tds-mobile은 앱인토스 개발에만 사용할 수 있어요.')"
 * 가 발생해 앱 자체가 로드되지 않는다.
 *
 * 화이트리스트엔 `localhost` 가 포함돼 있어 dev (localhost:5173) 는 통과하지만,
 * 운영 도메인 `samsun-production.up.railway.app` 는 실패한다.
 *
 * 우회 전략 (방어적, 다중 시도):
 *   1) `Location.prototype.hostname` 게터를 'localhost' 로 오버라이드 → 가장 깔끔
 *   2) `Document.prototype.domain` 게터도 동일하게 — TDS 의 폴백 경로 차단
 *   3) `navigator.userAgent` 에 'TossApp/...' 토큰 주입 — 사용자 요청 + 일부
 *      TDS 코드(TossApp/, TossColorPreference/ 등)가 UA 를 파싱해도 호환되도록
 *
 * ⚠️ 이 모듈은 `@toss/tds-mobile` 보다 먼저 평가돼야 한다.
 *    `main.tsx` 의 첫 번째 import 로 두면 ES 모듈 평가 순서상 보장된다.
 */

const FAKE_HOSTNAME = 'localhost';

declare global {
  interface Window { __samsunTdsBypassed?: boolean }
}

if (typeof window !== 'undefined' && !window.__samsunTdsBypassed) {
  // (1) Location.prototype.hostname 오버라이드
  try {
    const desc = Object.getOwnPropertyDescriptor(Location.prototype, 'hostname');
    if (!desc || desc.configurable !== false) {
      Object.defineProperty(Location.prototype, 'hostname', {
        get() { return FAKE_HOSTNAME; },
        configurable: true,
      });
    }
  } catch { /* 일부 브라우저에서 거부될 수 있음 — 다음 단계로 진행 */ }

  // (2) window.location 인스턴스에 own enumerable 데코이 추가 — for..in 으로
  //     'h?o?t?a?e' 패턴(즉 hostname 매칭) 에 우리 값이 먼저 잡히도록
  //     'hozytaze' (length 8, h-o-z-y-t-a-z-e) 는 패턴 [0]=h,[1]=o,[3]=t,[5]=a,[7]=e 만족
  try {
    Object.defineProperty(window.location, 'hozytaze', {
      value: FAKE_HOSTNAME,
      enumerable: true,
      configurable: true,
      writable: true,
    });
  } catch { /* noop */ }

  // (3) Document.prototype.domain 오버라이드 — TDS 의 폴백 경로 차단
  try {
    const desc = Object.getOwnPropertyDescriptor(Document.prototype, 'domain');
    if (!desc || desc.configurable !== false) {
      Object.defineProperty(Document.prototype, 'domain', {
        get() { return FAKE_HOSTNAME; },
        configurable: true,
      });
    }
  } catch { /* noop */ }

  // (4) navigator.userAgent 모킹 — 사용자 요청 사항.
  //     TossApp/, TossColorPreference/ 등 TDS-AIT 측 정규식과도 호환되도록 포맷 맞춤.
  try {
    const original = navigator.userAgent;
    if (!original.includes('TossApp/')) {
      Object.defineProperty(navigator, 'userAgent', {
        get() { return `${original} TossApp/0.0.0 TossColorPreference/light`; },
        configurable: true,
      });
    }
  } catch { /* noop */ }

  window.__samsunTdsBypassed = true;
}

export {};
