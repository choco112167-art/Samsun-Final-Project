import { useState } from 'react';
import TabBar, { type TabId } from './components/TabBar';
import OnboardingPage, { type Interest } from './pages/OnboardingPage';
import HomePage from './pages/HomePage';
import CategoryPage from './pages/CategoryPage';
import HotPage from './pages/HotPage';
import SearchPage from './pages/SearchPage';
import MyFeedPage from './pages/MyFeedPage';
import { useBookmarks } from './hooks/useBookmarks';

export default function App() {
  const [onboarded, setOnboarded] = useState(false);
  const [interests, setInterests] = useState<Interest[]>([]);
  const [userId, setUserId]       = useState('');
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const bm = useBookmarks();

  if (!onboarded) {
    return (
      <div style={{ height: '100dvh', maxWidth: 480, margin: '0 auto', overflow: 'hidden' }}>
        <OnboardingPage onDone={(selected, uid) => {
          setInterests(selected);
          setUserId(uid);
          setOnboarded(true);
        }} />
      </div>
    );
  }

  const renderPage = () => {
    switch (activeTab) {
      case 'home':     return <HomePage bm={bm} />;
      case 'category': return <CategoryPage bm={bm} />;
      case 'hot':      return <HotPage bm={bm} />;
      case 'search':   return <SearchPage bm={bm} />;
      case 'my':       return <MyFeedPage bm={bm} interests={interests} onInterestsChange={setInterests} userId={userId} />;
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100dvh', maxWidth: 480, margin: '0 auto',
      background: 'var(--color-bg)', overflow: 'hidden',
    }}>
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {renderPage()}
      </div>
      <TabBar activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
