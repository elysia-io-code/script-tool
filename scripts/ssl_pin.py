#!/usr/bin/env python3
import base64
import hashlib
import shutil
import subprocess
import sys


def run(command, input_text=None):
    result = subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"命令失败：{' '.join(command)}")
    return result.stdout


def run_bytes(command, input_bytes):
    result = subprocess.run(
        command,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：ssl_pin.py <domain> [port]")

    domain = sys.argv[1].strip()
    port = sys.argv[2].strip() if len(sys.argv) > 2 else "443"

    if not shutil.which("openssl"):
        raise SystemExit("找不到 openssl，请先安装或确认 openssl 在 PATH 中。")

    certs = run(
        [
            "openssl",
            "s_client",
            "-servername",
            domain,
            "-connect",
            f"{domain}:{port}",
            "-showcerts",
        ],
        input_text="",
    )
    cert = extract_first_certificate(certs)
    public_key = run(["openssl", "x509", "-pubkey", "-noout"], input_text=cert)
    public_key_der = run_bytes(
        ["openssl", "pkey", "-pubin", "-outform", "der"],
        public_key.encode("utf-8"),
    )

    digest = hashlib.sha256(public_key_der).digest()
    pin = base64.b64encode(digest).decode("ascii")

    print(f"域名：{domain}:{port}")
    print(f"sha256/{pin}")


def extract_first_certificate(output):
    begin = "-----BEGIN CERTIFICATE-----"
    end = "-----END CERTIFICATE-----"
    start = output.find(begin)
    stop = output.find(end, start)
    if start == -1 or stop == -1:
        raise RuntimeError("没有从 openssl 输出中读取到证书。")
    return output[start : stop + len(end)] + "\n"


if __name__ == "__main__":
    main()
