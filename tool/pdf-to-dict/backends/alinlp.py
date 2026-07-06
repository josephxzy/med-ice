# -*- coding: utf-8 -*-
"""阿里云 NLP 分词后端。"""

import hashlib
import hmac
import json
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

from backends.base import AbstractBackend

ENDPOINT = "alinlp.cn-hangzhou.aliyuncs.com"
API_VERSION = "2020-06-29"


class AlinlpBackend(AbstractBackend):
    name = "alinlp"

    def segment(self, text, config):
        ak_id = config.get("access_key_id", "")
        ak_secret = config.get("access_key_secret", "")
        out_type = config.get("out_type", "1")

        body = ""
        params = [
            ("Action", "GetWsChGeneral"), ("OutType", out_type),
            ("ServiceCode", "alinlp"), ("Text", text),
            ("TokenizerId", "GENERAL_CHN"),
        ]
        query = urllib.parse.urlencode(sorted(params), quote_via=urllib.parse.quote)

        auth, timestamp, nonce, payload_hash = self._sign(ak_id, ak_secret, "GET", query, body)

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

    def _sign(self, ak_id, ak_secret, method, query_string, body):
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
            ak_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        auth = f"ACS3-HMAC-SHA256 Credential={ak_id},SignedHeaders={signed_headers},Signature={signature}"
        return auth, timestamp, nonce, hashed_payload
