const sessionListEl = document.getElementById('session-list');
const runBtn = document.getElementById('run-analysis');
const regenBtn = document.getElementById('run-regenerate');
const statusPill = document.getElementById('status-pill');
const statusDetail = document.getElementById('status-detail');
const overviewEl = document.getElementById('overview');
const overviewSkeleton = document.getElementById('overview-skeleton');
const beatsEl = document.getElementById('beats');
const emotionsEl = document.getElementById('emotions');
const engagementEl = document.getElementById('engagement');
const improvementsEl = document.getElementById('improvements');
const rawJsonEl = document.getElementById('raw-json');
const chatFeed = document.getElementById('chat-feed');
const resultsPanel = document.getElementById('results-panel');
const feedbackBlock = document.getElementById('feedback-block');
const titleInput = document.getElementById('title');
const scriptInput = document.getElementById('script');
const regenInput = document.getElementById('regen');
const cfgModel = document.getElementById('cfg-model');
const cfgIterations = document.getElementById('cfg-iterations');
const cfgReasoningIterations = document.getElementById('cfg-reasoning-iterations');
const cfgTemperature = document.getElementById('cfg-temperature');
const cfgTemperatureValue = document.getElementById('cfg-temperature-value');
const cfgSteps = document.getElementById('cfg-steps');
const cfgReasoning = document.getElementById('cfg-reasoning');

let currentSessionId = null;
let currentSource = null;

const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tab-panel');

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((btn) => btn.classList.remove('active'));
    panels.forEach((panel) => panel.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
  });
});

function setStatus(label, detail) {
  statusPill.textContent = label;
  statusDetail.textContent = detail || '';
}

function addChatMessage(text, role = 'system') {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  chatFeed.appendChild(bubble);
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function clearChat() {
  chatFeed.innerHTML = '';
}

function setMode(mode) {
  if (mode === 'complete') {
    resultsPanel.classList.remove('hidden');
    feedbackBlock.classList.remove('hidden');
    feedbackBlock.style.display = 'grid';
    scriptInput.setAttribute('disabled', 'disabled');
    titleInput.setAttribute('disabled', 'disabled');
    runBtn.setAttribute('disabled', 'disabled');
    regenBtn.removeAttribute('disabled');
  } else if (mode === 'running') {
    resultsPanel.classList.add('hidden');
    feedbackBlock.classList.add('hidden');
    feedbackBlock.style.display = 'none';
    scriptInput.setAttribute('disabled', 'disabled');
    titleInput.setAttribute('disabled', 'disabled');
    runBtn.setAttribute('disabled', 'disabled');
    regenBtn.setAttribute('disabled', 'disabled');
  } else {
    resultsPanel.classList.add('hidden');
    feedbackBlock.classList.add('hidden');
    feedbackBlock.style.display = 'none';
    regenInput.value = '';
    scriptInput.removeAttribute('disabled');
    titleInput.removeAttribute('disabled');
    runBtn.removeAttribute('disabled');
    regenBtn.setAttribute('disabled', 'disabled');
  }
}

function setSessionId(sessionId) {
  currentSessionId = sessionId;
  if (sessionId) {
    localStorage.setItem('scriptpulse_session', sessionId);
  } else {
    localStorage.removeItem('scriptpulse_session');
  }
}

async function createSession() {
  const title = titleInput.value || null;
  const response = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });
  const data = await response.json();
  setSessionId(data.session_id);
  await refreshSessions();
  setStatus('Ready', 'Session created.');
}

async function saveInput() {
  if (!currentSessionId) {
    await createSession();
  }
  const title = titleInput.value || null;
  const raw_text = scriptInput.value;
  await fetch(`/api/sessions/${currentSessionId}/input`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, raw_text })
  });
}

async function saveRegeneration() {
  const regeneration_prompt = regenInput.value || '';
  if (!regeneration_prompt) {
    return;
  }
  await fetch(`/api/sessions/${currentSessionId}/regeneration`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ regeneration_prompt })
  });
}

async function saveConfig() {
  if (!currentSessionId) {
    return;
  }
  const payload = {
    model: cfgModel.value || null,
    temperature: parseFloat(cfgTemperature.value),
    max_iterations: parseInt(cfgIterations.value, 10),
    reasoning_iterations: parseInt(cfgReasoningIterations.value, 10),
    steps_pipeline: cfgSteps.checked,
    reasoning_pipeline: cfgReasoning.checked,
  };
  await fetch(`/api/sessions/${currentSessionId}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

function showSkeleton() {
  overviewSkeleton.style.display = 'grid';
  resultsPanel.classList.add('hidden');
  overviewEl.innerHTML = '';
  beatsEl.innerHTML = '';
  emotionsEl.innerHTML = '';
  engagementEl.innerHTML = '';
  improvementsEl.innerHTML = '';
  rawJsonEl.textContent = '';
}

function hideSkeleton() {
  overviewSkeleton.style.display = 'none';
  resultsPanel.classList.remove('hidden');
}

function renderOverview(report) {
  if (!report) return;
  const summary = report.summary_3_4_lines || [];
  overviewEl.innerHTML = `
    <div class="card">
      <h4>Summary</h4>
      <ul>${summary.map(line => `<li>${line}</li>`).join('')}</ul>
    </div>
    <div class="card">
      <h4>Strongest / Weakest</h4>
      <p><strong>Strongest:</strong> ${report.engagement_analysis?.strongest_element || '—'}</p>
      <p><strong>Weakest:</strong> ${report.engagement_analysis?.weakest_element || '—'}</p>
    </div>
  `;
}

function renderBeats(beats) {
  if (!beats) return;
  beatsEl.innerHTML = beats.map((beat) => `
    <div class="card">
      <h4>${beat.label} (${beat.beat_id})</h4>
      <p>${beat.short_description}</p>
      <p><strong>Evidence:</strong> ${beat.evidence_line_ids?.join(', ') || '—'}</p>
    </div>
  `).join('');
}

function renderEmotions(emotions) {
  if (!emotions) return;
  emotionsEl.innerHTML = emotions.map((shift) => `
    <div class="card">
      <h4>${shift.beat_id}</h4>
      <p>${shift.shift_from_previous}</p>
      <p><strong>Intensity:</strong> ${shift.emotional_intensity}</p>
    </div>
  `).join('');
}

function renderEngagement(analysis) {
  if (!analysis) return;
  engagementEl.innerHTML = analysis.factors.map((factor) => `
    <div class="card">
      <h4>${factor.factor}</h4>
      <p><strong>Score:</strong> ${factor.score} (weighted ${factor.weighted_score})</p>
      <p>${factor.reasoning}</p>
    </div>
  `).join('');
}

function renderImprovements(plan) {
  if (!plan) return;
  improvementsEl.innerHTML = plan.suggestions.map((item) => `
    <div class="card">
      <h4>${item.target_area}</h4>
      <p>${item.issue}</p>
      <p><strong>Fix:</strong> ${item.concrete_fix}</p>
    </div>
  `).join('');
}

function renderResult(payload) {
  setMode('complete');
  hideSkeleton();
  renderOverview(payload.report);
  renderBeats(payload.beat_extraction?.beats || []);
  renderEmotions(payload.emotion_analysis?.beatwise_arc || []);
  renderEngagement(payload.engagement_analysis || {});
  renderImprovements(payload.improvement_plan || {});
  rawJsonEl.textContent = JSON.stringify(payload, null, 2);
}

function startStream(mode) {
  if (currentSource) {
    currentSource.close();
  }
  clearChat();
  showSkeleton();
  setMode('running');
  setStatus('Running', 'Streaming updates...');
  addChatMessage(`Mode: ${mode}. Analysis started.`, 'system');

  currentSource = new EventSource(`/api/sessions/${currentSessionId}/stream?mode=${mode}`);

  currentSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    addChatMessage(`${data.stage} - ${data.status}`, 'system');
  });

  currentSource.addEventListener('result', (event) => {
    const payload = JSON.parse(event.data);
    renderResult(payload);
    setStatus('Complete', `Iterations: ${payload.iterations}`);
    addChatMessage('Analysis complete. Review the breakdown and regenerate if needed.', 'system');
    refreshSessions();
  });

  currentSource.addEventListener('error', (event) => {
    setStatus('Error', 'Analysis failed.');
    addChatMessage('Analysis failed. Check logs for details.', 'system');
    setMode('draft');
    currentSource.close();
  });

  currentSource.addEventListener('done', () => {
    currentSource.close();
  });
}

function renderSessionList(sessions) {
  sessionListEl.innerHTML = '';
  const draft = document.createElement('div');
  draft.className = `session-item ${currentSessionId ? '' : 'active'}`;
  draft.innerHTML = '<div class="session-title">Draft Session</div><div class="session-snippet">Not saved yet</div>';
  draft.addEventListener('click', () => {
    setSessionId(null);
    titleInput.value = '';
    scriptInput.value = '';
    regenInput.value = '';
    setMode('draft');
    showSkeleton();
    setStatus('Draft', 'New draft session ready.');
  });
  sessionListEl.appendChild(draft);

  sessions.forEach((session) => {
    const item = document.createElement('div');
    item.className = `session-item ${session.session_id === currentSessionId ? 'active' : ''}`;
    const title = session.title || session.snippet || 'Untitled Session';
    item.innerHTML = `
      <div class="session-row">
        <div>
          <div class="session-title">${title}</div>
          <div class="session-snippet">${session.snippet || 'No script yet'}</div>
        </div>
        <button class="session-delete" type="button">Delete</button>
      </div>
    `;
    item.addEventListener('click', async () => {
      await loadSession(session.session_id);
    });
    const deleteBtn = item.querySelector('.session-delete');
    deleteBtn.addEventListener('click', async (event) => {
      event.stopPropagation();
      await fetch(`/api/sessions/${session.session_id}`, { method: 'DELETE' });
      if (session.session_id === currentSessionId) {
        setSessionId(null);
        showSkeleton();
        setStatus('Draft', 'Session deleted.');
      }
      refreshSessions();
    });
    sessionListEl.appendChild(item);
  });
}

async function refreshSessions() {
  const response = await fetch('/api/sessions');
  const data = await response.json();
  renderSessionList(data.sessions || []);
}

async function loadSession(sessionId) {
  const response = await fetch(`/api/sessions/${sessionId}`);
  const data = await response.json();
  setSessionId(sessionId);
  titleInput.value = data.title || '';
  scriptInput.value = data.raw_text || '';
  regenInput.value = data.regeneration_prompt || '';
  if (data.last_report_json) {
    const reportPayload = {
      report: JSON.parse(data.last_report_json),
      validation: data.last_validation_json ? JSON.parse(data.last_validation_json) : null,
      engagement_analysis: data.last_engagement_json ? JSON.parse(data.last_engagement_json) : null,
      beat_extraction: data.last_beat_json ? JSON.parse(data.last_beat_json) : null,
      emotion_analysis: data.last_emotion_json ? JSON.parse(data.last_emotion_json) : null,
      improvement_plan: data.last_improvement_json ? JSON.parse(data.last_improvement_json) : null,
    };
    renderResult(reportPayload);
  } else {
    setMode('draft');
    showSkeleton();
  }
  setStatus(data.status || 'Idle', `Last updated ${data.updated_at || 'just now'}`);
  refreshSessions();
}

runBtn.addEventListener('click', async () => {
  await saveInput();
  await saveConfig();
  await saveRegeneration();
  addChatMessage('Script submitted for analysis.', 'user');
  startStream('analyze');
});

regenBtn.addEventListener('click', async () => {
  await saveInput();
  await saveConfig();
  await saveRegeneration();
  addChatMessage('Regeneration prompt submitted.', 'user');
  startStream('regenerate');
});

cfgTemperature.addEventListener('input', () => {
  cfgTemperatureValue.textContent = Number(cfgTemperature.value).toFixed(2);
});

refreshSessions();
setMode('draft');
