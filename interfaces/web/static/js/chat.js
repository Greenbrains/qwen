'use strict';
/* Чат Green Brain: текст + голос. Эндпоинты правь ТОЛЬКО в CONFIG. */
const wsBase = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;
const CONFIG = {
  textWs:   d => `${wsBase}/ws/text`  + (d ? `?destination=${encodeURIComponent(d)}` : ''),
  voiceWs:  d => `${wsBase}/ws/voice` + (d ? `?destination=${encodeURIComponent(d)}` : ''),
  destInfo: d => `/api/destinations/${encodeURIComponent(d)}`,
};

const $ = s => document.querySelector(s);
const chatLog = $('#chatLog'), msgInput = $('#msgInput'), sendBtn = $('#sendBtn');
const clearBtn = $('#clearBtn'), modeText = $('#modeText'), modeVoice = $('#modeVoice');
const textInput = $('#textInput'), voiceBox = $('#voiceBox'), voiceBtn = $('#voiceBtn');
const connStatus = $('#connStatus'), destBadge = $('#destBadge'), destName = $('#destName');

const dest = new URLSearchParams(location.search).get('dest') || '';
let textWs = null, voiceWs = null, mediaRec = null, recording = false;

function addMsg(text, cls = 'bot') {
  const div = document.createElement('div');
  div.className = `msg ${cls}`;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
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

/* текст */
function connectTextWs() {
  textWs = new WebSocket(CONFIG.textWs(dest));
  textWs.onopen = () => setStatus('Онлайн', true);
  textWs.onclose = () => { setStatus('Оффлайн, реконнект...', false); setTimeout(connectTextWs, 3000); };
  textWs.onerror = () => textWs.close();
  textWs.onmessage = ev => {
    if (typeof ev.data !== 'string') return;
    let payload = ev.data;
    try {
      const j = JSON.parse(ev.data);
      payload = j.text || j.message || j.response || j.content || ev.data;
    } catch (_) {}
    addMsg(payload, 'bot');
  };
}
function sendText() {
  const text = msgInput.value.trim();
  if (!text) return;
  if (!textWs || textWs.readyState !== WebSocket.OPEN) { addMsg('Нет соединения с сервером', 'sys'); return; }
  textWs.send(JSON.stringify({ type: 'message', text, destination: dest }));
  addMsg(text, 'user');
  msgInput.value = '';
}

/* голос */
function connectVoiceWs() {
  voiceWs = new WebSocket(CONFIG.voiceWs(dest));
  voiceWs.binaryType = 'arraybuffer';
  voiceWs.onmessage = ev => {
    if (ev.data instanceof ArrayBuffer && ev.data.byteLength) {
      const url = URL.createObjectURL(new Blob([ev.data], { type: 'audio/wav' }));
      const a = new Audio(url);
      a.onended = () => URL.revokeObjectURL(url);
      a.play();
    } else if (typeof ev.data === 'string') addMsg(ev.data, 'bot');
  };
}
async function startRecording() {
  if (recording) return;
  if (!voiceWs || voiceWs.readyState !== WebSocket.OPEN) { addMsg('Голосовой канал не подключён', 'sys'); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRec = new MediaRecorder(stream);
    mediaRec.ondataavailable = e => {
      if (e.data.size && voiceWs.readyState === WebSocket.OPEN) e.data.arrayBuffer().then(b => voiceWs.send(b));
    };
    mediaRec.start(250);
    recording = true;
    voiceBtn.classList.add('recording');
    voiceBtn.textContent = '⏹';
  } catch (e) { addMsg('Нет доступа к микрофону', 'sys'); }
}
function stopRecording() {
  if (!recording || !mediaRec) return;
  mediaRec.stop();
  mediaRec.stream.getTracks().forEach(t => t.stop());
  recording = false;
  voiceBtn.classList.remove('recording');
  voiceBtn.textContent = '🎤';
}

sendBtn.addEventListener('click', sendText);
msgInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendText(); });
clearBtn.addEventListener('click', () => { chatLog.innerHTML = ''; });
modeText.addEventListener('click', () => showMode('text'));
modeVoice.addEventListener('click', () => showMode('voice'));
voiceBtn.addEventListener('mousedown', startRecording);
voiceBtn.addEventListener('mouseup', stopRecording);
voiceBtn.addEventListener('touchstart', e => { e.preventDefault(); startRecording(); });
voiceBtn.addEventListener('touchend', stopRecording);

/* init */
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