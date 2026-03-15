const sessionListEl = document.getElementById('session-list');
const runBtn = document.getElementById('run-analysis');
const regenBtn = document.getElementById('run-regenerate');
const clearEvidenceBtn = document.getElementById('clear-evidence');
const statusPill = document.getElementById('status-pill');
const statusDetail = document.getElementById('status-detail');
const titleInput = document.getElementById('title');
const scriptInput = document.getElementById('script');
const regenInput = document.getElementById('regen');
const feedbackBlock = document.getElementById('feedback-block');
const chatFeed = document.getElementById('chat-feed');
const overviewEl = document.getElementById('overview');
const emptyOverviewEl = document.getElementById('empty-overview');
const beatsEl = document.getElementById('beats');
const emotionsEl = document.getElementById('emotions');
const engagementEl = document.getElementById('engagement');
const improvementsEl = document.getElementById('improvements');
const validationEl = document.getElementById('validation');
const emptyValidationEl = document.getElementById('empty-validation');
const scriptLinesEl = document.getElementById('script-lines');
const rawJsonEl = document.getElementById('raw-json');
const reportTitleEl = document.getElementById('report-title');
const reportContextEl = document.getElementById('report-context');
const reportMetaEl = document.getElementById('report-meta');
const statTokensEl = document.getElementById('stat-tokens');
const statTokensNoteEl = document.getElementById('stat-tokens-note');
const statIterationsEl = document.getElementById('stat-iterations');
const statIterationsNoteEl = document.getElementById('stat-iterations-note');
const statValidationEl = document.getElementById('stat-validation');
const statValidationNoteEl = document.getElementById('stat-validation-note');
const statSessionEl = document.getElementById('stat-session');
const statSessionNoteEl = document.getElementById('stat-session-note');
const cfgModel = document.getElementById('cfg-model');
const cfgModelNote = document.getElementById('cfg-model-note');
const cfgIterations = document.getElementById('cfg-iterations');
const cfgIterationsValue = document.getElementById('cfg-iterations-value');
const cfgTemperature = document.getElementById('cfg-temperature');
const cfgTemperatureValue = document.getElementById('cfg-temperature-value');
const applyValidationFixBtn = document.getElementById('apply-validation-fix');
const validationFixNoteEl = document.getElementById('validation-fix-note');
const exportPdfBtn = document.getElementById('export-pdf');
const progressWrap = document.getElementById('progress-bar-wrap');
const progressFill = document.getElementById('progress-bar-fill');
const progressLabel = document.getElementById('progress-bar-label');

const tabs = Array.from(document.querySelectorAll('.tab'));
const panels = Array.from(document.querySelectorAll('.tab-panel'));

const DEFAULT_CONFIG = {
  model: 'gpt-5.4::medium',
  temperature: 0.2,
  max_iterations: 1,
};

const MODEL_CATALOG = {
  'gpt-5.4::minimal': {
    label: 'GPT-5.4 / Minimal thinking',
    note: 'OpenAI | 1.05M context | minimal thinking',
  },
  'gpt-5.4::low': {
    label: 'GPT-5.4 / Low thinking',
    note: 'OpenAI | 1.05M context | low thinking',
  },
  'gpt-5.4::medium': {
    label: 'GPT-5.4 / Medium thinking',
    note: 'OpenAI | 1.05M context | medium thinking',
  },
  'gpt-5.4::high': {
    label: 'GPT-5.4 / High thinking',
    note: 'OpenAI | 1.05M context | high thinking',
  },
  'claude-sonnet-4.5': {
    label: 'Claude Sonnet 4.5',
    note: 'Anthropic | 1.0M context | native reasoning',
  },
  'gemini-3.1-pro-preview': {
    label: 'Gemini 3.1 Pro Preview',
    note: 'Google | 1.05M context | reasoning tokens available',
  },
  'grok-4.1-fast': {
    label: 'Grok 4.1 Fast',
    note: 'xAI | 2.0M context | latest fast Grok route',
  },
};

const FEED_KEY_BASE = 'scriptpulse_feed';
const MAX_FEED_ENTRIES = 80;

const STAGE_LABELS = {
  start: 'Starting',
  iteration: 'Iteration',
  beat_extraction: 'Beats',
  emotion_analysis: 'Emotions',
  engagement_scoring: 'Engagement',
  improvement_plan: 'Improvements',
  validation: 'Validation',
  retry: 'Retry',
  complete: 'Complete',
};

const STAGE_ORDER = [
  'beat_extraction',
  'emotion_analysis',
  'engagement_scoring',
  'improvement_plan',
  'validation',
];

const ICONS = {
  format: `
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <rect x="2.5" y="2.5" width="11" height="11" rx="2"></rect>
      <path d="M5 6h6M5 8h6M5 10h4"></path>
    </svg>
  `,
  lines: `
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M5 4h8M5 8h8M5 12h8"></path>
      <circle cx="3" cy="4" r="0.8"></circle>
      <circle cx="3" cy="8" r="0.8"></circle>
      <circle cx="3" cy="12" r="0.8"></circle>
    </svg>
  `,
  characters: `
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="5.25" r="2.5"></circle>
      <path d="M3.5 13c0-2.2 2.05-4 4.5-4s4.5 1.8 4.5 4"></path>
    </svg>
  `,
  clock: `
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="5.5"></circle>
      <path d="M8 5v3.4l2.3 1.4"></path>
    </svg>
  `,
};

let currentSessionId = null;
let currentSource = null;
let currentPayload = null;
let currentLineLookup = new Map();
let selectedLineIds = [];

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatNumber(value) {
  const numericValue = Number(value || 0);
  return Number.isFinite(numericValue) ? numericValue.toLocaleString() : '0';
}

function formatScriptFormat(value) {
  const mapping = {
    scene_dialogue: 'Scene + Dialogue',
    dialogue: 'Dialogue',
    mixed: 'Mixed',
    unknown: 'Unknown',
  };
  return mapping[value] || 'Unknown';
}

function formatEnumLabel(value) {
  const cleaned = String(value || '').trim();
  if (!cleaned || cleaned === 'null') {
    return '';
  }
  return cleaned
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\b[a-z]/g, (char) => char.toUpperCase());
}

function formatDateTime(value, compact = false) {
  if (!value) {
    return compact ? 'Just now' : 'just now';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  const formatter = new Intl.DateTimeFormat(undefined, compact ? {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  } : {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  return formatter.format(date);
}

function capitalize(value) {
  if (!value) {
    return 'Idle';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function iconMarkup(name) {
  return `<span class="meta-icon">${ICONS[name] || ''}</span>`;
}

function buildHeaderMetric(icon, label, value) {
  return `
    <div class="report-metric">
      ${iconMarkup(icon)}
      <div>
        <span class="report-metric-label">${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    </div>
  `;
}

function setStatus(label, detail, state = 'idle') {
  statusPill.textContent = label;
  statusPill.dataset.state = state;
  statusDetail.textContent = detail || '';
}

function setProgress(stage, status, visible = true) {
  if (!progressWrap || !progressFill || !progressLabel) {
    return;
  }
  progressWrap.classList.toggle('visible', visible);
  if (!visible) {
    return;
  }

  const idx = STAGE_ORDER.indexOf(stage);
  const pct = idx < 0
    ? 10
    : Math.round(((idx + 1) / STAGE_ORDER.length) * 100);
  const label = STAGE_LABELS[stage] || stage || 'Working';
  const detail = status ? `${label} - ${status}` : label;

  progressFill.style.width = `${pct}%`;
  progressLabel.textContent = detail;
}

function setStats({
  tokens = '0',
  tokensNote = 'No run yet',
  iterations = '0',
  iterationsNote = 'Passes',
  validation = '\u2014',
  validationNote = 'Not run',
  session = 'Draft',
  sessionNote = 'Unsaved',
} = {}) {
  statTokensEl.textContent = tokens;
  statTokensNoteEl.textContent = tokensNote;
  statIterationsEl.textContent = iterations;
  statIterationsNoteEl.textContent = iterationsNote;
  statValidationEl.textContent = validation;
  statValidationNoteEl.textContent = validationNote;
  statSessionEl.textContent = session;
  statSessionNoteEl.textContent = sessionNote;
}

function getFeedKey() {
  return `${FEED_KEY_BASE}:${currentSessionId || 'draft'}`;
}

function getFeedStore() {
  try {
    return JSON.parse(localStorage.getItem(getFeedKey()) || '[]');
  } catch (error) {
    return [];
  }
}

function saveFeedStore(entries = []) {
  try {
    localStorage.setItem(getFeedKey(), JSON.stringify(entries.slice(0, MAX_FEED_ENTRIES)));
  } catch (error) {
    return;
  }
}

function formatFeedTime(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return '??-?? ??:??:??';
  }
  const dateStr = date.toLocaleDateString(undefined, { month: '2-digit', day: '2-digit' });
  const timeStr = date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  return `${dateStr} ${timeStr}`;
}

function renderFeedEntry(entry, insert = 'append') {
  const emptyState = chatFeed.querySelector('.chat-empty');
  if (emptyState) {
    emptyState.remove();
  }
  const bubble = document.createElement('div');
  const prefix = entry.role === 'user' ? '→' : '·';
  bubble.className = `chat-bubble ${entry.role}`;
  bubble.innerHTML = `
    <span class="log-time">${escapeHtml(formatFeedTime(entry.time))}</span>
    <span class="log-prefix">${prefix}</span>
    <span class="log-text">${escapeHtml(entry.text)}</span>
  `;

  const latest = chatFeed.querySelector('.chat-bubble.is-latest');
  if (latest) {
    latest.classList.remove('is-latest');
  }
  bubble.classList.add('is-latest');

  if (insert === 'prepend') {
    chatFeed.prepend(bubble);
  } else {
    chatFeed.append(bubble);
  }

  chatFeed.scrollTop = 0;
}

function renderFeedEmptyState() {
  if (!chatFeed) {
    return;
  }
  const existing = chatFeed.querySelector('.chat-empty');
  const entries = getFeedStore();
  if (entries.length) {
    if (existing) {
      existing.remove();
    }
    return;
  }
  if (existing) {
    return;
  }
  const empty = document.createElement('div');
  empty.className = 'chat-empty';
  empty.textContent = 'Updates will appear here.';
  chatFeed.append(empty);
}

function addChatMessage(text, role = 'system') {
  const entry = {
    text: String(text || ''),
    role,
    time: new Date().toISOString(),
  };
  const entries = getFeedStore();
  entries.unshift(entry);
  saveFeedStore(entries);
  renderFeedEntry(entry, 'append');
}

function clearChat({ wipeStore = false } = {}) {
  chatFeed.innerHTML = '';
  if (wipeStore) {
    localStorage.removeItem(getFeedKey());
    renderFeedEmptyState();
  }
}

function restoreFeed() {
  const entries = getFeedStore();
  if (!entries.length) {
    renderFeedEmptyState();
    return;
  }

  [...entries].reverse().forEach((entry) => {
    renderFeedEntry(entry, 'append');
  });
  renderFeedEmptyState();
}

function syncFeedView() {
  clearChat({ wipeStore: false });
  restoreFeed();
}

// ─── Tab Indicator ─────────────────────────────────────────────
function positionTabIndicator(tabName) {
  const indicator = document.getElementById('tab-indicator');
  const activeTabEl = document.querySelector(`.tab[data-tab="${tabName}"]`);
  if (!indicator || !activeTabEl) return;
  indicator.style.width = `${activeTabEl.offsetWidth}px`;
  indicator.style.transform = `translateX(${activeTabEl.offsetLeft}px)`;
}

function activateTab(tabName) {
  tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === tabName));
  panels.forEach((panel) => panel.classList.toggle('active', panel.id === `tab-${tabName}`));
  positionTabIndicator(tabName);
}

tabs.forEach((tab) => {
  tab.addEventListener('click', () => activateTab(tab.dataset.tab));
});

function setMode(mode) {
  if (mode === 'complete') {
    feedbackBlock.classList.remove('hidden');
    scriptInput.setAttribute('disabled', 'disabled');
    titleInput.setAttribute('disabled', 'disabled');
    runBtn.setAttribute('disabled', 'disabled');
    regenBtn.removeAttribute('disabled');
    setProgress('', '', false);
    return;
  }

  if (mode === 'running') {
    feedbackBlock.classList.add('hidden');
    scriptInput.setAttribute('disabled', 'disabled');
    titleInput.setAttribute('disabled', 'disabled');
    runBtn.setAttribute('disabled', 'disabled');
    regenBtn.setAttribute('disabled', 'disabled');
    return;
  }

  feedbackBlock.classList.add('hidden');
  regenInput.value = '';
  scriptInput.removeAttribute('disabled');
  titleInput.removeAttribute('disabled');
  runBtn.removeAttribute('disabled');
  regenBtn.setAttribute('disabled', 'disabled');
  setProgress('', '', false);
}

function setSessionId(sessionId) {
  currentSessionId = sessionId;
  if (sessionId) {
    localStorage.setItem('scriptpulse_session', sessionId);
  } else {
    localStorage.removeItem('scriptpulse_session');
  }
}

function ensureModelOption(value) {
  if (!value) {
    return DEFAULT_CONFIG.model;
  }
  if (Array.from(cfgModel.options).some((option) => option.value === value)) {
    return value;
  }

  const option = document.createElement('option');
  option.value = value;
  option.textContent = `Custom model (${value})`;
  cfgModel.appendChild(option);
  return value;
}

function updateModelNote() {
  const modelKey = cfgModel.value || DEFAULT_CONFIG.model;
  const modelInfo = MODEL_CATALOG[modelKey];
  cfgModelNote.textContent = modelInfo ? modelInfo.note : `Custom model | ${modelKey}`;
}

function applyConfig(config = {}) {
  const merged = {
    ...DEFAULT_CONFIG,
    ...(config || {}),
  };

  cfgModel.value = ensureModelOption(merged.model || DEFAULT_CONFIG.model);
  cfgIterations.value = String(Math.max(1, parseInt(merged.max_iterations || DEFAULT_CONFIG.max_iterations, 10)));
  if (cfgIterationsValue) {
    cfgIterationsValue.textContent = cfgIterations.value;
  }
  cfgTemperature.value = Number(merged.temperature ?? DEFAULT_CONFIG.temperature).toFixed(2);
  cfgTemperatureValue.textContent = Number(cfgTemperature.value).toFixed(2);
  updateModelNote();
}

function buildLineLookup(scriptInputPayload) {
  const lookup = new Map();
  const lines = scriptInputPayload?.lines || [];
  lines.forEach((line) => {
    lookup.set(line.line_id, line);
  });
  return lookup;
}

function getEvidenceItems(lineIds = []) {
  return (lineIds || [])
    .map((lineId) => {
      const entry = currentLineLookup.get(lineId);
      if (!entry) {
        return {
          lineId,
          text: 'Referenced line not found in the normalized input.',
        };
      }
      return {
        lineId,
        text: entry.text,
      };
    });
}

function renderEvidenceList(lineIds = []) {
  const evidenceItems = getEvidenceItems(lineIds);
  if (!evidenceItems.length) {
    return '<p class="session-snippet">No cited lines.</p>';
  }

  return `
    <div class="evidence-list">
      ${evidenceItems.map((item) => `
        <div class="evidence-row">
          <button class="evidence-chip" type="button" data-line-ids="${escapeHtml(item.lineId)}">${escapeHtml(item.lineId)}</button>
          <div class="evidence-text">${escapeHtml(item.text)}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderValidationList(items = [], emptyMessage) {
  const entries = (items || []).map((item) => String(item || '').trim()).filter(Boolean);
  if (!entries.length) {
    return `<p>${escapeHtml(emptyMessage)}</p>`;
  }

  return `
    <ul>
      ${entries.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
    </ul>
  `;
}

function buildRegenerationPrompt(validation) {
  const entries = (validation?.regeneration_instructions || [])
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  if (!entries.length) {
    return '';
  }
  return entries.map((item) => `- ${item}`).join('\n');
}

function updateValidationFixState(validation) {
  if (!applyValidationFixBtn || !validationFixNoteEl) {
    return;
  }

  if (!validation) {
    applyValidationFixBtn.disabled = true;
    validationFixNoteEl.textContent = 'No validation results yet.';
    return;
  }

  const prompt = buildRegenerationPrompt(validation);
  const instructionCount = validation.regeneration_instructions?.length || 0;
  applyValidationFixBtn.disabled = !prompt;

  if (!prompt) {
    validationFixNoteEl.textContent = 'No regeneration instructions were returned for this run.';
    return;
  }

  validationFixNoteEl.textContent = `Regeneration instructions ready - this will send ${instructionCount} instruction(s) and start a new run.`;
}

function applySelectedLines() {
  const activeIds = new Set(selectedLineIds);
  scriptLinesEl.querySelectorAll('.script-line').forEach((row) => {
    row.classList.toggle('active', activeIds.has(row.dataset.lineId));
  });
}

function highlightEvidence(lineIds = [], switchToScript = false) {
  selectedLineIds = lineIds.filter(Boolean);
  applySelectedLines();
  if (switchToScript && selectedLineIds.length) {
    activateTab('script');
    const firstLine = scriptLinesEl.querySelector(`[data-line-id="${selectedLineIds[0]}"]`);
    if (firstLine) {
      firstLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function clearEvidenceSelection() {
  selectedLineIds = [];
  applySelectedLines();
}

function setReportHeader(title, scriptInputPayload = null) {
  reportTitleEl.textContent = title;
  const heading = document.querySelector('.report-heading');
  if (heading) {
    heading.dataset.title = title;
    heading.dataset.date = new Date().toLocaleDateString();
  }

  if (!scriptInputPayload) {
    reportContextEl.textContent = 'Run an analysis to populate the report, token usage, and evidence view.';
    reportMetaEl.innerHTML = '';
    return;
  }

  reportContextEl.textContent = 'Evidence chips in the report map directly back to these normalized lines.';
  reportMetaEl.innerHTML = [
    buildHeaderMetric('format', 'Format', formatScriptFormat(scriptInputPayload.script_format)),
    buildHeaderMetric('lines', 'Lines', `${formatNumber(scriptInputPayload.lines?.length || 0)} normalized`),
    buildHeaderMetric('characters', 'Characters', `${formatNumber(scriptInputPayload.detected_characters?.length || 0)} detected`),
  ].join('');
}

function resetReport() {
  currentPayload = null;
  currentLineLookup = new Map();
  selectedLineIds = [];
  overviewEl.innerHTML = '';
  beatsEl.innerHTML = '';
  emotionsEl.innerHTML = '';
  engagementEl.innerHTML = '';
  improvementsEl.innerHTML = '';
  validationEl.innerHTML = '';
  scriptLinesEl.innerHTML = '';
  rawJsonEl.textContent = '';
  emptyOverviewEl.classList.remove('hidden');
  emptyValidationEl.classList.remove('hidden');
  updateValidationFixState(null);
  setReportHeader('No report loaded');
  setStats();
}

function renderScriptLines(scriptInputPayload) {
  const lines = scriptInputPayload?.lines || [];
  if (!lines.length) {
    scriptLinesEl.innerHTML = '<div class="empty-state"><h3>No script lines</h3><p>Normalized lines appear here after a run or when you load a saved session.</p></div>';
    return;
  }

  scriptLinesEl.innerHTML = lines.map((line) => `
    <div class="script-line" data-line-id="${escapeHtml(line.line_id)}">
      <div class="line-id">${escapeHtml(line.line_id)}</div>
      <div class="line-text">${escapeHtml(line.text)}</div>
    </div>
  `).join('');
  applySelectedLines();
}

function renderOverview(payload) {
  const report = payload.report || {};
  const engagement = payload.engagement_analysis || {};
  const validation = payload.validation;
  const tokenUsage = payload.token_usage || {};
  const topPriorities = payload.improvement_plan?.top_3_priorities || [];
  const strongestLabel = formatEnumLabel(engagement.strongest_element) || 'Not available';
  const weakestLabel = formatEnumLabel(engagement.weakest_element) || 'Not available';
  const instructionCount = validation?.regeneration_instructions?.length || 0;
  const validationLabel = validation
    ? (validation.valid ? 'Passed' : 'Failed')
    : 'Not run';
  const validationNote = validation
    ? `${validation.errors?.length || 0} errors, ${validation.warnings?.length || 0} warnings`
    : 'Validation did not run for this payload.';
  const validatorPrompt = validation && !validation.valid
    ? (instructionCount
      ? `Validator flagged issues. ${instructionCount} regeneration instruction(s) ready in Validation.`
      : 'Validator flagged issues. Use Regenerate if you want another pass with the verdict in view.')
    : 'Validator cleared the report or did not return blocking issues.';

  emptyOverviewEl.classList.add('hidden');
  overviewEl.innerHTML = `
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Summary</div>
          <h3>Scene readout</h3>
        </div>
        <div class="soft-pill">${escapeHtml(report.beat_extraction?.probable_cliffhanger_beat_id || payload.beat_extraction?.probable_cliffhanger_beat_id || 'No cliffhanger id')}</div>
      </div>
      <ul>
        ${(report.summary_3_4_lines || []).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}
      </ul>
      <div class="meta-grid">
        <div class="meta-chip">
          <strong>Strongest element</strong>
          <span>${escapeHtml(strongestLabel)}</span>
        </div>
        <div class="meta-chip">
          <strong>Weakest element</strong>
          <span>${escapeHtml(weakestLabel)}</span>
        </div>
        <div class="meta-chip">
          <strong>Validation</strong>
          <span>${escapeHtml(validationLabel)}. ${escapeHtml(validationNote)} ${escapeHtml(validatorPrompt)}</span>
        </div>
      </div>
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Priorities</div>
          <h3>Highest-impact revisions</h3>
        </div>
      </div>
      ${topPriorities.length ? `
        <ol>
          ${topPriorities.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
        </ol>
      ` : '<p>No improvement priorities were returned.</p>'}
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Tokens</div>
          <h3>Usage by stage</h3>
        </div>
      </div>
      <div class="meta-grid">
        <div class="meta-chip">
          <strong>Total</strong>
          <span>${formatNumber(tokenUsage.total_tokens)} tokens</span>
        </div>
        <div class="meta-chip">
          <strong>Input</strong>
          <span>${formatNumber(tokenUsage.input_tokens)} tokens</span>
        </div>
        <div class="meta-chip">
          <strong>Output</strong>
          <span>${formatNumber(tokenUsage.output_tokens)} tokens</span>
        </div>
        <div class="meta-chip">
          <strong>Reasoning</strong>
          <span>${formatNumber(tokenUsage.reasoning_tokens)} tokens</span>
        </div>
      </div>
      <div class="token-stage-grid">
        ${(tokenUsage.stages || []).map((stage) => `
          <div class="token-stage">
            <strong>${escapeHtml(stage.label)}</strong>
            <span>${formatNumber(stage.total_tokens)} total tokens across ${formatNumber(stage.calls)} call(s)</span>
          </div>
        `).join('')}
      </div>
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Validation notes</div>
          <h3>Errors and warnings</h3>
        </div>
      </div>
      ${validation ? `
        <div class="meta-grid">
          <div class="meta-chip">
            <strong>Errors</strong>
            <span>${escapeHtml((validation.errors || []).join(' | ') || 'None')}</span>
          </div>
          <div class="meta-chip">
            <strong>Warnings</strong>
            <span>${escapeHtml((validation.warnings || []).join(' | ') || 'None')}</span>
          </div>
        </div>
      ` : '<p>Validation did not run for this payload.</p>'}
    </article>
  `;
}

function renderValidation(payload) {
  const validation = payload?.validation;
  if (!validationEl || !emptyValidationEl) {
    return;
  }

  if (!validation) {
    validationEl.innerHTML = '';
    emptyValidationEl.classList.remove('hidden');
    updateValidationFixState(null);
    return;
  }

  const errors = validation.errors || [];
  const warnings = validation.warnings || [];
  const groundingIssues = validation.grounding_issues || [];
  const scoreIssues = validation.score_consistency_issues || [];
  const instructions = validation.regeneration_instructions || [];
  const verdictLabel = validation.valid ? 'Passed' : 'Failed';
  const verdictPill = validation.valid ? 'success' : 'error';
  const instructionPill = instructions.length ? 'warn' : 'neutral';

  emptyValidationEl.classList.add('hidden');
  validationEl.innerHTML = `
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Verdict</div>
          <h3>${escapeHtml(verdictLabel)}</h3>
        </div>
        <div class="validation-pill ${verdictPill}">${escapeHtml(verdictLabel)}</div>
      </div>
      <div class="meta-grid">
        <div class="meta-chip">
          <strong>Retryable</strong>
          <span>${validation.retryable ? 'Yes - regeneration allowed' : 'No - manual review needed'}</span>
        </div>
        <div class="meta-chip">
          <strong>Errors</strong>
          <span>${formatNumber(errors.length)}</span>
        </div>
        <div class="meta-chip">
          <strong>Warnings</strong>
          <span>${formatNumber(warnings.length)}</span>
        </div>
        <div class="meta-chip">
          <strong>Grounding issues</strong>
          <span>${formatNumber(groundingIssues.length)}</span>
        </div>
        <div class="meta-chip">
          <strong>Score consistency</strong>
          <span>${formatNumber(scoreIssues.length)}</span>
        </div>
      </div>
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Regeneration</div>
          <h3>Validator guidance</h3>
        </div>
        <div class="validation-pill ${instructionPill}">${instructions.length ? 'Instructions ready' : 'No instructions'}</div>
      </div>
      ${renderValidationList(instructions, 'No regeneration instructions were returned.')}
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Errors</div>
          <h3>Blocking issues</h3>
        </div>
      </div>
      ${renderValidationList(errors, 'No errors were reported.')}
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Warnings</div>
          <h3>Non-blocking issues</h3>
        </div>
      </div>
      ${renderValidationList(warnings, 'No warnings were reported.')}
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Grounding</div>
          <h3>Grounding issues</h3>
        </div>
      </div>
      ${renderValidationList(groundingIssues, 'No grounding issues were reported.')}
    </article>
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Scoring</div>
          <h3>Score consistency issues</h3>
        </div>
      </div>
      ${renderValidationList(scoreIssues, 'No score consistency issues were reported.')}
    </article>
  `;

  updateValidationFixState(validation);
}

function renderBeats(beats = []) {
  if (!beats.length) {
    beatsEl.innerHTML = '<div class="empty-state"><h3>No beats</h3><p>The beat extractor did not return any beats.</p></div>';
    return;
  }

  beatsEl.innerHTML = beats.map((beat) => `
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">${escapeHtml(beat.beat_id)}</div>
          <h3>${escapeHtml(beat.label)}</h3>
        </div>
        <div class="soft-pill">Tension ${escapeHtml(beat.tension_level)}</div>
      </div>
      <p>${escapeHtml(beat.short_description)}</p>
      <div class="pill-row">
        ${(beat.involved_characters || []).map((character) => `<span class="soft-pill">${escapeHtml(character)}</span>`).join('')}
      </div>
      ${renderEvidenceList(beat.evidence_line_ids)}
    </article>
  `).join('');
}

function renderEmotions(analysis = {}) {
  const dominantSceneEmotions = analysis.dominant_scene_emotions || [];
  const beatwiseArc = analysis.beatwise_arc || [];
  const cards = [];

  cards.push(`
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Overall tone</div>
          <h3>Scene emotions</h3>
        </div>
      </div>
      <p>${escapeHtml(analysis.emotional_arc_summary || 'No emotional summary returned.')}</p>
      <div class="pill-row">
        ${(analysis.overall_tone || []).map((tone) => `<span class="soft-pill">${escapeHtml(tone)}</span>`).join('')}
      </div>
      ${dominantSceneEmotions.map((emotion) => `
        <div class="meta-chip">
          <strong>${escapeHtml(emotion.emotion)} (${escapeHtml(emotion.strength)}/5)</strong>
          <span>${escapeHtml(emotion.justification)}</span>
          ${renderEvidenceList(emotion.evidence_line_ids)}
        </div>
      `).join('')}
    </article>
  `);

  beatwiseArc.forEach((shift) => {
    cards.push(`
      <article class="card">
        <div class="card-head">
          <div>
            <div class="card-kicker">${escapeHtml(shift.beat_id)}</div>
            <h3>Intensity ${escapeHtml(shift.emotional_intensity)}</h3>
          </div>
        </div>
        <p>${escapeHtml(shift.shift_from_previous)}</p>
        ${shift.dominant_emotions.map((emotion) => `
          <div class="meta-chip">
            <strong>${escapeHtml(emotion.emotion)} (${escapeHtml(emotion.strength)}/5)</strong>
            <span>${escapeHtml(emotion.justification)}</span>
            ${renderEvidenceList(emotion.evidence_line_ids)}
          </div>
        `).join('')}
      </article>
    `);
  });

  emotionsEl.innerHTML = cards.join('');
}

function renderEngagement(analysis = {}) {
  const factors = analysis.factors || [];
  const strongestLabel = formatEnumLabel(analysis.strongest_element) || 'Not available';
  const weakestLabel = formatEnumLabel(analysis.weakest_element) || 'Not available';
  if (!factors.length) {
    engagementEl.innerHTML = '<div class="empty-state"><h3>No engagement scores</h3><p>The engagement stage did not return factor scores.</p></div>';
    return;
  }

  engagementEl.innerHTML = `
    <article class="card">
      <div class="card-head">
        <div>
          <div class="card-kicker">Overall score</div>
          <h3>${escapeHtml(analysis.overall_score)} / 100</h3>
        </div>
        <div class="soft-pill">${escapeHtml(analysis.score_band || 'Unknown band')}</div>
      </div>
      <p>${escapeHtml(analysis.cliffhanger_reason || 'No cliffhanger rationale returned.')}</p>
      <div class="meta-grid">
        <div class="meta-chip">
          <strong>Strongest</strong>
          <span>${escapeHtml(strongestLabel)}</span>
        </div>
        <div class="meta-chip">
          <strong>Weakest</strong>
          <span>${escapeHtml(weakestLabel)}</span>
        </div>
        <div class="meta-chip">
          <strong>Cliffhanger line</strong>
          <span>${escapeHtml(analysis.cliffhanger_moment_text || 'Not available')}</span>
        </div>
      </div>
    </article>
    ${factors.map((factor) => `
      <article class="card">
        <div class="card-head">
          <div>
            <div class="card-kicker">${escapeHtml(formatEnumLabel(factor.factor) || factor.factor)}</div>
            <h3>${escapeHtml(factor.score)} / 10</h3>
          </div>
          <div class="soft-pill">Weighted ${escapeHtml(factor.weighted_score)}</div>
        </div>
        <p>${escapeHtml(factor.reasoning)}</p>
        ${renderEvidenceList(factor.evidence_line_ids)}
      </article>
    `).join('')}
  `;
}

function renderImprovements(plan = {}) {
  const suggestions = plan.suggestions || [];
  if (!suggestions.length) {
    improvementsEl.innerHTML = '<div class="empty-state"><h3>No improvement plan</h3><p>The critique stage did not return rewrite suggestions.</p></div>';
    return;
  }

  improvementsEl.innerHTML = `
    ${plan.optional_stronger_opening ? `
      <article class="card">
        <div class="card-head">
          <div>
            <div class="card-kicker">Optional opening</div>
            <h3>Alternative start</h3>
          </div>
        </div>
        <p>${escapeHtml(plan.optional_stronger_opening)}</p>
      </article>
    ` : ''}
    ${suggestions.map((item) => `
      <article class="card">
        <div class="card-head">
          <div>
            <div class="card-kicker">${escapeHtml(item.target_area)}</div>
            <h3>${escapeHtml(item.issue)}</h3>
          </div>
        </div>
        <p>${escapeHtml(item.why_it_hurts_engagement)}</p>
        <div class="meta-chip">
          <strong>Concrete fix</strong>
          <span>${escapeHtml(item.concrete_fix)}</span>
        </div>
        ${item.example_rewrite ? `
          <div class="meta-chip">
            <strong>Example rewrite</strong>
            <span>${escapeHtml(item.example_rewrite)}</span>
          </div>
        ` : ''}
        ${renderEvidenceList(item.target_line_ids)}
      </article>
    `).join('')}
  `;
}

function updateReportStats(payload) {
  const validation = payload.validation;
  const validationLabel = validation
    ? (validation.valid ? 'Passed' : 'Failed')
    : 'Not run';
  const validationNote = validation
    ? `${validation.errors?.length || 0} errors, ${validation.warnings?.length || 0} warnings`
    : 'No validator verdict available.';
  const tokenUsage = payload.token_usage || {};
  const title = titleInput.value || currentPayload?.script_input?.title || 'Untitled';

  setStats({
    tokens: formatNumber(tokenUsage.total_tokens || payload.tokens_used || 0),
    tokensNote: `${formatNumber(tokenUsage.input_tokens || 0)} in / ${formatNumber(tokenUsage.output_tokens || 0)} out`,
    iterations: formatNumber(payload.iterations || 0),
    iterationsNote: 'Completed passes',
    validation: validationLabel,
    validationNote,
    session: title || 'Draft',
    sessionNote: currentSessionId ? `ID: ${currentSessionId.slice(0, 8)}` : 'Unsaved copy',
  });
}

function renderResult(payload) {
  currentPayload = payload;
  currentLineLookup = buildLineLookup(payload.script_input);
  clearEvidenceSelection();
  setMode('complete');
  setReportHeader(payload.script_input?.title || titleInput.value || 'Current report', payload.script_input || null);
  updateReportStats(payload);
  renderOverview(payload);
  renderBeats(payload.beat_extraction?.beats || []);
  renderEmotions(payload.emotion_analysis || {});
  renderEngagement(payload.engagement_analysis || {});
  renderImprovements(payload.improvement_plan || {});
  renderValidation(payload);
  renderScriptLines(payload.script_input || {});
  rawJsonEl.textContent = JSON.stringify(payload, null, 2);
}

async function createSession() {
  const title = titleInput.value || null;
  const response = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  const data = await response.json();
  setSessionId(data.session_id);
  syncFeedView();
  await refreshSessions();
  setStatus('Ready', 'Session created.', 'idle');
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
    body: JSON.stringify({ title, raw_text }),
  });
}

async function saveRegeneration() {
  const regeneration_prompt = regenInput.value || '';
  if (!regeneration_prompt || !currentSessionId) {
    return;
  }
  await fetch(`/api/sessions/${currentSessionId}/regeneration`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ regeneration_prompt }),
  });
}

async function runValidationFix() {
  const validation = currentPayload?.validation;
  if (!validation) {
    addChatMessage('No validation output to apply yet.', 'system');
    return;
  }

  const prompt = buildRegenerationPrompt(validation);
  if (!prompt) {
    addChatMessage('No regeneration instructions were returned by the validator.', 'system');
    return;
  }

  regenInput.value = prompt;
  feedbackBlock.classList.remove('hidden');
  await saveInput();
  await saveConfig();
  await saveRegeneration();
  addChatMessage('Validator guidance applied. Regenerating now.', 'user');
  startStream('regenerate');
}

async function saveConfig() {
  if (!currentSessionId) {
    return;
  }
  const payload = {
    model: cfgModel.value || null,
    temperature: parseFloat(cfgTemperature.value),
    max_iterations: parseInt(cfgIterations.value, 10),
  };
  await fetch(`/api/sessions/${currentSessionId}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

function closeCurrentSource() {
  if (currentSource) {
    currentSource.close();
    currentSource = null;
  }
}

function startStream(mode) {
  closeCurrentSource();
  resetReport();
  setMode('running');
  setStatus('Running', 'Streaming backend progress.', 'running');
  setProgress('start', 'starting', true);
  addChatMessage(`Mode: ${mode}.`, 'system');

  currentSource = new EventSource(`/api/sessions/${currentSessionId}/stream?mode=${mode}`);

  currentSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    const detailBits = [];
    if (data.iteration) {
      detailBits.push(`iteration ${data.iteration}`);
    }
    if (data.tokens) {
      detailBits.push(`${formatNumber(data.tokens)} tokens`);
    }
    const label = STAGE_LABELS[data.stage] || data.stage || 'Working';
    setProgress(data.stage, data.status, true);
    setStatus('Running', `${label}${data.status ? ` - ${data.status}` : ''}`, 'running');
    addChatMessage(`${data.stage} - ${data.status}${detailBits.length ? ` (${detailBits.join(', ')})` : ''}`, 'system');
  });

  currentSource.addEventListener('result', (event) => {
    const payload = JSON.parse(event.data);
    renderResult(payload);
    setProgress('', '', false);
    if (payload.validation && payload.validation.valid === false) {
      setStatus('Review', `Validator flagged issues after ${formatNumber(payload.iterations)} iteration(s).`, 'error');
      addChatMessage('Analysis complete, but the validator found issues. Use Regenerate if you want another pass.', 'system');
    } else {
      setStatus('Complete', `Completed ${formatNumber(payload.iterations)} iteration(s).`, 'complete');
      addChatMessage('Analysis complete.', 'system');
    }
    refreshSessions();
  });

  currentSource.addEventListener('error', (event) => {
    if (!event.data) {
      return;
    }
    let payload = { message: 'Analysis failed.' };
    try {
      payload = JSON.parse(event.data);
    } catch (error) {
      payload = { message: 'Analysis failed.' };
    }
    setStatus('Error', payload.message || 'Analysis failed.', 'error');
    addChatMessage(payload.message || 'Analysis failed.', 'system');
    setMode('draft');
    setProgress('', '', false);
    closeCurrentSource();
  });

  currentSource.addEventListener('done', () => {
    closeCurrentSource();
  });

  currentSource.onerror = () => {
    if (currentSource && currentSource.readyState === EventSource.CLOSED) {
      closeCurrentSource();
    }
  };
}

function renderSessionList(sessions) {
  sessionListEl.innerHTML = '';

  const draft = document.createElement('div');
  draft.className = `session-item ${currentSessionId ? '' : 'active'}`;
  draft.innerHTML = `
    <div class="session-row">
      <div class="session-main">
        <div class="session-title">New draft</div>
        <div class="session-snippet">Start a fresh analysis</div>
        <div class="session-meta">
          <span class="session-status">draft</span>
        </div>
      </div>
    </div>
  `;
  draft.addEventListener('click', () => {
    setSessionId(null);
    syncFeedView();
    titleInput.value = '';
    scriptInput.value = '';
    regenInput.value = '';
    applyConfig();
    resetReport();
    setMode('draft');
    setStatus('Draft', 'Working on a new unsaved script.', 'idle');
    setStats();
  });
  sessionListEl.appendChild(draft);

  sessions.forEach((session) => {
    const item = document.createElement('div');
    item.className = `session-item ${session.session_id === currentSessionId ? 'active' : ''}`;
    item.innerHTML = `
      <div class="session-row">
        <div class="session-main">
          <div class="session-title">${escapeHtml(session.title || session.snippet || 'Untitled session')}</div>
          <div class="session-snippet">${escapeHtml(session.snippet || 'No script yet')}</div>
          <div class="session-meta">
            <span class="session-status">${escapeHtml(session.status || 'idle')}</span>
            <span class="session-time">${escapeHtml(formatDateTime(session.updated_at, true))}</span>
          </div>
        </div>
        <button class="session-delete" type="button" aria-label="Delete session">✕</button>
      </div>
    `;
    item.addEventListener('click', async () => {
      await loadSession(session.session_id);
    });
    item.querySelector('.session-delete').addEventListener('click', async (event) => {
      event.stopPropagation();
      await fetch(`/api/sessions/${session.session_id}`, { method: 'DELETE' });
      if (session.session_id === currentSessionId) {
        setSessionId(null);
        syncFeedView();
        titleInput.value = '';
        scriptInput.value = '';
        regenInput.value = '';
        applyConfig();
        resetReport();
        setMode('draft');
        setStatus('Draft', 'Session deleted.', 'idle');
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

function buildPayloadFromSession(data) {
  if (!data.last_report_json) {
    return null;
  }

  return {
    script_input: data.script_input || null,
    iterations: data.iterations || 0,
    tokens_used: data.tokens_used || 0,
    token_usage: data.token_usage || null,
    report: JSON.parse(data.last_report_json),
    validation: data.last_validation_json ? JSON.parse(data.last_validation_json) : null,
    engagement_analysis: data.last_engagement_json ? JSON.parse(data.last_engagement_json) : null,
    beat_extraction: data.last_beat_json ? JSON.parse(data.last_beat_json) : null,
    emotion_analysis: data.last_emotion_json ? JSON.parse(data.last_emotion_json) : null,
    improvement_plan: data.last_improvement_json ? JSON.parse(data.last_improvement_json) : null,
  };
}

async function loadSession(sessionId) {
  const response = await fetch(`/api/sessions/${sessionId}`);
  const data = await response.json();
  setSessionId(sessionId);
  syncFeedView();
  titleInput.value = data.title || '';
  scriptInput.value = data.raw_text || '';
  regenInput.value = data.regeneration_prompt || '';
  applyConfig(data.config || {});

  const payload = buildPayloadFromSession(data);
  if (payload) {
    renderResult(payload);
    setMode('complete');
  } else {
    resetReport();
    renderScriptLines(data.script_input || {});
    setMode('draft');
  }

  const sessionState = payload?.validation && payload.validation.valid === false
    ? 'error'
    : (data.status === 'error' ? 'error' : (payload ? 'complete' : 'idle'));
  const sessionLabel = payload?.validation && payload.validation.valid === false
    ? 'Review'
    : capitalize(data.status);

  setStatus(
    sessionLabel,
    `Updated ${formatDateTime(data.updated_at)}`,
    sessionState
  );
  setStats({
    tokens: formatNumber(data.token_usage?.total_tokens || data.tokens_used || 0),
    tokensNote: data.token_usage ? `${formatNumber(data.token_usage.input_tokens || 0)} in / ${formatNumber(data.token_usage.output_tokens || 0)} out` : 'No run yet',
    iterations: formatNumber(data.iterations || 0),
    iterationsNote: payload ? 'Saved result' : 'No run yet',
    validation: payload?.validation ? (payload.validation.valid ? 'Passed' : 'Failed') : '\u2014',
    validationNote: payload?.validation ? `${payload.validation.errors?.length || 0} errors, ${payload.validation.warnings?.length || 0} warnings` : (payload ? 'No verdict available' : 'No report yet'),
    session: data.title || 'Untitled',
    sessionNote: formatDateTime(data.updated_at, true),
  });
  refreshSessions();
}

document.addEventListener('click', (event) => {
  const evidenceButton = event.target.closest('[data-line-ids]');
  if (!evidenceButton) {
    return;
  }
  const ids = (evidenceButton.dataset.lineIds || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  if (ids.length) {
    highlightEvidence(ids, true);
  }
});

clearEvidenceBtn.addEventListener('click', () => {
  clearEvidenceSelection();
});

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

if (applyValidationFixBtn) {
  applyValidationFixBtn.addEventListener('click', async () => {
    await runValidationFix();
  });
}

cfgIterations.addEventListener('input', () => {
  if (cfgIterationsValue) {
    cfgIterationsValue.textContent = cfgIterations.value;
  }
});

cfgTemperature.addEventListener('input', () => {
  cfgTemperatureValue.textContent = Number(cfgTemperature.value).toFixed(2);
});

cfgModel.addEventListener('change', () => {
  updateModelNote();
});

if (exportPdfBtn) {
  exportPdfBtn.addEventListener('click', () => {
    if (!currentPayload) {
      addChatMessage('No report loaded yet. Run an analysis first.', 'system');
      return;
    }
    window.print();
  });
}

// ─── Sidebar Toggle ─────────────────────────────────────────────
const sidebarEl = document.getElementById('sidebar');
const sidebarToggleBtn = document.getElementById('sidebar-toggle');
const SIDEBAR_COLLAPSED_KEY = 'scriptpulse_sidebar_collapsed';

function setSidebarCollapsed(collapsed) {
  if (collapsed) {
    sidebarEl.classList.add('collapsed');
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, '1');
  } else {
    sidebarEl.classList.remove('collapsed');
    localStorage.removeItem(SIDEBAR_COLLAPSED_KEY);
  }
}

if (sidebarToggleBtn) {
  sidebarToggleBtn.addEventListener('click', () => {
    setSidebarCollapsed(!sidebarEl.classList.contains('collapsed'));
  });
}

if (localStorage.getItem(SIDEBAR_COLLAPSED_KEY)) {
  setSidebarCollapsed(true);
}

// ─── Initialize ─────────────────────────────────────────────────
async function initialize() {
  resetReport();
  applyConfig();
  setMode('draft');
  syncFeedView();
  await refreshSessions();

  // Position tab indicator at the initial active tab
  requestAnimationFrame(() => positionTabIndicator('overview'));

  const savedSessionId = localStorage.getItem('scriptpulse_session');
  if (savedSessionId) {
    try {
      await loadSession(savedSessionId);
    } catch (error) {
      setSessionId(null);
      applyConfig();
      setStatus('Idle', 'Waiting for script input.', 'idle');
    }
  } else {
    setStatus('Idle', 'Waiting for script input.', 'idle');
  }
}

initialize();