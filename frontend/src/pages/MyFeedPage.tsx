import { useState, useEffect, useCallback } from 'react';
import { fetchFeed } from '../data/api';
import type { FeedArticle } from '../data/api';
import ArticleCard from '../components/ArticleCard';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';
import type { Interest } from './OnboardingPage';

const ALL_INTERESTS: { id: Interest; emoji: string; desc: string }[] = [
  { id: '신규 출시/제품', emoji: '🚀', desc: '스냅드래곤, 엑시노스 등 신제품 출시 소식' },
  { id: '기술 이슈',     emoji: '⚡', desc: 'AI·반도체·소프트웨어 핵심 기술 동향' },
  { id: '블록체인/양자', emoji: '🔬', desc: '블록체인, 양자컴퓨팅 관련 뉴스' },
  { id: '대기업',        emoji: '🏢', desc: '구글·MS·애플·Meta·삼성 등 빅테크 동향' },
];

type MyTab = 'feed' | 'bookmarks' | 'interests';

interface Props {
  bm: BookmarkHook;
  interests: Interest[];
  onInterestsChange: (next: Interest[]) => void;
  userId: string;
}

export default function MyFeedPage({ bm, interests, onInterestsChange, userId }: Props) {
  const [tab, setTab]           = useState<MyTab>('feed');
  const [editMode, setEditMode] = useState(false);
  const [detail, setDetail]     = useState<FeedArticle | null>(null);

  const [feedArticles, setFeedArticles] = useState<FeedArticle[]>([]);
  const [feedLoading, setFeedLoading]   = useState(false);
  const [feedError, setFeedError]       = useState<string | null>(null);

  const bookmarkCount = bm.bookmarked.size;

  const loadFeed = useCallback(() => {
    if (!userId) return;
    setFeedLoading(true);
    setFeedError(null);
    fetchFeed(userId, 20)
      .then(data => { setFeedArticles(data); setFeedLoading(false); })
      .catch(() => { setFeedError('피드를 불러오지 못했어요'); setFeedLoading(false); });
  }, [userId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- userId 변경 시 피드 재로드 (loadFeed는 버튼과 공유)
    loadFeed();
  }, [loadFeed]);

  const toggleInterest = (id: Interest) => {
    onInterestsChange(
      interests.includes(id) ? interests.filter(i => i !== id) : [...interests, id]
    );
  };

  if (detail) return (
    <DetailPage
      article={detail}
      bookmarked={bm.isBookmarked(detail.id)}
      onBookmark={bm.toggle}
      onBack={() => setDetail(null)}
    />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <style>{`
        @keyframes fadeSlide { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>

      {/* 헤더 */}
      <header style={{ background: 'var(--color-surface)', borderBottom: '0.5px solid var(--color-border)', flexShrink: 0 }}>
        <div style={{ padding: '18px 20px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 2 }}>내 피드</h1>
            <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
              관심 주제 {interests.length}개 · 북마크 {bookmarkCount}개
            </p>
          </div>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            background: 'linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, fontWeight: 700, color: '#fff',
          }}>AI</div>
        </div>

        {/* 탭 */}
        <div style={{ display: 'flex', marginTop: 12 }}>
          {([['feed','추천 피드'], ['bookmarks','북마크'], ['interests','관심 주제']] as [MyTab, string][]).map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} style={{
              flex: 1, padding: '10px 0', fontSize: 13,
              fontWeight: tab === id ? 600 : 400,
              color: tab === id ? 'var(--color-primary)' : 'var(--color-text-tertiary)',
              borderBottom: `2px solid ${tab === id ? 'var(--color-primary)' : 'transparent'}`,
              transition: 'all 0.15s',
            }}>{label}</button>
          ))}
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>

        {/* ── 추천 피드 탭 */}
        {tab === 'feed' && (
          <div style={{ padding: '12px 16px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {feedLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '60px 0', gap: 12 }}>
                <div style={{ width: 24, height: 24, border: '2.5px solid var(--color-border)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                <span style={{ fontSize: 13, color: 'var(--color-text-tertiary)' }}>벡터 유사도 계산 중...</span>
              </div>
            )}
            {!feedLoading && feedError && (
              <div style={{ textAlign: 'center', padding: '48px 0' }}>
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)', marginBottom: 12 }}>😢 {feedError}</p>
                <button onClick={loadFeed} style={{ fontSize: 13, color: 'var(--color-primary)', padding: '8px 18px', border: '1px solid var(--color-primary)', borderRadius: 20 }}>
                  다시 시도
                </button>
              </div>
            )}
            {!feedLoading && !feedError && feedArticles.length === 0 && (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>🤖</div>
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)', lineHeight: 1.6 }}>
                  추천 기사가 없어요<br/>관심 주제를 설정해보세요
                </p>
              </div>
            )}
            {!feedLoading && feedArticles.map((article, i) => (
              <div key={article.id} style={{ position: 'relative', animation: `fadeSlide 0.25s ${i * 0.04}s ease both` }}>
                <ArticleCard
                  article={article}
                  bookmarked={bm.isBookmarked(article.id)}
                  onBookmark={bm.toggle}
                  onClick={() => setDetail(article)}
                />
                {article.similarity !== undefined && (
                  <div style={{
                    position: 'absolute', top: 10, right: 10,
                    fontSize: 10, fontWeight: 600,
                    color: 'var(--color-primary)',
                    background: 'var(--color-primary-light)',
                    padding: '2px 7px', borderRadius: 6,
                  }}>
                    {Math.round(article.similarity * 100)}% 매칭
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ── 북마크 탭 */}
        {tab === 'bookmarks' && (
          <div style={{ padding: '12px 16px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {bookmarkCount === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>🔖</div>
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)', lineHeight: 1.6 }}>
                  아직 저장한 기사가 없어요<br/>기사 카드의 북마크 버튼을 눌러보세요
                </p>
              </div>
            ) : (
              feedArticles
                .filter(a => bm.isBookmarked(a.id))
                .map((article, i) => (
                  <ArticleCard key={article.id} article={article}
                    bookmarked={bm.isBookmarked(article.id)} onBookmark={bm.toggle}
                    onClick={() => setDetail(article)}
                    style={{ animation: `fadeSlide 0.25s ${i * 0.05}s ease both` }}
                  />
                ))
            )}
          </div>
        )}

        {/* ── 관심 주제 탭 */}
        {tab === 'interests' && (
          <div style={{ padding: '16px 16px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
                선택한 주제 기반으로 피드가 추천돼요
              </p>
              <button onClick={() => setEditMode(!editMode)} style={{
                fontSize: 12, fontWeight: 500, color: 'var(--color-primary)',
                background: 'var(--color-primary-light)', padding: '5px 12px',
                borderRadius: 16, flexShrink: 0,
              }}>
                {editMode ? '완료' : '편집'}
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {ALL_INTERESTS.map(({ id, emoji, desc }) => {
                const on = interests.includes(id);
                return (
                  <button key={id} onClick={() => editMode && toggleInterest(id)} style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '13px 16px', borderRadius: 'var(--radius-lg)', textAlign: 'left',
                    background: on ? 'var(--color-primary-light)' : 'var(--color-surface)',
                    border: `1.5px solid ${on ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    boxShadow: on ? '0 0 0 3px rgba(79,70,229,0.06)' : 'var(--shadow-card)',
                    opacity: !editMode && !on ? 0.5 : 1,
                    transition: 'all 0.15s',
                  }}>
                    <span style={{ fontSize: 20 }}>{emoji}</span>
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: on ? 'var(--color-primary)' : 'var(--color-text-primary)' }}>{id}</p>
                      <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginTop: 1 }}>{desc}</p>
                    </div>
                    {editMode && (
                      <div style={{
                        width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                        background: on ? 'var(--color-primary)' : 'transparent',
                        border: `1.5px solid ${on ? 'var(--color-primary)' : 'var(--color-border-medium)'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.15s',
                      }}>
                        {on && <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                          <path d="M20 6L9 17L4 12" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>}
                      </div>
                    )}
                    {!editMode && on && (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <path d="M20 6L9 17L4 12" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
