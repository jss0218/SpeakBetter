import { useState } from 'react';

interface SetupScreenProps {
  onStartSession: (config: {
    practiceType: 'presentation' | 'pitch';
    audienceSize: 'small' | 'medium' | 'large';
    environment: 'conference' | 'classroom' | 'lecture';
    duration: number;
    topic: string;
  }) => void;
  onBack: () => void;
}

export function SetupScreen({ onStartSession, onBack }: SetupScreenProps) {
  const [practiceType, setPracticeType] = useState<'presentation' | 'pitch' | null>(null);
  const [audienceSize, setAudienceSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [environment, setEnvironment] = useState<'conference' | 'classroom' | 'lecture' | null>(null);
  const [duration, setDuration] = useState(5);
  const [topic, setTopic] = useState('');

  const canStart = practiceType !== null && environment !== null;

  const handleStart = () => {
    if (canStart && practiceType && environment) {
      onStartSession({
        practiceType,
        audienceSize,
        environment,
        duration,
        topic
      });
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#FAFAF7', color: '#1A1A1A' }}>
      <div className="px-8 py-6">
        <div className="flex items-center justify-between max-w-[560px] mx-auto">
          <div className="flex items-center gap-1">
            <span style={{ fontWeight: 500 }}>speak</span>
            <span style={{ fontWeight: 500, color: '#E8B84B' }}>B</span>
            <span style={{ fontWeight: 500 }}>etter</span>
          </div>
          <button
            onClick={onBack}
            className="px-4 py-2 rounded-full opacity-60 hover:opacity-100 transition-opacity"
            style={{ border: '0.5px solid rgba(26, 26, 26, 0.2)' }}
          >
            ← Back
          </button>
        </div>
      </div>

      <div className="px-8 py-16">
        <div className="max-w-[560px] mx-auto space-y-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl mb-3" style={{ fontWeight: 500 }}>
              Let's get you ready.
            </h1>
            <p className="text-lg" style={{ color: '#888888' }}>
              Set up your session and start practicing.
            </p>
          </div>

          <div className="space-y-8">
            <div>
              <label
                className="block mb-4 uppercase tracking-wider"
                style={{ fontSize: '11px', color: '#888888', letterSpacing: '0.06em' }}
              >
                What are you practicing for?
              </label>
              <div className="flex gap-4 justify-center">
                {[
                  {
                    id: 'presentation' as const,
                    title: 'Presentation',
                    icon: '📊',
                    description: 'Pitch decks, project updates, stakeholder meetings'
                  },
                  {
                    id: 'pitch' as const,
                    title: 'Pitch',
                    icon: '💡',
                    description: 'Startup pitches, investor meetings, demos'
                  }
                ].map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setPracticeType(type.id)}
                    className="flex-1 text-left transition-all duration-200"
                    style={{
                      backgroundColor: practiceType === type.id ? '#FFFBEF' : '#FFFFFF',
                      border: practiceType === type.id
                        ? '2px solid #E8B84B'
                        : '0.5px solid #E8E6E0',
                      borderRadius: '14px',
                      padding: '28px 24px',
                      minWidth: '200px',
                      maxWidth: '240px',
                      opacity: practiceType && practiceType !== type.id ? 0.7 : 1,
                      boxShadow: practiceType === type.id ? '0 2px 8px rgba(232, 184, 75, 0.1)' : 'none'
                    }}
                  >
                    <div className="text-4xl mb-3">{type.icon}</div>
                    <h3 className="mb-2" style={{ fontWeight: 500 }}>
                      {type.title}
                    </h3>
                    <p className="text-sm leading-relaxed" style={{ color: '#888888' }}>
                      {type.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label
                className="block mb-4 uppercase tracking-wider"
                style={{ fontSize: '11px', color: '#888888', letterSpacing: '0.06em' }}
              >
                Audience size
              </label>
              <div className="flex gap-3 justify-center">
                {[
                  { id: 'small' as const, label: 'Small  1–10' },
                  { id: 'medium' as const, label: 'Medium  20–50' },
                  { id: 'large' as const, label: 'Large  100+' }
                ].map((size) => (
                  <button
                    key={size.id}
                    onClick={() => setAudienceSize(size.id)}
                    className="transition-all duration-150"
                    style={{
                      backgroundColor: audienceSize === size.id ? '#E8B84B' : '#FFFFFF',
                      color: audienceSize === size.id ? '#5C3D00' : '#666666',
                      border: `0.5px solid ${audienceSize === size.id ? '#E8B84B' : '#E8E6E0'}`,
                      borderRadius: '99px',
                      padding: '10px 22px',
                      fontWeight: audienceSize === size.id ? 500 : 400
                    }}
                  >
                    {size.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label
                className="block mb-4 uppercase tracking-wider"
                style={{ fontSize: '11px', color: '#888888', letterSpacing: '0.06em' }}
              >
                Environment
              </label>
              <div className="flex gap-4 justify-center">
                {[
                  {
                    id: 'conference' as const,
                    title: 'Conference room',
                    illustration: (
                      <svg width="80" height="60" viewBox="0 0 80 60" fill="none">
                        <rect x="10" y="10" width="60" height="40" rx="4" fill="#F0EDE6" />
                        <ellipse cx="40" cy="30" rx="20" ry="12" fill="#E8B84B" opacity="0.3" />
                        <circle cx="25" cy="25" r="3" fill="#E8B84B" />
                        <circle cx="35" cy="22" r="3" fill="#E8B84B" />
                        <circle cx="45" cy="22" r="3" fill="#E8B84B" />
                        <circle cx="55" cy="25" r="3" fill="#E8B84B" />
                        <circle cx="30" cy="35" r="3" fill="#E8B84B" />
                        <circle cx="50" cy="35" r="3" fill="#E8B84B" />
                      </svg>
                    )
                  },
                  {
                    id: 'classroom' as const,
                    title: 'Classroom',
                    illustration: (
                      <svg width="80" height="60" viewBox="0 0 80 60" fill="none">
                        <rect x="10" y="10" width="60" height="40" rx="4" fill="#F0EDE6" />
                        <rect x="15" y="8" width="50" height="6" rx="2" fill="#E8B84B" />
                        <rect x="20" y="22" width="8" height="6" rx="1" fill="#E8B84B" opacity="0.4" />
                        <rect x="32" y="22" width="8" height="6" rx="1" fill="#E8B84B" opacity="0.4" />
                        <rect x="44" y="22" width="8" height="6" rx="1" fill="#E8B84B" opacity="0.4" />
                        <rect x="20" y="32" width="8" height="6" rx="1" fill="#E8B84B" opacity="0.4" />
                        <rect x="32" y="32" width="8" height="6" rx="1" fill="#E8B84B" opacity="0.4" />
                        <rect x="44" y="32" width="8" height="6" rx="1" fill="#E8B84B" opacity="0.4" />
                      </svg>
                    )
                  },
                  {
                    id: 'lecture' as const,
                    title: 'Lecture hall',
                    illustration: (
                      <svg width="80" height="60" viewBox="0 0 80 60" fill="none">
                        <rect x="10" y="10" width="60" height="40" rx="4" fill="#F0EDE6" />
                        <rect x="15" y="42" width="50" height="4" rx="2" fill="#E8B84B" />
                        <path d="M 20 38 L 60 38 L 65 30 L 15 30 Z" fill="#E8B84B" opacity="0.3" />
                        <path d="M 22 30 L 58 30 L 62 22 L 18 22 Z" fill="#E8B84B" opacity="0.4" />
                        <path d="M 24 22 L 56 22 L 59 14 L 21 14 Z" fill="#E8B84B" opacity="0.5" />
                      </svg>
                    )
                  }
                ].map((env) => (
                  <button
                    key={env.id}
                    onClick={() => setEnvironment(env.id)}
                    className="flex-1 text-center transition-all duration-200"
                    style={{
                      backgroundColor: environment === env.id ? '#FFFBEF' : '#FFFFFF',
                      border: environment === env.id
                        ? '2px solid #E8B84B'
                        : '0.5px solid #E8E6E0',
                      borderRadius: '14px',
                      padding: '24px 20px',
                      maxWidth: '180px',
                      opacity: environment && environment !== env.id ? 0.7 : 1
                    }}
                  >
                    <div className="mb-3 flex justify-center">{env.illustration}</div>
                    <h3 style={{ fontWeight: 500, fontSize: '14px' }}>
                      {env.title}
                    </h3>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label
                className="block mb-4 uppercase tracking-wider"
                style={{ fontSize: '11px', color: '#888888', letterSpacing: '0.06em' }}
              >
                How long is your session?
              </label>
              <div className="px-4">
                <input
                  type="range"
                  min="1"
                  max="15"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full"
                  style={{
                    height: '4px',
                    borderRadius: '2px',
                    background: `linear-gradient(to right, #E8B84B 0%, #E8B84B ${((duration - 1) / 14) * 100}%, #E8E6E0 ${((duration - 1) / 14) * 100}%, #E8E6E0 100%)`,
                    outline: 'none',
                    appearance: 'none',
                    WebkitAppearance: 'none'
                  }}
                />
                <style>{`
                  input[type="range"]::-webkit-slider-thumb {
                    appearance: none;
                    width: 18px;
                    height: 18px;
                    border-radius: 50%;
                    background: #FFFFFF;
                    border: 2px solid #E8B84B;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    cursor: pointer;
                  }
                  input[type="range"]::-moz-range-thumb {
                    width: 18px;
                    height: 18px;
                    border-radius: 50%;
                    background: #FFFFFF;
                    border: 2px solid #E8B84B;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    cursor: pointer;
                  }
                `}</style>
                <div className="text-center mt-3" style={{ color: '#E8B84B', fontWeight: 500, fontSize: '14px' }}>
                  {duration} {duration === 1 ? 'minute' : 'minutes'}
                </div>
              </div>
            </div>

            <div>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Topic or talking points (optional) — e.g. Q3 earnings, climate policy, product launch"
                className="w-full transition-all duration-150"
                style={{
                  border: topic ? '0.5px solid #E8B84B' : '0.5px solid #E8E6E0',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  fontSize: '14px',
                  backgroundColor: topic ? '#FFFBEF' : '#FFFFFF',
                  outline: 'none'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#E8B84B';
                  e.target.style.backgroundColor = '#FFFBEF';
                }}
                onBlur={(e) => {
                  if (!topic) {
                    e.target.style.borderColor = '#E8E6E0';
                    e.target.style.backgroundColor = '#FFFFFF';
                  }
                }}
              />
            </div>

            <button
              onClick={handleStart}
              disabled={!canStart}
              className="w-full transition-all duration-150"
              style={{
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
      </div>
    </div>
  );
}
