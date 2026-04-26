import { useEffect, useRef, useState } from 'react';
import { ImageWithFallback } from './components/figma/ImageWithFallback';
import { Calibration } from './components/Calibration';
import { LiveSession } from './components/LiveSession';
import { Logo } from './components/Logo';
import { SetupFlow } from './components/SetupFlow';

type Screen = 'landing' | 'setup' | 'calibration' | 'session' | 'results';

interface FeedbackItem {
  timestamp: string;
  text: string;
  category: 'filler' | 'pacing' | 'eyecontact' | 'engagement';
}

interface SessionBreakdown {
  overall_score?: number;
  high_moments?: Array<{
    timestamp_seconds?: number;
    description?: string;
    transcript_snippet?: string;
    timeline_kind?: string;
  }>;
  low_moments?: Array<{
    timestamp_seconds?: number;
    description?: string;
    transcript_snippet?: string;
    timeline_kind?: string;
  }>;
  strengths?: string[];
  improvements?: string[];
  next_session_focus?: string;
  argument_feedback?: string;
}

interface SessionResult {
  breakdown: SessionBreakdown;
  engagementHistory: Array<Record<string, unknown>>;
  recordingUrl: string | null;
}

function mapTimelineKind(kind: string | undefined, isHigh: boolean): FeedbackItem['category'] {
  if (kind === 'filler') return 'filler';
  if (kind === 'eye_contact') return 'eyecontact';
  if (kind === 'engagement') return 'engagement';
  if (kind === 'pace') return 'pacing';
  return isHigh ? 'eyecontact' : 'pacing';
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-full opacity-60 hover:opacity-100 transition-opacity"
      style={{ border: '0.5px solid rgba(26, 26, 26, 0.2)' }}
    >
      ← Back
    </button>
  );
}

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('landing');
  const [sessionConfig, setSessionConfig] = useState({
    practiceType: 'presentation' as 'pitch' | 'presentation' | 'interview',
    audienceCount: 12,
    duration: 5,
    colorEngagement: false
  });
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [progress, setProgress] = useState(45);
  const [sessionResult, setSessionResult] = useState<SessionResult | null>(null);
  const resultsVideoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    return () => {
      if (sessionResult?.recordingUrl) {
        URL.revokeObjectURL(sessionResult.recordingUrl);
      }
    };
  }, [sessionResult]);

  const sendChat = async () => {
    const question = chatInput.trim();
    if (!question || chatLoading) return;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: question }]);
    setChatLoading(true);
    try {
      const agentBase = import.meta.env.VITE_COACH_AGENT_URL || 'http://localhost:8000';
      const res = await fetch(`${agentBase}/rest/post`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        throw new Error(`chat_failed_${res.status}`);
      }
      const data = await res.json();
      const answer = typeof data.answer === 'string' && data.answer.trim()
        ? data.answer.trim()
        : 'I could not generate a useful follow-up answer.';
      setChatMessages(prev => [...prev, { role: 'assistant', content: answer }]);
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Could not reach the coach. Please try again.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  if (currentScreen === 'landing') {
    return (
      <div className="min-h-screen" style={{ backgroundColor: '#FAFAF7', color: '#1A1A1A' }}>
        <nav className="px-8 py-6 flex items-center justify-between max-w-7xl mx-auto">
          <Logo />
          <button
            onClick={() => setCurrentScreen('setup')}
            className="px-6 py-2.5 rounded-full"
            style={{
              backgroundColor: '#E8B84B',
              color: '#1A1A1A',
              fontWeight: 500,
              border: '0.5px solid rgba(26, 26, 26, 0.1)'
            }}
          >
            Get started
          </button>
        </nav>

        <section className="px-8 py-20 max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <h1 className="text-5xl md:text-6xl" style={{ fontWeight: 500, lineHeight: '1.1' }}>
                Practice like the room is real.
              </h1>
              <p className="text-xl opacity-70">
                AI-powered public speaking training with a live reactive audience.
              </p>
              <button
                onClick={() => setCurrentScreen('setup')}
                className="px-8 py-4 rounded-full"
                style={{
                  backgroundColor: '#E8B84B',
                  color: '#1A1A1A',
                  fontWeight: 500,
                  border: '0.5px solid rgba(26, 26, 26, 0.1)'
                }}
              >
                Start practicing
              </button>
            </div>
            <div className="rounded-2xl overflow-hidden" style={{ border: '0.5px solid rgba(26, 26, 26, 0.1)' }}>
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=800&h=600&fit=crop"
                alt="Confident speaker at podium"
                className="w-full h-[400px] object-cover"
              />
            </div>
          </div>
        </section>

        <section className="px-8 py-12 max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { stat: 'Live audience', label: 'AI-driven faces that react to your delivery in real time' },
              { stat: 'Multi-agent AI', label: 'Speech, vision, and argument analyzed simultaneously' },
              { stat: 'Full breakdown', label: 'Post-session coaching grounded in your actual performance' }
            ].map((item, i) => (
              <div
                key={i}
                className="p-8 rounded-2xl relative"
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '0.5px solid rgba(26, 26, 26, 0.1)'
                }}
              >
                <div
                  className="absolute top-0 left-8 right-8 h-1 rounded-full"
                  style={{ backgroundColor: '#E8B84B' }}
                />
                <div className="text-3xl" style={{ fontWeight: 500 }}>{item.stat}</div>
                <div className="mt-2 opacity-70">{item.label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="px-8 py-20 max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: 'Presentations',
                icon: '📊',
                description: 'Master your next business presentation with real-time feedback on pacing and clarity.'
              },
              {
                title: 'Speeches',
                icon: '🎤',
                description: 'Build confidence for keynotes and events with AI-powered audience simulation.'
              },
              {
                title: 'Pitches',
                icon: '💡',
                description: 'Perfect your investor pitch with instant analysis of delivery and engagement.'
              }
            ].map((service, i) => (
              <div
                key={i}
                className="p-8 rounded-2xl"
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '0.5px solid rgba(26, 26, 26, 0.1)'
                }}
              >
                <div className="text-4xl mb-4">{service.icon}</div>
                <h3 className="mb-3" style={{ fontWeight: 500 }}>{service.title}</h3>
                <p className="opacity-70">{service.description}</p>
              </div>
            ))}
          </div>
        </section>

        <footer className="px-8 py-12 max-w-7xl mx-auto border-t" style={{ borderColor: 'rgba(26, 26, 26, 0.1)' }}>
          <Logo />
          <p className="mt-2 opacity-50">Practice with confidence</p>
        </footer>
      </div>
    );
  }

  if (currentScreen === 'setup') {
    return (
      <SetupFlow
        onStart={(config) => {
          setSessionConfig(config);
          setCurrentScreen('calibration');
        }}
        onBack={() => setCurrentScreen('landing')}
      />
    );
  }

  if (currentScreen === 'calibration') {
    return (
      <Calibration
        onBegin={() => setCurrentScreen('session')}
        onBack={() => setCurrentScreen('setup')}
      />
    );
  }

  if (currentScreen === 'session') {
    return (
      <LiveSession
        audienceSize={Math.min(20, Math.max(1, sessionConfig.audienceCount))}
        duration={sessionConfig.duration}
        practiceType={sessionConfig.practiceType}
        colorEngagement={sessionConfig.colorEngagement}
        onEndSession={(result) => {
          setSessionResult(result);
          setChatMessages([]);
          setChatInput('');
          setCurrentScreen('results');
        }}
      />
    );
  }

  if (currentScreen === 'results') {
    const breakdown = sessionResult?.breakdown || {};
    const engagementHistory = sessionResult?.engagementHistory || [];
    const feedbackItems: FeedbackItem[] = [
      ...((breakdown.high_moments || []).map((item) => ({
        timestamp: formatTimestamp(item.timestamp_seconds),
        text: String(item.description || 'Strong moment').trim(),
        category: mapTimelineKind(item.timeline_kind, true),
      }))),
      ...((breakdown.low_moments || []).map((item) => ({
        timestamp: formatTimestamp(item.timestamp_seconds),
        text: String(item.description || 'Moment to improve').trim(),
        category: mapTimelineKind(item.timeline_kind, false),
      }))),
    ].sort((a, b) => timestampToSeconds(a.timestamp) - timestampToSeconds(b.timestamp));

    const avgEngagement = engagementHistory.length
      ? Math.round(
          (engagementHistory.reduce((sum, item) => sum + Number(item.score || 0), 0) / engagementHistory.length) * 100
        )
      : null;
    const score = Number.isFinite(breakdown.overall_score) ? Math.round(Number(breakdown.overall_score)) : 0;
    const strengths = (breakdown.strengths || []).slice(0, 3);
    const improvements = (breakdown.improvements || []).slice(0, 3);
    const highs = (breakdown.high_moments || []).length;
    const lows = (breakdown.low_moments || []).length;
    const recordingUrl = sessionResult?.recordingUrl || null;

    const getCategoryColor = (category: string) => {
      switch (category) {
        case 'filler': return '#F59E0B';
        case 'pacing': return '#14B8A6';
        case 'eyecontact': return '#A855F7';
        case 'engagement': return '#0D9488';
        default: return '#E8B84B';
      }
    };

    const timelineRows = feedbackItems.length
      ? feedbackItems
      : [{ timestamp: '0:00', text: 'No detailed moment data was returned for this run.', category: 'pacing' as const }];

    return (
      <div className="min-h-screen" style={{ backgroundColor: '#FAFAF7', color: '#1A1A1A' }}>
        <div className="px-8 py-5 flex items-center justify-between border-b" style={{ borderColor: 'rgba(26, 26, 26, 0.1)' }}>
          <Logo />
          <div className="opacity-60">
            {sessionConfig.practiceType === 'pitch'
              ? 'Investor Pitch'
              : sessionConfig.practiceType === 'presentation'
                ? 'Presentation'
                : sessionConfig.practiceType === 'interview'
                  ? 'Interview'
                  : 'Session'} · {sessionConfig.audienceCount} people · {sessionConfig.duration} min
          </div>
          <div
            className="px-5 py-2 rounded-full"
            style={{ backgroundColor: '#E8B84B', color: '#1A1A1A', fontWeight: 500 }}
          >
            Score: {score}/100
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6 p-8 max-w-[1600px] mx-auto">
          <div className="col-span-3">
            <div
              className="p-6 rounded-2xl h-[calc(100vh-180px)] overflow-y-auto"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h2 className="mb-6" style={{ fontWeight: 500 }}>Feedback timeline</h2>
              <div className="space-y-4">
                {timelineRows.map((item, i) => (
                  <div key={`${item.timestamp}-${i}`}>
                    <div className="flex items-start gap-3">
                      <div
                        className="px-2 py-1 rounded text-sm shrink-0"
                        style={{ backgroundColor: '#E8B84B', color: '#1A1A1A', fontWeight: 500 }}
                      >
                        {item.timestamp}
                      </div>
                      <div>
                        <p className="text-sm leading-relaxed">{item.text}</p>
                        <div
                          className="inline-block px-2 py-0.5 rounded mt-2 text-xs"
                          style={{
                            backgroundColor: `${getCategoryColor(item.category)}20`,
                            color: getCategoryColor(item.category),
                            fontWeight: 500
                          }}
                        >
                          {item.category === 'filler'
                            ? 'Filler word'
                            : item.category === 'pacing'
                              ? 'Pacing'
                              : item.category === 'eyecontact'
                                ? 'Eye contact'
                                : 'Engagement'}
                        </div>
                      </div>
                    </div>
                    {i < timelineRows.length - 1 && (
                      <div className="my-4 border-t" style={{ borderColor: 'rgba(26, 26, 26, 0.05)' }} />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="col-span-5 space-y-6">
            <div
              className="rounded-2xl overflow-hidden"
              style={{ backgroundColor: '#2A2A3E', aspectRatio: '16/9' }}
            >
              {recordingUrl ? (
                <video
                  ref={resultsVideoRef}
                  src={recordingUrl}
                  controls
                  playsInline
                  className="w-full h-full object-cover bg-black"
                  onTimeUpdate={(event) => {
                    const video = event.currentTarget;
                    if (!video.duration) return;
                    setProgress((video.currentTime / video.duration) * 100);
                  }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <button
                    className="w-20 h-20 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: '#E8B84B' }}
                  >
                    <div
                      style={{
                        width: 0,
                        height: 0,
                        borderLeft: '20px solid #1A1A1A',
                        borderTop: '12px solid transparent',
                        borderBottom: '12px solid transparent',
                        marginLeft: '4px'
                      }}
                    />
                  </button>
                </div>
              )}
            </div>

            <div className="px-4">
              <div
                className="w-full h-2 rounded-full overflow-hidden cursor-pointer"
                style={{ backgroundColor: 'rgba(26, 26, 26, 0.1)' }}
                onClick={(e) => {
                  const video = resultsVideoRef.current;
                  if (!video || !video.duration) return;
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const newProgress = (x / rect.width) * 100;
                  setProgress(newProgress);
                  video.currentTime = (newProgress / 100) * video.duration;
                }}
              >
                <div
                  className="h-full rounded-full relative"
                  style={{ backgroundColor: '#E8B84B', width: `${progress}%` }}
                >
                  <div
                    className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full"
                    style={{ backgroundColor: '#E8B84B', border: '2px solid #1A1A1A' }}
                  />
                </div>
              </div>
            </div>

            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h3 className="mb-3" style={{ fontWeight: 500 }}>Ask a follow-up</h3>
              {chatMessages.length > 0 && (
                <div className="mb-3 space-y-2 max-h-48 overflow-y-auto">
                  {chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className="px-3 py-2 rounded-xl text-sm"
                      style={{
                        backgroundColor: msg.role === 'user' ? '#F0F0EB' : '#FEF9EC',
                        textAlign: msg.role === 'user' ? 'right' : 'left',
                        border: msg.role === 'assistant' ? '0.5px solid rgba(232,184,75,0.3)' : 'none',
                      }}
                    >
                      {msg.role === 'assistant' && (
                        <span className="text-xs font-medium mr-1" style={{ color: '#E8B84B' }}>Coach</span>
                      )}
                      {msg.content}
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="px-3 py-2 rounded-xl text-sm" style={{ backgroundColor: '#FEF9EC', color: '#888' }}>
                      <span className="text-xs font-medium mr-1" style={{ color: '#E8B84B' }}>Coach</span>
                      Thinking...
                    </div>
                  )}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendChat()}
                  placeholder="Ask anything about your session..."
                  className="flex-1 px-4 py-3 rounded-xl"
                  style={{
                    backgroundColor: '#FAFAF7',
                    border: '0.5px solid rgba(26, 26, 26, 0.1)',
                    outline: 'none'
                  }}
                />
                <button
                  onClick={sendChat}
                  disabled={chatLoading}
                  className="px-6 py-3 rounded-xl"
                  style={{
                    backgroundColor: '#E8B84B',
                    color: '#1A1A1A',
                    fontWeight: 500,
                    border: '0.5px solid rgba(26, 26, 26, 0.1)',
                    opacity: chatLoading ? 0.6 : 1,
                  }}
                >
                  Send
                </button>
              </div>
            </div>

            <button
              onClick={() => {
                if (sessionResult?.recordingUrl) {
                  URL.revokeObjectURL(sessionResult.recordingUrl);
                }
                setSessionResult(null);
                setCurrentScreen('landing');
              }}
              className="w-full py-4 rounded-full"
              style={{
                backgroundColor: '#E8B84B',
                color: '#1A1A1A',
                fontWeight: 500,
                border: '0.5px solid rgba(26, 26, 26, 0.1)'
              }}
            >
              Return to home
            </button>
          </div>

          <div className="col-span-4 space-y-4">
            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h3 className="mb-2 opacity-60">Pace</h3>
              <div className="text-4xl mb-1" style={{ fontWeight: 500 }}>
                {avgEngagement !== null ? `${avgEngagement}%` : '--'}
              </div>
              <p className="text-sm opacity-60 mb-4">Average engagement across the session</p>
              <div className="flex gap-1 h-12 items-end">
                {(engagementHistory.length ? engagementHistory.slice(-8).map((entry) => Math.max(8, Math.round(Number(entry.score || 0) * 100))) : [25, 35, 45, 55, 60, 58, 62, 68]).map((height, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-t"
                    style={{ backgroundColor: '#E8B84B', height: `${height}%` }}
                  />
                ))}
              </div>
            </div>

            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h3 className="mb-2 opacity-60">Filler words</h3>
              <div className="text-4xl mb-3" style={{ fontWeight: 500 }}>{improvements.length}</div>
              <div className="space-y-1" style={{ color: '#E8B84B' }}>
                {improvements.length ? improvements.map((item, index) => (
                  <div key={index}>{item}</div>
                )) : <div>No improvement notes returned</div>}
              </div>
            </div>

            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h3 className="mb-4 opacity-60">Eye contact</h3>
              <div className="flex items-center justify-center">
                <div className="relative w-32 h-32">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="rgba(26, 26, 26, 0.1)"
                      strokeWidth="8"
                      fill="none"
                    />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="#E8B84B"
                      strokeWidth="8"
                      fill="none"
                      strokeDasharray={`${2 * Math.PI * 56}`}
                      strokeDashoffset={`${2 * Math.PI * 56 * (1 - score / 100)}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center text-3xl" style={{ fontWeight: 500 }}>
                    {score}%
                  </div>
                </div>
              </div>
            </div>

            <div
              className="p-6 rounded-2xl"
              style={{
                backgroundColor: '#FFFBEF',
                border: '1px solid #E8B84B'
              }}
            >
              <h3 className="mb-2" style={{ color: '#E8B84B', fontWeight: 500 }}>Key insight</h3>
              <p className="text-sm leading-relaxed">
                {breakdown.next_session_focus || breakdown.argument_feedback || 'No final coaching summary was returned for this session.'}
              </p>
            </div>

            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h3 className="mb-2 opacity-60">Strengths</h3>
              <div className="space-y-2">
                {strengths.length ? strengths.map((item, index) => (
                  <div key={index}>{item}</div>
                )) : <div className="opacity-60">No strengths returned</div>}
              </div>
            </div>

            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
            >
              <h3 className="mb-2 opacity-60">Session shape</h3>
              <div className="space-y-1 opacity-80">
                <div>High moments: {highs}</div>
                <div>Low moments: {lows}</div>
                <div>Audience size: {sessionConfig.audienceCount}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

function formatTimestamp(seconds?: number) {
  const total = Math.max(0, Math.round(Number(seconds || 0)));
  const mins = Math.floor(total / 60);
  const remainder = total % 60;
  return `${mins}:${String(remainder).padStart(2, '0')}`;
}

function timestampToSeconds(value: string) {
  const [mins, secs] = value.split(':').map(Number);
  return (mins || 0) * 60 + (secs || 0);
}
