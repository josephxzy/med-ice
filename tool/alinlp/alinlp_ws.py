# -*- coding: utf-8 -*-
"""
阿里云 NLP 中文分词 CLI

用法：
  python alinlp_ws.py "阿苯达唑片治疗寄生虫感染"
  echo "双价肾综合征出血热灭活疫苗" | python alinlp_ws.py
  python alinlp_ws.py config
  python alinlp_ws.py config --limit 500
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
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
CONFIG_TEMPLATE = os.path.join(SCRIPT_DIR, "config.template.json")
DAILY_LIMIT = 500


def load_config():
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists(CONFIG_TEMPLATE):
            import shutil
            shutil.copy(CONFIG_TEMPLATE, CONFIG_FILE)
            print(f"已从模板创建: {CONFIG_FILE}", file=sys.stderr)
            print("请编辑填入密钥后重新运行", file=sys.stderr)
            sys.exit(0)
        return {"access_key_id": "", "access_key_secret": "", "limit": DAILY_LIMIT, "date": "", "count": 0}

    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    if not cfg.get("access_key_id"):
        cfg["access_key_id"] = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
    if not cfg.get("access_key_secret"):
        cfg["access_key_secret"] = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")
    cfg.setdefault("limit", DAILY_LIMIT)
    cfg.setdefault("date", "")
    cfg.setdefault("count", 0)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)


def check_quota(cfg):
    today = time.strftime("%Y-%m-%d")
    if cfg["date"] != today:
        cfg["date"] = today
        cfg["count"] = 0
        save_config(cfg)
    if cfg["count"] >= cfg["limit"]:
        raise Exception(f"今日已达上限 ({cfg['count']}/{cfg['limit']})")


def increment_count(cfg):
    cfg["count"] += 1
    save_config(cfg)


def sign(access_key_id, access_key_secret, method, query_string, body):
    """ACS3-HMAC-SHA256 签名"""
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


def segment(text):
    cfg = load_config()
    ak_id = cfg.get("access_key_id", "")
    ak_secret = cfg.get("access_key_secret", "")
    if not ak_id or not ak_secret:
        raise Exception("请编辑 config.json 填入密钥")

    check_quota(cfg)

    body = ""
    params = [("Action", "GetWsChGeneral"), ("OutType", "1"),
              ("ServiceCode", "alinlp"), ("Text", text),
              ("TokenizerId", "GENERAL_CHN")]
    query = urllib.parse.urlencode(sorted(params))

    auth, timestamp, nonce, payload_hash = sign(ak_id, ak_secret, "GET", query, body)

    req = urllib.request.Request(
        f"https://{ENDPOINT}/?{query}",
        method="GET"
    )
    req.add_header("Host", ENDPOINT)
    req.add_header("x-acs-action", "GetWsChGeneral")
    req.add_header("x-acs-version", API_VERSION)
    req.add_header("x-acs-date", timestamp)
    req.add_header("x-acs-signature-nonce", nonce)
    req.add_header("x-acs-content-sha256", payload_hash)
    req.add_header("Authorization", auth)

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.read().decode('utf-8')}")

    # 响应结构: {"Data": "{\"result\":[...],\"success\":true}"}
    inner = json.loads(data.get("Data", "{}"))
    if not inner.get("success"):
        raise Exception(json.dumps(data, ensure_ascii=False))

    increment_count(cfg)
    return [item["word"] for item in inner.get("result", [])], cfg


def show_config():
    cfg = load_config()
    print(f"配置: {CONFIG_FILE}")
    print(f"日期: {cfg.get('date', '-')}")
    print(f"已用: {cfg.get('count', 0)}/{cfg.get('limit', DAILY_LIMIT)}")
    if cfg.get("access_key_id"):
        print(f"密钥: {cfg['access_key_id'][:4]}***")
    else:
        print("密钥: 未配置")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        if len(sys.argv) > 3 and sys.argv[2] == "--limit":
            cfg = load_config()
            cfg["limit"] = int(sys.argv[3])
            save_config(cfg)
            print(f"限制已更新: {cfg['limit']}")
        else:
            show_config()
        return

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("用法: python alinlp_ws.py <文本>")
        print("      python alinlp_ws.py config")
        sys.exit(1)

    if len(text) > 1024:
        text = text[:1024]

    try:
        words, cfg = segment(text)
        print(" ".join(words))
        print(f"[{cfg['count']}/{cfg['limit']}]", file=sys.stderr)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
