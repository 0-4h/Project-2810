from __future__ import annotations
from flask import Flask, render_template, request, flash, jsonify, send_from_directory
import pandas as pd
from pathlib import Path
import subprocess, sys, threading

from fixed_rate import fixed_rate_bill  # 你的业务函数

BASE_DIR   = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES  = BASE_DIR / "templates"

TEST_FILE  = "tests/test_fixed_rate.py"   # 需要时可改为 "tests"
UNIT_HTML  = STATIC_DIR / "unit_grade.html"
COV_DIR    = STATIC_DIR / "cov_report"
COV_INDEX  = COV_DIR / "index.html"
TEST_LOG   = STATIC_DIR / "last_tests.log"
COV_LOG    = STATIC_DIR / "last_cov.log"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
COV_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES))
app.secret_key = "xpower-secret-key"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

# 统一响应头：允许同源 iframe/跳转 + 禁缓存
@app.after_request
def _headers(resp):
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(BASE_DIR),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, shell=False
    )

@app.route("/", methods=["GET", "POST"])
def index():
    """账单计算页（保留你的计算与图表功能）"""
    total_usage = None
    total_bill  = None
    rows        = None
    rate        = 0.25
    fixed_fee   = 10.0

    if request.method == "POST":
        file = request.files.get("file")
        rate = float(request.form.get("rate", 0.25))
        fixed_fee = float(request.form.get("fixed_fee", 10))
        try:
            if not file:
                flash("请上传包含列 kWh 的 CSV 文件")
            else:
                df = pd.read_csv(file)
                if "kWh" not in df.columns:
                    flash("CSV 必须包含名为 kWh 的列")
                else:
                    total_usage = float(df["kWh"].sum())
                    total_bill  = fixed_rate_bill(total_usage, rate, fixed_fee)
                    rows = df.head(200).to_dict(orient="records")
                    flash("账单计算成功！")
        except Exception as e:
            flash(f"处理失败：{e}")

    return render_template("index.html",
                           total_usage=total_usage, total_bill=total_bill, rows=rows,
                           rate=rate, fixed_fee=fixed_fee)

# ======= 简洁的“后台运行”接口（无轮询/无iframe） =======
def _bg_run_tests():
    try:
        cmd = [
            sys.executable, "-m", "pytest",
            TEST_FILE, "-q", "--disable-warnings", "--maxfail=1",
            "--html", str(UNIT_HTML), "--self-contained-html",
        ]
        result = _run(cmd)
        TEST_LOG.write_text(result.stdout or "", encoding="utf-8")
    except Exception as e:
        TEST_LOG.write_text(str(e), encoding="utf-8")

def _bg_run_cov():
    try:
        cmd = [
            sys.executable, "-m", "pytest",
            TEST_FILE, "-q", "--disable-warnings", "--maxfail=1",
            "--cov=fixed_rate", "--cov-branch",
            f"--cov-report=html:{COV_DIR}",
        ]
        result = _run(cmd)
        COV_LOG.write_text(result.stdout or "", encoding="utf-8")
    except Exception as e:
        COV_LOG.write_text(str(e), encoding="utf-8")

@app.route("/api/tests/start", methods=["POST"])
def api_tests_start():
    threading.Thread(target=_bg_run_tests, daemon=True).start()
    return jsonify({"started": True})

@app.route("/api/cov/start", methods=["POST"])
def api_cov_start():
    threading.Thread(target=_bg_run_cov, daemon=True).start()
    return jsonify({"started": True})

# ======= 报告路由：用于新标签直接打开 =======
@app.route("/report/tests")
def report_tests():
    if not UNIT_HTML.exists():
        return "报告尚未生成（请先点击“后台运行单元测试”）", 404
    resp = send_from_directory(str(STATIC_DIR), UNIT_HTML.name)
    resp.cache_control.no_cache = True
    resp.cache_control.max_age = 0
    resp.headers["Pragma"] = "no-cache"; resp.headers["Expires"] = "0"
    return resp

@app.route("/report/cov")
def report_cov():
    if not COV_INDEX.exists():
        return "覆盖率报告尚未生成（请先点击“后台运行覆盖率测试”）", 404
    resp = send_from_directory(str(COV_DIR), "index.html")
    resp.cache_control.no_cache = True
    resp.cache_control.max_age = 0
    resp.headers["Pragma"] = "no-cache"; resp.headers["Expires"] = "0"
    return resp

if __name__ == "__main__":
    # 禁用 reloader，避免双进程导致“写在A、看在B”的不同步
    app.run(debug=True, use_reloader=False)
