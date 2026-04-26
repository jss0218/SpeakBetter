import { useEffect, useRef, useState } from 'react';

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

type SessionPhase = 'connecting' | 'speaking' | 'qa' | 'finishing' | 'ended';
type AvatarState = 'engaged' | 'neutral' | 'bored' | 'confused' | 'distracted';

interface AudienceMember extends PersonDef {
  id: string;
  avatarState: AvatarState;
  transitionDelay: number;
  mirrored: boolean;
}

interface LiveSessionProps {
  audienceSize?: number;
  duration?: number;
  practiceType: 'pitch' | 'presentation' | 'interview';
  onEndSession: (result: {
    breakdown: Record<string, unknown>;
    engagementHistory: Array<Record<string, unknown>>;
    recordingUrl: string | null;
  }) => void;
}

const clamp = (value: number, min = 0, max = 1) => Math.max(min, Math.min(max, value));

const getGridCols = (count: number) => {
  if (count <= 1) return 'grid-cols-1';
  if (count <= 4) return 'grid-cols-2';
  if (count <= 9) return 'grid-cols-3';
  return 'grid-cols-4';
};

const getAudienceImage = (member: AudienceMember): string => {
  switch (member.avatarState) {
    case 'engaged':
      return member.engagedImages[0];
    case 'neutral':
      return member.engagedImages[1];
    case 'confused':
      return member.disengagedImages[0];
    case 'distracted':
      return member.disengagedImages[1];
    case 'bored':
    default:
      return member.disengagedImages[0];
  }
};

const getRingColor = (state: AvatarState, engagementScore: number): string => {
  if (state === 'engaged') return 'rgb(34, 197, 94)';
  if (state === 'neutral') return engagementScore >= 0.55 ? 'rgb(234, 179, 8)' : 'rgb(249, 115, 22)';
  if (state === 'confused') return 'rgb(245, 158, 11)';
  if (state === 'distracted') return 'rgb(239, 68, 68)';
  return 'rgb(185, 28, 28)';
};

const formatTime = (secs: number) => {
  const mins = Math.floor(secs / 60);
  const remainingSecs = secs % 60;
  return `${mins.toString().padStart(2, '0')}:${remainingSecs.toString().padStart(2, '0')}`;
};

const createInitialAudience = (audienceSize: number): AudienceMember[] =>
  Array.from({ length: audienceSize }, (_, i) => {
    const person = PEOPLE[i % PEOPLE.length];
    const pass = Math.floor(i / PEOPLE.length);
    return {
      ...person,
      id: `avatar_${i}`,
      avatarState: 'neutral',
      transitionDelay: i * 120,
      mirrored: pass % 2 === 1,
    };
  });

const floatTo16BitPCM = (input: Float32Array): ArrayBuffer => {
  const buffer = new ArrayBuffer(input.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < input.length; i += 1) {
    const sample = clamp(input[i], -1, 1);
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return buffer;
};

const resampleBuffer = (input: Float32Array, inputRate: number, outputRate: number): Float32Array => {
  if (inputRate === outputRate) return input;
  const ratio = inputRate / outputRate;
  const outputLength = Math.max(1, Math.round(input.length / ratio));
  const output = new Float32Array(outputLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < output.length) {
    const nextOffsetBuffer = Math.min(input.length, Math.round((offsetResult + 1) * ratio));
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer; i += 1) {
      accum += input[i];
      count += 1;
    }
    output[offsetResult] = count ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return output;
};

const chunkLevel = (input: Float32Array): number => {
  if (!input.length) return 0;
  let total = 0;
  for (let i = 0; i < input.length; i += 1) {
    total += input[i] * input[i];
  }
  return clamp(Math.sqrt(total / input.length) * 3.2);
};

const playBase64Audio = async (audioBase64: string) => {
  if (!audioBase64) return;
  const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
  try {
    await audio.play();
  } catch {
    return;
  }
};

export function LiveSession({
  audienceSize = 9,
  duration = 5,
  practiceType,
  onEndSession,
}: LiveSessionProps) {
  const [seconds, setSeconds] = useState(0);
  const [phase, setPhase] = useState<SessionPhase>('connecting');
  const [statusText, setStatusText] = useState('Connecting to backend…');
  const [connectionState, setConnectionState] = useState('Connecting');
  const [micLevel, setMicLevel] = useState(0);
  const [wpm, setWpm] = useState(0);
  const [engagementScore, setEngagementScore] = useState(0.5);
  const [dominantSignal, setDominantSignal] = useState('--');
  const [questionText, setQuestionText] = useState('Speak for a bit, then stop the session to receive a voiced adversarial question.');
  const [qaInput, setQaInput] = useState('');
  const [questionPending, setQuestionPending] = useState(false);
  const [showEndButton, setShowEndButton] = useState(false);
  const [audience, setAudience] = useState<AudienceMember[]>(() => createInitialAudience(audienceSize));
  const [debugLines, setDebugLines] = useState<string[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const recordingUrlRef = useRef<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const visionTimerRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const lastFrameRef = useRef<Uint8ClampedArray | null>(null);
  const stopRequestedRef = useRef(false);
  const breakdownSeenRef = useRef(false);
  const calibrationSamplesRef = useRef<Record<string, unknown>[]>([]);
  const calibrationDeadlineRef = useRef(0);
  const calibrationSentRef = useRef(false);
  const sessionIdRef = useRef(
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? `session-${crypto.randomUUID().slice(0, 8)}`
      : `session-${Math.random().toString(36).slice(2, 10)}`
  );

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    setAudience(createInitialAudience(audienceSize));
  }, [audienceSize]);

  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      setSeconds((current) => current + 1);
    }, 1000);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    if (phase !== 'speaking') return;
    if (seconds < duration * 60) return;
    void stopSession();
  }, [duration, phase, seconds]);

  useEffect(() => {
    void startSession();
    return () => {
      if (recordingUrlRef.current) {
        URL.revokeObjectURL(recordingUrlRef.current);
        recordingUrlRef.current = null;
      }
      void cleanupLocalMedia();
      closeSocket();
    };
  }, []);

  const pushDebug = (line: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugLines((current) => [`${timestamp}: ${line}`, ...current].slice(0, 10));
  };

  const closeSocket = () => {
    const socket = wsRef.current;
    wsRef.current = null;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, 'component cleanup');
    }
  };

  const cleanupLocalMedia = async () => {
    if (visionTimerRef.current) {
      window.clearInterval(visionTimerRef.current);
      visionTimerRef.current = null;
    }

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    if (audioContextRef.current) {
      await audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    lastFrameRef.current = null;
    setMicLevel(0);
  };

  const stopRecorder = async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    if (recorder.state === 'inactive') {
      mediaRecorderRef.current = null;
      return;
    }

    await new Promise<void>((resolve) => {
      const handleStop = () => {
        recorder.removeEventListener('stop', handleStop);
        resolve();
      };
      recorder.addEventListener('stop', handleStop);
      recorder.stop();
    });
    mediaRecorderRef.current = null;
  };

  const buildRecordingUrl = () => {
    if (!recordedChunksRef.current.length) return recordingUrlRef.current;
    if (recordingUrlRef.current) {
      URL.revokeObjectURL(recordingUrlRef.current);
    }
    const mimeType = recordedChunksRef.current[0]?.type || 'video/webm';
    const blob = new Blob(recordedChunksRef.current, { type: mimeType });
    recordingUrlRef.current = URL.createObjectURL(blob);
    return recordingUrlRef.current;
  };

  const computeVisionPayload = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      return {
        type: 'vision_update',
        eye_contact: 0.5,
        face_detected: false,
        gesture_detected: false,
        timestamp: Date.now() / 1000,
        motion_score: 0,
        posture_score: 0.5,
        brow_furrow: 0,
        smile_score: 0,
        expression: 'unknown',
        head_yaw: 0,
        head_pitch: 0,
        head_roll: 0,
        face_size: 0,
        hand_motion: 0,
        vision_confidence: 0,
      };
    }

    if (!video.videoWidth || !video.videoHeight) {
      return {
        type: 'vision_update',
        eye_contact: 0.5,
        face_detected: false,
        gesture_detected: false,
        timestamp: Date.now() / 1000,
        motion_score: 0,
        posture_score: 0.5,
        brow_furrow: 0,
        smile_score: 0,
        expression: 'unknown',
        head_yaw: 0,
        head_pitch: 0,
        head_roll: 0,
        face_size: 0,
        hand_motion: 0,
        vision_confidence: 0,
      };
    }

    canvas.width = 160;
    canvas.height = 120;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return {
        type: 'vision_update',
        eye_contact: 0.5,
        face_detected: false,
        gesture_detected: false,
        timestamp: Date.now() / 1000,
        motion_score: 0,
        posture_score: 0.5,
        brow_furrow: 0,
        smile_score: 0,
        expression: 'unknown',
        head_yaw: 0,
        head_pitch: 0,
        head_roll: 0,
        face_size: 0,
        hand_motion: 0,
        vision_confidence: 0,
      };
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let total = 0;
    let center = 0;
    let motion = 0;
    const cx0 = Math.floor(canvas.width * 0.3);
    const cx1 = Math.floor(canvas.width * 0.7);
    const cy0 = Math.floor(canvas.height * 0.2);
    const cy1 = Math.floor(canvas.height * 0.8);

    for (let y = 0; y < canvas.height; y += 1) {
      for (let x = 0; x < canvas.width; x += 1) {
        const idx = (y * canvas.width + x) * 4;
        const brightness = (image[idx] + image[idx + 1] + image[idx + 2]) / 3;
        total += brightness;
        if (x >= cx0 && x <= cx1 && y >= cy0 && y <= cy1) {
          center += brightness;
        }
      }
    }

    if (lastFrameRef.current) {
      for (let i = 0; i < image.length; i += 8) {
        motion += Math.abs(image[i] - lastFrameRef.current[i]);
        motion += Math.abs(image[i + 1] - lastFrameRef.current[i + 1]);
        motion += Math.abs(image[i + 2] - lastFrameRef.current[i + 2]);
      }
    }
    lastFrameRef.current = new Uint8ClampedArray(image);

    const avg = total / (canvas.width * canvas.height);
    const centerAvg = center / Math.max(1, (cx1 - cx0) * (cy1 - cy0));
    const motionScore = clamp(motion / (image.length * 0.6));
    const eyeContact = clamp(1 - Math.abs(centerAvg - avg) / 140 + 0.08, 0.1, 1);

    return {
      type: 'vision_update',
      eye_contact: eyeContact,
      face_detected: true,
      gesture_detected: motionScore > 0.12,
      timestamp: Date.now() / 1000,
      motion_score: motionScore,
      posture_score: 0.5,
      brow_furrow: 0,
      smile_score: 0,
      expression: 'unknown',
      head_yaw: 0,
      head_pitch: 0,
      head_roll: 0,
      face_size: 0.2,
      hand_motion: motionScore,
      vision_confidence: 0.35,
    };
  };

  const startVisionLoop = () => {
    if (visionTimerRef.current) {
      window.clearInterval(visionTimerRef.current);
    }

    visionTimerRef.current = window.setInterval(() => {
      const socket = wsRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return;

      const payload = computeVisionPayload();
      socket.send(JSON.stringify(payload));

      if (!calibrationSentRef.current && Date.now() <= calibrationDeadlineRef.current) {
        calibrationSamplesRef.current.push(payload);
      } else if (!calibrationSentRef.current && calibrationSamplesRef.current.length >= 8) {
        socket.send(
          JSON.stringify({
            type: 'vision_calibration',
            samples: calibrationSamplesRef.current,
            timestamp: Date.now() / 1000,
          })
        );
        calibrationSentRef.current = true;
        pushDebug('Sent vision calibration');
      }
    }, 500);
  };

  const startMedia = async () => {
    pushDebug('Requesting camera and microphone');
    setStatusText('Requesting camera and microphone…');

    const mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: { facingMode: 'user' },
    });
    mediaStreamRef.current = mediaStream;
    recordedChunksRef.current = [];

    if (typeof MediaRecorder !== 'undefined') {
      const mimeCandidates = [
        'video/mp4;codecs=h264,aac',
        'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
        'video/mp4',
        'video/webm;codecs=vp9,opus',
        'video/webm;codecs=vp8,opus',
        'video/webm',
      ];
      const supportedMimeType = mimeCandidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || '';
      const recorder = supportedMimeType
        ? new MediaRecorder(mediaStream, { mimeType: supportedMimeType })
        : new MediaRecorder(mediaStream);
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };
      recorder.start(1000);
      mediaRecorderRef.current = recorder;
      pushDebug(`MediaRecorder started (${supportedMimeType || 'browser default'})`);
    }

    const video = videoRef.current;
    if (video) {
      video.srcObject = mediaStream;
      await video.play();
    }

    const audioContext = new AudioContext();
    audioContextRef.current = audioContext;
    sourceNodeRef.current = audioContext.createMediaStreamSource(mediaStream);
    processorNodeRef.current = audioContext.createScriptProcessor(4096, 1, 1);
    processorNodeRef.current.onaudioprocess = (event) => {
      const socket = wsRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      const input = event.inputBuffer.getChannelData(0);
      const resampled = resampleBuffer(input, audioContext.sampleRate, 16000);
      setMicLevel(Math.round(chunkLevel(resampled) * 100));
      socket.send(floatTo16BitPCM(resampled));
    };

    sourceNodeRef.current.connect(processorNodeRef.current);
    processorNodeRef.current.connect(audioContext.destination);
    calibrationSamplesRef.current = [];
    calibrationSentRef.current = false;
    calibrationDeadlineRef.current = Date.now() + 5000;
    startVisionLoop();
    pushDebug('Camera and microphone started');
  };

  const startSession = async () => {
    const backendBase = import.meta.env.VITE_PODIUM_BACKEND_URL || 'http://localhost:8000';
    const backendUrl = new URL(backendBase);
    const protocol = backendUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${backendUrl.host}/ws/${encodeURIComponent(sessionIdRef.current)}?user_id=${encodeURIComponent('frontend_user')}&scenario=${encodeURIComponent(practiceType)}&target_duration=${encodeURIComponent(duration * 60)}&audience_size=${encodeURIComponent(audienceSize)}`;

    pushDebug(`Opening websocket: ${wsUrl}`);
    setConnectionState('Connecting');
    setStatusText('Connecting to backend…');
    setPhase('connecting');

    const socket = new WebSocket(wsUrl);
    socket.binaryType = 'arraybuffer';
    wsRef.current = socket;

    socket.onopen = async () => {
      pushDebug('Websocket connected');
      setConnectionState('Connected');
      try {
        await startMedia();
        setPhase('speaking');
        setStatusText('Session live. Start speaking.');
      } catch (error) {
        const detail = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
        pushDebug(`Media startup failed: ${detail}`);
        setConnectionState('Connected');
        setStatusText(`Camera/mic blocked: ${detail}`);
        setPhase('ended');
      }
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data) as Record<string, unknown>;
      pushDebug(`Message: ${String(data.type || 'unknown')}`);

      if (data.type === 'connected') {
        setStatusText(`Session ready: ${String(data.session_id || sessionIdRef.current)}`);
      }
      if (data.type === 'transcript') {
        setWpm(Math.round(Number(data.wpm || 0)));
        const text = String(data.text || '').trim();
        if (text) {
          setStatusText(`Transcript: ${text}`);
        }
      }
      if (data.type === 'engagement_update') {
        setEngagementScore(Number(data.score || 0));
        setDominantSignal(String(data.dominant_signal || '--'));
      }
      if (data.type === 'audience_update') {
        const avatarStates = (data.avatar_states || {}) as Record<string, string>;
        const transitionDelays = (data.transition_delays_ms || {}) as Record<string, number>;
        setAudience((current) =>
          current.map((member) => ({
            ...member,
            avatarState: (avatarStates[member.id] as AvatarState) || member.avatarState,
            transitionDelay:
              typeof transitionDelays[member.id] === 'number' ? transitionDelays[member.id] : member.transitionDelay,
          }))
        );
      }
      if (data.type === 'coach_tip') {
        const tip = String(data.tip || '').trim();
        if (tip) {
          setStatusText(`Coach tip: ${tip}`);
        }
        const audioBase64 = String(data.audio_base64 || '');
        if (audioBase64) {
          void playBase64Audio(audioBase64);
        }
      }
      if (data.type === 'qa_question') {
        const question = String(data.question || '').trim();
        if (question) {
          setQuestionText(question);
          setStatusText(`Question: ${question}`);
          setPhase('qa');
          setQuestionPending(true);
        }
        const audioBase64 = String(data.audio_base64 || '');
        if (audioBase64) {
          void playBase64Audio(audioBase64);
        }
      }
      if (data.type === 'session_breakdown') {
        breakdownSeenRef.current = true;
        setPhase('ended');
        setStatusText('Session complete.');
        setConnectionState('Complete');
        void (async () => {
          await stopRecorder();
          const recordingUrl = buildRecordingUrl();
          await cleanupLocalMedia();
          const breakdown = ((data.breakdown || {}) as Record<string, unknown>);
          const engagementHistory = Array.isArray(data.engagement_history)
            ? (data.engagement_history as Array<Record<string, unknown>>)
            : [];
          window.setTimeout(() => {
            recordingUrlRef.current = null; // transfer ownership to caller before cleanup can revoke it
            onEndSession({ breakdown, engagementHistory, recordingUrl });
          }, 400);
        })();
      }
      if (data.type === 'error') {
        setStatusText(String(data.message || 'Session error'));
      }
    };

    socket.onerror = () => {
      pushDebug('Websocket error');
      setConnectionState('Error');
      setStatusText('Websocket error');
    };

    socket.onclose = () => {
      pushDebug('Websocket closed');
      void cleanupLocalMedia();
      if (!breakdownSeenRef.current) {
        setConnectionState('Disconnected');
        setStatusText(stopRequestedRef.current ? 'Session closed before backend finished.' : 'Disconnected.');
        setPhase('ended');
      }
    };
  };

  const stopSession = async () => {
    if (phase !== 'speaking') return;
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    pushDebug('Sending session_end');
    stopRequestedRef.current = true;
    setPhase('finishing');
    setStatusText('Stopping session…');
    socket.send(JSON.stringify({ type: 'session_end', user_id: 'frontend_user' }));
    await cleanupLocalMedia();
    setConnectionState('Waiting for backend');
  };

  const submitQaAnswer = () => {
    const socket = wsRef.current;
    const answer = qaInput.trim();
    if (!socket || socket.readyState !== WebSocket.OPEN || !answer) return;

    socket.send(
      JSON.stringify({
        type: 'qa_answer',
        answer,
        timestamp: Date.now() / 1000,
      })
    );
    pushDebug('Sent qa_answer');
    setQaInput('');
    setQuestionPending(false);
    setPhase('finishing');
    setStatusText('Answer sent. Waiting for final breakdown…');
  };

  return (
    <div
      className="h-screen w-screen overflow-hidden relative"
      style={{ backgroundColor: '#111111' }}
      onMouseMove={() => {
        if (phase === 'speaking') setShowEndButton(true);
      }}
      onMouseLeave={() => setShowEndButton(false)}
    >
      <video ref={videoRef} className="hidden" muted playsInline />
      <canvas ref={canvasRef} className="hidden" />

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
        <div className="text-right" style={{ fontSize: '12px', color: '#FFFFFF', opacity: 0.75 }}>
          {connectionState}
        </div>
      </div>

      <div className="absolute top-14 right-6 z-20 flex gap-3">
        {[
          { label: `Mic ${micLevel}%` },
          { label: `WPM ${wpm}` },
          { label: `Engagement ${Math.round(engagementScore * 100)}%` },
        ].map((chip) => (
          <div
            key={chip.label}
            className="px-4 py-2 rounded-full"
            style={{ backgroundColor: 'rgba(255,255,255,0.08)', color: '#FFFFFF', backdropFilter: 'blur(8px)' }}
          >
            {chip.label}
          </div>
        ))}
      </div>

      <div className="absolute top-14 left-6 z-20 max-w-xl rounded-3xl px-5 py-4" style={{ backgroundColor: 'rgba(0,0,0,0.35)', color: '#FFFFFF', backdropFilter: 'blur(8px)' }}>
        <div className="text-xs uppercase tracking-[0.28em] opacity-60">Live status</div>
        <div className="mt-2 text-lg" style={{ fontWeight: 500 }}>{statusText}</div>
        <div className="mt-2 text-sm opacity-70">Signal: {dominantSignal}</div>
      </div>

      <div className="absolute inset-0 flex items-center justify-center" style={{ paddingTop: '36px' }}>
        <div className={`grid ${getGridCols(audience.length)} gap-4`} style={{ width: 'min(82vw, 880px)' }}>
          {audience.map((member) => (
            <div
              key={member.id}
              className="relative overflow-hidden rounded-lg bg-[#1a1a1a]"
              style={{
                aspectRatio: '4/3',
                transform: member.mirrored ? 'scaleX(-1)' : 'none',
                boxShadow: `0 0 0 3px ${getRingColor(member.avatarState, engagementScore)}`,
                transition: `box-shadow 1000ms ease, transform 500ms ease`,
              }}
            >
              <img
                src={getAudienceImage(member)}
                alt=""
                className="absolute inset-0 w-full h-full object-cover object-center"
                style={{
                  transition: 'opacity 1500ms ease',
                  transitionDelay: `${member.transitionDelay}ms`,
                }}
              />
              <div
                className="absolute bottom-2 left-2 px-2 py-0.5 rounded z-10"
                style={{
                  backgroundColor: 'rgba(0,0,0,0.25)',
                  fontSize: '11px',
                  color: '#FFFFFF',
                  opacity: 0.7,
                  fontWeight: 400,
                  transform: member.mirrored ? 'scaleX(-1)' : 'none',
                }}
              >
                {(member.mirrored ? member.mirroredName : member.name)} · {member.avatarState}
              </div>
            </div>
          ))}
        </div>
      </div>

      {(phase === 'qa' || phase === 'finishing') && (
        <div className="absolute inset-x-0 bottom-8 z-30 flex justify-center px-6">
          <div className="w-full max-w-3xl rounded-[28px] p-5" style={{ backgroundColor: 'rgba(9, 12, 20, 0.92)', border: '1px solid rgba(232,184,75,0.22)', backdropFilter: 'blur(20px)' }}>
            <div className="text-xs uppercase tracking-[0.28em]" style={{ color: '#E8B84B' }}>Argument question</div>
            <div className="mt-3 text-lg leading-relaxed" style={{ color: '#FFFFFF', fontWeight: 500 }}>
              {questionText}
            </div>
            {questionPending && (
              <div className="mt-4 flex gap-3">
                <input
                  value={qaInput}
                  onChange={(event) => setQaInput(event.target.value)}
                  placeholder="Answer the question..."
                  className="flex-1 rounded-full px-5 py-3 bg-transparent outline-none"
                  style={{ border: '1px solid rgba(255,255,255,0.14)', color: '#FFFFFF' }}
                />
                <button
                  onClick={submitQaAnswer}
                  disabled={!qaInput.trim()}
                  className="rounded-full px-5 py-3 disabled:opacity-40"
                  style={{ backgroundColor: '#E8B84B', color: '#111111', fontWeight: 600 }}
                >
                  Send
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {phase === 'speaking' && (
        <div
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-30"
          style={{
            opacity: showEndButton ? 1 : 0,
            pointerEvents: showEndButton ? 'auto' : 'none',
            transition: 'opacity 0.3s ease',
          }}
        >
          <button
            onClick={() => void stopSession()}
            style={{
              backgroundColor: 'rgba(255,255,255,0.08)',
              backdropFilter: 'blur(8px)',
              color: '#FFFFFF',
              borderRadius: '99px',
              padding: '10px 24px',
              fontSize: '13px',
              fontWeight: 500,
              border: '0.5px solid rgba(255,255,255,0.15)',
            }}
          >
            I'm done
          </button>
        </div>
      )}

      <div className="absolute bottom-6 left-6 z-20 w-[420px] rounded-[28px] p-5" style={{ backgroundColor: 'rgba(0,0,0,0.32)', color: '#FFFFFF', backdropFilter: 'blur(18px)' }}>
        <div className="text-xs uppercase tracking-[0.28em]" style={{ color: '#E8B84B' }}>Session debug</div>
        <div className="mt-3 space-y-2 text-sm opacity-85">
          {debugLines.length ? (
            debugLines.map((line) => <div key={line}>{line}</div>)
          ) : (
            <div>Waiting for session startup…</div>
          )}
        </div>
      </div>
    </div>
  );
}
