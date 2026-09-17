const socket = io();
const perf = {t: [], r: [], b: []};
let paused = false;
function togglePause(){ paused = !paused; document.getElementById('pauseBtn').textContent = paused ? 'Resume' : 'Pause'; sendControl(); }
function sendControl(){ socket.emit('control', {paused: paused, speed: parseFloat(document.getElementById('speed').value), alpha: parseFloat(document.getElementById('alpha').value), beta: parseFloat(document.getElementById('beta').value)}); }
socket.on('update', (d) => {
  document.getElementById('frame').textContent = d.frame;
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
  document.getElementById('frameTime').textContent = d.frame_time.toFixed(1);
  document.getElementById('fps').textContent = d.fps.toFixed(1);
  document.getElementById('roiCount').textContent = d.roi_count;
  document.getElementById('maxRisk').textContent = d.max_risk.toFixed(2);
  document.getElementById('budget').textContent = (d.budget_util*100).toFixed(1);
  document.getElementById('objCount').textContent = d.objects.length;
  const st = document.getElementById('status');
  st.textContent = d.fallback ? 'FALLBACK' : 'RUNNING';
  st.className = d.fallback ? 'err' : 'ok';
  document.getElementById('riskImg').src = 'data:image/png;base64,' + d.risk_img;
  document.getElementById('dynImg').src = 'data:image/png;base64,' + d.dyn_img;
  document.getElementById('objects').innerHTML = d.objects.map(o =>
    '<tr><td>' + o.id + '</td><td>(' + o.x.toFixed(1) + ', ' + o.y.toFixed(1) + ')</td><td>(' + o.vx.toFixed(1) + ', ' + o.vy.toFixed(1) + ')</td><td>' + o.halo.toFixed(1) + 'm</td></tr>').join('');
  perf.t.push(d.frame_time); perf.r.push(d.roi_count); perf.b.push(d.budget_util*100);
  if (perf.t.length > 80) { perf.t.shift(); perf.r.shift(); perf.b.shift(); }
  Plotly.newPlot('perfPlot', [
    {y: perf.t, name: 'ms', line: {color: '#00d9a5'}},
    {y: perf.r, name: 'ROIs', yaxis: 'y2', line: {color: '#e94560'}},
    {y: perf.b, name: 'budget%', yaxis: 'y2', line: {color: '#ffd60a', dash: 'dot'}},
  ], {yaxis: {title: 'ms'}, yaxis2: {title: 'count/%', overlaying: 'y', side: 'right', range: [0, 110]},
      paper_bgcolor: '#16213e', plot_bgcolor: '#1a1a2e', font: {color: '#eee'}, margin: {t: 20}});
});
