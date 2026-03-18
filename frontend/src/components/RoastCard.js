import React, { useState, useEffect, useRef } from 'react';

const STATE = {
  LOADING: 'LOADING',
  PLAYING: 'PLAYING',
  SHARED: 'SHARED',
  ERROR: 'ERROR',
};

function RoastCard({ roastData, error }) {
  const [cardState, setCardState] = useState(STATE.LOADING);
  const audioRef = useRef(null);
  const audioUrlRef = useRef(null);

  useEffect(() => {
    if (error) {
      setCardState(STATE.ERROR);
      return;
    }

    if (!roastData) return; // Still loading

    setCardState(STATE.PLAYING);

    if (roastData.audio_base64) {
      try {
        const binary = atob(roastData.audio_base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);
        audioUrlRef.current = url;
        audioRef.current = new Audio(url);
        audioRef.current.play().catch((e) => {
          console.warn('Audio autoplay blocked:', e);
        });
      } catch (e) {
        console.error('Audio decode error:', e);
      }
    }

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
    };
  }, [roastData, error]);

  const handleShare = () => {
    if (!roastData) return;
    const text = [
      `🎙️ DERP TOP 40 | ${roastData.genre_emoji} ${roastData.genre.toUpperCase()}`,
      `"${roastData.character_type}"`,
      `❝ ${roastData.quote} ❞`,
      `— LiquidSMARTS™ Voice Training`,
    ].join('\n');

    navigator.clipboard.writeText(text).then(() => {
      setCardState(STATE.SHARED);
      setTimeout(() => setCardState(STATE.PLAYING), 2000);
    }).catch(() => {
      console.warn('Clipboard write failed');
    });
  };

  if (cardState === STATE.LOADING) {
    return (
      <div style={styles.card}>
        <div style={styles.loadingIcon}>🎙️</div>
        <p style={styles.loadingText}>Generating your roast...</p>
      </div>
    );
  }

  if (cardState === STATE.ERROR) {
    return (
      <div style={styles.card}>
        <div style={styles.header}>🎙️ DERP TOP 40</div>
        <p style={styles.errorText}>
          The roast machine timed out. Your performance was too much to process.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>🎙️ DERP TOP 40</div>
      <div style={styles.divider} />

      <div style={styles.genre}>
        {roastData.genre_emoji} {roastData.genre.toUpperCase()}
      </div>

      <div style={styles.characterType}>"{roastData.character_type}"</div>
      <div style={styles.judgment}>{roastData.judgment}</div>

      <div style={styles.quoteBlock}>
        <span style={styles.quoteMarks}>❝</span>
        {' '}{roastData.quote}{' '}
        <span style={styles.quoteMarks}>❞</span>
      </div>

      {roastData.audio_base64 && (
        <div style={styles.audioBar}>▶ Playing...</div>
      )}

      <button
        style={styles.shareButton}
        onClick={handleShare}
      >
        {cardState === STATE.SHARED ? '✅ Copied!' : '📋 Share This Shame'}
      </button>
    </div>
  );
}

const styles = {
  card: {
    background: '#1a1a2e',
    color: '#eee',
    borderRadius: 12,
    padding: '24px 28px',
    maxWidth: 420,
    margin: '24px auto',
    fontFamily: 'monospace',
    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
    textAlign: 'center',
  },
  header: {
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 2,
    color: '#a78bfa',
  },
  divider: {
    borderTop: '1px solid #333',
    margin: '12px 0',
  },
  genre: {
    fontSize: 22,
    fontWeight: 'bold',
    margin: '8px 0',
    color: '#f97316',
  },
  characterType: {
    fontSize: 20,
    fontWeight: 'bold',
    margin: '12px 0 4px',
    color: '#fff',
  },
  judgment: {
    fontSize: 14,
    color: '#aaa',
    margin: '0 0 16px',
    lineHeight: 1.5,
  },
  quoteBlock: {
    background: '#0f0f23',
    borderLeft: '3px solid #a78bfa',
    padding: '12px 16px',
    borderRadius: 6,
    fontSize: 15,
    fontStyle: 'italic',
    color: '#e2e8f0',
    margin: '0 0 16px',
    textAlign: 'left',
    lineHeight: 1.6,
  },
  quoteMarks: {
    color: '#a78bfa',
    fontSize: 18,
  },
  audioBar: {
    fontSize: 13,
    color: '#6ee7b7',
    margin: '0 0 12px',
    letterSpacing: 1,
  },
  shareButton: {
    background: '#4f46e5',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '10px 20px',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 0.5,
    width: '100%',
  },
  loadingIcon: {
    fontSize: 40,
    display: 'block',
    margin: '0 auto 12px',
  },
  loadingText: {
    color: '#aaa',
    fontSize: 14,
    letterSpacing: 1,
  },
  errorText: {
    color: '#f87171',
    fontSize: 14,
    marginTop: 12,
    lineHeight: 1.6,
  },
};

export default RoastCard;
