import { useCallback, useRef, useState } from 'react';
import { Room, RoomEvent, Track, ConnectionState } from 'livekit-client';
import * as api from '../api/client';

function makeEntry(id, role, content, source, final = true) {
  return {
    id,
    role,
    content,
    source, // 'stt' | 'tts' | 'text'
    final,
    timestamp: new Date(),
  };
}

function normalizeText(text) {
  return (text || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

/** Normalize LiveKit transcription chunk payloads into plain display text. */
function cleanTranscriptionChunk(raw) {
  return (raw || '')
    .split('\n')
    .map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return '';
      if (trimmed.startsWith('{')) {
        try {
          const parsed = JSON.parse(trimmed);
          return parsed.text || parsed.value || '';
        } catch {
          return trimmed;
        }
      }
      return trimmed;
    })
    .filter(Boolean)
    .join(' ')
    .trim();
}

/**
 * LiveKit may yield either:
 * - cumulative text (full string so far), or
 * - deltas (just the next word) — treat as append so we don't show only the last word.
 */
function mergeTranscription(previous, incoming) {
  const next = (incoming || '').trim();
  if (!next) return previous || '';
  const prev = (previous || '').trim();
  if (!prev) return next;

  // Cumulative snapshot (or longer revision of the same utterance)
  if (next.startsWith(prev)) return next;
  // Shorter cumulative repair / rewind
  if (prev.startsWith(next) && next.length >= Math.min(8, prev.length * 0.5)) return next;

  // Duplicate chunk
  if (prev.endsWith(next) || prev === next) return prev;

  // Delta: append the new fragment
  const needsSpace = !/\s$/.test(prev) && !/^[.,!?;:]/.test(next);
  return `${prev}${needsSpace ? ' ' : ''}${next}`.replace(/\s+/g, ' ').trim();
}

export function useLiveKit(voiceProvider) {
  const roomRef = useRef(null);
  const interimIdsRef = useRef({ user: null, assistant: null });
  const seenFinalRef = useRef(new Set());
  const transcriptRef = useRef([]);
  const conversationIdRef = useRef(null);
  const [connectionState, setConnectionState] = useState(ConnectionState.Disconnected);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);

  const setConversation = useCallback((id) => {
    conversationIdRef.current = id || null;
    setConversationId(id || null);
  }, []);

  const updateTranscript = useCallback((updater) => {
    setTranscript((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      transcriptRef.current = next;
      return next;
    });
  }, []);

  const addTranscript = useCallback((role, content, source = 'text') => {
    const text = (content || '').trim();
    if (!text) return;
    const id = `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    updateTranscript((prev) => [...prev, makeEntry(id, role, text, source, true)]);
  }, [updateTranscript]);

  const upsertVoiceTranscript = useCallback((role, segment) => {
    const text = (segment.text || '').trim();
    if (!text) return;

    const key = role === 'user' ? 'user' : 'assistant';
    const source = role === 'user' ? 'stt' : 'tts';
    const isFinal = Boolean(segment.final);
    const dedupeKey = `${role}:${normalizeText(text)}`;

    if (isFinal && seenFinalRef.current.has(dedupeKey)) {
      // Same final text already shown — drop duplicate stream chunk
      interimIdsRef.current[key] = null;
      return;
    }

    // Prefer stable segment id; otherwise keep updating the open interim bubble only
    let id = segment.id || interimIdsRef.current[key];
    if (!id) {
      id = `${key}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    }

    if (!isFinal) {
      interimIdsRef.current[key] = id;
    } else {
      interimIdsRef.current[key] = null;
      seenFinalRef.current.add(dedupeKey);
    }

    updateTranscript((prev) => {
      // 1) Same segment id → update that bubble only (streaming growth)
      let existingIndex = prev.findIndex((entry) => entry.id === id);

      // 2) Or the one open interim slot for this speaker (same id we tracked)
      if (existingIndex < 0 && !isFinal) {
        const tracked = interimIdsRef.current[key];
        if (tracked) {
          existingIndex = prev.findIndex((entry) => entry.id === tracked && !entry.final);
        }
      }

      // Never replace an older finalized (or another turn's) bubble.
      // If a previous interim never finalized, seal it and append a new message.
      if (existingIndex < 0 && !isFinal) {
        const stuckInterim = prev.findIndex(
          (entry) => !entry.final && entry.role === role && entry.source === source,
        );
        if (stuckInterim >= 0) {
          const sealed = [...prev];
          sealed[stuckInterim] = { ...sealed[stuckInterim], final: true };
          return [...sealed, makeEntry(id, role, text, source, false)];
        }
      }

      const entry = makeEntry(id, role, text, source, isFinal);
      if (existingIndex >= 0) {
        const next = [...prev];
        const prevContent = next[existingIndex].content || '';
        const mergedText = mergeTranscription(prevContent, text);
        next[existingIndex] = {
          ...entry,
          content: mergedText,
          timestamp: next[existingIndex].timestamp,
          final: isFinal,
        };
        return next;
      }

      return [...prev, entry];
    });
  }, [updateTranscript]);

  const connect = useCallback(async () => {
    if (roomRef.current) return;

    try {
      setError(null);
      interimIdsRef.current = { user: null, assistant: null };
      seenFinalRef.current = new Set(
        transcriptRef.current
          .filter((entry) => entry.final)
          .map((entry) => `${entry.role}:${normalizeText(entry.content)}`),
      );
      // Seal any open interim bubbles so a new voice session appends below them
      updateTranscript((prev) =>
        prev.map((entry) => (entry.final ? entry : { ...entry, final: true })),
      );

      const tokenData = await api.getToken(voiceProvider, conversationIdRef.current);
      setConversation(tokenData.conversation_id);

      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      room.on(RoomEvent.ConnectionStateChanged, (state) => {
        setConnectionState(state);
        setIsListening(state === ConnectionState.Connected);
      });

      room.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.id = `audio-${participant.identity}`;
          document.body.appendChild(el);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((el) => el.remove());
      });

      room.registerTextStreamHandler('lk.transcription', async (reader, participantInfo) => {
        const localIdentity = room.localParticipant?.identity;
        const identity = participantInfo?.identity;
        const isUser = !identity || identity === localIdentity;
        const role = isUser ? 'user' : 'assistant';
        const attrs = reader.info?.attributes || {};
        // Prefer a stable segment id; if missing, keep growing the open interim bubble
        // so word-level streams for the same utterance stay in one bubble.
        const segmentId =
          attrs['lk.segment_id'] ||
          attrs['lk.transcription_segment_id'] ||
          reader.info?.id ||
          interimIdsRef.current[role] ||
          `${role}-${Date.now()}`;

        let latest = '';
        // Seed from open interim with same id so a new delta stream continues the sentence
        const open = transcriptRef.current.find(
          (entry) => entry.id === segmentId && !entry.final && entry.role === role,
        );
        if (open?.content) latest = open.content;

        try {
          for await (const chunk of reader) {
            const cleaned = cleanTranscriptionChunk(
              typeof chunk === 'string' ? chunk : String(chunk ?? ''),
            );
            if (!cleaned) continue;
            latest = mergeTranscription(latest, cleaned);
            upsertVoiceTranscript(role, {
              id: segmentId,
              text: latest,
              final: false,
            });
          }
        } catch {
          // stream aborted / room closed
        }

        if (!latest) return;
        upsertVoiceTranscript(role, {
          id: segmentId,
          text: latest,
          final: true,
        });
      });

      await room.connect(tokenData.url, tokenData.token);
      await room.localParticipant.setMicrophoneEnabled(true);
      setIsListening(true);
    } catch (e) {
      roomRef.current = null;
      setError(e.response?.data?.detail || e.message || 'Failed to connect');
      setIsListening(false);
    }
  }, [voiceProvider, upsertVoiceTranscript, setConversation, updateTranscript]);

  const disconnect = useCallback(async ({ clearChat = false } = {}) => {
    const room = roomRef.current;
    if (room) {
      await room.localParticipant.setMicrophoneEnabled(false);
      room.disconnect();
      roomRef.current = null;
    }
    setIsListening(false);
    setConnectionState(ConnectionState.Disconnected);
    interimIdsRef.current = { user: null, assistant: null };
    seenFinalRef.current = new Set();
    const activeConversationId = conversationIdRef.current;
    if (clearChat) {
      updateTranscript([]);
      setConversation(null);
    } else {
      // Keep history; just mark any streaming bubbles complete
      updateTranscript((prev) =>
        prev.map((entry) => (entry.final ? entry : { ...entry, final: true })),
      );
    }
    if (activeConversationId) {
      try { await api.endSession(activeConversationId); } catch { /* ignore */ }
    }
  }, [updateTranscript, setConversation]);

  const sendText = useCallback(async (text) => {
    addTranscript('user', text, 'text');
    try {
      const result = await api.queryMedicine(text, conversationIdRef.current);
      if (result.conversation_id) {
        setConversation(result.conversation_id);
      }
      addTranscript('assistant', result.answer, 'text');
    } catch {
      addTranscript('assistant', "Sorry, I couldn't process that request. Please try again.", 'text');
    }
  }, [addTranscript, setConversation]);

  const toggleMic = useCallback(async () => {
    if (!roomRef.current || connectionState !== ConnectionState.Connected) {
      await connect();
      return;
    }
    const local = roomRef.current.localParticipant;
    const enabled = local.isMicrophoneEnabled;
    if (!enabled) {
      await local.setMicrophoneEnabled(true);
      setIsListening(true);
      return;
    }
    await local.setMicrophoneEnabled(true);
    setIsListening(true);
  }, [connect, connectionState]);

  return {
    connect, disconnect, toggleMic, sendText,
    isListening, connectionState, transcript, conversationId, error,
    isConnected: connectionState === ConnectionState.Connected,
  };
}
