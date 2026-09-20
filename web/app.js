const $ = (id) => document.getElementById(id);

let activeRun = null;
let runTimer = null;
let dashboardTimer = null;

const PODS = [
  {actor: 'aidlc-api', legacy: 'api', label: 'API', role: 'Request intake / 请求接入'},
  {actor: 'hermes-orchestrator', label: 'Orchestrator', role: 'Plan & dispatch / 规划分派'},
  {actor: 'hermes-sf-dev', label: 'Dev Agent', role: 'GLM + implementation / 开发'},
  {actor: 'hermes-sf-qa', label: 'QA Agent', role: 'Deterministic tests / 测试'},
  {actor: 'hermes-sf-review', label: 'Review Agent', role: 'Code & security / 评审'},
  {actor: 'hermes-sf-deploy', label: 'Deploy Agent', role: 'Build • SWR • CCE / 构建与部署'},
];

async function json(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    throw new Error('Authentication expired. Reopen the page and sign in again. / 登录已过期，请重新打开页面并登录。');
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function formatTime(value, includeDate = false) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const options = includeDate
    ? {month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false}
    : {hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3, hour12: false};
  return new Intl.DateTimeFormat('en-GB', options).format(date);
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(Number(value || 0));
}

function formatDuration(seconds) {
  const value = Number(seconds || 0);
  if (value < 60) return `${value.toFixed(value < 10 ? 1 : 0)}s`;
  const minutes = Math.floor(value / 60);
  return `${minutes}m ${Math.round(value % 60)}s`;
}

function tone(value) {
  const text = String(value || '').toUpperCase();
  if (['PASS', 'COMPLETED', 'ALLOW_PR', 'ALLOW_PREVIEW', 'OK'].some((item) => text.includes(item))) return 'success';
  if (['DENY', 'FAILED', 'ERROR'].some((item) => text.includes(item))) return 'error';
  if (['START', 'DISPATCH', 'RUNNING', 'DEVELOPMENT', 'TESTING', 'REVIEW', 'DEPLOYMENT', 'PLANNING'].some((item) => text.includes(item))) return 'running';
  return 'neutral';
}

function setFeedback(message, state = '') {
  $('run-feedback').textContent = message;
  $('run-feedback').className = `run-feedback ${state}`.trim();
}

function resetButton() {
  $('run').disabled = false;
  $('run').textContent = 'Run Full AIDLC / 运行完整 AIDLC';
}

function renderMetrics(dashboard) {
  const summary = dashboard.summary;
  $('metric-total').textContent = formatNumber(summary.total_runs);
  $('metric-completed').textContent = formatNumber(summary.completed_runs);
  $('metric-active').textContent = `${summary.active_runs} active / 运行中`;
  $('metric-success').textContent = `${summary.success_rate}%`;
  $('metric-failed').textContent = `${summary.failed_runs} failed / 失败`;
  $('metric-tokens').textContent = formatNumber(summary.total_tokens);
  $('metric-token-detail').textContent = `${formatNumber(summary.prompt_tokens)} prompt · ${formatNumber(summary.completion_tokens)} completion`;
  $('metric-duration').textContent = formatDuration(summary.average_duration_seconds);
  $('metric-events').textContent = formatNumber(dashboard.runs.reduce((total, run) => total + run.event_count, 0));
  $('last-refresh').textContent = `Updated ${formatTime(dashboard.generated_at)} / 更新于 ${formatTime(dashboard.generated_at)}`;
}

function renderHistory(runs) {
  if (!runs.length) {
    $('history-body').innerHTML = '<tr><td colspan="8">No runs yet / 暂无任务</td></tr>';
    return;
  }
  $('history-body').innerHTML = runs.map((run) => {
    const selected = run.run_id === activeRun ? ' selected' : '';
    const pr = run.pull_request?.url
      ? `<a href="${escapeHtml(run.pull_request.url)}" target="_blank" rel="noreferrer">#${escapeHtml(run.pull_request.number)}</a>`
      : '—';
    return `<tr class="${selected}">
      <td><button class="run-link" data-run-id="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)}</button></td>
      <td>${formatTime(run.created_at, true)}</td>
      <td><span class="table-badge ${tone(run.status)}">${escapeHtml(run.status)}</span></td>
      <td>${escapeHtml(run.final_decision || '—')}</td>
      <td>${formatDuration(run.duration_seconds)}</td>
      <td>${formatNumber(run.event_count)}</td>
      <td>${formatNumber(run.tokens.total_tokens)}</td>
      <td>${pr}</td>
    </tr>`;
  }).join('');
}

function renderPods(run) {
  const events = run?.events || [];
  $('pod-grid').innerHTML = PODS.map((pod) => {
    const podEvents = events.filter((event) => event.actor === pod.actor || event.actor === pod.legacy);
    const latest = podEvents[podEvents.length - 1];
    const isRunning = run && !['COMPLETED', 'FAILED'].includes(run.status) && run.current_agent === pod.actor;
    let state = 'WAITING';
    if (isRunning) state = 'RUNNING';
    else if (latest) state = ['DENY', 'ERROR'].includes(latest.result) ? 'FAILED' : 'COMPLETED';
    const host = latest?.pod || 'No pod event yet / 暂无 Pod 事件';
    return `<article class="pod-card ${tone(state)}">
      <div class="pod-card-head"><span class="pod-indicator"></span><strong>${pod.label}</strong><em>${state}</em></div>
      <p>${pod.role}</p>
      <code title="${escapeHtml(host)}">${escapeHtml(host)}</code>
      <small>${latest ? `${formatTime(latest.at)} · ${escapeHtml(latest.stage)}` : 'Waiting / 等待中'}</small>
    </article>`;
  }).join('');
}

function renderConsole(run) {
  const events = run.events || [];
  $('console-run-id').textContent = `${run.run_id} · ${run.status}`;
  if (!events.length) {
    $('events').innerHTML = '<div class="console-empty">Waiting for run events… / 等待任务事件…</div>';
    return;
  }
  $('events').innerHTML = events.map((event, index) => {
    const metadata = event.metadata || {};
    const task = metadata.task_id ? `<small>${escapeHtml(metadata.task_id)}</small>` : '';
    return `<div class="console-line ${tone(event.result)}">
      <time>${formatTime(event.at)}</time>
      <span class="sequence">#${String(event.sequence || index + 1).padStart(2, '0')}</span>
      <span class="console-pod" title="${escapeHtml(event.pod || event.actor)}">${escapeHtml(event.actor)}<small>${escapeHtml(event.pod || '')}</small></span>
      <span>${escapeHtml(event.stage)}</span>
      <span class="result-chip">${escapeHtml(event.result)}</span>
      <span class="console-detail">${escapeHtml(event.detail)}${task}</span>
    </div>`;
  }).join('');
  $('events').scrollTop = $('events').scrollHeight;
}

function renderRun(run) {
  const actor = run.current_agent || 'hermes-orchestrator';
  $('status').textContent = `${run.run_id} · ${run.status} · ${actor}`;
  $('status').className = `status-pill ${tone(run.status)}`;
  renderPods(run);
  renderConsole(run);
}

function evidenceCard(title, value, detail, state = 'neutral') {
  return `<article class="evidence-item ${state}">
    <span>${escapeHtml(title)}</span>
    <strong>${escapeHtml(value || '\u2014')}</strong>
    <small title="${escapeHtml(detail || '')}">${escapeHtml(detail || '\u2014')}</small>
  </article>`;
}

function renderEvidenceSummary(evidence, run) {
  const results = evidence.results || run.results || {};
  const dev = results.dev || {};
  const qa = results.qa || {};
  const review = results.review || {};
  const deploy = results.deploy || {};
  const delivery = deploy.outputs?.delivery || {};
  const registry = delivery.registry || {};
  const runtime = delivery.runtime || {};
  const smoke = delivery.smoke_test || {};
  const source = delivery.source || dev.outputs || {};
  const pr = evidence.pull_request || run.pull_request || {};
  const decision = evidence.final_decision || run.final_decision || run.status;
  const realDelivery = delivery.mode === 'real';
  const cards = [
    evidenceCard('Source / \u6e90\u7801', source.commit ? source.commit.slice(0, 12) : 'Pending', source.branch || run.request?.base_branch, source.commit ? 'success' : 'running'),
    evidenceCard('QA Gate / \u6d4b\u8bd5\u95e8\u7981', qa.passed ? 'PASS' : (qa.passed === false ? 'DENY' : 'Pending'), qa.summary, qa.passed ? 'success' : (qa.passed === false ? 'error' : 'running')),
    evidenceCard('Security / \u5b89\u5168\u8bc4\u5ba1', review.passed ? 'PASS' : (review.passed === false ? 'DENY' : 'Pending'), review.summary, review.passed ? 'success' : (review.passed === false ? 'error' : 'running')),
    evidenceCard('Image Build / \u955c\u50cf\u6784\u5efa', realDelivery ? 'KANIKO PASS' : 'Pending', delivery.build?.job, realDelivery ? 'success' : 'running'),
    evidenceCard('Huawei Cloud SWR', registry.digest ? 'PUSHED' : 'Pending', registry.digest || registry.image, registry.digest ? 'success' : 'running'),
    evidenceCard('CCE Rollout / CCE \u53d1\u5e03', runtime.pod ? 'READY' : 'Pending', runtime.pod || runtime.deployment, runtime.pod ? 'success' : 'running'),
    evidenceCard('Smoke Test / \u5192\u70df\u6d4b\u8bd5', smoke.passed ? 'PASS' : 'Pending', smoke.passed ? 'Health + functional + idempotency' : '', smoke.passed ? 'success' : 'running'),
    evidenceCard('GitHub PR', pr.number ? `#${pr.number}` : 'Pending', pr.url, pr.number ? 'success' : 'running'),
  ];
  const actions = [];
  if (pr.url) actions.push(`<a href="${escapeHtml(pr.url)}" target="_blank" rel="noreferrer">Open Pull Request / \u6253\u5f00 PR</a>`);
  if (runtime.preview_path) actions.push(`<a href="${escapeHtml(runtime.preview_path)}" target="_blank" rel="noreferrer">Open Live Preview / \u6253\u5f00\u771f\u5b9e\u9884\u89c8</a>`);
  $('evidence-summary').innerHTML = `
    <div class="evidence-decision ${tone(decision)}">
      <div><span>Final Decision / \u6700\u7ec8\u51b3\u7b56</span><strong>${escapeHtml(decision || 'IN PROGRESS')}</strong></div>
      <div class="evidence-actions">${actions.join('')}</div>
    </div>
    <div class="evidence-grid">${cards.join('')}</div>
    ${registry.image ? `<div class="evidence-path"><b>Image / \u955c\u50cf</b><code>${escapeHtml(registry.image)}</code><b>Digest</b><code>${escapeHtml(registry.digest)}</code></div>` : ''}
  `;
}

async function loadEvidence(run) {
  let evidence = run;
  if (run.status === 'COMPLETED') {
    try {
      evidence = await json(`/api/runs/${run.run_id}/evidence`);
    } catch (error) {
      evidence = run;
    }
  }
  renderEvidenceSummary(evidence, run);
  $('result').textContent = JSON.stringify(evidence, null, 2);
}

async function pollRun(loadFinalEvidence = true) {
  if (!activeRun) return;
  try {
    const run = await json(`/api/runs/${activeRun}`);
    renderRun(run);
    setFeedback(`${run.run_id}: ${run.status} · ${run.current_agent || 'hermes-orchestrator'}`, tone(run.status));
    if (['COMPLETED', 'FAILED'].includes(run.status)) {
      clearInterval(runTimer);
      runTimer = null;
      resetButton();
      if (loadFinalEvidence) await loadEvidence(run);
    }
  } catch (error) {
    clearInterval(runTimer);
    runTimer = null;
    resetButton();
    setFeedback(`Status update failed / 状态更新失败: ${error.message}`, 'error');
  }
}

async function refreshDashboard() {
  try {
    const dashboard = await json('/api/dashboard');
    renderMetrics(dashboard);
    renderHistory(dashboard.runs);
    if (!activeRun && dashboard.runs.length) {
      activeRun = dashboard.runs[0].run_id;
      await pollRun(true);
    }
  } catch (error) {
    $('last-refresh').textContent = `Dashboard unavailable / 统计不可用: ${error.message}`;
  }
}

async function selectRun(runId) {
  activeRun = runId;
  await pollRun(true);
  await refreshDashboard();
}

async function run() {
  if ($('run').disabled) return;
  const payload = {
    repository: $('repository').value,
    base_branch: $('branch').value,
    requirement_file: $('requirement').value,
    execution_mode: 'live',
    skill_profile: 'openspec-core+aidlc-demo',
    model: 'glm-5.2',
  };
  $('run').disabled = true;
  $('run').textContent = 'Submitting… / 正在提交…';
  setFeedback('Submitting the AIDLC run… / 正在提交 AIDLC 任务…', 'running');
  try {
    const data = await json('/api/runs', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    });
    activeRun = data.run_id;
    $('run').textContent = 'Running… / 运行中…';
    setFeedback(`${activeRun}: QUEUED / 已进入队列`, 'running');
    clearInterval(runTimer);
    runTimer = setInterval(() => pollRun(false), 1500);
    await pollRun(false);
    await refreshDashboard();
  } catch (error) {
    setFeedback(error.message, 'error');
    resetButton();
  }
}

async function boot() {
  try {
    const health = await json('/health');
    $('health').textContent = health.status === 'ok' ? 'Healthy / 健康' : 'Degraded / 降级';
    $('health').className = `badge ${health.status === 'ok' ? 'ok' : ''}`;
    const architecture = await json('/api/architecture');
    $('skills').innerHTML = architecture.skills
      .map((skill) => `<span class="skill">${escapeHtml(skill.name)} · ${escapeHtml(skill.source)}</span>`)
      .join('');
    await refreshDashboard();
    dashboardTimer = setInterval(refreshDashboard, 4000);
  } catch (error) {
    $('health').textContent = 'Unavailable / 不可用';
    setFeedback(error.message, 'error');
  }
}

$('run').addEventListener('click', run);
$('history-body').addEventListener('click', (event) => {
  const button = event.target.closest('[data-run-id]');
  if (button) selectRun(button.dataset.runId);
});
$('toggle-raw').addEventListener('click', () => {
  $('result').classList.toggle('raw-hidden');
  $('toggle-raw').textContent = $('result').classList.contains('raw-hidden')
    ? 'Show Raw Evidence JSON / \u5c55\u5f00\u539f\u59cb\u8bc1\u636e'
    : 'Hide Raw Evidence JSON / \u6536\u8d77\u539f\u59cb\u8bc1\u636e';
});
setInterval(() => {$('live-clock').textContent = formatTime(new Date().toISOString());}, 1000);
boot();
