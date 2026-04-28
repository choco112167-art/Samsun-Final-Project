import React from 'react';

// Toss grey 팔레트 직접 hex 값.
// (`var(--adaptiveGreyXXX)` 토큰은 `@toss/tds-mobile-ait` 의 GlobalCSSVariables
//  컴포넌트가 emotion <Global> 로 동적 주입해야만 정의되는데, 본 앱은 일반
//  브라우저 호환을 위해 AIT Provider 를 제거(이슈 #6)했으므로 토큰이 비어 있어
//  활성/비활성이 모두 상속된 body 색으로 진하게 출력되는 버그가 있었다.)
const ACTIVE_COLOR   = '#191f28'; // grey900
const INACTIVE_ICON  = '#c0c8d0'; // grey300~400 사이
const INACTIVE_LABEL = '#8b95a1'; // grey500 (라벨은 살짝 더 진하게 가독성 ↑)

export type TabId = 'home' | 'category' | 'hot' | 'search' | 'my';

interface Tab {
  id: TabId;
  label: string;
  /** SVG 내부는 currentColor 로 칠한다. 색은 부모 <svg style={{color}}> 에서 결정 */
  icon: React.ReactNode;
}

const tabs: Tab[] = [
  {
    id: 'home',
    label: '홈',
    icon: (
      <path
        d="M3 12L12 3L21 12V21H15V15H9V21H3V12Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    ),
  },
  {
    id: 'category',
    label: '카테고리',
    icon: (
      <>
        <rect x="3" y="3" width="8" height="8" rx="2" fill="currentColor" />
        <rect x="13" y="3" width="8" height="8" rx="2" fill="currentColor" />
        <rect x="3" y="13" width="8" height="8" rx="2" fill="currentColor" />
        <rect x="13" y="13" width="8" height="8" rx="2" fill="currentColor" />
      </>
    ),
  },
  {
    id: 'hot',
    label: '핫이슈',
    icon: (
      <path
        d="M12 2L14.5 9H22L16 13.5L18.5 21L12 16.5L5.5 21L8 13.5L2 9H9.5L12 2Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    ),
  },
  {
    id: 'search',
    label: '검색',
    icon: (
      <>
        <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      </>
    ),
  },
  {
    id: 'my',
    label: '내 피드',
    icon: (
      <>
        <circle cx="12" cy="8" r="4" fill="currentColor" />
        <path
          d="M4 20C4 17 7.5 14 12 14C16.5 14 20 17 20 20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
        />
      </>
    ),
  },
];

interface TabBarProps {
  activeTab: TabId;
  onChange: (id: TabId) => void;
}

export default function TabBar({ activeTab, onChange }: TabBarProps) {
  return (
    <div style={{
      flexShrink: 0,
      background: 'var(--color-bg)',
      paddingBottom: 'calc(env(safe-area-inset-bottom) + 12px)',
      paddingTop: 10,
      paddingLeft: 16,
      paddingRight: 16,
    }}>
      <nav style={{
        display: 'flex',
        background: '#FFFFFF',
        borderRadius: 40,
        boxShadow: '0 4px 20px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)',
        height: 64,
        alignItems: 'center',
        padding: '0 4px',
      }}>
        {tabs.map((tab) => {
          const active = tab.id === activeTab;
          const tint = active ? ACTIVE_COLOR : INACTIVE_ICON;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 3,
                padding: '8px 0 6px',
                background: active ? 'rgba(0,0,0,0.06)' : 'none',
                borderRadius: 14,
                border: 'none',
                outline: 'none',
                cursor: 'pointer',
                transition: 'transform 0.12s, background 0.15s',
                height: 56,
              }}
              onTouchStart={(e) => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.92)'; }}
              onTouchEnd={(e) => { (e.currentTarget as HTMLElement).style.transform = ''; }}
            >
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                style={{ color: tint, display: 'block' }}
              >
                {tab.icon}
              </svg>
              <span style={{
                fontSize: 10,
                fontWeight: active ? 700 : 500,
                color: active ? ACTIVE_COLOR : INACTIVE_LABEL,
                letterSpacing: '-0.01em',
                lineHeight: 1,
              }}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
