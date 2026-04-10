import React from 'react';

export type TabId = 'home' | 'category' | 'hot' | 'search' | 'my';

interface Tab {
  id: TabId;
  label: string;
  icon: (active: boolean) => React.ReactNode;
}

const tabs: Tab[] = [
  {
    id: 'home',
    label: '홈',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        {active ? (
          <path
            d="M3 12L12 3L21 12V21H15V15H9V21H3V12Z"
            fill="#111111"
            stroke="#111111"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        ) : (
          <path
            d="M3 12L12 3L21 12V21H15V15H9V21H3V12Z"
            fill="#C2C8D0"
            stroke="#C2C8D0"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        )}
      </svg>
    ),
  },
  {
    id: 'category',
    label: '카테고리',
    icon: (active) => {
      const c = active ? '#111111' : '#C2C8D0';
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="8" height="8" rx="2" fill={c} />
          <rect x="13" y="3" width="8" height="8" rx="2" fill={c} />
          <rect x="3" y="13" width="8" height="8" rx="2" fill={c} />
          <rect x="13" y="13" width="8" height="8" rx="2" fill={c} />
        </svg>
      );
    },
  },
  {
    id: 'hot',
    label: '핫이슈',
    icon: (active) => {
      const c = active ? '#111111' : '#C2C8D0';
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2L14.5 9H22L16 13.5L18.5 21L12 16.5L5.5 21L8 13.5L2 9H9.5L12 2Z"
            fill={c}
            stroke={c}
            strokeWidth="1.2"
            strokeLinejoin="round"
          />
        </svg>
      );
    },
  },
  {
    id: 'search',
    label: '검색',
    icon: (active) => {
      const c = active ? '#111111' : '#C2C8D0';
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="7" fill={c} />
          <circle cx="11" cy="11" r="4.5" fill="white" />
          <path d="M16.5 16.5L21 21" stroke={c} strokeWidth="2.2" strokeLinecap="round" />
        </svg>
      );
    },
  },
  {
    id: 'my',
    label: '내 피드',
    icon: (active) => {
      const c = active ? '#111111' : '#C2C8D0';
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="8" r="4" fill={c} />
          <path
            d="M4 20C4 17 7.5 14 12 14C16.5 14 20 17 20 20"
            stroke={c}
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      );
    },
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
      {/* 플로팅 필 컨테이너 */}
      <nav style={{
        display: 'flex',
        background: '#FFFFFF',
        borderRadius: 40,
        boxShadow: '0 4px 20px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)',
        height: 64,
        alignItems: 'center',
        overflow: 'hidden',
      }}>
        {tabs.map((tab) => {
          const active = tab.id === activeTab;
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
                padding: '10px 0 8px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                transition: 'transform 0.12s',
              }}
              onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.9)'; }}
              onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
            >
              {tab.icon(active)}
              <span style={{
                fontSize: 10,
                fontWeight: active ? 700 : 500,
                color: active ? '#111111' : '#9EA8B2',
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
