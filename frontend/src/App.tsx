import { useState, useEffect } from 'react';
import TabBar, { type TabId } from './components/TabBar';
import OnboardingPage, { type Interest } from './pages/OnboardingPage';
import HomePage from './pages/HomePage';
import CategoryPage from './pages/CategoryPage';
import HotPage from './pages/HotPage';
import SearchPage from './pages/SearchPage';
import MyFeedPage from './pages/MyFeedPage';
import { useBookmarks } from './hooks/useBookmarks';
import { recordArticleView, logArticleView, fetchAbsenceSummary, markUserSeen, type AbsenceSummaryResponse } from './data/api';

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
  const [userId, setUserId] = useState(() => {
    const key = 'samsun_user_id';
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const id = `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem(key, id);
    return id;
  });
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const bm = useBookmarks();
  const [absenceData, setAbsenceData] = useState<AbsenceSummaryResponse | null>(null);

  // 앱 진입 시 부재 요약 확인
  useEffect(() => {
    if (!userId) return;
    fetchAbsenceSummary(userId)
      .then(res => { if (res.show) setAbsenceData(res); })
      .catch(() => {});
  }, [userId]);

  const handleInterestsChange = (next: Interest[]) => {
    setInterests(next);
    localStorage.setItem(LS_INTERESTS, JSON.stringify(next));
  };

  // 모든 탭에서 기사 클릭 시 호출 — user_vector 업데이트 + 조회수 기록
  const handleArticleClick = (urlHash: string) => {
    if (userId) {
      recordArticleView(userId, urlHash).catch(() => {});
      logArticleView(userId, urlHash).catch(() => {});
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
          localStorage.setItem('samsun_user_id', uid); // 첫 번째 코드에서 유지
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
            userId={userId}
            interests={interests}
            onNavigateToFeed={() => setActiveTab('my')}
            onArticleClick={handleArticleClick}
            absenceData={absenceData}
            onAbsenceDismiss={() => {
              setAbsenceData(null);
              if (userId) markUserSeen(userId).catch(() => {});
            }}
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
    </div>
  );
}