import { useState, useEffect } from 'react';
import TabBar, { type TabId } from './components/TabBar';
import OnboardingPage, { type Interest } from './pages/OnboardingPage';
import HomePage from './pages/HomePage';
import CategoryPage from './pages/CategoryPage';
import HotPage from './pages/HotPage';
import SearchPage from './pages/SearchPage';
import MyFeedPage from './pages/MyFeedPage';
import ReviewPage from './pages/ReviewPage';
import { useBookmarks } from './hooks/useBookmarks';
import { useTonePreference } from './hooks/useTonePreference';
import { recordArticleView, fetchAbsenceSummary, markUserSeen, type AbsenceSummaryResponse } from './data/api';
import { getSamsunUserId, tossHaptic } from './lib/toss';
import { goToOnboardingResetUrl, resetDemoState } from './utils/resetDemoState';

const LS_ONBOARDED = 'samsun_onboarded';
const LS_INTERESTS = 'samsun_interests';
const BUILD_MARKER = 'b214982+demo-reset-20260520';

/** 개발 중 강제 온보딩 화면 — 배포 전 반드시 false */
const DEV_FORCE_ONBOARDING = false;

function loadInterests(): Interest[] {
  try { return JSON.parse(localStorage.getItem(LS_INTERESTS) ?? '[]'); }
  catch { return []; }
}

function hasOnboardingResetQuery(): boolean {
  const params = new URLSearchParams(window.location.search);
  return params.get('resetOnboarding') === '1' || params.get('onboarding') === '1';
}

function hasReviewQuery(): boolean {
  return new URLSearchParams(window.location.search).get('review') === '1';
}

function initialOnboardedState(): boolean {
  if (hasOnboardingResetQuery() || DEV_FORCE_ONBOARDING) return false;
  const storedInterests = loadInterests();
  return localStorage.getItem(LS_ONBOARDED) === 'true' && storedInterests.length > 0 && Boolean(localStorage.getItem('samsun_user_id'));
}

export default function App() {
  const [onboarded, setOnboarded] = useState(initialOnboardedState);
  const [interests, setInterests] = useState<Interest[]>(() => (onboarded ? loadInterests() : []));
  const [userId, setUserId] = useState<string | null>(() => (onboarded ? getSamsunUserId() : null));
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const bm = useBookmarks();
  const { tone, setTone } = useTonePreference();
  const [absenceData, setAbsenceData] = useState<AbsenceSummaryResponse | null>(null);
  const [reviewMode] = useState(hasReviewQuery);

  useEffect(() => {
    console.log(`[SamsunNews] build ${BUILD_MARKER} onboarding reset enabled`);
    if (!hasOnboardingResetQuery()) return;

    resetDemoState().finally(() => {
      setInterests([]);
      setUserId(null);
      setAbsenceData(null);
      setActiveTab('home');
      setOnboarded(false);
      window.history.replaceState(null, '', window.location.pathname || '/');
    });
  }, []);

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

  const resetOnboarding = () => {
    resetDemoState().finally(() => {
      setInterests([]);
      setUserId(null);
      setAbsenceData(null);
      setActiveTab('home');
      setOnboarded(false);
      goToOnboardingResetUrl();
    });
  };

  // 모든 탭에서 기사 클릭 시 호출 — user_vector 업데이트 + 조회수 기록
  const handleArticleClick = (urlHash: string) => {
    if (userId) {
      tossHaptic().catch(() => {});
      recordArticleView(userId, urlHash).catch(() => {});
    }
  };

  if (reviewMode) return <ReviewPage />;

  if (!onboarded || !userId || interests.length === 0) {
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
            tone={tone}
            onToneChange={setTone}
          />
        );
      case 'category': return <CategoryPage bm={bm} onArticleClick={handleArticleClick} tone={tone} onToneChange={setTone} />;
      case 'hot':      return <HotPage bm={bm} onArticleClick={handleArticleClick} tone={tone} onToneChange={setTone} />;
      case 'search':   return <SearchPage bm={bm} onArticleClick={handleArticleClick} tone={tone} onToneChange={setTone} />;
      case 'my':
        return (
          <MyFeedPage
            key={activeTab}
            bm={bm}
            interests={interests}
            onInterestsChange={handleInterestsChange}
            onResetOnboarding={resetOnboarding}
            userId={userId}
            tone={tone}
            onToneChange={setTone}
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
