'use strict';

// ── State ───────────────────────────────────────────────────────
let sessionId = sessionStorage.getItem('merge_sid') || null;

// ── DOM refs ────────────────────────────────────────────────────
const authOverlay   = document.getElementById('auth-overlay');
const app           = document.getElementById('app');
const pwInput       = document.getElementById('pw-input');
const pwBtn         = document.getElementById('pw-btn');
const pwError       = document.getElementById('pw-error');
const sidDisplay    = document.getElementById('sid-display');
const dropZone      = document.getElementById('drop-zone');
const fileInput     = document.getElementById('file-input');
const cardArea      = document.getElementById('card-area');
const cardList      = document.getElementById('card-list');
const btnConvert    = document.getElementById('btn-convert');
const selFormat     = document.getElementById('sel-format');
const selSize       = document.getElementById('sel-size');
const selAlgo       = document.getElementById('sel-algo');
const inpManualPx   = document.getElementById('inp-manual-px');
const manualPxGroup = document.getElementById('manual-px-group');
const progressArea  = document.getElementById('progress-area');
const progressFill  = document.getElementById('progress-fill');
const progressMsg   = document.getElementById('progress-msg');
const downloadArea  = document.getElementById('download-area');
const downloadLink  = document.getElementById('download-link');

// ── Auth ─────────────────────────────────────────────────────────
async function tryAuth() {
  const pw = pwInput.value.trim();
  if (!pw) return;
  pwBtn.disabled = true;
  try {
    const fd = new FormData();
    fd.append('password', pw);
    const res = await fetch('/api/auth', { method: 'POST', body: fd });
    if (!res.ok) { showPwError(); return; }
    const data = await res.json();
    sessionId = data.session_id;
    sessionStorage.setItem('merge_sid', sessionId);
    enterApp();
  } catch {
    showPwError();
  } finally {
    pwBtn.disabled = false;
  }
}

function showPwError() {
  pwError.classList.remove('hidden');
  pwInput.value = '';
  pwInput.focus();
}

async function validateExistingSession() {
  if (!sessionId) return false;
  try {
    const res = await fetch(`/api/files?session_id=${sessionId}`);
    if (!res.ok) return false;
    const data = await res.json();
    renderCards(data.file_list);
    return true;
  } catch {
    return false;
  }
}

function enterApp() {
  authOverlay.classList.add('hidden');
  app.classList.remove('hidden');
  sidDisplay.textContent = sessionId.slice(0, 8) + '…';
}

pwBtn.addEventListener('click', tryAuth);
pwInput.addEventListener('keydown', e => { if (e.key === 'Enter') tryAuth(); });

// ── Init ─────────────────────────────────────────────────────────
(async () => {
  if (sessionId && await validateExistingSession()) {
    enterApp();
  }
})();

// ── Drop zone ────────────────────────────────────────────────────
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  uploadFiles(Array.from(e.dataTransfer.files));
});
dropZone.addEventListener('click', e => {
  if (e.target.tagName === 'LABEL' || e.target.tagName === 'INPUT') return;
  fileInput.click();
});
fileInput.addEventListener('change', () => {
  uploadFiles(Array.from(fileInput.files));
  fileInput.value = '';
});

// ── Upload ───────────────────────────────────────────────────────
async function uploadFiles(files) {
  if (!files.length) return;
  const fd = new FormData();
  fd.append('session_id', sessionId);
  files.forEach(f => fd.append('files', f));

  showProgress('上傳中…', 30);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || '上傳失敗'); hideProgress(); return; }
    renderCards(data.file_list);
    hideProgress();
  } catch (e) {
    alert('上傳失敗：' + e.message);
    hideProgress();
  }
}

// ── Cards ────────────────────────────────────────────────────────
let sortable = null;

function renderCards(fileList) {
  cardList.innerHTML = '';
  if (!fileList.length) {
    cardArea.classList.add('hidden');
    btnConvert.disabled = true;
    return;
  }
  cardArea.classList.remove('hidden');
  btnConvert.disabled = false;
  downloadArea.classList.add('hidden');

  fileList.forEach(f => cardList.appendChild(buildCard(f)));

  // Sortable
  if (sortable) sortable.destroy();
  sortable = Sortable.create(cardList, {
    animation: 150,
    ghostClass: 'sortable-ghost',
    onEnd: async () => {
      const ids = Array.from(cardList.children).map(el => el.dataset.id);
      const fd = new FormData();
      fd.append('session_id', sessionId);
      fd.append('order', JSON.stringify(ids));
      await fetch('/api/reorder', { method: 'POST', body: fd });
    },
  });
}

function buildCard(f) {
  const card = document.createElement('div');
  card.className = 'file-card';
  card.dataset.id = f.id;

  // Thumbnail — rotation applied via CSS so cache never needs invalidation
  const thumb = document.createElement('img');
  thumb.className = 'card-thumb';
  thumb.src = `/api/thumbnail/${sessionId}/${f.id}`;
  thumb.alt = f.original_name;
  thumb.style.transform = `rotate(${f.rotation || 0}deg)`;
  thumb.onerror = () => {
    const ph = document.createElement('div');
    ph.className = 'card-thumb-placeholder';
    ph.textContent = extEmoji(f.original_name);
    card.replaceChild(ph, thumb);
  };

  // Info
  const info = document.createElement('div');
  info.className = 'card-info';
  const name = document.createElement('div');
  name.className = 'card-name';
  name.textContent = f.original_name;
  const metaEl = document.createElement('div');
  metaEl.className = 'card-meta';
  const updateMeta = rot => {
    metaEl.textContent = `${(f.size / 1024).toFixed(1)} KB` + (rot ? ` · 旋轉 ${rot}°` : '');
  };
  updateMeta(f.rotation || 0);
  info.append(name, metaEl);

  // Actions
  const actions = document.createElement('div');
  actions.className = 'card-actions';

  let currentRot = f.rotation || 0;
  const makeRotBtn = (deg, label) => {
    const b = document.createElement('button');
    b.textContent = label;
    b.title = `旋轉 ${deg}°`;
    b.addEventListener('click', () => {
      // Instant CSS update — no round-trip wait
      currentRot = (currentRot + deg + 360) % 360;
      thumb.style.transform = `rotate(${currentRot}deg)`;
      updateMeta(currentRot);
      // Persist to server in background
      const fd = new FormData();
      fd.append('session_id', sessionId);
      fd.append('file_id', f.id);
      fd.append('degrees', deg);
      fetch('/api/rotate', { method: 'POST', body: fd });
    });
    return b;
  };

  const delBtn = document.createElement('button');
  delBtn.className = 'btn-delete';
  delBtn.textContent = '✕';
  delBtn.title = '移除';
  delBtn.addEventListener('click', async () => {
    const fd = new FormData();
    fd.append('session_id', sessionId);
    fd.append('file_id', f.id);
    const res = await fetch('/api/delete', { method: 'POST', body: fd });
    const data = await res.json();
    renderCards(data.file_list);
  });

  actions.append(makeRotBtn(90, '↻90°'), makeRotBtn(270, '↺90°'), delBtn);
  card.append(thumb, info, actions);
  return card;
}

function extEmoji(name) {
  const ext = (name.split('.').pop() || '').toLowerCase();
  if (['pdf'].includes(ext)) return '📄';
  if (['doc', 'docx'].includes(ext)) return '📝';
  if (['xls', 'xlsx'].includes(ext)) return '📊';
  if (['ppt', 'pptx'].includes(ext)) return '📑';
  return '🖼';
}

// ── Settings ─────────────────────────────────────────────────────
selSize.addEventListener('change', () => {
  manualPxGroup.style.display = selSize.value === 'manual' ? '' : 'none';
});

// ── Convert ──────────────────────────────────────────────────────
btnConvert.addEventListener('click', async () => {
  btnConvert.disabled = true;
  showProgress('轉換中…', 10);
  downloadArea.classList.add('hidden');

  const fd = new FormData();
  fd.append('session_id', sessionId);
  fd.append('output_format', selFormat.value);
  fd.append('size_mode', selSize.value);
  fd.append('algorithm', selAlgo.value);
  fd.append('manual_px', inpManualPx.value || '0');

  try {
    setProgress(40, '載入檔案…');
    const res = await fetch('/api/convert', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || '轉換失敗'); return; }

    setProgress(90, '準備下載…');
    downloadLink.href = data.download_url;
    downloadLink.download = data.filename;
    downloadLink.textContent = `⬇ 下載 ${data.filename}`;
    setProgress(100, '完成！');
    setTimeout(() => {
      hideProgress();
      downloadArea.classList.remove('hidden');
    }, 600);
  } catch (e) {
    alert('轉換失敗：' + e.message);
    hideProgress();
  } finally {
    btnConvert.disabled = false;
  }
});

// ── Progress helpers ──────────────────────────────────────────────
function showProgress(msg, pct) {
  progressArea.classList.remove('hidden');
  setProgress(pct, msg);
}
function setProgress(pct, msg) {
  progressFill.style.width = pct + '%';
  if (msg) progressMsg.textContent = msg;
}
function hideProgress() {
  progressArea.classList.add('hidden');
  progressFill.style.width = '0';
}
