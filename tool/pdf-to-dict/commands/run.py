# -*- coding: utf-8 -*-
"""python main.py run — 执行流水线。"""

from config.manager import ConfigManager
from pipeline.orchestrator import PipelineOrchestrator


def run(args):
    cm = ConfigManager()
    orch = PipelineOrchestrator(
        cm,
        start_phase=args.phase or 1,
        stop_phase=args.phase or 5,
        repdf=args.repdf,
    )
    orch.run()
