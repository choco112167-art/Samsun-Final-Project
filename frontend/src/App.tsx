import { useState, useEffect } from 'react';
import { BottomSheet } from '@toss/tds-mobile';
import TabBar, { type TabId } from './components/TabBar';
import OnboardingPage, { type Interest } from './pages/OnboardingPage';
import HomePage from './pages/HomePage';
import CategoryPage from './pages/CategoryPage';
import HotPage from './pages/HotPage';
import SearchPage from './pages/SearchPage';
import MyFeedPage from './pages/MyFeedPage';
import { useBookmarks } from './hooks/useBookmarks';
import {
  recordArticleView,
  fetchAbsenceSummary,
  markUserSeen,
  type AbsenceSummaryResponse,
} from './data/api';

const LS_ONBOARDED = 'samsun_onboarded';
const LS_INTERESTS = 'samsun_interests';

/** 개발 중 강제 온보딩 화면 — 배포 전 반드시 false */
const DEV_FORCE_ONBOARDING = false;

function loadInterests(): Interest[] {
  try { return JSON.parse(localStorage.getItem(LS_INTERESTS) ?? '[]'); }
  catch { return []; }
}

export default function App() {
  const [onboarded, setOnboarded] = useState(
    () => (DEV_FORCE_ONBOARDING ? false : localStorage.getItem(LS_ONBOARDED) === 'true'),
  );
  const [interests, setInterests] = useState<Interest[]>(loadInterests);
  const [userId, setUserId] = useState(
    () => localStorage.getItem('samsun_user_id') ?? '',
  );
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const bm = useBookmarks();

  const [absenceData, setAbsenceData] = useState<AbsenceSummaryResponse | null>(null);
  const [absenceOpen, setAbsenceOpen] = useState(false);

  // 앱 진입 시 부재중 요약 확인
  useEffect(() => {
    if (!userId) return;
    fetchAbsenceSummary(userId)
      .then(res => {
        if (res.show) {
          setAbsenceData(res);
          setAbsenceOpen(true);
        }
      })
      .catch(() => {});
  }, [userId]);

  const handleAbsenceDismiss = () => {
    setAbsenceOpen(false);
    if (userId) markUserSeen(userId).catch(() => {});
    setAbsenceData(null);
  };

  const handleInterestsChange = (next: Interest[]) => {
    setInterests(next);
    localStorage.setItem(LS_INTERESTS, JSON.stringify(next));
  };

  // 모든 탭에서 기사 클릭 시 호출 — user_vector 업데이트
  const handleArticleClick = (urlHash: string) => {
    if (userId) {
      recordArticleView(userId, urlHash).catch(() => {});
    }
  };

  if (!onboarded) {
    return (
      <div style={{ height: '100dvh', maxWidth: 480, margin: '0 auto', overflow: 'hidden' }}>
        <OnboardingPage onDone={(selected, uid) => {
          setInterests(selected);
          setUserId(uid);
          setOnboarded(true);
          localStorage.setItem(LS_ONBOARDED, 'true');
          localStorage.setItem(LS_INTERESTS, JSON.stringify(selected));
          localStorage.setItem('samsun_user_id', uid); // 최초 진입 시에도 persistence 확보
        }} />
      </div>
    );
  }

  const renderPage = () => {
    switch (activeTab) {
      case 'home':
        return (
          <HomePage
            bm={bm}
            onNavigateToFeed={() => setActiveTab('my')}
            onArticleClick={handleArticleClick}
          />
        );
      case 'category': return <CategoryPage bm={bm} onArticleClick={handleArticleClick} />;
      case 'hot':      return <HotPage bm={bm} onArticleClick={handleArticleClick} />;
      case 'search':   return <SearchPage bm={bm} onArticleClick={handleArticleClick} />;
      case 'my':
        return (
          <MyFeedPage
            key={activeTab}
            bm={bm}
            interests={interests}
            onInterestsChange={handleInterestsChange}
            userId={userId}
          />
        );
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100dvh', maxWidth: 480, margin: '0 auto',
      background: 'var(--color-bg)', overflow: 'hidden',
    }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, position: 'relative' }}>
        {renderPage()}
      </div>
      <TabBar activeTab={activeTab} onChange={setActiveTab} />

      {/* 부재중 알림 BottomSheet */}
      {absenceData?.show && (
        <BottomSheet open={absenceOpen} onClose={handleAbsenceDismiss}>
          <BottomSheet.Header>
            <BottomSheet.Title>{absenceData.message ?? '놓친 기사예요!'}</BottomSheet.Title>
            {absenceData.days_away !== undefined && (
              <BottomSheet.Description>
                {absenceData.days_away}일 만에 들르셨네요. 그동안 주목받은 기사를 모아봤어요.
              </BottomSheet.Description>
            )}
          </BottomSheet.Header>
          <BottomSheet.Body>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '0 20px 12px' }}>
              {(absenceData.articles ?? []).map(a => (
                <div
                  key={a.url_hash}
                  onClick={() => { handleArticleClick(a.url_hash); handleAbsenceDismiss(); }}
                  style={{
                    background: 'var(--color-surface)',
                    border: '0.5px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: 14, cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{a.source}</span>
                    <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>· {a.category}</span>
                  </div>
                  <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 6 }}>
                    {a.title}
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {a.summary_formal}
                  </p>
                </div>
              ))}
            </div>
          </BottomSheet.Body>
          <BottomSheet.Footer>
            <BottomSheet.Button onClick={handleAbsenceDismiss}>확인했어요</BottomSheet.Button>
          </BottomSheet.Footer>
        </BottomSheet>
      )}
    </div>
  );
}
