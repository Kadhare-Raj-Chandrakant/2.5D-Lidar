#!/usr/bin/env python3
"""Live Foveated LiDAR system: headless pipeline + browser dashboard."""
import argparse
import base64
import io
import os
import sys
import threading
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, 'fovea_lidar'))

from flask import Flask, jsonify
from flask_socketio import SocketIO

from run_enhanced_demo import EnhancedDemo

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

demo = None
latest = {}
lock = threading.Lock()
running = True


def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def render_risk_png(data):
    fig, ax = plt.subplots(figsize=(5, 5), dpi=80)
    ax.imshow(data['risk'], origin='lower', cmap='hot', vmin=0, vmax=5,
              extent=[-20, 20, -20, 20], aspect='equal')
    ax.set_title('Risk Map + ROIs (frame %s)' % data.get('frame', '?'), color='white', fontsize=10)
    ax.set_xlabel('X (m)', color='white')
    ax.set_ylabel('Y (m)', color='white')
    ax.tick_params(colors='white')
    res = 0.4
    for roi in data['rois']:
        rect = Rectangle((roi.center_x - roi.size_x*res/2, roi.center_y - roi.size_y*res/2),
                         roi.size_x*res, roi.size_y*res,
                         linewidth=2, edgecolor='cyan', facecolor='none')
        ax.add_patch(rect)
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')
    return fig_to_b64(fig)


def render_dynamic_png(data):
    fig, ax = plt.subplots(figsize=(5, 5), dpi=80)
    ax.set_xlim(-20, 20)
    ax.set_ylim(-20, 20)
    ax.set_aspect('equal')
    ax.set_title('Dynamic Objects + Safety Halos', color='white', fontsize=10)
    ax.grid(True, alpha=0.3)
    colors = [(1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1)]
    for j, obj in enumerate(data['objects']):
        c = colors[j % len(colors)]
        ax.plot(obj.center[0], obj.center[1], 'o', color=c, markersize=10,
                markeredgecolor='white', markeredgewidth=2)
        ax.arrow(obj.center[0], obj.center[1], obj.velocity[0]*3, obj.velocity[1]*3,
                 head_width=0.6, head_length=0.6, fc=c, ec='white', linewidth=2)
        halo = Circle((obj.center[0], obj.center[1]), obj.get_halo_radius(),
                      fill=False, edgecolor=c, linestyle='--', linewidth=2, alpha=0.7)
        ax.add_patch(halo)
        for t in np.linspace(0.2, 2.5, 6):
            p = obj.predict(t)
            ax.plot(p[0], p[1], 'x', color=c, alpha=0.4, markersize=7)
        ax.text(obj.center[0], obj.center[1]+1.8, 'ID:%s' % obj.id,
                color='white', fontsize=9, ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=c, alpha=0.9))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')
    ax.tick_params(colors='white')
    return fig_to_b64(fig)


def pipeline_loop():
    global latest
    n = 0
    while running:
        try:
            data = demo.process_frame()
        except Exception as e:
            print('pipeline error: %s' % e)
            time.sleep(0.5)
            continue
        if data is None:
            time.sleep(0.2)
            continue
        data['frame'] = n
        n += 1
        try:
            risk_img = render_risk_png(data)
            dyn_img = render_dynamic_png(data)
        except Exception as e:
            print('render error: %s' % e)
            time.sleep(0.2)
            continue
        payload = {
            'frame': data['frame'],
            'frame_time': data['frame_time'],
            'fps': 1000.0 / max(data['frame_time'], 1e-3),
            'roi_count': len(data['rois']),
            'max_risk': float(data['risk'].max()),
            'budget_util': data['budget']['utilization'],
            'fallback': data['fallback'],
            'objects': [{'id': o.id, 'x': float(o.center[0]), 'y': float(o.center[1]),
                         'vx': float(o.velocity[0]), 'vy': float(o.velocity[1]),
                         'halo': float(o.get_halo_radius())} for o in data['objects']],
            'risk_img': risk_img,
            'dyn_img': dyn_img,
        }
        with lock:
            latest = payload
        socketio.emit('update', payload)
        time.sleep(0.05)


@app.route('/')
def index():
    with open(os.path.join(BASE, 'dashboard.html')) as f:
        return f.read()


@app.route('/app.js')
def app_js():
    with open(os.path.join(BASE, 'static_app.js')) as f:
        js = f.read()
    return app.response_class(js, mimetype='application/javascript')


@app.route('/api/state')
def state():
    with lock:
        s = dict(latest)
    s.pop('risk_img', None)
    s.pop('dyn_img', None)
    return jsonify(s)


@socketio.on('control')
def handle_control(msg):
    demo.paused = bool(msg.get('paused', False))
    if 'speed' in msg:
        demo.object_speed = float(msg['speed'])
    if 'alpha' in msg:
        demo.config['foveation_alpha'] = float(msg['alpha'])
    if 'beta' in msg:
        demo.config['foveation_beta'] = float(msg['beta'])


def main():
    global demo
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=5000)
    args = ap.parse_args()
    demo = EnhancedDemo(use_web_dashboard=False)
    demo.paused = False
    t = threading.Thread(target=pipeline_loop, daemon=True)
    t.start()
    print('LIVE system running: http://localhost:%d' % args.port)
    socketio.run(app, host='0.0.0.0', port=args.port)


if __name__ == '__main__':
    main()
