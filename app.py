from flask import Flask, render_template, request, redirect, url_for, abort
import json
import os
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

DATA_FILE = "result.json"
ADMIN_PASSWORD = "password1234"
KST = timezone(timedelta(hours=9))


# ======================
# 헬스체크 (UptimeRobot용)
# ======================
@app.route("/")
def health():
    # UptimeRobot 등이 찍을 루트 경로: 아주 가볍게 200만 돌려줌
    return "OK", 200


# ======================
# 공통: 데이터 로드 / 저장
# ======================
def load_data():
    """result.json 로드 (없으면 빈 리스트 반환)"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_all(records):
    """records 리스트 전체를 result.json에 저장"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)


def save_result(name, manitto):
    """이름-마니또 기록을 result.json에 추가 저장"""
    data = load_data()
    data.append({
        "name": name,
        "manitto": manitto,
        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    })
    save_all(data)


# ======================
# 입력 폼 (/form)
# ======================
@app.route("/form", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        manitto = request.form.get("manitto", "").strip()

        if name and manitto:
            save_result(name, manitto)
            return redirect(url_for("result_page", name=name, manitto=manitto))
        else:
            # 하나라도 비었으면 다시 폼
            return render_template("index.html")

    # GET이면 폼 보여주기
    return render_template("index.html")


# ======================
# 제출 결과 화면
# ======================
@app.route("/result")
def result_page():
    name = request.args.get("name")
    manitto = request.args.get("manitto")
    return render_template("result.html", name=name, manitto=manitto)


# ======================
# 관리자 페이지 (/admin)
# - 비번 맞으면 마니또 공개
# - 이름 가나다 정렬 토글(sort=1)
# ======================
@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    data = load_data()

    # 정렬 여부(쿼리 파라미터)
    sort_mode = request.args.get("sort", "0") == "1"
    records = data.copy()
    if sort_mode:
        records.sort(key=lambda x: x["name"])

    # 최신 제출 5개 요약 (원본 제출 순서 기준, 최신이 위로)
    summary = data[-5:][::-1]

    # 비밀번호 확인
    show_full = False
    message = ""

    if request.method == "POST":
        pw = request.form.get("password", "").strip()
        if pw == ADMIN_PASSWORD:
            show_full = True
        else:
            message = "관리자 비밀번호가 올바르지 않습니다."

    return render_template(
        "admin.html",
        records=records,
        summary=summary,
        show_full=show_full,
        sort=sort_mode,
        message=message,
    )


# ======================
# 이름 수정 (/admin/edit/<idx>)
# ======================
@app.route("/admin/edit/<int:idx>", methods=["GET", "POST"])
def edit(idx):
    records = load_data()

    # 범위 체크
    if idx < 0 or idx >= len(records):
        abort(404)

    record = records[idx]

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name:
            record["name"] = new_name
            save_all(records)
        return redirect(url_for("admin_page"))

    return render_template("edit.html", record=record, idx=idx)


# ======================
# 삭제 (/admin/delete/<idx>)
# ======================
@app.route("/admin/delete/<int:idx>", methods=["POST"])
def delete(idx):
    records = load_data()

    # 인덱스 범위 체크
    if idx < 0 or idx >= len(records):
        abort(404)

    # 해당 기록 삭제
    records.pop(idx)

    # 파일에 다시 저장
    save_all(records)

    # 관리자 페이지로 돌아가기
    return redirect(url_for("admin_page"))


# ======================
# 로컬 서버 실행
# ======================
if __name__ == "__main__":
    app.run()