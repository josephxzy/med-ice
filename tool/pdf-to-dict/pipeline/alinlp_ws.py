# -*- coding: utf-8 -*-
"""
阿里云 NLP 中文分词 — 核心模块（被 segment.py 子进程调用）。

提供 call_api / load_config / save_config 三个接口。
"""

import sys
import os
import json
import hashlib
import hmac
import time
import uuid
import urllib.request
import urllib.error
import urllib.parse

ENDPOINT = "alinlp.cn-hangzhou.aliyuncs.com"
API_VERSION = "2020-06-29"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
DEFAULT_DIR = os.path.join(CONFIG_DIR, "default")
USER_DIR = os.path.join(CONFIG_DIR, "user")
CONFIG_FILE = os.path.join(USER_DIR, "alinlp.json")
DAILY_LIMIT = 500000


def _merge_config(default_path, user_path):
    cfg = {}
    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    if os.path.exists(user_path):
        with open(user_path, "r", encoding="utf-8") as f:
            user = json.load(f)
        _deep_update(cfg, user)
    return cfg


def _deep_update(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


def load_config():
    default_path = os.path.join(DEFAULT_DIR, "alinlp.json")
    user_path = os.path.join(USER_DIR, "alinlp.json")
    if not os.path.exists(user_path):
        os.makedirs(USER_DIR, exist_ok=True)
        cfg = {"access_key_id": "", "access_key_secret": "", "limit": DAILY_LIMIT, "date": "", "count": 0}
        with open(user_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"已创建配置文件: {user_path}", file=sys.stderr)
        print("请编辑填入阿里云密钥后重新运行", file=sys.stderr)
        return cfg

    cfg = _merge_config(default_path, user_path)
    if not cfg.get("access_key_id"):
        cfg["access_key_id"] = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
    if not cfg.get("access_key_secret"):
        cfg["access_key_secret"] = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")
    cfg.setdefault("limit", DAILY_LIMIT)
    cfg.setdefault("date", "")
    cfg.setdefault("count", 0)
    cfg.setdefault("backend", "alinlp")
    cfg.setdefault("alinlp_batch", 20)
    cfg.setdefault("llm_batch", 10)
    cfg.setdefault("ollama_batch", 1)
    cfg.setdefault("llm", {})
    llm = cfg["llm"]
    llm.setdefault("base_url", "https://api.deepseek.com")
    llm.setdefault("api_key", "")
    llm.setdefault("model", "deepseek-chat")
    llm.setdefault("thinking", False)
    llm.setdefault("reasoning_effort", "high")
    llm.setdefault("system_prompt", "你是一个中文分词器。将医学文本切分为真实存在的词语（不是短语或短句），空格分隔。每个词不超过8个字。规则：不输出数字+量词、不输出人名、不输出章节名。注意：不要凭空造词，确保每个词都是真实存在的，如'原发性头痛'应切为'原发性 头痛'而非'原发 性头痛'。只输出分词结果，禁止任何解释、标点、换行。")
    llm.setdefault("user_prompt", "分词：{text}")
    cfg.setdefault("ollama", {})
    ollama = cfg["ollama"]
    ollama.setdefault("host", "http://localhost:11434")
    ollama.setdefault("model", "qwen2.5:1.5b")
    ollama.setdefault("prompt", "将以下医学文本分词，空格分隔，只输出分词结果。\n{text}")
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def sign(access_key_id, access_key_secret, method, query_string, body):
    hashed_payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    nonce = str(uuid.uuid4())

    canonical_headers = (
        f"host:{ENDPOINT}\n"
        f"x-acs-action:GetWsChGeneral\n"
        f"x-acs-content-sha256:{hashed_payload}\n"
        f"x-acs-date:{timestamp}\n"
        f"x-acs-signature-nonce:{nonce}\n"
        f"x-acs-version:{API_VERSION}\n"
    )
    signed_headers = "host;x-acs-action;x-acs-content-sha256;x-acs-date;x-acs-signature-nonce;x-acs-version"

    canonical_request = (
        f"{method}\n/\n{query_string}\n"
        f"{canonical_headers}\n{signed_headers}\n{hashed_payload}"
    )
    hashed = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"ACS3-HMAC-SHA256\n{hashed}"
    signature = hmac.new(
        access_key_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    auth = f"ACS3-HMAC-SHA256 Credential={access_key_id},SignedHeaders={signed_headers},Signature={signature}"
    return auth, timestamp, nonce, hashed_payload


def call_api(text, ak_id, ak_secret, out_type="1"):
    body = ""
    params = [("Action", "GetWsChGeneral"), ("OutType", out_type),
              ("ServiceCode", "alinlp"), ("Text", text),
              ("TokenizerId", "GENERAL_CHN")]
    query = urllib.parse.urlencode(sorted(params), quote_via=urllib.parse.quote)

    auth, timestamp, nonce, payload_hash = sign(ak_id, ak_secret, "GET", query, body)

    req = urllib.request.Request(f"https://{ENDPOINT}/?{query}", method="GET")
    req.add_header("Host", ENDPOINT)
    req.add_header("x-acs-action", "GetWsChGeneral")
    req.add_header("x-acs-version", API_VERSION)
    req.add_header("x-acs-date", timestamp)
    req.add_header("x-acs-signature-nonce", nonce)
    req.add_header("x-acs-content-sha256", payload_hash)
    req.add_header("Authorization", auth)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        raise Exception(f"请求失败: {e}")

    inner = json.loads(data.get("Data", "{}"))
    if not inner.get("success"):
        raise Exception(json.dumps(data, ensure_ascii=False))

    return [item["word"] for item in inner.get("result", [])], 0
