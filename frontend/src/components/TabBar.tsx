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
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path
          d="M3 12L12 3L21 12V21H15V15H9V21H3V12Z"
          stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'}
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    id: 'category',
    label: '카테고리',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="8" height="8" rx="2" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" />
        <rect x="13" y="3" width="8" height="8" rx="2" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" />
        <rect x="3" y="13" width="8" height="8" rx="2" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" />
        <rect x="13" y="13" width="8" height="8" rx="2" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" />
      </svg>
    ),
  },
  {
    id: 'hot',
    label: '핫이슈',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 2L14.5 9H22L16 13.5L18.5 21L12 16.5L5.5 21L8 13.5L2 9H9.5L12 2Z"
          stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'}
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    id: 'search',
    label: '검색',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="11" cy="11" r="6" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" />
        <path d="M16.5 16.5L20 20" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 'my',
    label: '내 피드',
    icon: (active) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="8" r="4" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" />
        <path d="M4 20C4 17 7.5 14.5 12 14.5C16.5 14.5 20 17 20 20" stroke={active ? 'var(--color-primary)' : 'var(--color-text-tertiary)'} strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
];

interface TabBarProps {
  activeTab: TabId;
  onChange: (id: TabId) => void;
}

export default function TabBar({ activeTab, onChange }: TabBarProps) {
  return (
    <nav style={{
      display: 'flex',
      background: 'var(--color-surface)',
      borderTop: '0.5px solid var(--color-border)',
      height: 64,
      flexShrink: 0,
      paddingBottom: 'env(safe-area-inset-bottom)',
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
              padding: '8px 0 4px',
              transition: 'opacity 0.15s',
            }}
          >
            {tab.icon(active)}
            <span style={{
              fontSize: 10,
              fontWeight: active ? 600 : 400,
              color: active ? 'var(--color-primary)' : 'var(--color-text-tertiary)',
              letterSpacing: '-0.01em',
            }}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
