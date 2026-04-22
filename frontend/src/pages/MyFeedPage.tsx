import { useState, useEffect, useCallback } from 'react';
import { fetchFeed, fetchFeedLlm, postOnboarding, recordArticleView } from '../data/api';
import type { Article } from '../data/articles';
import ArticleCard from '../components/ArticleCard';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';
import type { Interest } from './OnboardingPage';

type FeedItem = Article & { similarity?: number };
type LlmItem  = Article & { reason?: string };

const ALL_INTERESTS: { id: Interest; emoji: string; desc: string }[] = [
  { id: 'AI 연구',    emoji: '🔮', desc: 'MIT TR · The Decoder 등 AI 최신 연구 동향' },
  { id: 'AI 서베이',  emoji: '📘', desc: 'MIT TR · The Decoder 등 AI 서베이 분석·리포트' },
  { id: 'AI 스타트업', emoji: '🚀', desc: 'TechCrunch · VentureBeat 등 AI 스타트업·투자 동향' },
  { id: 'AI 비즈니스', emoji: '💼', desc: 'VentureBeat 등 AI 비즈니스·산업 적용 소식' },
  { id: 'AI 윤리',    emoji: '⚖️', desc: 'The Guardian 등 AI 윤리·규제·사회적 영향' },
  { id: 'AI 커뮤니티', emoji: '💬', desc: 'Reddit 등 AI 커뮤니티 여론·트렌드' },
  { id: '테크 전반',  emoji: '💻', desc: 'The Verge 등 AI를 포함한 테크 업계 전반 소식' },
];

type MyTab = 'feed' | 'llm' | 'bookmarks' | 'interests';

interface Props {
  bm: BookmarkHook;
  interests: Interest[];
  onInterestsChange: (next: Interest[]) => void;
  userId: string;
}

export default function MyFeedPage({ bm, interests, onInterestsChange, userId }: Props) {
  const [tab, setTab]           = useState<MyTab>('feed');
  const [editMode, setEditMode] = useState(false);
  const [detail, setDetail]     = useState<FeedItem | null>(null);
  const [needsRefresh, setNeedsRefresh] = useState(false);

  const [feedArticles, setFeedArticles] = useState<FeedItem[]>([]);
  const [feedLoading, setFeedLoading]   = useState(false);
  const [feedError, setFeedError]       = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(20);

  const [llmArticles, setLlmArticles] = useState<LlmItem[]>([]);
  const [llmLoading, setLlmLoading]   = useState(false);
  const [llmError, setLlmError]       = useState<string | null>(null);
  const [llmLoaded, setLlmLoaded]     = useState(false);

  const bookmarkCount = bm.bookmarked.size;

  const loadFeed = useCallback(() => {
    if (!userId) return;
    setFeedLoading(true);
    setFeedError(null);
    setVisibleCount(20);
    fetchFeed(userId, 50)
      .then(data => {
        setFeedArticles(data);
        setFeedLoading(false);
      })
      .catch(() => { setFeedError('피드를 불러오지 못했어요'); setFeedLoading(false); });
  }, [userId]);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  const loadLlmFeed = useCallback(() => {
    if (!userId) return;
    setLlmLoading(true);
    setLlmError(null);
    fetchFeedLlm(userId)
      .then(data => { setLlmArticles(data); setLlmLoading(false); setLlmLoaded(true); })
      .catch(() => { setLlmError('LLM 추천을 불러오지 못했어요'); setLlmLoading(false); });
  }, [userId]);

  /** 기사 클릭 시 — user_vector 업데이트 + 상세 진입, 복귀 시 피드 재로드 */
  const handleArticleClick = useCallback(async (article: FeedItem) => {
    if (userId) {
      try { await recordArticleView(userId, article.urlHash); } catch { /* silent */ }
    }
    setNeedsRefresh(true);
    setDetail(article);
  }, [userId]);

  const toggleInterest = (id: Interest) => {
    const next = interests.includes(id)
      ? interests.filter(i => i !== id)
      : [...interests, id];
    onInterestsChange(next);
    if (userId) {
      postOnboarding(userId, next).catch(() =>
        console.warn('[MyFeed] 관심 주제 백엔드 동기화 실패 — 로컬 상태만 유지'),
      );
    }
  };

  if (detail) return (
    <DetailPage
      article={detail}
      bookmarked={bm.isBookmarked(detail.urlHash)}
      onBookmark={bm.toggle}
      onBack={() => {
        setDetail(null);
        if (needsRefresh) {
          setNeedsRefresh(false);
          loadFeed();
        }
      }}
    />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <style>{`
        @keyframes fadeSlide { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>

      <header style={{ flexShrink: 0, padding: '22px 20px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
          <div>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 3 }}>내 피드</h1>
            <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)' }}>
              관심 주제 {interests.length}개 · 북마크 {bookmarkCount}개
            </p>
          </div>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            background: 'linear-gradient(135deg,#3081fb 0%,#1960ca 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, fontWeight: 700, color: '#fff',
          }}>AI</div>
        </div>

        <div style={{ display: 'flex', gap: 7, marginTop: 14, paddingBottom: 16, overflowX: 'auto', scrollbarWidth: 'none' }}>
          {([['feed','추천 피드'], ['llm','AI 추천'], ['bookmarks','북마크'], ['interests','관심 주제']] as [MyTab, string][]).map(([id, label]) => (
            <button
              key={id}
              onClick={() => { setTab(id); if (id === 'llm' && !llmLoaded) loadLlmFeed(); }}
              style={{
                flexShrink: 0, fontSize: 12,
                fontWeight: tab === id ? 700 : 400,
                color: tab === id ? '#FFFFFF' : '#6B7684',
                background: tab === id ? '#111111' : '#F2F4F6',
                border: 'none',
                padding: '6px 16px', borderRadius: 20, transition: 'all 0.15s', whiteSpace: 'nowrap',
              }}
            >{label}</button>
          ))}
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', background: 'var(--color-bg)', borderRadius: '32px 32px 0 0' }}>

        {/* ── 추천 피드 ── */}
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
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)', marginBottom: 12 }}>⚠️ {feedError}</p>
                <button onClick={loadFeed} style={{ fontSize: 13, color: 'var(--color-primary)', padding: '8px 18px', border: '1px solid var(--color-primary)', borderRadius: 20 }}>
                  다시 시도
                </button>
              </div>
            )}
            {!feedLoading && !feedError && feedArticles.length === 0 && (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>✨</div>
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)', lineHeight: 1.6 }}>
                  추천 기사가 없어요<br/>관심 주제를 설정해보세요
                </p>
              </div>
            )}
            {!feedLoading && feedArticles.slice(0, visibleCount).map((article, i) => (
              <div key={article.urlHash} style={{ position: 'relative', animation: `fadeSlide 0.25s ${i * 0.04}s ease both` }}>
                <ArticleCard
                  article={article}
                  bookmarked={bm.isBookmarked(article.urlHash)}
                  onBookmark={bm.toggle}
                  onClick={() => handleArticleClick(article)}
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
                {(article as LlmItem).reason && (
                  <div style={{
                    marginTop: 6, fontSize: 11, color: 'var(--color-text-tertiary)',
                    background: 'var(--color-surface-secondary)',
                    padding: '5px 10px', borderRadius: 8,
                    display: 'flex', alignItems: 'center', gap: 5,
                  }}>
                    <span>💡</span>
                    <span>{(article as LlmItem).reason}</span>
                  </div>
                )}
              </div>
            ))}
            {visibleCount < feedArticles.length && !feedLoading && (
              <button onClick={() => setVisibleCount(v => v + 20)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '4px auto 8px', padding: '10px 24px', fontSize: 13, color: 'var(--color-primary)', background: 'var(--color-primary-light)', border: '1px solid var(--color-primary-mid)', borderRadius: 20, cursor: 'pointer' }}>
                기사 더 보기
              </button>
            )}
          </div>
        )}

        {/* ── AI 추천 (LLM) ── */}
        {tab === 'llm' && (
          <div style={{ padding: '12px 16px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ background: 'linear-gradient(135deg,#3081fb 0%,#1960ca 100%)', borderRadius: 12, padding: '12px 16px', marginBottom: 4 }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>✨ AI가 직접 고른 기사</p>
              <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.75)', marginTop: 2 }}>관심사와 읽기 패턴을 분석해 5개를 선별했어요</p>
            </div>
            {llmLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '60px 0', gap: 12 }}>
                <div style={{ width: 24, height: 24, border: '2.5px solid var(--color-border)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                <span style={{ fontSize: 13, color: 'var(--color-text-tertiary)' }}>AI가 기사를 분석 중이에요...</span>
              </div>
            )}
            {!llmLoading && llmError && (
              <div style={{ textAlign: 'center', padding: '48px 0' }}>
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)', marginBottom: 12 }}>⚠️ {llmError}</p>
                <button onClick={loadLlmFeed} style={{ fontSize: 13, color: 'var(--color-primary)', padding: '8px 18px', border: '1px solid var(--color-primary)', borderRadius: 20 }}>다시 시도</button>
              </div>
            )}
            {!llmLoading && !llmError && llmArticles.map((article, i) => (
              <div key={article.urlHash} style={{ position: 'relative', animation: `fadeSlide 0.25s ${i * 0.08}s ease both` }}>
                <ArticleCard
                  article={article}
                  bookmarked={bm.isBookmarked(article.urlHash)}
                  onBookmark={bm.toggle}
                  onClick={() => handleArticleClick(article)}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, padding: '0 4px' }}>
                  <span style={{ fontSize: 13 }}>💡</span>
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.reason ?? '회원님의 취향을 분석해 추천했어요'}</span>
                </div>
              </div>
            ))}
            {!llmLoading && llmLoaded && llmArticles.length === 0 && (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>✨</div>
                <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)' }}>추천할 기사가 없어요</p>
              </div>
            )}
          </div>
        )}

        {/* ── 북마크 ── */}
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
              bm.bookmarkedList.map((article, i) => (
                <ArticleCard key={article.urlHash} article={article}
                  bookmarked={bm.isBookmarked(article.urlHash)} onBookmark={bm.toggle}
                  onClick={() => setDetail(article)}
                  style={{ animation: `fadeSlide 0.25s ${i * 0.05}s ease both` }}
                />
              ))
            )}
          </div>
        )}

        {/* ── 관심 주제 ── */}
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
