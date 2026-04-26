import { useState, useEffect, useRef } from 'react';

interface CalibrationProps {
  onBegin: () => void;
  onBack: () => void;
}

export function Calibration({ onBegin, onBack }: CalibrationProps) {
  const [cameraReady, setCameraReady] = useState(false);
  const [micReady, setMicReady] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const animFrameRef = useRef<number>(0);
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((s) => {
        setStream(s);

        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
        setCameraReady(true);

        // Audio level monitoring
        const audioCtx = new AudioContext();
        audioCtxRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(s);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);
        setMicReady(true);

        const data = new Uint8Array(analyser.frequencyBinCount);
        const tick = () => {
          analyser.getByteFrequencyData(data);
          const avg = data.reduce((a, b) => a + b, 0) / data.length;
          setAudioLevel(Math.min(1, avg / 80));
          animFrameRef.current = requestAnimationFrame(tick);
        };
        tick();
      })
      .catch(() => {
        setPermissionError(
          'Camera or microphone access was denied. Please allow both in your browser settings and reload.'
        );
      });

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      audioCtxRef.current?.close();
    };
  }, []);

  const handleBegin = () => {
    if (stream) onBegin();
  };

  const canBegin = cameraReady && micReady;

  // Build 20 VU bars from audioLevel
  const BAR_COUNT = 20;
  const activeBars = Math.round(audioLevel * BAR_COUNT);

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#FAFAF7', color: '#1A1A1A' }}>
      {/* Header */}
      <div className="px-8 py-6">
        <div className="max-w-[760px] mx-auto flex items-center justify-between">
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

      {/* Body */}
      <div className="px-8 pt-8">
        <div className="max-w-[760px] mx-auto">
          <div className="mb-10">
            <h1 className="text-3xl mb-2" style={{ fontWeight: 500 }}>
              Camera & audio check
            </h1>
            <p style={{ color: '#999999' }}>
              Make sure your face is visible and your microphone is picking up your voice before you begin.
            </p>
          </div>

          {permissionError ? (
            <div
              className="p-6 rounded-2xl"
              style={{ backgroundColor: '#FFF1F1', border: '1px solid #FECACA' }}
            >
              <p style={{ color: '#DC2626', fontWeight: 500 }}>{permissionError}</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-5">
              {/* Camera preview */}
              <div
                className="rounded-2xl overflow-hidden"
                style={{ border: '0.5px solid rgba(26, 26, 26, 0.1)', backgroundColor: '#111111', aspectRatio: '4/3' }}
              >
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                  style={{ transform: 'scaleX(-1)' }} // mirror so it feels natural
                />
              </div>

              {/* Right column */}
              <div className="flex flex-col gap-5">
                {/* Camera status */}
                <div
                  className="p-5 rounded-2xl"
                  style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
                >
                  <div className="flex items-center gap-3 mb-1">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: cameraReady ? '#22c55e' : '#D1D5DB' }}
                    />
                    <span style={{ fontWeight: 500 }}>Camera</span>
                  </div>
                  <p className="text-sm" style={{ color: '#999999' }}>
                    {cameraReady
                      ? 'Camera detected. Make sure your face fills the frame.'
                      : 'Waiting for camera access…'}
                  </p>
                </div>

                {/* Microphone status + level */}
                <div
                  className="p-5 rounded-2xl flex-1"
                  style={{ backgroundColor: '#FFFFFF', border: '0.5px solid rgba(26, 26, 26, 0.1)' }}
                >
                  <div className="flex items-center gap-3 mb-1">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: micReady ? '#22c55e' : '#D1D5DB' }}
                    />
                    <span style={{ fontWeight: 500 }}>Microphone</span>
                  </div>
                  <p className="text-sm mb-5" style={{ color: '#999999' }}>
                    {micReady
                      ? 'Speak normally — the bar should move when you talk.'
                      : 'Waiting for microphone access…'}
                  </p>

                  {/* VU meter */}
                  <div className="flex items-end gap-[3px]" style={{ height: '48px' }}>
                    {Array.from({ length: BAR_COUNT }, (_, i) => {
                      const active = i < activeBars;
                      const isHigh = i >= BAR_COUNT * 0.75;
                      const isMid = i >= BAR_COUNT * 0.5;
                      const color = active
                        ? isHigh
                          ? '#ef4444'
                          : isMid
                            ? '#E8B84B'
                            : '#22c55e'
                        : 'rgba(26,26,26,0.08)';
                      const heightPct = 40 + (i / BAR_COUNT) * 60;
                      return (
                        <div
                          key={i}
                          className="flex-1 rounded-sm transition-colors duration-75"
                          style={{ height: `${heightPct}%`, backgroundColor: color }}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Tips */}
                <div
                  className="p-5 rounded-2xl"
                  style={{ backgroundColor: '#FFFBEF', border: '1px solid #E8B84B' }}
                >
                  <p className="text-sm leading-relaxed" style={{ color: '#92681A' }}>
                    <strong>Tips:</strong> Sit in a well-lit area, position your camera at eye level,
                    and reduce background noise for the best experience.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Begin button */}
          <div className="mt-8 flex justify-center">
            <button
              onClick={handleBegin}
              disabled={!canBegin}
              className="px-12 py-4 rounded-full transition-all"
              style={{
                backgroundColor: canBegin ? '#E8B84B' : 'rgba(26,26,26,0.06)',
                color: canBegin ? '#1A1A1A' : 'rgba(26,26,26,0.3)',
                fontWeight: 500,
                fontSize: '15px',
                border: '0.5px solid rgba(26,26,26,0.1)',
                cursor: canBegin ? 'pointer' : 'not-allowed',
              }}
            >
              {canBegin ? 'Begin session' : 'Waiting for permissions…'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
