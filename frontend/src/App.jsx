import { useState, useEffect, useRef, useCallback } from "react";

// ─── API CONFIG ────────────────────────────────────────────────────────────────
const API = "http://localhost:8000/api/v1";

async function apiFetch(path, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.status === 204 ? null : res.json();
}

// ─── ICONS ─────────────────────────────────────────────────────────────────────
const Icon = ({ d, size = 20, className = "", style = {} }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
    <path d={d} />
  </svg>
);

const Icons = {
  rocket: "M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09zM12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z",
  plus: "M12 5v14M5 12h14",
  trash: "M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2",
  upload: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6",
  search: "M21 21l-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0z",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  chat: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  chevron: "M9 18l6-6-6-6",
  x: "M18 6L6 18M6 6l12 12",
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  check: "M20 6L9 17l-5-5",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  heart: "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
  alert: "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01",
  users: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  refresh: "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15",
  mic: "M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3zM19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8",
  micOff: "M1 1l22 22M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23M12 19v4M8 23h8",
  waveform: "M22 12h-4l-3 9L9 3l-3 9H2",
  video: "M23 7l-7 5 7 5V7zM2 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z", // added video icon
};

// ─── STARFIELD BACKGROUND ──────────────────────────────────────────────────────
function Starfield() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let animId;
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
    resize();
    window.addEventListener("resize", resize);
    const stars = Array.from({ length: 180 }, () => ({
      x: Math.random(), y: Math.random(), r: Math.random() * 1.5 + 0.3,
      speed: Math.random() * 0.00008 + 0.00002, opacity: Math.random() * 0.7 + 0.2,
      twinkle: Math.random() * Math.PI * 2,
    }));
    let t = 0;
    const draw = () => {
      t += 0.01;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      stars.forEach((s) => {
        s.x -= s.speed;
        if (s.x < 0) { s.x = 1; s.y = Math.random(); }
        const flicker = s.opacity * (0.7 + 0.3 * Math.sin(t * 2 + s.twinkle));
        ctx.beginPath();
        ctx.arc(s.x * canvas.width, s.y * canvas.height, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180,220,255,${flicker})`;
        ctx.fill();
      });
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(animId); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none" }} />;
}

// ─── STYLES ────────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Crimson+Pro:ital,wght@0,300;0,400;1,300&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --void: #05080f; --deep: #080d1a; --surface: #0d1425; --panel: #111929;
    --border: #1e2d45; --border-hi: #2a3f5f;
    --aurora-1: #0ff4c6; --aurora-2: #38bdf8;
    --amber: #f59e0b; --amber-dim: #b45309;
    --text: #c8daf4; --text-dim: #5a7a9e; --text-muted: #3a5070;
    --danger: #ef4444; --success: #10b981;
    --font-ui: 'Space Grotesk', sans-serif; --font-mono: 'JetBrains Mono', monospace; --font-prose: 'Crimson Pro', serif;
    --r: 10px; --r-lg: 16px;
  }
  html, body, #root { height: 100%; overflow: hidden; }
  body { background: var(--void); color: var(--text); font-family: var(--font-ui); font-size: 14px; line-height: 1.5; }
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 99px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--aurora-2); }
  .app { position: relative; zIndex: 1; height: 100vh; display: flex; flex-direction: column; }

  /* ── AUTH ── */
  .auth-wrap { flex: 1; display: flex; align-items: center; justify-content: center; padding: 24px; gap: 48px; }
  .auth-hero { flex: 0 0 380px; display: flex; flex-direction: column; gap: 20px; }
  .auth-hero-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; background: rgba(15,244,198,0.06); border: 1px solid rgba(15,244,198,0.2); border-radius: 99px; font-size: 11px; font-family: var(--font-mono); color: var(--aurora-1); letter-spacing: 0.08em; text-transform: uppercase; width: fit-content; }
  .auth-hero h1 { font-family: var(--font-mono); font-size: 48px; font-weight: 500; color: #fff; line-height: 1.1; letter-spacing: -0.02em; }
  .auth-hero h1 span { background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
  .auth-hero p { font-family: var(--font-prose); font-size: 18px; color: var(--text-dim); line-height: 1.6; font-weight: 300; }
  .auth-features { display: flex; flex-direction: column; gap: 12px; margin-top: 8px; }
  .auth-feature { display: flex; align-items: center; gap: 12px; color: var(--text-dim); font-size: 13px; }
  .auth-feature-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--aurora-1); flex-shrink: 0; box-shadow: 0 0 8px var(--aurora-1); }
  .auth-card { background: rgba(13,20,37,0.85); backdrop-filter: blur(20px); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 36px; width: 380px; flex-shrink: 0; }
  .auth-card-header { margin-bottom: 28px; }
  .auth-card-header h2 { font-size: 22px; font-weight: 600; color: #fff; margin-bottom: 6px; }
  .auth-card-header p { font-size: 13px; color: var(--text-dim); }
  .auth-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--deep); padding: 4px; border-radius: var(--r); }
  .auth-tab { flex: 1; padding: 8px; border: none; background: transparent; color: var(--text-dim); font-family: var(--font-ui); font-size: 13px; font-weight: 500; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
  .auth-tab.active { background: var(--surface); color: var(--aurora-1); box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
  .form-group { margin-bottom: 16px; }
  .form-group label { display: block; font-size: 11px; font-family: var(--font-mono); color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
  .form-group input { width: 100%; background: var(--deep); border: 1px solid var(--border); border-radius: var(--r); padding: 10px 14px; color: var(--text); font-family: var(--font-ui); font-size: 14px; outline: none; transition: border-color 0.2s, box-shadow 0.2s; }
  .form-group input:focus { border-color: var(--aurora-2); box-shadow: 0 0 0 3px rgba(56,189,248,0.1); }
  .form-group input::placeholder { color: var(--text-muted); }
  .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 20px; border-radius: var(--r); border: none; font-family: var(--font-ui); font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary { background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2)); color: var(--void); width: 100%; }
  .btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(15,244,198,0.25); }
  .btn-ghost { background: transparent; color: var(--text-dim); border: 1px solid var(--border); }
  .btn-ghost:hover:not(:disabled) { background: var(--surface); color: var(--text); border-color: var(--border-hi); }
  .btn-danger { background: transparent; color: var(--danger); border: 1px solid rgba(239,68,68,0.3); }
  .btn-danger:hover:not(:disabled) { background: rgba(239,68,68,0.1); }
  .btn-sm { padding: 6px 12px; font-size: 12px; }
  .btn-icon { padding: 8px; border-radius: 8px; }
  .error-msg { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: var(--r); padding: 10px 14px; color: #f87171; font-size: 13px; margin-bottom: 16px; }
  .success-msg { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); border-radius: var(--r); padding: 10px 14px; color: #34d399; font-size: 13px; margin-bottom: 16px; }

  /* ── LAYOUT ── */
  .layout { display: flex; height: 100vh; overflow: hidden; }

  /* ── SIDEBAR ── */
  .sidebar { width: 260px; flex-shrink: 0; background: rgba(8,13,26,0.95); border-right: 1px solid var(--border); display: flex; flex-direction: column; backdrop-filter: blur(12px); }
  .sidebar-header { padding: 20px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; }
  .sidebar-logo { width: 32px; height: 32px; background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2)); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--void); flex-shrink: 0; }
  .sidebar-logo-text { font-family: var(--font-mono); font-size: 16px; font-weight: 500; color: #fff; }
  .sidebar-logo-sub { font-size: 10px; color: var(--text-dim); font-family: var(--font-mono); letter-spacing: 0.1em; }
  .sidebar-nav { flex: 1; padding: 12px 8px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
  .nav-section-label { font-size: 10px; font-family: var(--font-mono); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.12em; padding: 8px 8px 4px; margin-top: 4px; }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 8px; color: var(--text-dim); font-size: 13px; font-weight: 400; cursor: pointer; transition: all 0.15s; border: none; background: transparent; width: 100%; text-align: left; }
  .nav-item:hover { background: var(--surface); color: var(--text); }
  .nav-item.active { background: rgba(15,244,198,0.06); color: var(--aurora-1); border: 1px solid rgba(15,244,198,0.12); }
  .nav-item svg { flex-shrink: 0; }
  .nav-item-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sidebar-footer { padding: 12px 8px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 4px; }
  .user-pill { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; background: var(--surface); border: 1px solid var(--border); }
  .user-pill-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2)); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; color: var(--void); flex-shrink: 0; }
  .user-pill-info { flex: 1; overflow: hidden; }
  .user-pill-name { font-size: 12px; font-weight: 500; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .user-pill-role { font-size: 10px; color: var(--text-muted); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: 0.06em; }

  /* ── MAIN ── */
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
  .topbar { height: 52px; padding: 0 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; background: rgba(8,13,26,0.8); backdrop-filter: blur(12px); flex-shrink: 0; }
  .topbar-title { font-size: 15px; font-weight: 500; color: var(--text); flex: 1; }

  /* ── CHAT ── */
  .chat-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
  .messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; }
  .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; padding: 40px; text-align: center; color: var(--text-dim); }
  .empty-icon { width: 64px; height: 64px; background: rgba(15,244,198,0.06); border: 1px solid rgba(15,244,198,0.12); border-radius: 20px; display: flex; align-items: center; justify-content: center; color: var(--aurora-1); margin-bottom: 4px; }
  .empty-title { font-size: 20px; font-weight: 500; color: var(--text); }
  .empty-sub { font-size: 14px; color: var(--text-dim); max-width: 360px; font-family: var(--font-prose); font-size: 16px; line-height: 1.5; }
  .prompts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; max-width: 480px; }
  .prompt-chip { background: var(--panel); border: 1px solid var(--border); border-radius: var(--r); padding: 12px 14px; font-size: 12px; color: var(--text-dim); cursor: pointer; text-align: left; transition: all 0.2s; font-family: var(--font-ui); }
  .prompt-chip:hover { background: rgba(15,244,198,0.04); border-color: rgba(15,244,198,0.2); color: var(--text); }
  .message { display: flex; gap: 12px; animation: msgIn 0.3s ease-out; }
  @keyframes msgIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  .message.assistant { flex-direction: row; }
  .message.user { flex-direction: row-reverse; }
  .msg-avatar { width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; }
  .message.assistant .msg-avatar { background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2)); color: var(--void); }
  .message.user .msg-avatar { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: var(--amber); }
  .msg-body { flex: 1; max-width: 680px; }
  .message.user .msg-body { display: flex; flex-direction: column; align-items: flex-end; }
  .msg-bubble { padding: 12px 16px; border-radius: 14px; font-size: 14px; line-height: 1.65; max-width: 100%; }
  .message.assistant .msg-bubble { background: var(--panel); border: 1px solid var(--border); border-top-left-radius: 4px; color: var(--text); }
  .message.user .msg-bubble { background: rgba(15,244,198,0.06); border: 1px solid rgba(15,244,198,0.15); border-top-right-radius: 4px; color: var(--text); }
  .msg-time { font-size: 10px; font-family: var(--font-mono); color: var(--text-muted); margin-top: 4px; padding: 0 4px; }
  .msg-sources { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .msg-source-label { font-size: 10px; font-family: var(--font-mono); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; }
  .source-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(56,189,248,0.06); border: 1px solid rgba(56,189,248,0.15); border-radius: 99px; font-size: 11px; color: var(--aurora-2); font-family: var(--font-mono); }
  .msg-timing { font-size: 10px; font-family: var(--font-mono); color: var(--text-muted); margin-top: 6px; display: flex; gap: 8px; }

  /* ── INPUT ── */
  .chat-input-wrap { padding: 16px 24px 20px; border-top: 1px solid var(--border); background: rgba(8,13,26,0.8); backdrop-filter: blur(12px); }
  .chat-input-inner { display: flex; align-items: flex-end; gap: 10px; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 10px 10px 10px 16px; transition: border-color 0.2s, box-shadow 0.2s; }
  .chat-input-inner:focus-within { border-color: var(--aurora-2); box-shadow: 0 0 0 3px rgba(56,189,248,0.08); }
  .chat-textarea { flex: 1; background: transparent; border: none; outline: none; color: var(--text); font-family: var(--font-ui); font-size: 14px; line-height: 1.6; resize: none; max-height: 200px; overflow-y: auto; min-height: 24px; }
  .chat-textarea::placeholder { color: var(--text-muted); }
  .send-btn { width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2)); border: none; color: var(--void); display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; transition: all 0.2s; }
  .send-btn:hover:not(:disabled) { transform: scale(1.05); box-shadow: 0 4px 14px rgba(15,244,198,0.3); }
  .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .typing-indicator { display: flex; gap: 4px; align-items: center; padding: 4px 0; }
  .typing-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--aurora-1); animation: typingBounce 1.2s infinite; }
  .typing-dot:nth-child(2) { animation-delay: 0.2s; }
  .typing-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes typingBounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-6px); opacity: 1; } }

  /* ── MIC BUTTON ── */
  .mic-btn { width: 36px; height: 36px; border-radius: 10px; border: none; display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; transition: all 0.2s; background: transparent; color: var(--text-dim); }
  .mic-btn:hover:not(:disabled) { background: var(--surface); color: var(--text); }
  .mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .mic-btn.recording { background: rgba(239,68,68,0.12); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); animation: micPulse 1.4s ease-in-out infinite; }
  @keyframes micPulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); } 50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); } }
  .rec-timer { font-size: 11px; font-family: var(--font-mono); color: #ef4444; min-width: 32px; text-align: center; letter-spacing: 0.04em; }

  /* ── MEDIA HUD (Audio + Video) ── */
  .media-hud {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 12px;
    pointer-events: none;
    align-items: flex-end;
    max-width: 340px;
  }
  .media-hud > * { pointer-events: all; }

 /* ── SENSOR HUD ── */
.sensor-hud {
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}
.sensor-hud > * { pointer-events: all; }

/* ── PULSING BUTTON ── */
.pulsing {
  animation: btnPulse 1.5s ease-in-out infinite;
}
@keyframes btnPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
}

/* ── VAD INDICATOR ── */
.vad-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(15,244,198,0.06);
  border: 1px solid rgba(15,244,198,0.15);
  border-radius: 99px;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--aurora-1);
  transition: all 0.3s;
}
.vad-indicator.speaking {
  background: rgba(239,68,68,0.08);
  border-color: rgba(239,68,68,0.25);
  color: #ef4444;
}
.vad-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 1.5s infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

  /* ── VIDEO HUD ── */
  .video-hud {
    display: flex;
    flex-direction: column;
    gap: 10px;
    pointer-events: none;
    align-items: flex-end;
  }
  .video-hud > * { pointer-events: all; }
  .video-preview-card {
    width: 260px;
    height: 195px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    overflow: hidden;
    position: relative;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }
  .video-preview-video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transform: scaleX(-1);
  }
  .video-recording-badge {
    position: absolute;
    top: 10px;
    left: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(239,68,68,0.9);
    border-radius: 99px;
    font-size: 11px;
    font-family: var(--font-mono);
    color: #fff;
    font-weight: 600;
  }
  .video-rec-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #fff;
    animation: pulse-dot 1s infinite;
  }
  .video-controls {
    background: rgba(8,13,26,0.95);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px 16px;
    backdrop-filter: blur(16px);
    display: flex;
    align-items: center;
  }

  /* ── VIDEO RESULT CARD ── */
  .video-result-card {
    width: 300px;
    background: rgba(8,13,26,0.95);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    padding: 16px;
    backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    animation: slideInRight 0.3s ease;
  }
  .video-result-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
  }
  .video-result-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    flex: 1;
  }
  .video-severity-badge {
    font-size: 10px;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 8px;
    border-radius: 99px;
    font-weight: 600;
  }
  .video-sev-critical { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
  .video-sev-high { background: rgba(249,115,22,0.12); color: #f97316; border: 1px solid rgba(249,115,22,0.25); }
  .video-sev-medium { background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.2); }
  .video-sev-low { background: rgba(59,130,246,0.12); color: #3b82f6; border: 1px solid rgba(59,130,246,0.2); }
  .video-sev-none { background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.2); }
  .video-sev-unknown { background: rgba(100,116,139,0.12); color: #64748b; border: 1px solid rgba(100,116,139,0.2); }
  .video-score-bar-track {
    height: 6px;
    background: var(--border);
    border-radius: 99px;
    overflow: hidden;
    margin-bottom: 6px;
  }
  .video-score-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.6s ease;
  }
  .video-emotion-bars {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 10px 0;
  }
  .video-emotion-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .video-emotion-label {
    width: 60px;
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--text-dim);
    text-transform: capitalize;
    flex-shrink: 0;
  }
  .video-emotion-track {
    flex: 1;
    height: 4px;
    background: var(--border);
    border-radius: 99px;
    overflow: hidden;
  }
  .video-emotion-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease;
  }
  .video-emotion-pct {
    width: 32px;
    text-align: right;
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }
  .video-indicators {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0;
  }
  .video-indicator-chip {
    padding: 3px 8px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 99px;
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--text-dim);
  }
  .video-action {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: rgba(15,244,198,0.04);
    border: 1px solid rgba(15,244,198,0.1);
    border-radius: 8px;
    font-size: 11px;
    color: var(--aurora-1);
    line-height: 1.5;
    margin: 8px 0;
  }
  .video-meta {
    display: flex;
    gap: 12px;
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--text-muted);
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }
  @keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: none; }
  }

  /* ── ADMIN PANEL ── */
  .panel-page { flex: 1; overflow-y: auto; padding: 32px; display: flex; flex-direction: column; gap: 24px; }
  .panel-title { font-size: 22px; font-weight: 600; color: #fff; }
  .panel-sub { font-size: 14px; color: var(--text-dim); margin-top: 4px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 24px; }
  .card-title { font-size: 13px; font-family: var(--font-mono); color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  .upload-zone { border: 2px dashed var(--border-hi); border-radius: var(--r-lg); padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; display: flex; flex-direction: column; align-items: center; gap: 10px; }
  .upload-zone:hover, .upload-zone.drag { border-color: var(--aurora-1); background: rgba(15,244,198,0.03); }
  .upload-zone-icon { width: 48px; height: 48px; border-radius: 14px; background: rgba(15,244,198,0.08); border: 1px solid rgba(15,244,198,0.2); display: flex; align-items: center; justify-content: center; color: var(--aurora-1); }
  .upload-zone p { font-size: 14px; color: var(--text-dim); }
  .upload-zone span { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }
  .doc-table { width: 100%; border-collapse: collapse; }
  .doc-table th { font-size: 10px; font-family: var(--font-mono); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); font-weight: 400; }
  .doc-table td { padding: 12px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text); vertical-align: middle; }
  .doc-table tr:last-child td { border-bottom: none; }
  .doc-table tr:hover td { background: rgba(255,255,255,0.02); }
  .status-badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 9px; border-radius: 99px; font-size: 11px; font-family: var(--font-mono); }
  .status-indexed { background: rgba(16,185,129,0.1); color: #34d399; border: 1px solid rgba(16,185,129,0.2); }
  .status-processing { background: rgba(245,158,11,0.1); color: #fbbf24; border: 1px solid rgba(245,158,11,0.2); }
  .status-failed { background: rgba(239,68,68,0.1); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }
  .status-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
  .badge-count { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; background: rgba(15,244,198,0.12); color: var(--aurora-1); border-radius: 99px; font-size: 10px; font-family: var(--font-mono); margin-left: auto; }
  .search-bar { display: flex; align-items: center; gap: 10px; background: var(--panel); border: 1px solid var(--border); border-radius: var(--r); padding: 8px 14px; transition: border-color 0.2s; }
  .search-bar:focus-within { border-color: var(--aurora-2); }
  .search-input { flex: 1; background: transparent; border: none; outline: none; color: var(--text); font-family: var(--font-ui); font-size: 14px; }
  .search-input::placeholder { color: var(--text-muted); }
  .search-results { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
  .search-result { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 14px; }
  .search-result-content { font-size: 14px; color: var(--text); line-height: 1.55; }
  .search-result-meta { font-size: 11px; font-family: var(--font-mono); color: var(--text-muted); margin-top: 6px; }
  .divider { height: 1px; background: var(--border); margin: 4px 0; }
  .flex-1 { flex: 1; } .flex { display: flex; } .items-center { align-items: center; } .gap-2 { gap: 8px; } .gap-3 { gap: 12px; } .text-dim { color: var(--text-dim); } .text-xs { font-size: 12px; } .mt-2 { margin-top: 8px; } .col { flex-direction: column; }
  .loader { width: 18px; height: 18px; border: 2px solid var(--border-hi); border-top-color: var(--aurora-1); border-radius: 50%; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .admin-auth-toggle { text-align: center; margin-top: 16px; font-size: 12px; color: var(--text-dim); }
  .admin-auth-toggle button { background: none; border: none; color: var(--aurora-1); cursor: pointer; font-family: var(--font-ui); font-size: 12px; text-decoration: underline; text-underline-offset: 2px; }
  @media (max-width: 768px) { .auth-hero { display: none; } .auth-card { width: 100%; max-width: 400px; } .sidebar { width: 200px; } .media-hud { right: 10px; bottom: 10px; } }
  .sev-critical { --sev-color: #ef4444; --sev-bg: rgba(239,68,68,0.08); --sev-border: rgba(239,68,68,0.25); }
  .sev-high { --sev-color: #f97316; --sev-bg: rgba(249,115,22,0.08); --sev-border: rgba(249,115,22,0.25); }
  .sev-medium { --sev-color: #f59e0b; --sev-bg: rgba(245,158,11,0.08); --sev-border: rgba(245,158,11,0.2); }
  .sev-low { --sev-color: #3b82f6; --sev-bg: rgba(59,130,246,0.08); --sev-border: rgba(59,130,246,0.2); }
  .sev-none { --sev-color: var(--text-dim); --sev-bg: rgba(255,255,255,0.03); --sev-border: var(--border); }
  .sev-badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-family: var(--font-mono); font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; background: var(--sev-bg); color: var(--sev-color); border: 1px solid var(--sev-border); }
  .sev-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--sev-color); flex-shrink: 0; }
  .sev-critical .sev-dot { box-shadow: 0 0 6px var(--sev-color); animation: pulse-dot 1.5s infinite; }
  .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
  .stat-card { background: var(--panel); border: 1px solid var(--border); border-radius: var(--r); padding: 18px; display: flex; flex-direction: column; gap: 6px; position: relative; overflow: hidden; }
  .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--sev-color, var(--aurora-1)); }
  .stat-card-value { font-size: 32px; font-weight: 700; font-family: var(--font-mono); color: var(--sev-color, var(--text)); line-height: 1; }
  .stat-card-label { font-size: 11px; font-family: var(--font-mono); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; }
  .insight-card { background: var(--panel); border: 1px solid var(--border); border-left: 3px solid var(--sev-color); border-radius: var(--r); padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; transition: border-color 0.2s, background 0.2s; }
  .insight-card:hover { background: rgba(255,255,255,0.015); border-color: var(--border-hi); border-left-color: var(--sev-color); }
  .insight-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .insight-type { font-family: var(--font-mono); font-size: 12px; font-weight: 500; color: var(--text); text-transform: capitalize; flex: 1; }
  .insight-meta { font-size: 11px; font-family: var(--font-mono); color: var(--text-muted); }
  .insight-summary { font-size: 13px; color: var(--text-dim); line-height: 1.6; }
  .insight-indicators { display: flex; flex-wrap: wrap; gap: 6px; }
  .indicator-chip { padding: 3px 10px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); border-radius: 99px; font-size: 11px; font-family: var(--font-mono); color: var(--text-dim); font-style: italic; }
  .insight-action { display: flex; align-items: flex-start; gap: 8px; padding: 10px 12px; background: rgba(15,244,198,0.04); border: 1px solid rgba(15,244,198,0.1); border-radius: 8px; font-size: 12px; color: var(--aurora-1); line-height: 1.5; }
  .insight-footer { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .confidence-bar-wrap { display: flex; align-items: center; gap: 8px; flex: 1; }
  .confidence-bar-track { height: 4px; background: var(--border); border-radius: 99px; flex: 1; overflow: hidden; }
  .confidence-bar-fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--aurora-2), var(--aurora-1)); transition: width 0.6s ease; }
  .confidence-label { font-size: 10px; font-family: var(--font-mono); color: var(--text-muted); white-space: nowrap; }
  .astronaut-row { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: var(--r); border: 1px solid var(--border); background: var(--panel); cursor: pointer; transition: all 0.15s; }
  .astronaut-row:hover { background: rgba(255,255,255,0.02); border-color: var(--border-hi); }
  .astronaut-row.selected { background: rgba(15,244,198,0.04); border-color: rgba(15,244,198,0.2); }
  .astronaut-avatar { width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, var(--surface), var(--panel)); border: 2px solid var(--sev-color, var(--border)); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; color: var(--sev-color, var(--text-dim)); flex-shrink: 0; }
  .astronaut-info { flex: 1; overflow: hidden; }
  .astronaut-email { font-size: 13px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .astronaut-sub { font-size: 11px; font-family: var(--font-mono); color: var(--text-muted); margin-top: 2px; }
  .sev-counts { display: flex; gap: 6px; align-items: center; }
  .sev-count-chip { font-size: 10px; font-family: var(--font-mono); padding: 2px 7px; border-radius: 99px; background: var(--sev-bg); color: var(--sev-color); border: 1px solid var(--sev-border); }
  .health-layout { display: grid; grid-template-columns: 280px 1fr; gap: 0; flex: 1; overflow: hidden; }
  .health-sidebar { border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
  .health-sidebar-header { padding: 16px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .health-astronaut-list { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
  .health-detail { flex: 1; overflow-y: auto; padding: 28px; display: flex; flex-direction: column; gap: 20px; }
  .empty-health { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text-dim); text-align: center; padding: 40px; }
`;

// ─── AUTH PAGE ─────────────────────────────────────────────────────────────────
function AuthPage({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [isAdmin, setIsAdmin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    setLoading(true);
    try {
      if (tab === "login") {
        const body = new URLSearchParams({ username: email, password });
        const endpoint = isAdmin ? "/admin/admin-login" : "/auth/login";
        const res = await fetch(`${API}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body,
        });
        if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Login failed"); }
        const data = await res.json();
        onLogin(data.access_token, isAdmin ? "admin" : "astronaut", email);
      } else {
        const endpoint = isAdmin ? "/admin/create-admin" : "/user/";
        await apiFetch(endpoint, { method: "POST", body: JSON.stringify({ email, password }) });
        setSuccess("Account created! You can now log in.");
        setTab("login");
        setPassword("");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <div className="auth-hero-badge">
          <Icon d={Icons.rocket} size={12} />
          Mission Support System
        </div>
        <h1>MAITRI<br /><span>AI Companion</span></h1>
        <p>An intelligent companion for astronauts — providing empathetic support, knowledge retrieval, and mission context awareness.</p>
        <div className="auth-features">
          {[
            "RAG-powered knowledge base queries",
            "Persistent conversation memory",
            "Real-time mission document analysis",
            "Compassionate mental wellness support",
            "Continuous voice monitoring",
          ].map((f) => (
            <div className="auth-feature" key={f}>
              <div className="auth-feature-dot" />
              {f}
            </div>
          ))}
        </div>
      </div>
      <div className="auth-card">
        <div className="auth-card-header">
          <h2>{isAdmin ? "Mission Control" : "Astronaut Access"}</h2>
          <p>{isAdmin ? "Administrative interface" : "Log in or create your crew account"}</p>
        </div>
        {!isAdmin && (
          <div className="auth-tabs">
            <button className={`auth-tab ${tab === "login" ? "active" : ""}`} onClick={() => { setTab("login"); setError(""); setSuccess(""); }}>Login</button>
            <button className={`auth-tab ${tab === "register" ? "active" : ""}`} onClick={() => { setTab("register"); setError(""); setSuccess(""); }}>Register</button>
          </div>
        )}
        {error && <div className="error-msg">{error}</div>}
        {success && <div className="success-msg">{success}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email address</label>
            <input type="email" placeholder="you@space.agency" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <div className="loader" /> : (tab === "login" ? "Access System" : "Create Account")}
          </button>
        </form>
        <div className="admin-auth-toggle">
          {isAdmin
            ? <button onClick={() => { setIsAdmin(false); setError(""); setSuccess(""); }}>← Switch to Astronaut login</button>
            : <button onClick={() => { setIsAdmin(true); setTab("login"); setError(""); setSuccess(""); }}>Admin / Mission Control →</button>
          }
        </div>
      </div>
    </div>
  );
}

// ─── VIDEO RESULT CARD ─────────────────────────────────────────────────────────
function VideoResultCard({ result, onClose }) {
  if (!result) return null;
  const { risk, analysis } = result;
  const sev = risk?.severity || "none";

  const scoreColor = (score) => {
    if (score >= 0.8) return "#ef4444";
    if (score >= 0.6) return "#f97316";
    if (score >= 0.35) return "#f59e0b";
    if (score >= 0.18) return "#3b82f6";
    return "#10b981";
  };

  const emotionColor = (emotion) => {
    const map = {
      angry: "#ef4444", disgust: "#f97316", fear: "#f59e0b",
      happy: "#10b981", neutral: "#64748b", sad: "#3b82f6", surprise: "#8b5cf6"
    };
    return map[emotion] || "#64748b";
  };

  return (
    <div className="video-result-card">
      <div className="video-result-header">
        <Icon d={Icons.activity} size={13} style={{ color: "var(--aurora-1)", flexShrink: 0 }} />
        <span className="video-result-title">Video Analysis</span>
        <span className={`video-severity-badge video-sev-${sev}`}>{sev}</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "2px", display: "flex", alignItems: "center" }}>
          <Icon d={Icons.x} size={13} />
        </button>
      </div>

      <div className="video-score-bar-track">
        <div className="video-score-bar-fill" style={{
          width: `${Math.round((risk?.risk_score || 0) * 100)}%`,
          background: `linear-gradient(90deg, ${scoreColor(risk?.risk_score || 0)}aa, ${scoreColor(risk?.risk_score || 0)})`
        }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
        <span style={{ fontSize: "10px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>Risk score</span>
        <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: scoreColor(risk?.risk_score || 0), fontWeight: 600 }}>
          {Math.round((risk?.risk_score || 0) * 100)}%
        </span>
      </div>

      {analysis?.dominant_emotion && (
        <div style={{ fontSize: "12px", color: "var(--text-dim)", marginBottom: "10px" }}>
          Dominant emotion: <strong style={{ color: emotionColor(analysis.dominant_emotion) }}>{analysis.dominant_emotion}</strong>
        </div>
      )}

      {analysis?.emotion_distribution && (
        <div className="video-emotion-bars">
          {Object.entries(analysis.emotion_distribution)
            .sort((a, b) => (b[1].percentage || 0) - (a[1].percentage || 0))
            .map(([emotion, data]) => (
              <div key={emotion} className="video-emotion-row">
                <span className="video-emotion-label">{emotion}</span>
                <div className="video-emotion-track">
                  <div className="video-emotion-fill" style={{
                    width: `${data.percentage}%`,
                    background: emotionColor(emotion)
                  }} />
                </div>
                <span className="video-emotion-pct">{data.percentage}%</span>
              </div>
            ))}
        </div>
      )}

      {risk?.indicators?.length > 0 && (
        <div className="video-indicators">
          {risk.indicators.map((ind, i) => <span key={i} className="video-indicator-chip">{ind}</span>)}
        </div>
      )}

      {risk?.recommended_action && risk.recommended_action !== "No action required." && (
        <div className="video-action">
          <Icon d={Icons.zap} size={12} style={{ flexShrink: 0, marginTop: "1px" }} />
          {risk.recommended_action}
        </div>
      )}

      <div className="video-meta">
        <span>⏱ {analysis?.duration_sec?.toFixed(1)}s</span>
        <span>🎬 {analysis?.frames_processed} frames</span>
        <span>👤 {analysis?.total_faces_detected} faces</span>
      </div>
    </div>
  );
}

// ─── VIDEO OVERLAY ─────────────────────────────────────────────────────────────
function VideoOverlay({ token, isAstronaut, onNewVideoResponse }) {
  if (!isAstronaut) return null;

  const [isRecording, setIsRecording] = useState(false);
  const [recDuration, setRecDuration] = useState(0);
  const [videoAnalysis, setVideoAnalysis] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [cameraError, setCameraError] = useState(null);

  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const streamRef = useRef(null);

  const openCamera = async () => {
    setCameraError(null);
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });
      streamRef.current = s;
      setShowPreview(true);
      requestAnimationFrame(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          videoRef.current.play().catch(() => { });
        }
      });
    } catch (err) {
      setCameraError(err.message || "Could not access camera");
      setShowPreview(false);
      streamRef.current = null;
    }
  };

  const closeCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
    }
    clearInterval(timerRef.current);
    streamRef.current = null;
    setShowPreview(false);
    setIsRecording(false);
    setRecDuration(0);
    setCameraError(null);
    chunksRef.current = [];
    mediaRecorderRef.current = null;
  };

  const startRecording = () => {
    const s = streamRef.current;
    if (!s) {
      alert("ERROR: No stream!");
      return;
    }

    const tracks = s.getVideoTracks();
    if (tracks.length === 0 || tracks[0].readyState !== 'live') {
      alert("ERROR: Video track not live!");
      return;
    }

    let mediaRecorder;
    try {
      mediaRecorder = new MediaRecorder(s);
      alert("MediaRecorder created: " + mediaRecorder.mimeType);
    } catch (err) {
      alert("MediaRecorder failed: " + err.message);
      return;
    }

    chunksRef.current = [];
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (event) => {
      console.log("[ondataavailable] size:", event.data?.size || 0);
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      console.log("[onstop] chunks:", chunksRef.current.length);
      clearInterval(timerRef.current);

      const actualMimeType = mediaRecorder.mimeType || 'video/webm';
      const finalBlob = new Blob(chunksRef.current, { type: actualMimeType });

      console.log("[onstop] Blob:", {
        size: finalBlob.size,
        type: finalBlob.type,
        chunks: chunksRef.current.length,
        chunkSizes: chunksRef.current.map(c => c.size)
      });

      alert("Stopped! Blob size: " + finalBlob.size);

      if (finalBlob.size < 100) {
        setCameraError("Recording too short. Record 3+ seconds.");
        closeCamera();
        return;
      }

      await sendVideo(finalBlob, actualMimeType);
      closeCamera();
    };

    mediaRecorder.onerror = (e) => {
      alert("Recorder error: " + (e.message || "unknown"));
      setIsRecording(false);
    };

    try {
      mediaRecorder.start();
      alert("Recording STARTED! State: " + mediaRecorder.state);
      setIsRecording(true);
      setRecDuration(0);
      timerRef.current = setInterval(() => setRecDuration(d => d + 1), 1000);
    } catch (err) {
      alert("Start failed: " + err.message);
    }
  };

  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === "recording") {
      mr.stop();
    } else {
      closeCamera();
    }
  };

  const sendVideo = async (blob, blobType) => {
    alert("sendVideo! size=" + blob.size);
    setProcessing(true);
    setCameraError(null);

    const ext = blobType.includes('mp4') ? 'mp4' : 'webm';
    const formData = new FormData();
    formData.append("file", blob, `astronaut_video.${ext}`);

    try {
      const res = await fetch(`${API}/video/detect-and-chat`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      setVideoAnalysis(data);
      if (onNewVideoResponse) onNewVideoResponse(data);
    } catch (err) {
      alert("Upload failed: " + err.message);
      setCameraError("Upload failed: " + err.message);
    } finally {
      setProcessing(false);
    }
  };

  const fmtDuration = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="video-hud">
      {showPreview && (
        <div className="video-preview-card">
          <video ref={videoRef} autoPlay muted playsInline className="video-preview-video" />
          {isRecording && (
            <div className="video-recording-badge">
              <div className="video-rec-dot" />
              REC {fmtDuration(recDuration)}
            </div>
          )}
        </div>
      )}

      {cameraError && (
        <div style={{
          background: "rgba(239,68,68,0.12)",
          border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: "10px",
          padding: "10px 14px",
          color: "#f87171",
          fontSize: "12px",
          maxWidth: "260px"
        }}>
          {cameraError}
        </div>
      )}

      <div className="video-controls">
        {!showPreview ? (
          <button className="btn btn-primary btn-sm" onClick={openCamera} disabled={processing}>
            <Icon d={Icons.video} size={14} /> Start Video Check-in
          </button>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className={`vad-indicator ${isRecording ? "speaking" : ""}`}>
              <div className="vad-dot" />
              {isRecording ? `Recording ${fmtDuration(recDuration)}` : "Camera On"}
            </div>

            {!isRecording ? (
              <>
                <button className="btn btn-primary btn-sm" onClick={startRecording}>
                  <Icon d={Icons.video} size={14} /> Record
                </button>
                <button className="btn btn-ghost btn-sm" onClick={closeCamera}>
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button className="btn btn-danger btn-sm pulsing" onClick={stopRecording}>
                  <Icon d={Icons.x} size={14} /> Stop
                </button>
                <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                  {fmtDuration(recDuration)}
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {processing && (
        <div style={{
          background: "rgba(8,13,26,0.95)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
          padding: "12px 16px",
          color: "var(--aurora-1)",
          fontSize: "13px",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          <div className="loader" style={{ width: "16px", height: "16px" }} />
          Analyzing facial emotions…
        </div>
      )}

      {videoAnalysis && (
        <VideoResultCard
          result={videoAnalysis.video_analysis}
          onClose={() => setVideoAnalysis(null)}
        />
      )}
    </div>
  );
}

// ─── AUDIO RESULT CARD ─────────────────────────────────────────────────────────
function AudioResultCard({ result, onClose }) {
  if (!result) return null;
  const { risk, analysis } = result;
  const sev = risk.severity || "none";

  const scoreColor = (score) => {
    if (score >= 0.8) return "#ef4444";
    if (score >= 0.6) return "#f97316";
    if (score >= 0.35) return "#f59e0b";
    if (score >= 0.18) return "#3b82f6";
    return "#10b981";
  };

  return (
    <div className="audio-result-card">
      <div className="audio-result-header">
        <Icon d={Icons.waveform} size={13} style={{ color: "var(--aurora-1)", flexShrink: 0 }} />
        <span className="audio-result-title">Voice Analysis</span>
        <span className={`audio-severity-badge audio-sev-${sev}`}>{sev}</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "2px", display: "flex", alignItems: "center" }}>
          <Icon d={Icons.x} size={13} />
        </button>
      </div>
      <div className="audio-score-bar-track">
        <div className="audio-score-bar-fill" style={{ width: `${Math.round(risk.risk_score * 100)}%`, background: `linear-gradient(90deg, ${scoreColor(risk.risk_score)}aa, ${scoreColor(risk.risk_score)})` }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "10px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>Risk score</span>
        <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: scoreColor(risk.risk_score), fontWeight: 600 }}>{Math.round(risk.risk_score * 100)}%</span>
      </div>
      {risk.indicators?.length > 0 && (
        <div className="audio-indicators">
          {risk.indicators.map((ind, i) => <span key={i} className="audio-indicator-chip">{ind}</span>)}
        </div>
      )}
      {risk.recommended_action && risk.recommended_action !== "No action required." && (
        <div className="audio-action">
          <Icon d={Icons.zap} size={12} style={{ flexShrink: 0, marginTop: "1px" }} />
          {risk.recommended_action}
        </div>
      )}
      <div className="audio-meta">
        <span>⏱ {analysis.duration_sec?.toFixed(1)}s</span>
        <span>🎙 {Math.round(analysis.estimated_speech_rate_wpm)} wpm</span>
        <span>🎯 {Math.round((risk.confidence || 0) * 100)}% conf</span>
      </div>
    </div>
  );
}

// ─── SENSOR OVERLAY — Voice Pipeline ─────────────────────────────────────────
function SensorOverlay({ token, isAstronaut, onNewVoiceResponse }) {
  if (!isAstronaut) return null;

  const [isRecording, setIsRecording] = useState(false);
  const [vadState, setVadState] = useState("idle"); // idle, listening, processing
  const [stressAlert, setStressAlert] = useState(null);
  const [audioResult, setAudioResult] = useState(null); // For the HUD card
  const [recDuration, setRecDuration] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recTimerRef = useRef(null);

  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/wav') ? 'audio/wav' : 'audio/webm'
      });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setIsRecording(false);
        clearInterval(recTimerRef.current);
        setRecDuration(0);
        setVadState("processing");

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioToBackend(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setVadState("listening");
      setRecDuration(0);
      recTimerRef.current = setInterval(() => setRecDuration(d => d + 1), 1000);

    } catch (err) {
      console.error("Microphone access denied:", err);
      setVadState("idle");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
  };

  const sendAudioToBackend = async (blob) => {
    const formData = new FormData();
    formData.append("file", blob, "astronaut_voice.webm");

    try {
      const res = await fetch(`${API}/audio/detect-and-chat`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Audio processing failed");
      }

      const data = await res.json();

      // Show stress analysis in HUD
      setAudioResult(data.audio_analysis);

      // Check for high stress
      const severity = data.audio_analysis?.risk?.severity || "none";
      if (severity === "critical" || severity === "high") {
        setStressAlert({
          severity,
          message: `Vocal stress alert: ${severity.toUpperCase()}`,
          action: data.audio_analysis?.risk?.recommended_action
        });
      } else {
        setStressAlert(null);
      }

      // Lift to parent (ChatView)
      if (onNewVoiceResponse) {
        onNewVoiceResponse(data);
      }

    } catch (err) {
      console.error("Voice pipeline error:", err);
      setStressAlert({ severity: "error", message: err.message });
    } finally {
      setVadState("idle");
      // Auto-clear stress alert after 10s if not critical
      setTimeout(() => setStressAlert(null), 10000);
    }
  };

  const fmtDuration = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="sensor-hud">
      {/* Recording Controls */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        background: "rgba(8,13,26,0.95)",
        border: "1px solid var(--border)",
        borderRadius: "12px",
        padding: "10px 16px",
        backdropFilter: "blur(16px)"
      }}>
        <div className={`vad-indicator ${vadState === "listening" ? "speaking" : ""}`}>
          <div className="vad-dot" />
          {vadState === "idle" && "Voice Ready"}
          {vadState === "listening" && `Recording ${fmtDuration(recDuration)}`}
          {vadState === "processing" && "Analyzing..."}
        </div>

        {!isRecording ? (
          <button
            className="btn btn-primary btn-sm"
            onClick={startRecording}
            style={{ gap: "6px" }}
          >
            <Icon d={Icons.mic} size={14} /> Hold to Speak
          </button>
        ) : (
          <button
            className="btn btn-danger btn-sm pulsing"
            onClick={stopRecording}
            style={{ gap: "6px" }}
          >
            <Icon d={Icons.micOff} size={14} /> Stop
          </button>
        )}
      </div>

      {/* Stress Alert Banner */}
      {stressAlert && (
        <div style={{
          background: stressAlert.severity === "critical" ? "rgba(239,68,68,0.15)" : "rgba(249,115,22,0.1)",
          border: `1px solid ${stressAlert.severity === "critical" ? "rgba(239,68,68,0.4)" : "rgba(249,115,22,0.3)"}`,
          borderRadius: "10px",
          padding: "12px 16px",
          color: stressAlert.severity === "critical" ? "#f87171" : "#fb923c",
          fontSize: "13px",
          backdropFilter: "blur(12px)",
          animation: "slideInRight 0.3s ease"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, marginBottom: "4px" }}>
            <Icon d={Icons.alert} size={14} />
            {stressAlert.message}
          </div>
          {stressAlert.action && (
            <div style={{ fontSize: "12px", opacity: 0.9, lineHeight: 1.4 }}>
              {stressAlert.action}
            </div>
          )}
        </div>
      )}

      {/* Audio Analysis Result Card */}
      {audioResult && (
        <AudioResultCard
          result={audioResult}
          onClose={() => setAudioResult(null)}
        />
      )}
    </div>
  );
}
// ─── CHAT VIEW ─────────────────────────────────────────────────────────────────
const PROMPTS = [
  "How am I managing isolation stress?",
  "What are symptoms of space adaptation syndrome?",
  "Help me prepare for tomorrow's EVA",
  "I need to talk about how I'm feeling",
];

function ChatView({ token, email, externalVoiceResponse, onVoiceConsumed, externalVideoResponse, onVideoConsumed }) {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const [searchKw, setSearchKw] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // ── Load conversations ──
  const loadConversations = useCallback(async () => {
    try {
      const data = await apiFetch("/chat/conversations", {}, token);
      setConversations(data.conversations || []);
    } catch { }
  }, [token]);

  const loadMessages = useCallback(async (convId) => {
    try {
      const data = await apiFetch(`/chat/history?conversation_id=${convId}`, {}, token);
      setMessages(data.messages || []);
      setActiveConvId(convId);
    } catch { }
  }, [token]);

  useEffect(() => { loadConversations(); }, [loadConversations]);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // ── Handle external voice responses from SensorOverlay ──
  useEffect(() => {
    if (!externalVoiceResponse) return;

    const data = externalVoiceResponse;

    // Add user transcript message
    const userMsg = {
      id: Date.now() - 1,
      role: "user",
      content: data.user_transcript,
      created_at: new Date().toISOString(),
      metadata: { is_voice: true, audio_analysis: data.audio_analysis }
    };

    // Add AI response message
    const aiMsg = {
      id: Date.now(),
      role: "assistant",
      content: data.assistant_response,
      created_at: new Date().toISOString(),
      sources: data.sources,
      timing: data.timing
    };

    setMessages(prev => [...prev, userMsg, aiMsg]);

    // If new conversation started from voice
    if (!activeConvId && data.conversation_id) {
      setActiveConvId(data.conversation_id);
      loadConversations();
    }

    onVoiceConsumed(); // Reset external state
  }, [externalVoiceResponse, activeConvId, loadConversations, onVoiceConsumed]);

  // ── Handle external video responses from VideoOverlay ──
  useEffect(() => {
    if (!externalVideoResponse) return;

    const data = externalVideoResponse;
    const analysis = data.video_analysis?.analysis;
    const risk = data.video_analysis?.risk;

    // Add user video message
    const userMsg = {
      id: Date.now() - 1,
      role: "user",
      content: `[Video Emotional State: ${analysis?.dominant_emotion || 'unknown'}]`,
      created_at: new Date().toISOString(),
      metadata: {
        is_video: true,
        video_analysis: data.video_analysis,
        dominant_emotion: analysis?.dominant_emotion,
        severity: risk?.severity
      }
    };

    // Add AI response message
    const aiMsg = {
      id: Date.now(),
      role: "assistant",
      content: data.assistant_response || "I received your video check-in. I'm here to support you.",
      created_at: new Date().toISOString(),
      sources: data.sources,
    };

    setMessages(prev => [...prev, userMsg, aiMsg]);

    if (!activeConvId && data.conversation_id) {
      setActiveConvId(data.conversation_id);
      loadConversations();
    }

    setTimeout(onVideoConsumed, 0);
  }, [externalVideoResponse, activeConvId, loadConversations, onVideoConsumed]);

  // ── Text send (unchanged) ──
  const handleSend = async (text) => {
    const msg = (text || input).trim();
    if (!msg || sending) return;
    setInput("");
    setSending(true);
    setSearchMode(false);

    const optimistic = {
      id: Date.now(),
      role: "user",
      content: msg,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, optimistic]);

    try {
      const data = await apiFetch("/chat/send", {
        method: "POST",
        body: JSON.stringify({ message: msg })
      }, token);

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: "assistant",
        content: data.response,
        created_at: new Date().toISOString(),
        sources: data.sources,
        timing: data.timing
      }]);

      if (!activeConvId && data.conversation_id) {
        setActiveConvId(data.conversation_id);
        loadConversations();
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: "assistant",
        content: `⚠ ${err.message}`,
        created_at: new Date().toISOString()
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const data = await apiFetch("/chat/new-conversation", { method: "POST" }, token);
      setActiveConvId(data.conversation_id);
      setMessages([]);
      loadConversations();
    } catch { }
  };

  const handleDeleteConv = async (e, id) => {
    e.stopPropagation();
    try {
      await apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }, token);
      if (activeConvId === id) {
        setActiveConvId(null);
        setMessages([]);
      }
      loadConversations();
    } catch { }
  };

  const handleSearch = async () => {
    if (!searchKw.trim()) return;
    setSearching(true);
    try {
      const data = await apiFetch(`/chat/search?keyword=${encodeURIComponent(searchKw)}`, {}, token);
      setSearchResults(data);
    } catch { }
    setSearching(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const autoResize = (e) => {
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  const initials = email ? email[0].toUpperCase() : "A";
  const fmtTime = (d) => new Date(d).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <>
      <div className="sidebar">
        {/* ... sidebar content unchanged ... */}
        <div className="sidebar-header">
          <div className="sidebar-logo"><Icon d={Icons.rocket} size={16} /></div>
          <div>
            <div className="sidebar-logo-text">Maitri</div>
            <div className="sidebar-logo-sub">AI Companion</div>
          </div>
        </div>
        <div className="sidebar-nav">
          <button className={`nav-item ${!searchMode ? "active" : ""}`} onClick={() => { setSearchMode(false); setSearchResults(null); }}>
            <Icon d={Icons.chat} size={16} /><span className="nav-item-label">Chat</span>
          </button>
          <button className={`nav-item ${searchMode ? "active" : ""}`} onClick={() => setSearchMode(true)}>
            <Icon d={Icons.search} size={16} /><span className="nav-item-label">Search History</span>
          </button>
          <div className="divider" style={{ margin: "8px 0" }} />
          <button className="nav-item" onClick={handleNewConversation}>
            <Icon d={Icons.plus} size={16} /><span className="nav-item-label">New Conversation</span>
          </button>
          <div className="nav-section-label">Conversations</div>
          {conversations.map((conv) => (
            <button key={conv.id} className={`nav-item ${activeConvId === conv.id ? "active" : ""}`} onClick={() => { loadMessages(conv.id); setSearchMode(false); }}>
              <Icon d={Icons.chat} size={14} />
              <span className="nav-item-label">{conv.title || `Chat #${conv.id}`}</span>
              <span style={{ marginLeft: "auto", color: "var(--text-muted)", padding: "2px 4px", borderRadius: "4px", flexShrink: 0 }} onClick={(e) => handleDeleteConv(e, conv.id)} title="Delete">
                <Icon d={Icons.trash} size={12} />
              </span>
            </button>
          ))}
        </div>
        <div className="sidebar-footer">
          <div className="user-pill">
            <div className="user-pill-avatar">{initials}</div>
            <div className="user-pill-info">
              <div className="user-pill-name">{email}</div>
              <div className="user-pill-role">Astronaut</div>
            </div>
          </div>
        </div>
      </div>

      <div className="main">
        <div className="topbar">
          <span className="topbar-title">
            {searchMode ? "Search History" : activeConvId ? `Conversation #${activeConvId}` : "Maitri AI Chat"}
          </span>
        </div>

        {searchMode ? (
          <div style={{ padding: "24px", overflow: "auto", flex: 1 }}>
            <div className="search-bar">
              <Icon d={Icons.search} size={16} style={{ color: "var(--text-dim)", flexShrink: 0 }} />
              <input className="search-input" placeholder="Search your conversation history…" value={searchKw} onChange={(e) => setSearchKw(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearch()} />
              <button className="btn btn-ghost btn-sm" onClick={handleSearch} disabled={searching}>
                {searching ? <div className="loader" /> : "Search"}
              </button>
            </div>
            {searchResults && (
              <div className="search-results">
                <div className="text-dim text-xs">
                  {searchResults.found} result{searchResults.found !== 1 ? "s" : ""} for "{searchResults.keyword}"
                </div>
                {searchResults.messages.map((m) => (
                  <div className="search-result" key={m.id}>
                    <div className="search-result-content">{m.content}</div>
                    <div className="search-result-meta">Conv #{m.conversation_id} · {fmtTime(m.created_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="chat-area">
            <div className="messages">
              {messages.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon"><Icon d={Icons.rocket} size={28} /></div>
                  <div className="empty-title">Hello, Astronaut</div>
                  <div className="empty-sub">
                    I'm Maitri, your AI companion. Ask me anything — mission knowledge,
                    how you're feeling, or what's on your mind.
                  </div>
                  <div className="prompts-grid">
                    {PROMPTS.map((p) => (
                      <button key={p} className="prompt-chip" onClick={() => handleSend(p)}>{p}</button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`message ${msg.role}`}>
                    <div className="msg-avatar">{msg.role === "assistant" ? "M" : initials}</div>
                    <div className="msg-body">
                      <div className="msg-bubble">
                        {msg.metadata?.is_voice && (
                          <div style={{ fontSize: '10px', opacity: 0.6, marginBottom: '4px' }}>
                            🎙️ Voice Input {msg.metadata?.audio_analysis?.risk?.severity &&
                              `· Stress: ${msg.metadata.audio_analysis.risk.severity}`}
                          </div>
                        )}
                        {msg.metadata?.is_video && (
                          <div style={{ fontSize: '10px', opacity: 0.6, marginBottom: '4px' }}>
                            🎥 Video Check-in · Dominant: {msg.metadata?.dominant_emotion || 'unknown'}
                            {msg.metadata?.severity && ` · Stress: ${msg.metadata.severity}`}
                          </div>
                        )}
                        {msg.content}
                      </div>
                      <div className="msg-time">{fmtTime(msg.created_at)}</div>
                      {msg.sources?.length > 0 && (
                        <div className="msg-sources">
                          <div className="msg-source-label">Sources</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            {msg.sources.map((s, i) => (
                              <div key={i} className="source-chip">
                                <Icon d={Icons.file} size={10} />{s.filename} · {Math.round(s.similarity * 100)}%
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {msg.timing && (
                        <div className="msg-timing">
                          <span>⚡ {msg.timing.total_ms}ms</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {sending && (
                <div className="message assistant">
                  <div className="msg-avatar">M</div>
                  <div className="msg-body">
                    <div className="msg-bubble">
                      <div className="typing-indicator">
                        <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Clean text-only input */}
            <div className="chat-input-wrap">
              <div className="chat-input-inner">
                <textarea
                  ref={textareaRef}
                  className="chat-textarea"
                  placeholder="Message Maitri…"
                  value={input}
                  onChange={(e) => { setInput(e.target.value); autoResize(e); }}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  disabled={sending}
                />
                <button className="send-btn" onClick={() => handleSend()} disabled={!input.trim() || sending}>
                  {sending ? (
                    <div className="loader" style={{ borderColor: "rgba(0,0,0,0.3)", borderTopColor: "#000" }} />
                  ) : (
                    <Icon d={Icons.send} size={16} />
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// ─── HEALTH INSIGHTS ───────────────────────────────────────────────────────────
function SevBadge({ severity }) {
  const labels = { critical: "Critical", high: "High", medium: "Medium", low: "Low", none: "None" };
  return (
    <span className={`sev-badge sev-${severity || "none"}`}>
      <span className="sev-dot" />{labels[severity] || severity}
    </span>
  );
}

function InsightCard({ insight, onDismiss }) {
  const sev = insight.severity || "none";
  return (
    <div className={`insight-card sev-${sev}`}>
      <div className="insight-header">
        <span className="insight-type">{insight.insight_type?.replace(/_/g, " ")}</span>
        <SevBadge severity={sev} />
        <span className="insight-meta">{new Date(insight.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
        {onDismiss && (
          <button className="btn btn-icon btn-danger btn-sm" title="Dismiss" onClick={() => onDismiss(insight.id)} style={{ padding: "4px 6px" }}>
            <Icon d={Icons.x} size={12} />
          </button>
        )}
      </div>
      {insight.summary && <div className="insight-summary">{insight.summary}</div>}
      {insight.indicators?.length > 0 && (
        <div className="insight-indicators">
          {insight.indicators.map((ind, i) => <span key={i} className="indicator-chip">"{ind}"</span>)}
        </div>
      )}
      {insight.recommended_action && insight.recommended_action !== "No action required" && (
        <div className="insight-action">
          <Icon d={Icons.zap} size={13} style={{ flexShrink: 0, marginTop: "1px" }} />
          {insight.recommended_action}
        </div>
      )}
      <div className="insight-footer">
        <div className="confidence-bar-wrap">
          <span className="confidence-label">Confidence</span>
          <div className="confidence-bar-track">
            <div className="confidence-bar-fill" style={{ width: `${Math.round((insight.confidence || 0) * 100)}%` }} />
          </div>
          <span className="confidence-label">{Math.round((insight.confidence || 0) * 100)}%</span>
        </div>
        {insight.message_id && <span className="insight-meta">msg #{insight.message_id}</span>}
      </div>
    </div>
  );
}

function HealthInsightsView({ token }) {
  const [subview, setSubview] = useState("alerts");
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [astronauts, setAstronauts] = useState([]);
  const [selectedAstronaut, setSelectedAstronaut] = useState(null);
  const [astronautReport, setAstronautReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAlerts = useCallback(async () => { setLoading(true); setError(""); try { const data = await apiFetch("/health/alerts?limit=50", {}, token); setAlerts(data.alerts || []); } catch (e) { setError(e.message); } setLoading(false); }, [token]);
  const loadSummary = useCallback(async () => { setLoading(true); setError(""); try { const [sumData, astData] = await Promise.all([apiFetch("/health/summary", {}, token), apiFetch("/health/astronauts", {}, token)]); setSummary(sumData); setAstronauts(astData.astronauts || []); } catch (e) { setError(e.message); } setLoading(false); }, [token]);
  const loadAstronautReport = useCallback(async (id) => { setLoading(true); setError(""); try { const data = await apiFetch(`/health/astronaut/${id}?limit=100`, {}, token); setAstronautReport(data); } catch (e) { setError(e.message); } setLoading(false); }, [token]);
  const handleDismiss = async (insightId) => { try { await apiFetch(`/health/insights/${insightId}`, { method: "DELETE" }, token); if (subview === "alerts") loadAlerts(); else if (subview === "astronaut" && selectedAstronaut) loadAstronautReport(selectedAstronaut.id); } catch (e) { setError(e.message); } };
  useEffect(() => { if (subview === "alerts") loadAlerts(); else if (subview === "summary" || subview === "astronaut") loadSummary(); }, [subview]);
  const handleSelectAstronaut = (a) => { setSelectedAstronaut(a); setSubview("astronaut"); loadAstronautReport(a.id); };
  const sevColor = (s) => ({ critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#3b82f6" }[s] || "var(--text-dim)");

  return (
    <div style={{ display: "flex", flex: 1, overflow: "hidden", flexDirection: "column" }}>
      <div style={{ padding: "12px 24px", borderBottom: "1px solid var(--border)", display: "flex", gap: "6px", background: "rgba(8,13,26,0.6)", flexShrink: 0 }}>
        {[{ id: "alerts", icon: Icons.alert, label: "Critical Alerts" }, { id: "summary", icon: Icons.users, label: "Crew Overview" }, { id: "astronaut", icon: Icons.activity, label: "Astronaut Report" }].map((t) => (
          <button key={t.id} className={`btn btn-sm ${subview === t.id ? "btn-primary" : "btn-ghost"}`} style={subview === t.id ? { background: "rgba(15,244,198,0.12)", color: "var(--aurora-1)", border: "1px solid rgba(15,244,198,0.25)" } : {}} onClick={() => setSubview(t.id)}>
            <Icon d={t.icon} size={13} />{t.label}
          </button>
        ))}
        <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto" }} onClick={() => { if (subview === "alerts") loadAlerts(); else if (subview === "astronaut" && selectedAstronaut) loadAstronautReport(selectedAstronaut.id); else loadSummary(); }}>
          {loading ? <div className="loader" /> : <Icon d={Icons.refresh} size={14} />}
        </button>
      </div>
      {error && <div className="error-msg" style={{ margin: "16px 24px 0" }}>{error}</div>}

      {subview === "alerts" && (
        <div className="health-detail">
          <div><div className="panel-title" style={{ fontSize: "18px" }}><Icon d={Icons.alert} size={18} style={{ display: "inline", verticalAlign: "middle", marginRight: "8px", color: "#ef4444" }} />Critical & High Alerts</div><div className="panel-sub">{alerts.length} active alert{alerts.length !== 1 ? "s" : ""} across all crew members</div></div>
          {loading && alerts.length === 0 ? <div style={{ textAlign: "center", padding: "40px" }}><div className="loader" style={{ margin: "0 auto" }} /></div>
            : alerts.length === 0 ? (
              <div className="empty-health"><div className="empty-icon" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}><Icon d={Icons.check} size={28} style={{ color: "var(--success)" }} /></div><div style={{ fontSize: "16px", fontWeight: 500, color: "var(--text)" }}>All Clear</div><div style={{ fontSize: "13px" }}>No critical or high severity alerts at this time.</div></div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {alerts.map((a) => (<div key={a.id}><div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}><span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: sevColor(a.severity) }}><Icon d={Icons.user} size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: "4px" }} />{a.astronaut_email}</span></div><InsightCard insight={a} onDismiss={handleDismiss} /></div>))}
              </div>
            )}
        </div>
      )}

      {subview === "summary" && (
        <div className="health-detail">
          {summary && (<>
            <div><div className="panel-title" style={{ fontSize: "18px" }}>Crew Health Overview</div><div className="panel-sub">{summary.total_astronauts_monitored} crew member{summary.total_astronauts_monitored !== 1 ? "s" : ""} monitored</div></div>
            <div className="stat-grid">{[{ label: "Monitored", value: summary.total_astronauts_monitored, sev: "none" }, { label: "Critical", value: summary.critical_count, sev: "critical" }, { label: "High Risk", value: summary.high_count, sev: "high" }, { label: "Stable", value: summary.total_astronauts_monitored - summary.critical_count - summary.high_count, sev: "low" }].map((s) => (<div key={s.label} className={`stat-card sev-${s.sev}`}><div className="stat-card-value">{s.value}</div><div className="stat-card-label">{s.label}</div></div>))}</div>
            <div className="card" style={{ padding: "0" }}>
              <div className="card-title" style={{ padding: "16px 20px 0" }}><Icon d={Icons.users} size={14} /> Crew Members by Risk</div>
              <div style={{ padding: "12px" }}>
                {summary.astronauts?.length === 0 ? <div style={{ padding: "24px", textAlign: "center", color: "var(--text-dim)", fontSize: "13px" }}>No health data recorded yet.</div>
                  : summary.astronauts?.map((a) => (
                    <div key={a.astronaut_id} className={`astronaut-row sev-${a.overall_risk}`} onClick={() => handleSelectAstronaut({ id: a.astronaut_id, email: a.astronaut_email })}>
                      <div className="astronaut-avatar">{a.astronaut_email[0].toUpperCase()}</div>
                      <div className="astronaut-info"><div className="astronaut-email">{a.astronaut_email}</div><div className="astronaut-sub">{a.total_insights} insight{a.total_insights !== 1 ? "s" : ""} · {a.latest_insight?.insight_type?.replace(/_/g, " ") || "—"}</div></div>
                      <div className="sev-counts">{a.severity_counts?.critical > 0 && <span className="sev-count-chip sev-critical">{a.severity_counts.critical}C</span>}{a.severity_counts?.high > 0 && <span className="sev-count-chip sev-high">{a.severity_counts.high}H</span>}{a.severity_counts?.medium > 0 && <span className="sev-count-chip sev-medium">{a.severity_counts.medium}M</span>}</div>
                      <SevBadge severity={a.overall_risk} />
                      <Icon d={Icons.chevron} size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                    </div>
                  ))}
              </div>
            </div>
          </>)}
          {loading && !summary && <div style={{ textAlign: "center", padding: "60px" }}><div className="loader" style={{ margin: "0 auto" }} /></div>}
        </div>
      )}

      {subview === "astronaut" && (
        <div className="health-layout">
          <div className="health-sidebar">
            <div className="health-sidebar-header"><div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "8px" }}>Select Crew Member</div>{loading && astronauts.length === 0 ? <div className="loader" style={{ margin: "8px auto" }} /> : null}</div>
            <div className="health-astronaut-list">
              {astronauts.map((a) => {
                const astSum = summary?.astronauts?.find(s => s.astronaut_id === a.id); const risk = astSum?.overall_risk || "none"; return (
                  <div key={a.id} className={`astronaut-row sev-${risk} ${selectedAstronaut?.id === a.id ? "selected" : ""}`} onClick={() => handleSelectAstronaut(a)}>
                    <div className="astronaut-avatar" style={{ borderColor: sevColor(risk), color: sevColor(risk) }}>{a.email[0].toUpperCase()}</div>
                    <div className="astronaut-info"><div className="astronaut-email">{a.email}</div>{astSum && <div className="astronaut-sub">{astSum.total_insights} insight{astSum.total_insights !== 1 ? "s" : ""}</div>}</div>
                    {astSum && <SevBadge severity={risk} />}
                  </div>
                );
              })}
              {astronauts.length === 0 && !loading && <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>No crew members found.</div>}
            </div>
          </div>
          <div className="health-detail">
            {!selectedAstronaut ? (<div className="empty-health"><div className="empty-icon"><Icon d={Icons.user} size={28} /></div><div style={{ fontSize: "15px", fontWeight: 500, color: "var(--text)" }}>Select a crew member</div><div style={{ fontSize: "13px" }}>Choose an astronaut to view their full health report.</div></div>)
              : loading ? (<div style={{ textAlign: "center", padding: "60px" }}><div className="loader" style={{ margin: "0 auto" }} /></div>)
                : astronautReport ? (<>
                  <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}><div><div className="panel-title" style={{ fontSize: "18px" }}>{astronautReport.astronaut_email}</div><div className="panel-sub">{astronautReport.total_insights} insight{astronautReport.total_insights !== 1 ? "s" : ""} recorded</div></div><SevBadge severity={astronautReport.overall_risk} /></div>
                  <div className="stat-grid">{[{ label: "Critical", value: astronautReport.severity_counts?.critical || 0, sev: "critical" }, { label: "High", value: astronautReport.severity_counts?.high || 0, sev: "high" }, { label: "Medium", value: astronautReport.severity_counts?.medium || 0, sev: "medium" }, { label: "Low", value: astronautReport.severity_counts?.low || 0, sev: "low" }].map((s) => (<div key={s.label} className={`stat-card sev-${s.sev}`}><div className="stat-card-value">{s.value}</div><div className="stat-card-label">{s.label}</div></div>))}</div>
                  {astronautReport.insights?.length === 0 ? (<div className="empty-health"><div style={{ fontSize: "13px" }}>No health insights recorded for this crew member yet.</div></div>)
                    : (<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}><div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Insights — sorted by severity</div>{astronautReport.insights.map((ins) => (<InsightCard key={ins.id} insight={ins} onDismiss={handleDismiss} />))}</div>)}
                </>) : null}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── ADMIN VIEW ────────────────────────────────────────────────────────────────
function AdminView({ token, email }) {
  const [view, setView] = useState("documents");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadErr, setUploadErr] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [queryText, setQueryText] = useState("");
  const [queryResult, setQueryResult] = useState(null);
  const [querying, setQuerying] = useState(false);
  const [alertCount, setAlertCount] = useState(null);
  const fileInputRef = useRef(null);

  const loadDocs = useCallback(async () => { setLoading(true); try { const data = await apiFetch("/rag/documents", {}, token); setDocuments(data.documents || []); } catch { } setLoading(false); }, [token]);

  useEffect(() => { apiFetch("/health/alerts?limit=100", {}, token).then((d) => setAlertCount(d.alerts?.length || 0)).catch(() => { }); }, [token]);
  useEffect(() => { if (view === "documents") loadDocs(); }, [view, loadDocs]);

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true); setUploadMsg(""); setUploadErr("");
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/rag/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Upload failed"); }
      setUploadMsg("File received — indexing in background.");
      loadDocs();
    } catch (e) { setUploadErr(e.message); }
    setUploading(false);
  };

  const handleDelete = async (id) => { try { await apiFetch(`/rag/documents/${id}`, { method: "DELETE" }, token); loadDocs(); } catch { } };
  const handleQuery = async () => {
    if (!queryText.trim()) return;
    setQuerying(true); setQueryResult(null);
    try { const data = await apiFetch("/rag/query", { method: "POST", body: JSON.stringify({ question: queryText, top_k: 5 }) }, token); setQueryResult(data); }
    catch (e) { setQueryResult({ error: e.message }); }
    setQuerying(false);
  };

  const fmtSize = (b) => b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.round(b / 1024)} KB`;
  const fmtDate = (d) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const indexed = documents.filter((d) => d.status === "indexed").length;
  const initials = email ? email[0].toUpperCase() : "A";

  return (
    <>
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo" style={{ background: "linear-gradient(135deg, var(--amber), #f97316)" }}><Icon d={Icons.shield} size={16} /></div>
          <div><div className="sidebar-logo-text">Control</div><div className="sidebar-logo-sub">Mission Admin</div></div>
        </div>
        <div className="sidebar-nav">
          <div className="nav-section-label">Management</div>
          {[{ id: "documents", icon: Icons.file, label: "Documents", badge: indexed }, { id: "upload", icon: Icons.upload, label: "Upload Files" }, { id: "query", icon: Icons.zap, label: "RAG Query" }].map((item) => (
            <button key={item.id} className={`nav-item ${view === item.id ? "active" : ""}`} onClick={() => setView(item.id)}>
              <Icon d={item.icon} size={16} /><span className="nav-item-label">{item.label}</span>
              {item.badge !== undefined && <span className="badge-count">{item.badge}</span>}
            </button>
          ))}
          <div className="divider" style={{ margin: "8px 0" }} />
          <div className="nav-section-label">Crew Health</div>
          <button className={`nav-item ${view === "health" ? "active" : ""}`} onClick={() => setView("health")}>
            <Icon d={Icons.heart} size={16} /><span className="nav-item-label">Health Insights</span>
            {alertCount !== null && alertCount > 0 && <span className="badge-count" style={{ background: "rgba(239,68,68,0.15)", color: "#f87171" }}>{alertCount}</span>}
          </button>
        </div>
        <div className="sidebar-footer">
          <div className="user-pill">
            <div className="user-pill-avatar" style={{ background: "linear-gradient(135deg, var(--amber), #f97316)", color: "#000" }}>{initials}</div>
            <div className="user-pill-info"><div className="user-pill-name">{email}</div><div className="user-pill-role">Admin</div></div>
          </div>
        </div>
      </div>

      <div className="main">
        <div className="topbar">
          <span className="topbar-title">{view === "documents" ? "Knowledge Base" : view === "upload" ? "Upload Document" : view === "health" ? "Crew Health Insights" : "RAG Query Test"}</span>
          {view === "documents" && <button className="btn btn-ghost btn-sm" onClick={loadDocs}>{loading ? <div className="loader" /> : "Refresh"}</button>}
        </div>

        {view === "health" ? <HealthInsightsView token={token} /> : (
          <div className="panel-page">
            {view === "documents" && (<>
              <div><div className="panel-title">Document Library</div><div className="panel-sub">{documents.length} documents · {indexed} indexed and ready</div></div>
              <div className="card">
                <div className="card-title"><Icon d={Icons.file} size={14} /> Indexed Files</div>
                {documents.length === 0 ? <div style={{ textAlign: "center", padding: "32px", color: "var(--text-dim)" }}>No documents yet. Upload files to populate the knowledge base.</div> : (
                  <table className="doc-table">
                    <thead><tr><th>Filename</th><th>Type</th><th>Size</th><th>Chunks</th><th>Status</th><th>Date</th><th></th></tr></thead>
                    <tbody>{documents.map((doc) => (<tr key={doc.id}><td style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>{doc.filename}</td><td><span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-dim)" }}>{doc.file_type}</span></td><td style={{ color: "var(--text-dim)", fontSize: "12px" }}>{fmtSize(doc.file_size)}</td><td style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>{doc.chunk_count}</td><td><span className={`status-badge status-${doc.status}`}><span className="status-dot" />{doc.status}</span></td><td style={{ color: "var(--text-dim)", fontSize: "12px" }}>{fmtDate(doc.created_at)}</td><td><button className="btn btn-icon btn-danger btn-sm" onClick={() => handleDelete(doc.id)} title="Delete"><Icon d={Icons.trash} size={13} /></button></td></tr>))}</tbody>
                  </table>
                )}
              </div>
            </>)}

            {view === "upload" && (
              <div style={{ maxWidth: "580px" }}>
                <div className="panel-title">Upload Document</div>
                <div className="panel-sub">Supported: PDF, TXT, MD, DOCX, RST, CSV — max 50 MB</div>
                <div className="card" style={{ marginTop: "20px" }}>
                  {uploadErr && <div className="error-msg">{uploadErr}</div>}
                  {uploadMsg && <div className="success-msg">{uploadMsg}</div>}
                  <div className={`upload-zone ${dragOver ? "drag" : ""}`} onClick={() => fileInputRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={(e) => { e.preventDefault(); setDragOver(false); const file = e.dataTransfer.files[0]; if (file) handleUpload(file); }}>
                    <div className="upload-zone-icon">{uploading ? <div className="loader" /> : <Icon d={Icons.upload} size={22} />}</div>
                    <p>{uploading ? "Uploading…" : "Drop file here or click to browse"}</p>
                    <span>.pdf .txt .md .docx .rst .csv</span>
                  </div>
                  <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md,.docx,.rst,.csv" style={{ display: "none" }} onChange={(e) => handleUpload(e.target.files[0])} />
                </div>
              </div>
            )}

            {view === "query" && (
              <div style={{ maxWidth: "720px" }}>
                <div className="panel-title">RAG Query Tester</div>
                <div className="panel-sub">Test direct queries against the knowledge base</div>
                <div className="card" style={{ marginTop: "20px" }}>
                  <div className="card-title"><Icon d={Icons.zap} size={14} /> Ask the Knowledge Base</div>
                  <div className="search-bar" style={{ marginBottom: "12px" }}>
                    <Icon d={Icons.search} size={16} style={{ color: "var(--text-dim)", flexShrink: 0 }} />
                    <input className="search-input" placeholder="Enter your question…" value={queryText} onChange={(e) => setQueryText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleQuery()} />
                  </div>
                  <button className="btn btn-primary" onClick={handleQuery} disabled={querying || !queryText.trim()}>{querying ? <><div className="loader" /> Querying…</> : <><Icon d={Icons.zap} size={14} /> Run Query</>}</button>
                  {queryResult && (
                    <div style={{ marginTop: "20px" }}>
                      {queryResult.error ? <div className="error-msg">{queryResult.error}</div> : (<>
                        <div className="card-title" style={{ marginBottom: "10px" }}>Answer</div>
                        <div style={{ background: "var(--surface)", borderRadius: "var(--r)", padding: "16px", fontSize: "14px", lineHeight: "1.7", color: "var(--text)", border: "1px solid var(--border)" }}>{queryResult.answer}</div>
                        {queryResult.sources.length > 0 && (<div style={{ marginTop: "16px" }}><div className="card-title" style={{ marginBottom: "10px" }}>Sources</div>{queryResult.sources.map((s, i) => (<div key={i} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: "12px", marginBottom: "8px" }}><div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}><span className="source-chip"><Icon d={Icons.file} size={10} />{s.filename}</span><span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-dim)" }}>{Math.round(s.similarity * 100)}% match</span></div><div style={{ fontSize: "12px", color: "var(--text-dim)", lineHeight: 1.5 }}>{s.excerpt}</div></div>))}</div>)}
                        <div className="msg-timing" style={{ marginTop: "10px" }}><span>⚡ {queryResult.timing.total_ms}ms total</span></div>
                      </>)}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

// ─── STORAGE HELPERS ───────────────────────────────────────────────────────────
const STORAGE_KEY = "maitri_auth";
function loadAuthFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved);
    const payload = JSON.parse(atob(parsed.token.split(".")[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) { localStorage.removeItem(STORAGE_KEY); return null; }
    return parsed;
  } catch { localStorage.removeItem(STORAGE_KEY); return null; }
}
function saveAuthToStorage(auth) { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(auth)); } catch { } }
function clearAuthFromStorage() { try { localStorage.removeItem(STORAGE_KEY); } catch { } }

// ─── APP ROOT ──────────────────────────────────────────────────────────────────
export default function App() {
  const [auth, setAuth] = useState(() => loadAuthFromStorage());
  const [voiceResponse, setVoiceResponse] = useState(null);
  const [videoResponse, setVideoResponse] = useState(null);

  const handleLogin = (token, role, email) => {
    const a = { token, role, email };
    saveAuthToStorage(a);
    setAuth(a);
  };

  const handleLogout = () => {
    clearAuthFromStorage();
    setAuth(null);
  };

  const handleVoiceResponse = useCallback((data) => {
    setVoiceResponse(data);
  }, []);

  const handleVideoResponse = useCallback((data) => {
    setVideoResponse(data);
  }, []);

  return (
    <>
      <style>{css}</style>
      <Starfield />
      <div className="app">
        {!auth ? (
          <AuthPage onLogin={handleLogin} />
        ) : (
          <div className="layout">
            {auth.role === "admin" ? (
              <AdminView token={auth.token} email={auth.email} />
            ) : (
              <ChatView
                token={auth.token}
                email={auth.email}
                externalVoiceResponse={voiceResponse}
                onVoiceConsumed={() => setVoiceResponse(null)}
                externalVideoResponse={videoResponse}
                onVideoConsumed={() => setVideoResponse(null)}
              />
            )}

            {auth.role === "astronaut" && (
              <div className="media-hud">
                <SensorOverlay
                  token={auth.token}
                  isAstronaut={true}
                  onNewVoiceResponse={handleVoiceResponse}
                />
                <VideoOverlay
                  token={auth.token}
                  isAstronaut={true}
                  onNewVideoResponse={handleVideoResponse}
                />
              </div>
            )}

            <div style={{ position: "fixed", top: "12px", right: "16px", zIndex: 400 }}>
              <button className="btn btn-ghost btn-sm" onClick={handleLogout} title="Log out">
                <Icon d={Icons.logout} size={14} /> Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}