import { useState, useEffect } from 'react';

interface PersonDef {
  name: string;
  mirroredName: string;
  engagedImages: [string, string];
  disengagedImages: [string, string];
}

const PEOPLE: PersonDef[] = [
  {
    name: 'Maya',
    mirroredName: 'Sophie',
    engagedImages: ['/Faces/Maya_Engaged_1.png', '/Faces/Maya_Engaged_2.png'],
    disengagedImages: ['/Faces/Maya_Disengaged_1.png', '/Faces/Maya_Disengaged_2.png'],
  },
  {
    name: 'Liam',
    mirroredName: 'Marcus',
    engagedImages: ['/Faces/Liam_Engaged_1.png', '/Faces/Liam_Engaged_2.png'],
    disengagedImages: ['/Faces/Liam_Disengaged_1.png', '/Faces/Liam_Disengaged_2.png'],
  },
  {
    name: 'Aisha',
    mirroredName: 'Priya',
    engagedImages: ['/Faces/Aisha_Engaged_1.png', '/Faces/Aisha_Engaged_2.png'],
    disengagedImages: ['/Faces/Aisha_Disengaged_1.png', '/Faces/Aisha_Disengaged_2.png'],
  },
  {
    name: 'Noah',
    mirroredName: 'James',
    engagedImages: ['/Faces/Noah_Engaged_1.png', '/Faces/Noah_Engaged_2.png'],
    disengagedImages: ['/Faces/Noah_Disengaged_1.png', '/Faces/Noah_Disengaged_2.png'],
  },
  {
    name: 'Zoe',
    mirroredName: 'Emma',
    engagedImages: ['/Faces/Zoe_Engaged_1.png', '/Faces/Zoe_Engaged_2.png'],
    disengagedImages: ['/Faces/Zoe_Disengaged_1.png', '/Faces/Zoe_Disengaged_2.png'],
  },
  {
    name: 'Ethan',
    mirroredName: 'Daniel',
    engagedImages: ['/Faces/Ethan_Engaged_1.png', '/Faces/Ethan_Engaged_2.png'],
    disengagedImages: ['/Faces/Ethan_Disengaged_1.png', '/Faces/Ethan_Disengaged_2.png'],
  },
  {
    name: 'Jalen',
    mirroredName: 'Tyler',
    engagedImages: ['/Faces/Jalen_Engaged_1.png', '/Faces/Jalen_Engaged_2.png'],
    disengagedImages: ['/Faces/Jalen_Disengaged_2.png', '/Faces/Jalen_Disengaged_2.png'],
  },
];

interface AudienceMember extends PersonDef {
  threshold: number;
  isEngaged: boolean;
  transitionDelay: number;
  engagedIdx: 0 | 1;
  disengagedIdx: 0 | 1;
  mirrored: boolean;
}

interface LiveSessionProps {
  audienceSize?: number; // 1–20
  duration?: number;
  onEndSession: () => void;
}

// diff = engagementScore - threshold
// > 7        : fully green (well above threshold)
// 0 to 7     : green → yellow (approaching threshold)
// -20 to 0   : yellow → orange (just crossed into disengaged)
// -40 to -20 : orange → red (deep disengagement)
// < -40      : deep red
const getRingColor = (engagementScore: number, threshold: number): string => {
  const diff = engagementScore - threshold;
  const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * Math.max(0, Math.min(1, t)));
  const rgb = (r1: number, g1: number, b1: number, r2: number, g2: number, b2: number, t: number) =>
    `rgb(${lerp(r1, r2, t)}, ${lerp(g1, g2, t)}, ${lerp(b1, b2, t)})`;

  if (diff > 7)        return 'rgb(34, 197, 94)';                                    // green
  if (diff >= 0)       return rgb(34, 197, 94,  234, 179, 8,   1 - diff / 7);        // green → yellow
  if (diff >= -20)     return rgb(234, 179, 8,  249, 115, 22,  -diff / 20);          // yellow → orange
  if (diff >= -40)     return rgb(249, 115, 22, 239, 68,  68,  (-diff - 20) / 20);   // orange → red
  return 'rgb(185, 28, 28)';                                                          // deep red
};

const getGridCols = (count: number) => {
  if (count <= 1) return 'grid-cols-1';
  if (count <= 4) return 'grid-cols-2';
  if (count <= 9) return 'grid-cols-3';
  return 'grid-cols-4';
};

export function LiveSession({ audienceSize = 9, duration = 5, onEndSession }: LiveSessionProps) {
  const [seconds, setSeconds] = useState(0);
  const [sessionPhase, setSessionPhase] = useState<'speaking' | 'qa' | 'results'>('speaking');
  const [engagementScore, setEngagementScore] = useState(74);
  const [showEndButton, setShowEndButton] = useState(false);
  const [buttonFading, setButtonFading] = useState(false);
  const [mouseTimeout, setMouseTimeout] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [audience, setAudience] = useState<AudienceMember[]>([]);

  useEffect(() => {
    const initial = Array.from({ length: audienceSize }, (_, i) => {
      const person = PEOPLE[i % PEOPLE.length];
      const pass = Math.floor(i / PEOPLE.length);
      return {
        ...person,
        threshold: 40 + Math.random() * 45,
        isEngaged: true,
        transitionDelay: i * 180 + Math.random() * 200,
        engagedIdx: (Math.random() < 0.5 ? 0 : 1) as 0 | 1,
        disengagedIdx: (Math.random() < 0.5 ? 0 : 1) as 0 | 1,
        mirrored: pass % 2 === 1,
      };
    });
    setAudience(initial);
  }, [audienceSize]);

  // Update engagement state when score changes — never touch transitionDelay so CSS transitions aren't interrupted
  useEffect(() => {
    const scoreInterval = setInterval(() => {
      const newScore = Math.max(50, Math.min(95, engagementScore + (Math.random() - 0.5) * 20));
      setEngagementScore(newScore);

      setAudience((prev) =>
        prev.map((member) => ({
          ...member,
          isEngaged: newScore > member.threshold,
        }))
      );
    }, 4000);
    return () => clearInterval(scoreInterval);
  }, [engagementScore]);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((s) => {
        const newSeconds = s + 1;
        if (sessionPhase === 'speaking' && newSeconds >= duration * 60) endSpeakingPhase();
        return newSeconds;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [duration, sessionPhase]);

  const handleMouseMove = () => {
    setShowEndButton(true);
    if (mouseTimeout) clearTimeout(mouseTimeout);
    const timeout = setTimeout(() => setShowEndButton(false), 2000);
    setMouseTimeout(timeout);
  };

  useEffect(() => {
    return () => { if (mouseTimeout) clearTimeout(mouseTimeout); };
  }, [mouseTimeout]);

  const endSpeakingPhase = () => {
    setButtonFading(true);
    setShowEndButton(false);
    setTimeout(() => {
      setSessionPhase('qa');
      setButtonFading(false);
    }, 2000);
  };

  const handleButtonClick = () => {
    if (sessionPhase === 'speaking') endSpeakingPhase();
    else if (sessionPhase === 'qa') onEndSession();
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${remainingSecs.toString().padStart(2, '0')}`;
  };


  return (
    <div
      className="h-screen w-screen overflow-hidden relative"
      style={{ backgroundColor: '#111111' }}
      onMouseMove={handleMouseMove}
    >
      {/* Top bar */}
      <div
        className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-6"
        style={{ height: '36px', backgroundColor: 'rgba(0,0,0,0.3)', backdropFilter: 'blur(8px)' }}
      >
        <div className="flex items-center gap-1 opacity-40">
          <span style={{ fontSize: '13px', fontWeight: 500, color: '#FFFFFF' }}>speak</span>
          <span style={{ fontSize: '13px', fontWeight: 500, color: '#E8B84B' }}>B</span>
          <span style={{ fontSize: '13px', fontWeight: 500, color: '#FFFFFF' }}>etter</span>
        </div>
        <div className="font-mono" style={{ fontSize: '13px', color: '#FFFFFF', opacity: 0.6, fontWeight: 500 }}>
          {formatTime(seconds)}
        </div>
        <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#10B981' }} />
      </div>

      {/* Audience grid */}
      <div className="absolute inset-0 flex items-center justify-center" style={{ paddingTop: '36px' }}>
        <div
          className={`grid ${getGridCols(audienceSize)} gap-4`}
          style={{ width: 'min(82vw, 880px)' }}
        >
          {audience.map((member, i) => (
            <div
              key={i}
              className="relative overflow-hidden rounded-lg bg-[#1a1a1a]"
              style={{
                aspectRatio: '4/3',
                transform: member.mirrored ? 'scaleX(-1)' : 'none',
                boxShadow: `0 0 0 3px ${getRingColor(engagementScore, member.threshold)}`,
                transition: 'box-shadow 2500ms ease-in-out',
              }}
            >
              {/* Disengaged image — always underneath */}
              <img
                src={member.disengagedImages[member.disengagedIdx]}
                alt=""
                className="absolute inset-0 w-full h-full object-cover object-center"
              />

              {/* Engaged image — crossfades in on top */}
              <img
                src={member.engagedImages[member.engagedIdx]}
                alt=""
                className="absolute inset-0 w-full h-full object-cover object-center"
                style={{
                  opacity: member.isEngaged ? 1 : 0,
                  transition: 'opacity 2500ms ease-in-out',
                  transitionDelay: `${member.transitionDelay}ms`,
                }}
              />

              {/* Name label — counter-flip so text reads normally when tile is mirrored */}
              <div
                className="absolute bottom-2 left-2 px-2 py-0.5 rounded z-10"
                style={{
                  backgroundColor: 'rgba(0,0,0,0.25)',
                  fontSize: '11px',
                  color: '#FFFFFF',
                  opacity: 0.6,
                  fontWeight: 400,
                  transform: member.mirrored ? 'scaleX(-1)' : 'none',
                }}
              >
                {member.mirrored ? member.mirroredName : member.name}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* End session button */}
      {sessionPhase !== 'results' && !buttonFading && (
        <div
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-30"
          style={{
            opacity: showEndButton ? 1 : 0,
            pointerEvents: showEndButton ? 'auto' : 'none',
            transition: 'opacity 0.3s ease',
          }}
        >
          <button
            onClick={handleButtonClick}
            style={{
              backgroundColor: 'rgba(255,255,255,0.08)',
              backdropFilter: 'blur(8px)',
              color: '#FFFFFF',
              borderRadius: '99px',
              padding: '10px 24px',
              fontSize: '13px',
              fontWeight: 500,
              border: sessionPhase === 'qa'
                ? '0.5px solid rgba(232,184,75,0.4)'
                : '0.5px solid rgba(255,255,255,0.15)',
              transition: 'opacity 0.3s ease, border-color 0.3s ease',
            }}
          >
            {sessionPhase === 'speaking' ? "I'm done" : 'End session'}
          </button>
        </div>
      )}
    </div>
  );
}
