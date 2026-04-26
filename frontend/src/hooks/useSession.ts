import { useState, useEffect, useRef, useCallback } from 'react';

const WS_BASE = 'ws://localhost:8000';

export interface SessionData {
  status: 'connecting' | 'live' | 'ending' | 'done' | 'error';
  engagementScore: number;           // 0–100
  avatarStates: Record<string, string>;   // { avatar_0: 'engaged'|'neutral'|'bored'|'confused'|'distracted' }
  avatarDelays: Record<string, number>;   // { avatar_0: delay_ms } — only avatars that changed
  wpm: number;
  fillerCount: number;
  fullTranscript: string;
  qaQuestion: string | null;
  qaAudio: string | null;            // base64 mp3
  breakdown: Record<string, unknown> | null;
  error: string | null;
}

interface UseSessionOptions {
  stream: MediaStream | null | undefined;
  sessionId: string;
  userId: string;
  scenario: string;
  durationSeconds: number;
}

export function useSession({ stream, sessionId, userId, scenario, durationSeconds }: UseSessionOptions) {
  const [data, setData] = useState<SessionData>({
    status: 'connecting',
    engagementScore: 74,
    avatarStates: {},
    avatarDelays: {},
    wpm: 0,
    fillerCount: 0,
    fullTranscript: '',
    qaQuestion: null,
    qaAudio: null,
    breakdown: null,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const visionTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastFrameRef = useRef<Uint8ClampedArray | null>(null);
  const transcriptPartsRef = useRef<string[]>([]);
  const calibSamplesRef = useRef<object[]>([]);
  const calibSentRef = useRef(false);
  const calibUntilRef = useRef(0);

  const sendJson = useCallback((payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const sendSessionEnd = useCallback(() => {
    sendJson({ type: 'session_end', user_id: userId });
    setData(prev => ({ ...prev, status: 'ending' }));
  }, [sendJson, userId]);

  const sendQaAnswer = useCallback((answer: string) => {
    sendJson({ type: 'qa_answer', answer, timestamp: Date.now() / 1000 });
  }, [sendJson]);

  useEffect(() => {
    // ── Audio helpers ──────────────────────────────────────────────────────────

    function floatTo16BitPCM(input: Float32Array): ArrayBuffer {
      const out = new DataView(new ArrayBuffer(input.length * 2));
      for (let i = 0; i < input.length; i++) {
        const s = Math.max(-1, Math.min(1, input[i]));
        out.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      }
      return out.buffer;
    }

    function resample(buf: Float32Array, fromRate: number, toRate = 16000): Float32Array {
      if (fromRate === toRate) return buf;
      const ratio = fromRate / toRate;
      const len = Math.max(1, Math.round(buf.length / ratio));
      const out = new Float32Array(len);
      for (let i = 0; i < len; i++) {
        const src = i * ratio;
        const l = Math.floor(src);
        const r = Math.min(buf.length - 1, l + 1);
        out[i] = buf[l] + (buf[r] - buf[l]) * (src - l);
      }
      return out;
    }

    // ── Vision helpers ─────────────────────────────────────────────────────────
    // Canvas-based brightness fallback (no MediaPipe dependency).
    // Provides enough signal for eye-contact, motion, and face-detection proxies.

    function getVisionPayload(): object {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const base = {
        type: 'vision_update',
        eye_contact: 0.5, face_detected: false, gesture_detected: false,
        timestamp: Date.now() / 1000, posture_score: 0.5, motion_score: 0,
        brow_furrow: 0, smile_score: 0, expression: 'neutral',
        head_yaw: 0, head_pitch: 0, head_roll: 0,
        face_size: 0, hand_motion: 0, vision_confidence: 0,
      };

      if (!video || !canvas || !video.videoWidth) return base;

      canvas.width = 160;
      canvas.height = 120;
      const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
      ctx.drawImage(video, 0, 0, 160, 120);
      const px = ctx.getImageData(0, 0, 160, 120).data;

      let total = 0, center = 0, motion = 0;
      const [cx0, cx1, cy0, cy1] = [48, 112, 24, 96];

      for (let y = 0; y < 120; y++) {
        for (let x = 0; x < 160; x++) {
          const i = (y * 160 + x) * 4;
          const b = (px[i] + px[i + 1] + px[i + 2]) / 3;
          total += b;
          if (x >= cx0 && x <= cx1 && y >= cy0 && y <= cy1) center += b;
        }
      }

      if (lastFrameRef.current) {
        for (let i = 0; i < px.length; i += 8) {
          motion += Math.abs(px[i] - lastFrameRef.current[i])
            + Math.abs(px[i + 1] - lastFrameRef.current[i + 1])
            + Math.abs(px[i + 2] - lastFrameRef.current[i + 2]);
        }
      }
      lastFrameRef.current = new Uint8ClampedArray(px);

      const avg = total / (160 * 120);
      const centerAvg = center / Math.max(1, (cx1 - cx0) * (cy1 - cy0));
      const motionScore = Math.min(1, motion / (px.length * 0.6));
      const eyeContact = Math.max(0.1, Math.min(1, 1 - Math.abs(centerAvg - avg) / 140 + 0.08));

      return {
        ...base,
        eye_contact: eyeContact,
        face_detected: true,
        gesture_detected: motionScore > 0.12,
        motion_score: motionScore,
        face_size: 0.2,
        hand_motion: motionScore,
        vision_confidence: 0.35,
      };
    }

    // ── Bail out if no stream (dev/test without calibration) ──────────────────
    if (!stream) return;

    // ── Offscreen video element for vision ─────────────────────────────────────

    const video = document.createElement('video');
    video.srcObject = stream;
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.play().catch(() => {});
    videoRef.current = video;
    canvasRef.current = document.createElement('canvas');

    // ── WebSocket ──────────────────────────────────────────────────────────────

    const url = `${WS_BASE}/ws/${encodeURIComponent(sessionId)}` +
      `?user_id=${encodeURIComponent(userId)}` +
      `&scenario=${encodeURIComponent(scenario)}` +
      `&target_duration=${encodeURIComponent(durationSeconds)}`;

    const ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      setData(prev => ({ ...prev, status: 'live' }));
      calibSamplesRef.current = [];
      calibSentRef.current = false;
      calibUntilRef.current = Date.now() + 5000;

      // Audio pipeline
      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;
      // ScriptProcessor is deprecated but universally supported; fine for now
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const raw = e.inputBuffer.getChannelData(0);
        ws.send(floatTo16BitPCM(resample(raw, audioCtx.sampleRate)));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      // Vision loop — every 500ms, matching speech-test.html
      visionTimerRef.current = setInterval(() => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const payload = getVisionPayload();
        ws.send(JSON.stringify(payload));

        // Collect calibration samples for first 5 s, then send once
        if (!calibSentRef.current) {
          if (Date.now() <= calibUntilRef.current) {
            calibSamplesRef.current.push(payload);
          } else if (calibSamplesRef.current.length >= 8) {
            ws.send(JSON.stringify({
              type: 'vision_calibration',
              samples: calibSamplesRef.current,
              timestamp: Date.now() / 1000,
            }));
            calibSentRef.current = true;
          }
        }
      }, 500);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string);

        switch (msg.type) {
          case 'engagement_update':
            setData(prev => ({
              ...prev,
              engagementScore: Math.round((msg.score ?? 0) * 100),
            }));
            break;

          case 'audience_update':
            setData(prev => ({
              ...prev,
              avatarStates: msg.avatar_states ?? {},
              avatarDelays: msg.transition_delays_ms ?? {},
            }));
            break;

          case 'transcript': {
            const clean = String(msg.text || '').trim();
            if (clean) {
              transcriptPartsRef.current.push(clean);
              if (transcriptPartsRef.current.length > 200)
                transcriptPartsRef.current = transcriptPartsRef.current.slice(-200);
            }
            setData(prev => ({
              ...prev,
              wpm: Math.round(msg.wpm || 0),
              fillerCount: msg.filler_count ?? prev.fillerCount,
              fullTranscript: transcriptPartsRef.current.join(' ').trim(),
            }));
            break;
          }

          case 'qa_question':
            setData(prev => ({
              ...prev,
              qaQuestion: msg.question || null,
              qaAudio: msg.audio_base64 || null,
            }));
            break;

          case 'session_breakdown':
            setData(prev => ({
              ...prev,
              status: 'done',
              breakdown: msg.breakdown ?? null,
            }));
            break;

          case 'error':
            setData(prev => ({ ...prev, error: msg.message }));
            break;
        }
      } catch {
        // ignore non-JSON binary frames
      }
    };

    ws.onerror = () => {
      setData(prev => ({ ...prev, status: 'error', error: 'Could not connect to backend.' }));
    };

    ws.onclose = () => {
      setData(prev => ({
        ...prev,
        status: prev.status === 'done' || prev.status === 'ending' ? 'done' : prev.status,
      }));
    };

    return () => {
      if (visionTimerRef.current) clearInterval(visionTimerRef.current);
      processorRef.current?.disconnect();
      sourceRef.current?.disconnect();
      audioCtxRef.current?.close();
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
        ws.close(1000, 'unmount');
      video.srcObject = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, sendSessionEnd, sendQaAnswer };
}
