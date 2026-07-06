# -*- coding: utf-8 -*-
"""python main.py segment — 单次分词。"""

import os
import sys
import subprocess
from utils.paths import ROOT


SEGMENT_SCRIPT = os.path.join(ROOT, "pipeline", "ph2_segment.py")


def run(args):
    cmd = [sys.executable, SEGMENT_SCRIPT]
    if args.segment_args:
        cmd.extend(args.segment_args)
    if args.backend:
        cmd.extend(["--backend", args.backend])
    subprocess.run(cmd)
