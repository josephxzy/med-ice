# -*- coding: utf-8 -*-
"""
阿里云 NLP 中文分词 CLI

用法：
  python alinlp_ws.py "阿苯达唑片治疗寄生虫感染"
  echo "双价肾综合征出血热灭活疫苗" | python alinlp_ws.py

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
import urllib.parse

ENDPOINT = "alinlp.cn-hangzhou.aliyuncs.com"
API_VERSION = "2020-06-29"


def get_signature(secret, method, canonical_uri, canonical_query, payload):
    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    nonce = str(uuid.uuid4())
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")

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
        f"{method}\n"
        f"{canonical_uri}\n"
        f"{canonical_query}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_payload}"
    )

    hashed_canonical = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"ACS3-HMAC-SHA256\n{hashed_canonical}"
    signature = hmac.new(access_key_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    auth = (
        f"ACS3-HMAC-SHA256 "
        f"Credential={access_key_id},"
        f"SignedHeaders={signed_headers},"
        f"Signature={signature}"
    )

    return auth, timestamp


def segment(text):
    """调用阿里云 NLP 分词 API"""
    payload = json.dumps({
        "Text": text,
        "TokenizerId": "GENERAL_CHN",
        "OutType": "1"
    })

    auth, timestamp = get_signature(
        os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", ""),
        "POST",
        "/",
        "",
        payload
    )

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

    words = [item["word"] for item in data.get("result", [])]
    return words


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("用法: python alinlp_ws.py <中文文本>")
        print("      echo <中文文本> | python alinlp_ws.py")
        sys.exit(1)

    if len(text) > 1024:
        print(f"警告: 文本长度 {len(text)} 超过 API 限制 1024，已截断")
        text = text[:1024]

    try:
        words = segment(text)
        print(" ".join(words))
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
