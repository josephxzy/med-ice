# -*- coding: utf-8 -*-
"""
阿里云 NLP 中文分词 CLI

用法：
  python alinlp_ws.py "阿苯达唑片治疗寄生虫感染"
  echo "双价肾综合征出血热灭活疫苗" | python alinlp_ws.py
  python alinlp_ws.py config           查看调用统计
  python alinlp_ws.py config --limit 500  设置每日限制

环境变量（必填）：
  ALIBABA_CLOUD_ACCESS_KEY_ID
  ALIBABA_CLOUD_ACCESS_KEY_SECRET
"""

import sys
import os
import json
import hashlib
import hmac
import time
import uuid
import urllib.request

ENDPOINT = "alinlp.cn-hangzhou.aliyuncs.com"
API_VERSION = "2020-06-29"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".alinlp_config.json")
DAILY_LIMIT = 500  # 免费版每日 500 次（阿里云 NLP 基础版免费额度）


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"date": "", "count": 0, "limit": DAILY_LIMIT}


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
        raise Exception(f"今日调用已达上限 ({cfg['count']}/{cfg['limit']})，请明天再试")


def increment_count(cfg):
    cfg["count"] += 1
    save_config(cfg)


def get_signature(access_key_id, access_key_secret, method, canonical_uri, canonical_query, payload):
    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    nonce = str(uuid.uuid4())

    canonical_headers = (
        f"content-type:application/json; charset=utf-8\n"
        f"host:{ENDPOINT}\n"
        f"x-acs-action:GetWsChGeneral\n"
        f"x-acs-content-sha256:{hashed_payload}\n"
        f"x-acs-date:{timestamp}\n"
        f"x-acs-signature-nonce:{nonce}\n"
        f"x-acs-version:{API_VERSION}\n"
    )
    signed_headers = "content-type;host;x-acs-action;x-acs-content-sha256;x-acs-date;x-acs-signature-nonce;x-acs-version"

    canonical_request = (
        f"{method}\n{canonical_uri}\n{canonical_query}\n"
        f"{canonical_headers}\n{signed_headers}\n{hashed_payload}"
    )
    hashed_canonical = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"ACS3-HMAC-SHA256\n{hashed_canonical}"
    signature = hmac.new(access_key_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    auth = (
        f"ACS3-HMAC-SHA256 "
        f"Credential={access_key_id},SignedHeaders={signed_headers},Signature={signature}"
    )
    return auth, timestamp


def segment(text):
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")
    if not access_key_id or not access_key_secret:
        raise Exception("请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    cfg = load_config()
    check_quota(cfg)

    payload = json.dumps({"Text": text, "TokenizerId": "GENERAL_CHN", "OutType": "1"})
    auth, timestamp = get_signature(access_key_id, access_key_secret, "POST", "/", "", payload)

    url = f"https://{ENDPOINT}/?Action=GetWsChGeneral&ServiceCode=alinlp"
    req = urllib.request.Request(url, data=payload.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Host", ENDPOINT)
    req.add_header("x-acs-action", "GetWsChGeneral")
    req.add_header("x-acs-version", API_VERSION)
    req.add_header("x-acs-date", timestamp)
    req.add_header("x-acs-signature-nonce", str(uuid.uuid4()))
    req.add_header("x-acs-content-sha256", hashlib.sha256(payload.encode("utf-8")).hexdigest())
    req.add_header("Authorization", auth)

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data.get("success"):
        raise Exception(f"API 错误: {json.dumps(data, ensure_ascii=False)}")

    increment_count(cfg)

    words = [item["word"] for item in data.get("result", [])]
    return words, cfg


def show_config():
    cfg = load_config()
    print(f"日期:        {cfg.get('date', '未记录')}")
    print(f"今日已调用:  {cfg.get('count', 0)}")
    print(f"每日限制:    {cfg.get('limit', DAILY_LIMIT)}")
    print(f"配置文件:    {CONFIG_FILE}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        if len(sys.argv) > 2 and sys.argv[2] == "--limit" and len(sys.argv) > 3:
            cfg = load_config()
            cfg["limit"] = int(sys.argv[3])
            save_config(cfg)
            print(f"每日限制已设为 {cfg['limit']}")
        else:
            show_config()
        return

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("用法: python alinlp_ws.py <中文文本>")
        print("      python alinlp_ws.py config")
        sys.exit(1)

    if len(text) > 1024:
        print(f"警告: 文本长度 {len(text)} 超过 API 限制 1024，已截断")
        text = text[:1024]

    try:
        words, cfg = segment(text)
        print(" ".join(words))
        print(f"[今日: {cfg['count']}/{cfg['limit']}]", file=sys.stderr)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
