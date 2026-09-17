#!/usr/bin/env python3
"""Unified hackathon entry point: synthetic / real-data / rosbag / interactive."""
import argparse
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, 'fovea_lidar'))


def main():
    p = argparse.ArgumentParser(description="Foveated LiDAR hackathon demo")
    p.add_argument('--mode', default='synthetic',
                   choices=['synthetic', 'real', 'interactive', 'web', 'gif'],
                   help='Demo mode')
    p.add_argument('--data', default='', help='Path to CSite*.txt real LiDAR file (real mode)')
    p.add_argument('--frames', type=int, default=100)
    p.add_argument('--backend', default='auto', choices=['auto', 'fastdem', 'python'])
    args = p.parse_args()

    if args.backend != 'python':
        from fovea_lidar.fastdem_bridge import HAVE_FASTDEM, FastDEMBridge
        print(f"FastDEM C++ available: {HAVE_FASTDEM}")
        if args.backend == 'fastdem' and not HAVE_FASTDEM:
            print("FastDEM not built; falling back to python_gridmap. See fastdem_pybind/CMakeLists.txt")
    else:
        print("Backend forced: python_gridmap")

    if args.mode == 'gif':
        from generate_demo import create_animation
        create_animation()
    elif args.mode == 'interactive':
        from run_enhanced_demo import EnhancedDemo
        EnhancedDemo(use_web_dashboard=False).run(frames=args.frames)
    elif args.mode == 'web':
        import live_server
        print("Live dashboard: http://localhost:5000")
        sys.argv = [sys.argv[0], '--port', '5000']
        live_server.main()
    elif args.mode == 'real':
        if not args.data or not os.path.exists(args.data):
            print("Provide --data path to CSite*.txt (lidar_viewer/Testdata)")
            sys.exit(1)
        from scripts.demo_scenarios import run_real_data_demo
        run_real_data_demo(args.data, frames=args.frames)
    else:
        from run_demo import demo_pipeline, visualize_results
        history, config, grid_map = demo_pipeline()
        visualize_results(history, config, grid_map)


if __name__ == '__main__':
    main()
