from flask import Flask, render_template, request, redirect, url_for, abort, Response
import json
import os
from datetime import datetime, timedelta, timezone
import csv
import io

app = Flask(__name__)

DATA_FILE = "result.json"
ADMIN_PASSWORD = "password"
KST = timezone(timedelta(hours=9))


# ======================
# 헬스체크 (UptimeRobot용)
# ======================
@app.route("/")
def health():
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
    """이름-마니또 기록 추가"""
    records = load_data()
    records.append({
        "name": name,
        "manitto": manitto,
        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    })
    save_all(records)


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

    # GET이면 폼
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
# - 비번 맞으면 마니또 공개(show_full=True)
# - sort=1 이면 이름 가나다순 정렬
# - records에는 항상 원본 인덱스(_idx)가 붙어 있음
# ======================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    records_raw = load_data()  # 원본(제출 순서)

    # 각 레코드에 원본 인덱스를 달아줌
    records = [
        {**rec, "_idx": i}
        for i, rec in enumerate(records_raw)
    ]

    # 정렬 여부(쿼리 파라미터)
    sort_mode = request.args.get("sort", "0") == "1"
    if sort_mode:
        # 이름 기준으로 정렬 (표시 순서만 바뀜, _idx는 그대로)
        records.sort(key=lambda x: x["name"])

    # 최신 제출 5개 (원본 제출 순서 기준, 최신이 위로)
    summary = records_raw[-5:][::-1]

    # 비밀번호 확인 (마니또 공개용)
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

    # 인덱스 범위 체크
    if idx < 0 or idx >= len(records):
        abort(404)

    record = records[idx]

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name:
            record["name"] = new_name
            save_all(records)
        # 수정 후 /admin으로 이동
        return redirect(url_for("admin"))

    # GET: 수정 폼
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
    save_all(records)

    # 삭제 후 /admin으로 이동
    return redirect(url_for("admin"))


# ======================
# CSV 다운로드 (/admin/export_csv)
# ======================
@app.route("/admin/export_csv")
def export_csv():
    records_raw = load_data()

    # sort 파라미터 확인
    sort_mode = request.args.get("sort", "0") == "1"

    # 화면 정렬 기준 그대로 적용
    if sort_mode:
        # 이름순 정렬
        records = sorted(records_raw, key=lambda x: x["name"])
    else:
        # 제출순
        records = records_raw

    # CSV 생성
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["이름", "뽑은 마니또"])
    for r in records:
        writer.writerow([
            r.get("name", ""),
            r.get("manitto", "")
        ])

    csv_text = output.getvalue()
    output.close()

    # CP949로 변환 (엑셀 한글 깨짐 방지)
    csv_bytes = csv_text.encode("cp949", errors="ignore")

    return Response(
        csv_bytes,
        mimetype="text/csv; charset=cp949",
        headers={
            "Content-Disposition": "attachment; filename=result.csv"
        }
    )


# ======================
# 로컬 실행
# ======================
if __name__ == "__main__":
    app.run()