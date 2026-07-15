const form = document.querySelector('#chat-form');
const input = document.querySelector('#query');
const messages = document.querySelector('#messages');
const send = document.querySelector('#send');
const trace = document.querySelector('#trace');
const metrics = document.querySelector('#metrics');
const summary = document.querySelector('#task-summary');
const turnState = document.querySelector('#turn-state');
const player = document.querySelector('#player');
const playerCopy = document.querySelector('#player-copy');
const demoAudio = document.querySelector('#demo-audio-element');
const senderId = (() => {
  const key = 'voiceagent-mcp-session-id';
  const existing = sessionStorage.getItem(key);
  if (existing) return existing;
  const suffix = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const value = `console-${suffix}`;
  sessionStorage.setItem(key, value);
  return value;
})();
const cockpit = document.querySelector('#cockpit');
const cockpitState = document.querySelector('#cockpit-state');
const navigation = document.querySelector('#navigation');
const routeCopy = document.querySelector('#route-copy');
const routeActions = document.querySelector('#route-actions');
const routeMetrics = document.querySelector('#route-metrics');
const routeMapElement = document.querySelector('#route-map');
let activeArtist = '';
let activeSong = '';
let demoAudioPlaying = false;
let pendingDestination = null;
let nearbyRequest = null;
let nearbyOrigin = null;
let amapMap = null;
let executionStageTimer = null;
let activeRoute = null;

document.querySelectorAll('.prompt').forEach((button) => button.addEventListener('click', () => {
  input.value = button.dataset.prompt;
  turnState.textContent = '\u5df2\u586b\u5165\u8349\u7a3f\uff0c\u53ef\u7f16\u8f91\u540e\u53d1\u9001';
  input.focus();
}));

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) return;
  appendMessage('user', query);
  input.value = '';
  send.disabled = true;
  renderPendingExecution();
  turnState.textContent = '执行中';
  try {
    const response = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, sender_id: senderId }) });
    const payload = await response.json().catch(() => ({ error: '\u672c\u5730\u670d\u52a1\u8fd4\u56de\u4e86\u65e0\u6548\u54cd\u5e94' }));
    if (!response.ok) throw new Error(payload.error || '请求失败');
    const frames = payload.frames || [];
    const answer = frames.map((frame) => frame.content || '').join('');
    const final = frames.at(-1) || { metadata: {} };
    appendMessage('assistant', answer || '任务已处理。');
    renderExecution(final);
  } catch (error) {
    const message = error instanceof TypeError
      ? '\u65e0\u6cd5\u8fde\u63a5\u672c\u5730 Agent \u670d\u52a1\uff0c\u8bf7\u5237\u65b0\u9875\u9762\u540e\u91cd\u8bd5\u3002'
      : error.message;
    appendMessage('assistant', `请求未完成：${message}`);
    summary.textContent = '请求失败';
  } finally {
    clearPendingExecution();
    send.disabled = false;
    turnState.textContent = '等待输入';
    input.focus();
  }
});

function renderPendingExecution() {
  clearPendingExecution();
  summary.textContent = '\u4efb\u52a1\u6267\u884c\u4e2d';
  turnState.textContent = '\u6b63\u5728\u83b7\u53d6\u771f\u5b9e\u6267\u884c Trace';
  const stages = [
    '\u672c\u5730 Reject \u4e0e Intent BERT \u8bc6\u522b',
    'DeepSeek Function Calling \u5de5\u5177\u51b3\u7b56',
    'MCP \u5de5\u5177\u8c03\u7528\u4e0e\u7ed3\u679c\u6574\u5408',
  ];
  let activeStage = 0;
  const render = () => {
    trace.innerHTML = stages.map((stage, index) => {
      const state = index < activeStage ? 'complete' : index === activeStage ? 'active' : 'idle';
      const suffix = index === activeStage ? '\u4e2d...' : index < activeStage ? '\u5df2\u5b8c\u6210' : '\u7b49\u5f85\u4e2d';
      return `<li><span class="dot ${state}"></span><span>${stage} / ${suffix}</span></li>`;
    }).join('');
  };
  render();
  executionStageTimer = window.setInterval(() => {
    activeStage = Math.min(activeStage + 1, stages.length - 1);
    render();
  }, 650);
}

function clearPendingExecution() {
  if (executionStageTimer !== null) {
    window.clearInterval(executionStageTimer);
    executionStageTimer = null;
  }
}

function appendMessage(role, text) {
  const article = document.createElement('article');
  article.className = `message ${role}`;
  article.innerHTML = `<div class="avatar">${role === 'user' ? 'YOU' : 'VA'}</div><div class="bubble"></div>`;
  article.querySelector('.bubble').textContent = text;
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function appendMusicChoices(artist, song) {
  const article = document.createElement('article');
  article.className = 'message assistant music-choice';
  article.innerHTML = '<div class="avatar">VA</div><div class="bubble"><div class="music-choice-copy"></div><div class="music-choice-actions"><button type="button" data-music-choice="qq-music"></button><button type="button" data-music-choice="netease-music"></button><button type="button" data-music-choice="demo_audio_play"></button></div></div>';
  const target = [artist, song].filter(Boolean).join(' ');
  article.querySelector('.music-choice-copy').textContent = target
    ? `${target}\u9700\u8981\u4f60\u4e3b\u52a8\u9009\u62e9\u64ad\u653e\u5e73\u53f0\u3002`
    : '\u8bf7\u9009\u62e9\u64ad\u653e\u65b9\u5f0f\u3002';
  const [qqMusic, neteaseMusic, localDemo] = article.querySelectorAll('[data-music-choice]');
  qqMusic.textContent = '\u6253\u5f00 QQ \u97f3\u4e50\u7cbe\u786e\u641c\u7d22';
  neteaseMusic.textContent = '\u6253\u5f00\u7f51\u6613\u4e91\u97f3\u4e50\u7cbe\u786e\u641c\u7d22';
  localDemo.textContent = '\u64ad\u653e\u7ad9\u5185\u539f\u521b\u6f14\u793a\u97f3\u9891';
  qqMusic.addEventListener('click', () => {
    openThirdParty('qq-music', artist, song);
    submitMusicChoice('QQ\u97f3\u4e50\u641c\u7d22');
  });
  neteaseMusic.addEventListener('click', () => {
    openThirdParty('netease-music', artist, song);
    submitMusicChoice('\u7f51\u6613\u4e91\u97f3\u4e50\u641c\u7d22');
  });
  localDemo.addEventListener('click', () => {
    startDemoAudio();
    submitMusicChoice('\u7ad9\u5185\u6f14\u793a\u97f3\u9891\u64ad\u653e');
  });
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function submitMusicChoice(choice) {
  input.value = choice;
  form.requestSubmit();
}

function showNavigationChoices(toolResult) {
  const destination = toolResult.pois?.[0];
  if (!destination?.location) return;
  pendingDestination = destination;
  navigation.classList.remove('hidden');
  routeMetrics.classList.add('hidden');
  routeMapElement.classList.add('hidden');
  routeCopy.textContent = `\u5df2\u786e\u8ba4\u76ee\u7684\u5730\uff1a${destination.name}\u3002\u8bf7\u9009\u62e9\u8d77\u70b9\u65b9\u5f0f\u3002`;
  routeActions.innerHTML = '<button type="button" data-route-action="location"></button><button type="button" data-route-action="manual"></button>';
  const locationButton = routeActions.querySelector('[data-route-action="location"]');
  const manualButton = routeActions.querySelector('[data-route-action="manual"]');
  locationButton.textContent = '\u4f7f\u7528\u5f53\u524d\u4f4d\u7f6e';
  manualButton.textContent = '\u624b\u52a8\u8f93\u5165\u8d77\u70b9';
  locationButton.addEventListener('click', useCurrentLocation);
  manualButton.addEventListener('click', showManualOriginInput);
}

function showNearbyLocationChoices(toolResult) {
  nearbyRequest = toolResult;
  nearbyOrigin = null;
  navigation.classList.remove('hidden');
  routeMetrics.classList.add('hidden');
  routeMapElement.classList.add('hidden');
  routeCopy.textContent = `\u8981\u641c\u7d22\u9644\u8fd1${toolResult.keyword || '\u670d\u52a1'}\uff0c\u8bf7\u5728\u5bf9\u8bdd\u533a\u9009\u62e9\u5f53\u524d\u4f4d\u7f6e\u6216\u624b\u52a8\u5730\u70b9\u3002`;
  routeActions.innerHTML = '';
  appendNearbyLocationChoices(toolResult.keyword || '\u5468\u8fb9\u670d\u52a1');
}

function appendNearbyLocationChoices(keyword) {
  const article = document.createElement('article');
  article.className = 'message assistant nearby-choice';
  article.innerHTML = '<div class="avatar">VA</div><div class="bubble"><div class="nearby-choice-copy"></div><div class="nearby-choice-actions"><button type="button" data-nearby-choice="location"></button><button type="button" data-nearby-choice="manual"></button></div></div>';
  article.querySelector('.nearby-choice-copy').textContent = `\u641c\u7d22\u9644\u8fd1${keyword}\u9700\u8981\u4e00\u4e2a\u641c\u7d22\u4e2d\u5fc3\u3002`;
  const locationButton = article.querySelector('[data-nearby-choice="location"]');
  const manualButton = article.querySelector('[data-nearby-choice="manual"]');
  locationButton.textContent = '\u4f7f\u7528\u5f53\u524d\u4f4d\u7f6e';
  manualButton.textContent = '\u624b\u52a8\u8f93\u5165\u5730\u70b9';
  locationButton.addEventListener('click', useNearbyCurrentLocation);
  manualButton.addEventListener('click', showNearbyManualOriginInput);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function showLocationRetry(message, retryHandler, manualHandler) {
  routeCopy.textContent = message;
  routeActions.innerHTML = retryHandler
    ? '<button type="button" data-location-retry></button><button type="button" data-location-manual></button>'
    : '<button type="button" data-location-manual></button>';
  const retry = routeActions.querySelector('[data-location-retry]');
  const manual = routeActions.querySelector('[data-location-manual]');
  if (retry) {
    retry.textContent = '\u91cd\u65b0\u8bf7\u6c42\u5b9a\u4f4d';
    retry.addEventListener('click', retryHandler);
  }
  manual.textContent = '\u624b\u52a8\u8f93\u5165\u5730\u70b9';
  manual.addEventListener('click', manualHandler);
}

function locationFailureMessage(error) {
  if (error?.code === 1) return '\u672a\u83b7\u5f97\u5b9a\u4f4d\u6388\u6743\u3002\u8bf7\u5141\u8bb8\u6d4f\u89c8\u5668\u4f7f\u7528\u5f53\u524d\u4f4d\u7f6e\uff0c\u7136\u540e\u91cd\u8bd5\u3002';
  if (error?.code === 2) return '\u6682\u65f6\u65e0\u6cd5\u83b7\u53d6\u5f53\u524d\u4f4d\u7f6e\u3002\u8bf7\u68c0\u67e5\u7f51\u7edc\u6216\u7cfb\u7edf\u5b9a\u4f4d\u540e\u91cd\u8bd5\u3002';
  return '\u83b7\u53d6\u5f53\u524d\u4f4d\u7f6e\u8d85\u65f6\u3002\u8bf7\u91cd\u65b0\u8bf7\u6c42\u5b9a\u4f4d\u3002';
}

function useNearbyCurrentLocation() {
  if (!nearbyRequest) return;
  if (!navigator.geolocation) {
    showLocationRetry('\u5f53\u524d\u6d4f\u89c8\u5668\u4e0d\u652f\u6301\u5b9a\u4f4d\u3002\u53ef\u624b\u52a8\u8f93\u5165\u4e00\u4e2a\u641c\u7d22\u4e2d\u5fc3\u3002', null, showNearbyManualOriginInput);
    return;
  }
  routeCopy.textContent = '\u6b63\u5728\u8bf7\u6c42\u4f4d\u7f6e\u6388\u6743\u2026';
  navigator.geolocation.getCurrentPosition(
    (position) => {
      nearbyOrigin = { origin: '\u5f53\u524d\u4f4d\u7f6e', origin_location: `${position.coords.longitude},${position.coords.latitude}` };
      appendMessage('user', '\u4f7f\u7528\u5f53\u524d\u4f4d\u7f6e\u641c\u7d22\u5468\u8fb9\u670d\u52a1');
      appendTraceEntry('\u4f4d\u7f6e\u6388\u6743 / browser geolocation', 'granted');
      requestNearbyPlaces();
    },
    (error) => {
      showLocationRetry(locationFailureMessage(error), useNearbyCurrentLocation, showNearbyManualOriginInput);
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
  );
}

function showNearbyManualOriginInput() {
  routeCopy.textContent = '\u8f93\u5165\u4f8b\u5982\uff1a\u4e2d\u5173\u6751\u3001\u5317\u4eac\u897f\u7ad9\u3001\u671b\u4eac\u3002';
  routeActions.innerHTML = '<input id="nearby-origin" autocomplete="off" placeholder="\u624b\u52a8\u8f93\u5165\u5730\u70b9" aria-label="\u624b\u52a8\u8f93\u5165\u5730\u70b9"><button type="button" id="nearby-submit"></button>';
  const originInput = routeActions.querySelector('#nearby-origin');
  const submit = routeActions.querySelector('#nearby-submit');
  submit.textContent = '\u641c\u7d22\u5468\u8fb9';
  submit.addEventListener('click', () => {
    const origin = originInput.value.trim();
    if (!origin) return;
    nearbyOrigin = { origin };
    appendMessage('user', `\u4ee5${origin}\u4e3a\u4e2d\u5fc3\u641c\u7d22\u5468\u8fb9\u670d\u52a1`);
    requestNearbyPlaces();
  });
  originInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') submit.click();
  });
  originInput.focus();
}

async function requestNearbyPlaces() {
  if (!nearbyRequest || !nearbyOrigin) return;
  routeActions.innerHTML = '';
  routeCopy.textContent = `\u6b63\u5728\u4f7f\u7528\u9ad8\u5fb7\u641c\u7d22\u9644\u8fd1${nearbyRequest.keyword || '\u670d\u52a1'}\u2026`;
  try {
    const response = await fetch('/nearby', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...nearbyOrigin, category: nearbyRequest.category }),
    });
    const payload = await response.json().catch(() => ({ error: '\u5468\u8fb9\u641c\u7d22\u670d\u52a1\u54cd\u5e94\u65e0\u6548' }));
    if (!response.ok || payload.nearby?.error) throw new Error(payload.nearby?.error || payload.error || '\u5468\u8fb9\u641c\u7d22\u5931\u8d25');
    renderNearbyPlaces(payload.nearby);
  } catch (error) {
    routeCopy.textContent = `\u5468\u8fb9\u641c\u7d22\u5931\u8d25\uff1a${error.message}`;
    showNearbyManualOriginInput();
  }
}

function renderNearbyPlaces(result) {
  const pois = result.pois || [];
  appendTraceEntry(`Amap / ${result.tool}`, `${result.latency_ms} ms`);
  if (!pois.length) {
    routeCopy.textContent = `\u5728 ${result.radius_meters || 3000} m \u5185\u672a\u627e\u5230${result.keyword || '\u5468\u8fb9\u670d\u52a1'}\u3002\u8bf7\u66f4\u6362\u5730\u70b9\u91cd\u8bd5\u3002`;
    routeActions.innerHTML = '<button type="button" id="nearby-change-origin"></button>';
    routeActions.querySelector('#nearby-change-origin').textContent = '\u66f4\u6362\u641c\u7d22\u5730\u70b9';
    routeActions.querySelector('#nearby-change-origin').addEventListener('click', showNearbyManualOriginInput);
    return;
  }
  routeCopy.textContent = `\u5df2\u627e\u5230 ${pois.length} \u4e2a\u9644\u8fd1${result.keyword || '\u670d\u52a1'}\uff0c\u9009\u62e9\u4e00\u4e2a\u540e\u76f4\u63a5\u89c4\u5212\u9a7e\u8f66\u8def\u7ebf\u3002`;
  appendMessage('assistant', `\u5df2\u627e\u5230 ${pois.length} \u4e2a\u9644\u8fd1${result.keyword || '\u670d\u52a1'}\uff0c\u5019\u9009\u70b9\u5df2\u663e\u793a\u5728\u53f3\u4fa7\u3002\u9009\u62e9\u4e00\u4e2a\u201c\u5bfc\u822a\u201d\u5373\u53ef\u89c4\u5212\u9a7e\u8f66\u8def\u7ebf\u3002`);
  routeActions.innerHTML = '';
  const list = document.createElement('div');
  list.className = 'nearby-results';
  pois.forEach((poi) => {
    const row = document.createElement('div');
    row.className = 'nearby-result';
    const copy = document.createElement('div');
    const name = document.createElement('strong');
    name.textContent = poi.name;
    const address = document.createElement('span');
    address.textContent = poi.address || '\u9ad8\u5fb7\u63d0\u4f9b\u7684 POI';
    copy.append(name, address);
    const navigate = document.createElement('button');
    navigate.type = 'button';
    navigate.textContent = '\u5bfc\u822a';
    navigate.addEventListener('click', () => {
      pendingDestination = { name: poi.name, location: poi.location };
      activeRoute = null;
      routeCopy.textContent = `\u5df2\u9009\u62e9${poi.name}\uff0c\u6b63\u5728\u8ba1\u7b97\u9a7e\u8f66\u8def\u7ebf\u2026`;
      requestDrivingRoute(nearbyOrigin);
    });
    row.append(copy, navigate);
    list.append(row);
  });
  routeActions.append(list);
}

function startNaturalLanguageRoute(request, toolResult) {
  const resolvedDestination = toolResult.pois?.find((poi) => poi.name === request.destination) || toolResult.pois?.[0];
  pendingDestination = {
    name: request.destination,
    location: resolvedDestination?.location || '',
  };
  activeRoute = null;
  navigation.classList.remove('hidden');
  routeMetrics.classList.add('hidden');
  routeMapElement.classList.add('hidden');
  routeCopy.textContent = `\u5df2\u786e\u8ba4\u4ece${request.origin}\u5230${request.destination}\uff0c\u6b63\u5728\u8ba1\u7b97\u9a7e\u8f66\u8def\u7ebf\u2026`;
  requestDrivingRoute({ origin: request.origin }, request.via || []);
}

function useCurrentLocation() {
  if (!pendingDestination) return;
  if (!navigator.geolocation) {
    showLocationRetry('\u5f53\u524d\u6d4f\u89c8\u5668\u4e0d\u652f\u6301\u5b9a\u4f4d\u3002\u53ef\u624b\u52a8\u8f93\u5165\u8d77\u70b9\u3002', null, showManualOriginInput);
    return;
  }
  routeCopy.textContent = '\u6b63\u5728\u8bf7\u6c42\u4f4d\u7f6e\u6388\u6743\u2026';
  navigator.geolocation.getCurrentPosition(
    (position) => {
      appendMessage('user', '\u4f7f\u7528\u5f53\u524d\u4f4d\u7f6e\u5bfc\u822a');
      appendTraceEntry('\u4f4d\u7f6e\u6388\u6743 / browser geolocation', 'granted');
      requestDrivingRoute({ origin: '\u5f53\u524d\u4f4d\u7f6e', origin_location: `${position.coords.longitude},${position.coords.latitude}` });
    },
    (error) => {
      showLocationRetry(locationFailureMessage(error), useCurrentLocation, showManualOriginInput);
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
  );
}

function showManualOriginInput() {
  routeCopy.textContent = '\u8f93\u5165\u4f8b\u5982\uff1a\u4e2d\u5173\u6751\u3001\u5317\u4eac\u897f\u7ad9\u3001\u671d\u9633\u533a\u671b\u4eac\u3002';
  routeActions.innerHTML = '<input id="route-origin" autocomplete="off" placeholder="\u624b\u52a8\u8f93\u5165\u8d77\u70b9" aria-label="\u624b\u52a8\u8f93\u5165\u8d77\u70b9"><button type="button" id="route-submit"></button>';
  const originInput = routeActions.querySelector('#route-origin');
  const routeSubmit = routeActions.querySelector('#route-submit');
  routeSubmit.textContent = '\u8ba1\u7b97\u9a7e\u8f66\u8def\u7ebf';
  routeSubmit.addEventListener('click', () => {
    const origin = originInput.value.trim();
    if (!origin) return;
    appendMessage('user', `\u4ece${origin}\u5bfc\u822a`);
    requestDrivingRoute({ origin });
  });
  originInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') routeSubmit.click();
  });
  originInput.focus();
}

async function requestDrivingRoute(origin, via = activeRoute?.via || []) {
  if (!pendingDestination) return;
  routeActions.innerHTML = '';
  routeCopy.textContent = '\u6b63\u5728\u8c03\u7528\u9ad8\u5fb7\u9a7e\u8f66\u8def\u7ebf\u2026';
  try {
    const response = await fetch('/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...origin, destination: pendingDestination.name, destination_location: pendingDestination.location, via }),
    });
    const payload = await response.json().catch(() => ({ error: '\u8def\u7ebf\u670d\u52a1\u54cd\u5e94\u65e0\u6548' }));
    if (!response.ok || payload.route?.error) throw new Error(payload.route?.error || payload.error || '\u8def\u7ebf\u8ba1\u7b97\u5931\u8d25');
    renderDrivingRoute(payload.route);
  } catch (error) {
    routeCopy.textContent = `\u8def\u7ebf\u8ba1\u7b97\u5931\u8d25\uff1a${error.message}`;
    showManualOriginInput();
  }
}

async function renderDrivingRoute(route) {
  const distance = formatDistance(route.distance_meters);
  const duration = formatDuration(route.duration_seconds);
  const via = route.via || [];
  const viaNames = via.map((point) => point.name).filter(Boolean);
  const viaCopy = viaNames.length ? `\uff0c\u9014\u7ecf${viaNames.join('\u3001')}` : '';
  activeRoute = {
    origin: route.origin,
    origin_location: route.origin_location,
    destination: route.destination,
    destination_location: route.destination_location,
    via: viaNames,
  };
  pendingDestination = { name: route.destination, location: route.destination_location };
  routeCopy.textContent = `${route.origin}\u5230${route.destination}${viaCopy}\uff1a${distance}\uff0c\u9884\u8ba1\u9a7e\u8f66${duration}\u3002`;
  routeMetrics.classList.remove('hidden');
  routeMetrics.innerHTML = metric('\u9a7e\u8f66\u8ddd\u79bb', distance) + metric('\u9884\u8ba1\u65f6\u95f4', duration);
  appendTraceEntry(`Amap / ${route.tool}`, `${route.latency_ms} ms`);
  appendMessage('assistant', `\u8def\u7ebf\u5df2\u751f\u6210\uff1a${route.origin}\u5230${route.destination}${viaCopy}\uff0c${distance}\uff0c\u9884\u8ba1\u9a7e\u8f66${duration}\u3002\u5730\u56fe\u5df2\u663e\u793a\u5728\u53f3\u4fa7\u3002`);
  routeActions.innerHTML = '<button type="button" id="route-add-via"></button><button type="button" id="route-change-origin"></button>';
  const addVia = routeActions.querySelector('#route-add-via');
  const changeOrigin = routeActions.querySelector('#route-change-origin');
  addVia.textContent = '\u6dfb\u52a0\u9014\u7ecf\u70b9';
  changeOrigin.textContent = '\u66f4\u6362\u8d77\u70b9';
  addVia.addEventListener('click', showWaypointInput);
  changeOrigin.addEventListener('click', showManualOriginInput);
  try {
    await renderAmapRoute(route);
  } catch {
    routeMapElement.classList.add('hidden');
    routeCopy.textContent += '\u5f53\u524d Key \u65e0\u6cd5\u52a0\u8f7d\u9ad8\u5fb7 JS \u5730\u56fe\uff0c\u8def\u7ebf\u6570\u636e\u4ecd\u5df2\u8ba1\u7b97\u5b8c\u6210\u3002';
  }
}

async function renderAmapRoute(route) {
  const config = await fetch('/map-config').then((response) => response.ok ? response.json() : Promise.reject());
  await loadAmap(config.key);
  const origin = route.origin_location.split(',').map(Number);
  const destination = route.destination_location.split(',').map(Number);
  const path = route.polyline.flatMap((line) => line.split(';').map((point) => point.split(',').map(Number)));
  if (!amapMap) amapMap = new window.AMap.Map('route-map', { zoom: 12, center: origin });
  amapMap.clearMap();
  const overlays = [
    new window.AMap.Marker({ position: origin, title: route.origin }),
    new window.AMap.Marker({ position: destination, title: route.destination }),
  ];
  (route.via || []).forEach((point, index) => {
    const position = point.location.split(',').map(Number);
    overlays.push(new window.AMap.Marker({ position, title: `\u9014\u7ecf\u70b9 ${index + 1}: ${point.name}` }));
  });
  if (path.length) overlays.push(new window.AMap.Polyline({ path, strokeColor: '#00786b', strokeWeight: 6, strokeOpacity: 0.88 }));
  amapMap.add(overlays);
  amapMap.setFitView(overlays, false, [24, 24, 24, 24]);
  routeMapElement.classList.remove('hidden');
}

function showWaypointInput() {
  if (!activeRoute) return;
  routeCopy.textContent = '\u8f93\u5165\u8981\u9014\u7ecf\u7684\u5730\u70b9\uff0c\u4f8b\u5982\uff1a\u5f90\u5dde\u706b\u8f66\u7ad9\u3001\u4e91\u9f99\u6e56\u3001\u5145\u7535\u7ad9\u3002';
  routeActions.innerHTML = '<input id="route-via" autocomplete="off" placeholder="\u8f93\u5165\u9014\u7ecf\u70b9" aria-label="\u8f93\u5165\u9014\u7ecf\u70b9"><button type="button" id="route-via-submit"></button>';
  const viaInput = routeActions.querySelector('#route-via');
  const submit = routeActions.querySelector('#route-via-submit');
  submit.textContent = '\u91cd\u65b0\u89c4\u5212';
  const addWaypoint = () => {
    const waypoint = viaInput.value.trim();
    if (!waypoint || !activeRoute) return;
    appendMessage('user', `\u8def\u7ebf\u52a0\u4e00\u4e2a${waypoint}`);
    requestDrivingRoute(
      { origin: activeRoute.origin, origin_location: activeRoute.origin_location },
      [...activeRoute.via, waypoint],
    );
  };
  submit.addEventListener('click', addWaypoint);
  viaInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') addWaypoint();
  });
  viaInput.focus();
}

function loadAmap(key) {
  if (window.AMap) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`;
    script.onload = () => window.AMap ? resolve() : reject(new Error('Amap JS did not load'));
    script.onerror = () => reject(new Error('Amap JS failed to load'));
    document.head.append(script);
  });
}

function appendTraceEntry(label, detail) {
  trace.insertAdjacentHTML('beforeend', `<li><span class="dot"></span><span>${escapeHtml(`${label} · ${detail}`)}</span></li>`);
}

function formatDistance(meters) { return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${meters} m`; }
function formatDuration(seconds) { return seconds >= 3600 ? `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}min` : `${Math.max(1, Math.round(seconds / 60))} min`; }

function renderCockpit(state) {
  if (!state) return;
  const air = state.air_condition || {};
  const ambient = state.ambient_light || {};
  const enabled = (value) => value ? '\u5df2\u5f00\u542f' : '\u5df2\u5173\u95ed';
  const rows = [
    ['\u7a7a\u8c03', `${enabled(air.on)} / ${air.temperature ?? '-'} \u5ea6 / ${air.mode === 'auto' ? '\u81ea\u52a8' : '\u624b\u52a8'}`],
    ['\u8f66\u7a97', state.windows === 'open' ? '\u5df2\u6253\u5f00' : '\u5df2\u5173\u95ed'],
    ['\u5ea7\u6905\u901a\u98ce', enabled(state.seat_ventilation)],
    ['\u540e\u5907\u7bb1', state.trunk === 'open' ? '\u5df2\u6253\u5f00' : '\u5df2\u5173\u95ed'],
    ['\u6c1b\u56f4\u706f', `${enabled(ambient.on)} / ${ambient.color || '-'}`],
    ['\u65e0\u7ebf\u5145\u7535', enabled(state.wireless_charging)],
  ];
  cockpitState.innerHTML = rows.map(([name, value]) => metric(name, value)).join('');
  cockpit.classList.remove('hidden');
}

function renderExecution(final) {
  const metadata = final.metadata || {};
  const chat = metadata.chat_trace || {};
  const reject = metadata.reject_trace || {};
  const nlu = metadata.nlu_trace || {};
  const intent = nlu.intent_recall || {};
  const fc = nlu.function_call || {};
  const tool = metadata.tool_trace || {};
  const conversationContext = metadata.conversation_context || {};
  const decisionPolicy = metadata.decision_policy || nlu.decision_policy || {};
  const usage = chat.usage || fc.usage || {};
  summary.textContent = final.function ? `${final.intent || '任务'} / ${final.function}` : final.intent || '对话';
  const entries = [];
  if (reject.backend) entries.push(`Reject ${reject.backend} · ${reject.allowed ? 'allow' : 'block'} · ${formatConfidence(reject.confidence)} · ${reject.latency_ms ?? '-'} ms`);
  if (intent.top_k_ids) entries.push(`Intent BERT · Top-K ${intent.top_k_ids.join(', ')} · ${intent.latency_ms ?? '-'} ms`);
  if (metadata.nlu_backend) entries.push(`NLU ${metadata.nlu_backend} · ${metadata.nlu_latency_ms ?? '-'} ms`);
  if (fc.model || fc.candidate_tools) {
    const schemaSize = fc.legacy_schema_chars
      ? `${fc.legacy_schema_chars} -> ${fc.candidate_schema_chars ?? '-'}`
      : `${fc.candidate_schema_chars ?? '-'}`;
    entries.push(`DeepSeek FC · ${fc.latency_ms ?? '-'} ms · ${fc.candidate_tools ?? '-'} candidates · schema ${schemaSize} chars`);
  }
  if (chat.backend) entries.push(`DeepSeek Chat · TTFT ${chat.first_token_ms ?? '-'} ms · ${chat.tokens_per_second ?? '-'} tok/s`);
  if (tool.function) entries.push(`${tool.provider || 'Tool'} / ${tool.tool || tool.function} · ${tool.latency_ms ?? '-'} ms`);
  if (tool.simulation) entries.push('Cockpit simulator / no physical vehicle control');
  if (tool.state_scope) entries.push(`Cockpit state / ${tool.state_scope}-scoped`);
  if (tool.context_source === 'history') entries.push('Cockpit context / resolved from previous turn');
  if (tool.action === 'await_confirmation') entries.push('Cockpit safety gate / confirmation required');
  if (conversationContext.task === 'navigation') entries.push(`Dialogue context / navigation awaiting ${conversationContext.awaiting || 'input'}`);
  if (decisionPolicy.strategy) entries.push(`Decision policy / ${decisionPolicy.strategy}`);
  if (metadata.fallback_reason) entries.push(`Fallback: ${metadata.fallback_reason}`);
  trace.innerHTML = entries.length ? entries.map((entry) => `<li><span class="dot"></span><span>${escapeHtml(entry)}</span></li>`).join('') : '<li><span class="dot idle"></span><span>当前路径未使用远程模型</span></li>';
  metrics.innerHTML = metric('总耗时', `${metadata.total_latency_ms ?? '-'} ms`) + metric('Token', usage.total_tokens ?? '-') + metric('远程状态', chat.backend || metadata.nlu_backend || '-');
  const toolResult = metadata.tool_result || {};
  const navigationRequest = metadata.navigation_request || {};
  if (final.function === 'cockpit.control' && toolResult.simulation) {
    renderCockpit(toolResult.state);
  } else if (navigationRequest.action === 'route_request') {
    startNaturalLanguageRoute(navigationRequest, toolResult);
  } else if (toolResult.action === 'consent_required') {
    activeArtist = toolResult.artist || '';
    activeSong = toolResult.song || '';
    player.classList.remove('hidden');
    playerCopy.textContent = activeArtist ? `检测到 ${activeArtist} 的音乐请求。请选择播放方式。` : '请选择播放方式。';
    appendMusicChoices(activeArtist, activeSong);
  } else if (toolResult.action === 'demo_audio_play') {
    activeArtist = toolResult.artist || activeArtist;
    activeSong = toolResult.song || activeSong;
    player.classList.remove('hidden');
    if (demoAudioPlaying) {
      player.dataset.audioState = 'playing';
      playerCopy.textContent = '\u7ad9\u5185\u539f\u521b\u6f14\u793a\u97f3\u9891\u6b63\u5728\u64ad\u653e\u3002';
    } else if (player.dataset.audioState === 'blocked') {
      playerCopy.textContent = '\u6d4f\u89c8\u5668\u62e6\u622a\u4e86\u81ea\u52a8\u64ad\u653e\u3002\u8bf7\u4f7f\u7528\u4e0b\u65b9\u539f\u751f\u64ad\u653e\u63a7\u4ef6\u91cd\u8bd5\u3002';
    } else {
      player.dataset.audioState = 'ready';
      playerCopy.textContent = '\u5df2\u786e\u8ba4\u7ad9\u5185\u539f\u521b\u6f14\u793a\u97f3\u9891\u3002\u8bf7\u70b9\u51fb\u804a\u5929\u6c14\u6ce1\u5185\u7684\u64ad\u653e\u6309\u94ae\u5f00\u59cb\u3002';
    }
  } else if (toolResult.action === 'third_party_search') {
    activeArtist = toolResult.artist || activeArtist;
    activeSong = toolResult.song || activeSong;
    player.classList.remove('hidden');
    const providerName = toolResult.platform === 'netease-music' ? '\u7f51\u6613\u4e91\u97f3\u4e50' : 'QQ \u97f3\u4e50';
    playerCopy.textContent = `\u5df2\u786e\u8ba4 ${providerName} \u7cbe\u786e\u641c\u7d22\uff1a${toolResult.query || activeArtist}\u3002\u8bf7\u5728\u8be5\u5e73\u53f0\u9009\u62e9\u53ef\u64ad\u653e\u7248\u672c\u3002`;
  } else if (final.function === 'weather.query' && toolResult.provider === 'amap-mcp') {
    player.classList.add('hidden');
  } else if (final.function === 'map.nearby' && toolResult.action === 'location_required') {
    showNearbyLocationChoices(toolResult);
  } else if (final.function === 'map.route' && toolResult.provider === 'amap-mcp') {
    showNavigationChoices(toolResult);
  }
}

function metric(name, value) { return `<div><dt>${name}</dt><dd>${escapeHtml(String(value))}</dd></div>`; }
function escapeHtml(value) { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; }
function formatConfidence(value) { return typeof value === 'number' ? value.toFixed(3) : '-'; }

function openThirdParty(platform, artist, song) {
  const query = encodeURIComponent([artist, song].filter(Boolean).join(' ') || 'music');
  const url = platform === 'netease-music'
    ? `https://music.163.com/#/search/m/?s=${query}&type=1`
    : `https://y.qq.com/n/ryqq/search?w=${query}`;
  window.open(url, '_blank', 'noopener');
}

document.querySelector('#third-party').addEventListener('click', () => {
  openThirdParty('qq-music', activeArtist, activeSong);
  playerCopy.textContent = '已打开第三方音乐搜索页面。';
});
document.querySelector('#netease-music').addEventListener('click', () => {
  openThirdParty('netease-music', activeArtist, activeSong);
  playerCopy.textContent = '\u5df2\u6253\u5f00\u7f51\u6613\u4e91\u97f3\u4e50\u7cbe\u786e\u641c\u7d22\u9875\u3002';
});
document.querySelector('#demo-audio').addEventListener('click', () => {
  startDemoAudio();
  playerCopy.textContent = '站内生成演示音频播放中。再次点击可重新开始。';
});

// The persistent player is also part of the observable tool-call trace.
document.querySelector('#third-party').addEventListener('click', () => submitMusicChoice('QQ\u97f3\u4e50\u641c\u7d22'));
document.querySelector('#netease-music').addEventListener('click', () => submitMusicChoice('\u7f51\u6613\u4e91\u97f3\u4e50\u641c\u7d22'));
document.querySelector('#demo-audio').addEventListener('click', () => submitMusicChoice('\u7ad9\u5185\u6f14\u793a\u97f3\u9891\u64ad\u653e'));

function startDemoAudio() {
  demoAudio.currentTime = 0;
  demoAudio.volume = 0.72;
  demoAudioPlaying = true;
  player.dataset.audioState = 'starting';
  demoAudio.play().catch(() => {
    demoAudioPlaying = false;
    player.dataset.audioState = 'blocked';
    playerCopy.textContent = '\u6d4f\u89c8\u5668\u62e6\u622a\u4e86\u97f3\u9891\u64ad\u653e\u3002\u8bf7\u518d\u6b21\u70b9\u51fb\u64ad\u653e\u6309\u94ae\u3002';
  });
}

demoAudio.addEventListener('playing', () => {
  demoAudioPlaying = true;
  player.dataset.audioState = 'playing';
  playerCopy.textContent = '\u7ad9\u5185\u539f\u521b\u6f14\u793a\u97f3\u9891\u6b63\u5728\u64ad\u653e\u3002';
});
demoAudio.addEventListener('ended', () => {
  demoAudioPlaying = false;
  player.dataset.audioState = 'ready';
  playerCopy.textContent = '\u7ad9\u5185\u539f\u521b\u6f14\u793a\u97f3\u9891\u64ad\u653e\u5b8c\u6210\u3002';
});

fetch('/health').then((response) => response.json()).then(() => {
  document.querySelector('#system-status').textContent = '本地链路已连接';
  document.querySelector('.pulse').classList.add('ready');
}).catch(() => { document.querySelector('#system-status').textContent = '后端不可用'; });
