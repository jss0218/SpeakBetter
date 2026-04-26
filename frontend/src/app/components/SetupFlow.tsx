import { useState } from 'react';
import { Logo } from './Logo';

interface SessionConfig {
  practiceType: 'pitch' | 'presentation' | 'interview';
  audienceCount: number;
  duration: number;
  colorEngagement: boolean;
}

interface SetupFlowProps {
  onStart: (config: SessionConfig) => void;
  onBack: () => void;
}

export function SetupFlow({ onStart, onBack }: SetupFlowProps) {
  const [practiceType, setPracticeType] = useState<'pitch' | 'presentation' | 'interview' | null>(null);
  const [audienceCount, setAudienceCount] = useState(12);
  const [duration, setDuration] = useState(5);
  const [colorEngagement, setColorEngagement] = useState(false);

  const canStart = practiceType !== null && audienceCount > 0 && duration > 0;

  const getAudienceSizeLabel = (count: number) => {
    if (count <= 10) return 'Small audience — intimate setting';
    if (count <= 30) return 'Medium audience — conference room';
    return 'Large audience — lecture hall';
  };

  const handleStart = () => {
    if (canStart && practiceType) {
      onStart({
        practiceType,
        audienceCount,
        duration,
        colorEngagement
      });
    }
  };

  return (
    <div className="min-h-screen pb-32" style={{ backgroundColor: '#FAFAF7', color: '#1A1A1A' }}>
      <div className="px-8 py-6">
        <div className="max-w-[520px] mx-auto flex items-center justify-between">
          <Logo height={60} />
          <button
            onClick={onBack}
            className="px-4 py-2 rounded-full opacity-60 hover:opacity-100 transition-opacity"
            style={{ border: '0.5px solid rgba(26, 26, 26, 0.2)' }}
          >
            ← Back
          </button>
        </div>
      </div>

      <div className="px-8 pt-12">
        <div className="max-w-[520px] mx-auto space-y-10">
          <div className="text-center mb-8">
            <h1 className="text-4xl mb-3" style={{ fontWeight: 500 }}>
              A few quick questions.
            </h1>
            <p style={{ color: '#888888' }}>
              We'll tailor your session to match.
            </p>
          </div>

          <div className="space-y-10">
            <div>
              <h2 className="text-lg mb-1" style={{ fontWeight: 500 }}>
                What are you practicing for?
              </h2>
              <p className="text-sm mb-6" style={{ color: '#999999' }}>
                We'll shape your Q&A around this.
              </p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  {
                    id: 'pitch' as const,
                    title: 'Investor Pitch',
                    icon: '💰',
                    subtext: "We'll challenge your weakest claim like a skeptical investor would."
                  },
                  {
                    id: 'presentation' as const,
                    title: 'Presentation',
                    icon: '📊',
                    subtext: "We'll question your logic like a critical audience member would."
                  },
                  {
                    id: 'interview' as const,
                    title: 'Interview',
                    icon: '💬',
                    subtext: "We'll find the gap in your answers and push back hard."
                  }
                ].map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setPracticeType(type.id)}
                    className="text-center transition-all duration-200"
                    style={{
                      backgroundColor: practiceType === type.id ? '#FFFBEF' : '#FFFFFF',
                      border: practiceType === type.id
                        ? '2px solid #E8B84B'
                        : '0.5px solid #E8E6E0',
                      borderRadius: '14px',
                      padding: '20px 16px',
                      opacity: practiceType && practiceType !== type.id ? 0.6 : 1
                    }}
                  >
                    <div className="text-2xl mb-2" style={{ color: '#E8B84B' }}>{type.icon}</div>
                    <h3 className="text-sm mb-1" style={{ fontWeight: 500 }}>
                      {type.title}
                    </h3>
                    <p className="text-xs leading-relaxed" style={{ color: '#999999' }}>
                      {type.subtext}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <h2 className="text-lg mb-1" style={{ fontWeight: 500 }}>
                How many people are you talking to?
              </h2>
              <p className="text-sm mb-6" style={{ color: '#999999' }}>
                This sets your audience size.
              </p>
              <div className="flex items-center justify-center gap-6 mb-3">
                <button
                  onClick={() => setAudienceCount(Math.max(1, audienceCount - 1))}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all"
                  style={{
                    border: '0.5px solid #E8E6E0',
                    backgroundColor: '#FFFFFF',
                    color: '#666666',
                    fontSize: '20px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#E8B84B';
                    e.currentTarget.style.color = '#E8B84B';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#E8E6E0';
                    e.currentTarget.style.color = '#666666';
                  }}
                >
                  −
                </button>
                <div className="text-5xl text-center" style={{ fontWeight: 500, minWidth: '80px' }}>
                  {audienceCount}
                </div>
                <button
                  onClick={() => setAudienceCount(Math.min(20, audienceCount + 1))}
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all"
                  style={{
                    border: '0.5px solid #E8E6E0',
                    backgroundColor: '#FFFFFF',
                    color: '#666666',
                    fontSize: '20px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#E8B84B';
                    e.currentTarget.style.color = '#E8B84B';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#E8E6E0';
                    e.currentTarget.style.color = '#666666';
                  }}
                >
                  +
                </button>
              </div>
              <p className="text-center text-sm italic" style={{ color: '#999999' }}>
                {getAudienceSizeLabel(audienceCount)}
              </p>
            </div>

            <div>
              <h2 className="text-lg mb-1" style={{ fontWeight: 500 }}>
                How long do you have?
              </h2>
              <p className="text-sm mb-6" style={{ color: '#999999' }}>
                We'll count you down and prompt Q&A when time's up.
              </p>
              <div className="px-4">
                <input
                  type="range"
                  min="1"
                  max="20"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full"
                  style={{
                    height: '4px',
                    borderRadius: '2px',
                    background: `linear-gradient(to right, #E8B84B 0%, #E8B84B ${((duration - 1) / 19) * 100}%, #E8E6E0 ${((duration - 1) / 19) * 100}%, #E8E6E0 100%)`,
                    outline: 'none',
                    appearance: 'none',
                    WebkitAppearance: 'none'
                  }}
                />
                <style>{`
                  input[type="range"]::-webkit-slider-thumb {
                    appearance: none;
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background: #FFFFFF;
                    border: 2px solid #E8B84B;
                    cursor: pointer;
                  }
                  input[type="range"]::-moz-range-thumb {
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background: #FFFFFF;
                    border: 2px solid #E8B84B;
                    cursor: pointer;
                  }
                `}</style>
                <div className="text-center mt-4" style={{ color: '#E8B84B', fontWeight: 500, fontSize: '16px' }}>
                  {duration} {duration === 1 ? 'minute' : 'minutes'}
                </div>
              </div>
            </div>

            <div>
              <h2 className="text-lg mb-1" style={{ fontWeight: 500 }}>
                Engagement feedback style
              </h2>
              <p className="text-sm mb-2" style={{ color: '#999999' }}>
                By default, engagement shows through your audience's facial expressions — just like a real room.
              </p>
              <p className="text-sm mb-6" style={{ color: '#999999' }}>
                Turn this on if you'd like a visual color indicator as well.
              </p>

              <div className="flex items-start gap-4 mb-4">
                <button
                  onClick={() => setColorEngagement(!colorEngagement)}
                  className="relative transition-all duration-200"
                  style={{
                    width: '44px',
                    height: '24px',
                    borderRadius: '12px',
                    backgroundColor: colorEngagement ? '#E8B84B' : '#E0DDD6',
                    border: 'none',
                    cursor: 'pointer',
                    flexShrink: 0
                  }}
                >
                  <div
                    className="absolute top-1 transition-all duration-200"
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      backgroundColor: '#FFFFFF',
                      left: colorEngagement ? '26px' : '2px',
                      boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                </button>
                <div>
                  <div className="text-sm mb-0.5" style={{ fontWeight: 500 }}>
                    Color engagement rings
                  </div>
                  <p className="text-xs" style={{ color: '#999999' }}>
                    Audience frames glow green → yellow → red based on how engaged they are.
                  </p>
                </div>
              </div>

              <div className="flex flex-col items-center gap-2 py-4 transition-opacity duration-300">
                <div className="flex gap-2">
                  {[
                    { border: colorEngagement ? '#4CAF50' : 'transparent' },
                    { border: colorEngagement ? '#E8B84B' : 'transparent' },
                    { border: colorEngagement ? '#F44336' : 'transparent' }
                  ].map((cell, i) => (
                    <div
                      key={i}
                      className="transition-all duration-300"
                      style={{
                        width: '40px',
                        height: '30px',
                        borderRadius: '4px',
                        backgroundColor: '#D0CEC8',
                        border: `2px solid ${cell.border}`
                      }}
                    />
                  ))}
                </div>
                <p className="text-xs text-center" style={{ color: '#BBBBBB' }}>
                  {colorEngagement
                    ? 'Reactions shown through expressions + color'
                    : 'Reactions shown through expressions'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        className="fixed bottom-0 left-0 right-0 flex justify-center"
        style={{
          background: 'linear-gradient(to bottom, transparent, #FAFAF7 40%)',
          padding: '16px 0 24px'
        }}
      >
        <button
          onClick={handleStart}
          disabled={!canStart}
          className="transition-all duration-150"
          style={{
            width: '100%',
            maxWidth: '520px',
            margin: '0 32px',
            backgroundColor: '#E8B84B',
            color: '#5C3D00',
            fontWeight: 500,
            fontSize: '15px',
            borderRadius: '99px',
            padding: '14px',
            border: 'none',
            opacity: canStart ? 1 : 0.4,
            cursor: canStart ? 'pointer' : 'not-allowed'
          }}
          onMouseEnter={(e) => {
            if (canStart) {
              e.currentTarget.style.backgroundColor = '#D4A93C';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#E8B84B';
          }}
        >
          Start session →
        </button>
      </div>
    </div>
  );
}
