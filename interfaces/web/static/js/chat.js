'use strict';
/* ================================================================
   Green Brain чат. Контракт — строго по interfaces/api/websocket.py:
   /ws:       -> {"type":"text","message":...} | {"type":"clear"}
              <- {"type":"text","message":...} | {"type":"cleared"} | {"type":"error",...}
   /ws/voice: -> {"type":"audio","data":base64 PCM16,"sample_rate":N} | {"type":"audio_end"}
              <- voice_ready | user_text | text_delta | audio_delta | tool_call | response_done | error
   ================================================================ */

const wsBase = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;
const CONFIG = {
  textWs:   `${wsBase}/ws`,
  voiceWs:  `${wsBase}/ws/voice`,
  destInfo: d => `/api/destinations/${encodeURIComponent(d)}`,
};

const $ = s => document.querySelector(s);
const chatLog = $('#chatLog'), msgInput = $('#msgInput'), sendBtn = $('#sendBtn');
const clearBtn = $('#clearBtn'), modeText = $('#modeText'), modeVoice = $('#modeVoice');
const textInput = $('#textInput'), voiceBox = $('#voiceBox'), voiceBtn = $('#voiceBtn');
const connStatus = $('#connStatus'), destBadge = $('#destBadge'), destName = $('#destName');
const voiceStatus = voiceBox.querySelector('.status');

const dest = new URLSearchParams(location.search).get('dest') || '';

let textWs = null, voiceWs = null;
let recording = false, mediaStream = null, procNode = null, recCtx = null;
let playCtx = null, nextStart = 0, streamDiv = null;

/* ---------- UI ---------- */
function addMsg(text, cls = 'bot') {
  const div = document.createElement('div');
  div.className = `msg ${cls}`;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}
function setStatus(t, online = false) {
  connStatus.textContent = t;
  connStatus.classList.toggle('online', online);
}
function showMode(m) {
  modeText.classList.toggle('active', m === 'text');
  modeVoice.classList.toggle('active', m === 'voice');
  textInput.classList.toggle('hidden', m !== 'text');
  voiceBox.classList.toggle('hidden', m !== 'voice');
}

/* ---------- /ws : текст ---------- */
function connectTextWs() {
  textWs = new WebSocket(CONFIG.textWs);
  textWs.onopen = () => setStatus('Онлайн', true);
  textWs.onclose = () => { setStatus('Оффлайн, реконнект...', false); setTimeout(connectTextWs, 3000); };
  textWs.onerror = () => textWs.close();
  textWs.onmessage = ev => {
    let j = null;
    try { j = JSON.parse(ev.data); } catch (_) {}
    if (!j) { addMsg(ev.data, 'bot'); return; }
    switch (j.type) {
      case 'text':    addMsg(j.message || '', 'bot'); break;
      case 'cleared': addMsg('История очищена', 'sys'); break;
      case 'error':   addMsg('⚠️ ' + (j.message || 'ошибка'), 'sys'); break;
      default: break; /* служебные не показываем */
    }
  };
}
function sendText() {
  const text = msgInput.value.trim();
  if (!text) return;
  if (!textWs || textWs.readyState !== WebSocket.OPEN) { addMsg('Нет соединения с сервером', 'sys'); return; }
  textWs.send(JSON.stringify({ type: 'text', message: text }));
  addMsg(text, 'user');
  msgInput.value = '';
}

/* ---------- /ws/voice : приём ---------- */
function connectVoiceWs() {
  voiceWs = new WebSocket(CONFIG.voiceWs);
  voiceWs.onopen = () => { if (voiceStatus) voiceStatus.textContent = 'Канал готов — нажми и говори'; };
  voiceWs.onclose = () => { if (voiceStatus) voiceStatus.textContent = 'Голосовой канал оффлайн'; };
  voiceWs.onmessage = ev => {
    let j = null;
    try { j = JSON.parse(ev.data); } catch (_) { return; }
    switch (j.type) {
      case 'voice_ready': break;
      case 'user_text': addMsg(j.text || '', 'user'); break;
      case 'text_delta':
        if (!streamDiv) streamDiv = addMsg('', 'bot');
        streamDiv.textContent += j.text || '';
        chatLog.scrollTop = chatLog.scrollHeight;
        break;
      case 'audio_delta': playPcm16b64(j.data || ''); break;
      case 'tool_call': addMsg('🔧 ' + (j.name || 'инструмент'), 'sys'); break;
      case 'response_done': streamDiv = null; nextStart = 0; break;
      case 'error': addMsg('⚠️ ' + (j.message || 'ошибка голоса'), 'sys'); break;
      default: break;
    }
  };
}

/* ---------- запись PCM16 (push-to-talk) ---------- */
function float32ToPcm16(f32) {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = Math.max(-1, Math.min(1, f32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return out;
}
function abToB64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = '';
  const CH = 0x8000;
  for (let i = 0; i < bytes.length; i += CH) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
  }
  return btoa(bin);
}
async function startRecording() {
  if (recording) return;
  if (!voiceWs || voiceWs.readyState !== WebSocket.OPEN) { addMsg('Голосовой канал не подключён', 'sys'); return; }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = recCtx.createMediaStreamSource(mediaStream);
    procNode = src.createScriptProcessor(4096, 1, 1);
    procNode.onaudioprocess = e => {
      if (!recording) return;
      const pcm = float32ToPcm16(e.inputBuffer.getChannelData(0));
      voiceWs.send(JSON.stringify({ type: 'audio', data: abToB64(pcm.buffer), sample_rate: recCtx.sampleRate }));
    };
    src.connect(procNode);
    procNode.connect(recCtx.destination);
    recording = true;
    nextStart = 0;
    voiceBtn.classList.add('recording');
    if (voiceStatus) voiceStatus.textContent = 'Слушаю... отпусти, чтобы отправить';
  } catch (e) {
    addMsg('Нет доступа к микрофону', 'sys');
  }
}
function stopRecording() {
  if (!recording) return;
  recording = false;
  try { voiceWs.send(JSON.stringify({ type: 'audio_end' })); } catch (_) {}
  if (procNode) { procNode.disconnect(); procNode = null; }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }
  if (recCtx) { recCtx.close(); recCtx = null; }
  voiceBtn.classList.remove('recording');
  if (voiceStatus) voiceStatus.textContent = 'Нажми и говори';
}

/* ---------- воспроизведение PCM16 (base64, 44100) ---------- */
function playPcm16b64(b64) {
  try {
    if (!playCtx) playCtx = new (window.AudioContext || window.webkitAudioContext)();
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const i16 = new Int16Array(bytes.buffer);
    if (!i16.length) return;
    const f32 = new Float32Array(i16.length);
    for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 0x8000;
    const buf = playCtx.createBuffer(1, f32.length, 44100);
    buf.copyToChannel(f32, 0);
    const srcNode = playCtx.createBufferSource();
    srcNode.buffer = buf;
    srcNode.connect(playCtx.destination);
    const t = Math.max(playCtx.currentTime + 0.01, nextStart);
    srcNode.start(t);
    nextStart = t + buf.duration;
  } catch (_) {}
}

/* ---------- события ---------- */
sendBtn.addEventListener('click', sendText);
msgInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendText(); });
clearBtn.addEventListener('click', () => {
  chatLog.innerHTML = '';
  streamDiv = null;
  if (textWs && textWs.readyState === WebSocket.OPEN) textWs.send(JSON.stringify({ type: 'clear' }));
});
modeText.addEventListener('click', () => showMode('text'));
modeVoice.addEventListener('click', () => showMode('voice'));
voiceBtn.addEventListener('mousedown', startRecording);
voiceBtn.addEventListener('mouseup', stopRecording);
voiceBtn.addEventListener('touchstart', e => { e.preventDefault(); startRecording(); });
voiceBtn.addEventListener('touchend', stopRecording);

/* ---------- init ---------- */
if (dest) {
  destName.textContent = dest;
  destBadge.classList.remove('hidden');
  fetch(CONFIG.destInfo(dest))
    .then(r => r.ok ? r.json() : null)
    .then(info => {
      if (!info) return;
      if (info.name) destName.textContent = info.name;
      if (info.full_description || info.description) addMsg(info.full_description || info.description, 'sys');
    })
    .catch(() => {});
}
showMode('text');
connectTextWs();
connectVoiceWs();