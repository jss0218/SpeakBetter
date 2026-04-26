import { useState } from 'react';
import { ImageWithFallback } from './components/figma/ImageWithFallback';
import { LiveSession } from './components/LiveSession';
import { SetupFlow } from './components/SetupFlow';

type Screen = 'landing' | 'setup' | 'session' | 'results';

interface FeedbackItem {
  timestamp: string;
  text: string;
  category: 'filler' | 'pacing' | 'eyecontact';
}

function Logo() {
  return (
    <div className="flex items-center gap-1">
      <span style={{ fontWeight: 500 }}>speak</span>
      <span style={{ fontWeight: 500, color: '#E8B84B' }}>B</span>
      <span style={{ fontWeight: 500 }}>etter</span>
    </div>
  );
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
  const [progress, setProgress] = useState(45);

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
              { stat: '10,000+', label: 'sessions' },
              { stat: '94%', label: 'confidence improvement' },
              { stat: 'Real-time', label: 'AI feedback' }
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
          setCurrentScreen('session');
        }}
        onBack={() => setCurrentScreen('landing')}
      />
    );
  }

  if (currentScreen === 'session') {
    return (
      <LiveSession
        audienceSize={Math.min(20, Math.max(1, sessionConfig.audienceCount))}
        duration={sessionConfig.duration}
        onEndSession={() => setCurrentScreen('results')}
      />
    );
  }

  if (currentScreen === 'results') {
    const feedbackItems: FeedbackItem[] = [
      { timestamp: '0:12', text: 'Strong opening with clear eye contact', category: 'eyecontact' },
      { timestamp: '0:42', text: 'You used a filler word during your transition', category: 'filler' },
      { timestamp: '1:15', text: 'Speaking pace increased — consider slowing down', category: 'pacing' },
      { timestamp: '1:48', text: 'Good pause before key statistic', category: 'pacing' },
      { timestamp: '2:03', text: 'Another filler word detected', category: 'filler' },
      { timestamp: '2:34', text: 'Excellent maintained eye contact in closing', category: 'eyecontact' }
    ];

    const getCategoryColor = (category: string) => {
      switch (category) {
        case 'filler': return '#F59E0B';
        case 'pacing': return '#14B8A6';
        case 'eyecontact': return '#A855F7';
        default: return '#E8B84B';
      }
    };

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
            Score: 74/100
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
                {feedbackItems.map((item, i) => (
                  <div key={i}>
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
                          {item.category === 'filler' ? 'Filler word' : item.category === 'pacing' ? 'Pacing' : 'Eye contact'}
                        </div>
                      </div>
                    </div>
                    {i < feedbackItems.length - 1 && (
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
            </div>

            <div className="px-4">
              <div
                className="w-full h-2 rounded-full overflow-hidden cursor-pointer"
                style={{ backgroundColor: 'rgba(26, 26, 26, 0.1)' }}
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const newProgress = (x / rect.width) * 100;
                  setProgress(newProgress);
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
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask anything about your session..."
                  className="flex-1 px-4 py-3 rounded-xl"
                  style={{
                    backgroundColor: '#FAFAF7',
                    border: '0.5px solid rgba(26, 26, 26, 0.1)',
                    outline: 'none'
                  }}
                />
                <button
                  className="px-6 py-3 rounded-xl"
                  style={{
                    backgroundColor: '#E8B84B',
                    color: '#1A1A1A',
                    fontWeight: 500,
                    border: '0.5px solid rgba(26, 26, 26, 0.1)'
                  }}
                >
                  Send
                </button>
              </div>
            </div>

            <button
              onClick={() => setCurrentScreen('landing')}
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
              <div className="text-4xl mb-1" style={{ fontWeight: 500 }}>142 wpm</div>
              <p className="text-sm opacity-60 mb-4">Ideal: 130–160 wpm</p>
              <div className="flex gap-1 h-12 items-end">
                {[30, 50, 70, 85, 95, 80, 75, 90].map((height, i) => (
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
              <div className="text-4xl mb-3" style={{ fontWeight: 500 }}>3</div>
              <div className="space-y-1" style={{ color: '#E8B84B' }}>
                <div>uh × 2</div>
                <div>um × 1</div>
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
                      strokeDashoffset={`${2 * Math.PI * 56 * (1 - 0.98)}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center text-3xl" style={{ fontWeight: 500 }}>
                    98%
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
                Your strongest moments came when you paused before key statistics — consider
                using this technique more consistently throughout.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
