# 公的データによる構造方程式モデリング — 再現用 Makefile
#
#   make setup    仮想環境と依存パッケージ（Python 3.13 が必要）
#   make all      data/raw から全分析と全図を再生成（ネットワーク不要）
#   make fetch    生データを公的機関から取り直す（ネットワーク必要・上書き）
#   make clean    results/ と figures/ を空にする
#
# data/raw/ には取得済みの生データをコミットしてある。公的機関側の更新で
# 数値が変わると過去の結果が再現できなくなるため、あえて固定している。
# 最新値で追試したいときだけ `make fetch` を使う。

PY := .venv/bin/python
SRC := src

.PHONY: all setup fetch clean country pref muni figures

all: country pref muni figures

setup:
	python3.13 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# ---------- 国レベル（World Bank） ----------
country:
	$(PY) $(SRC)/sem_analysis.py
	$(PY) $(SRC)/robustness.py
	$(PY) $(SRC)/sem_country_v2.py
	$(PY) $(SRC)/country_life_residuals.py
	$(PY) $(SRC)/country_model_check.py

# ---------- 都道府県（e-Stat 社会生活統計指標） ----------
pref:
	$(PY) $(SRC)/estat_parse.py
	$(PY) $(SRC)/estat_sem.py
	$(PY) $(SRC)/job_sem.py
	$(PY) $(SRC)/pref_influence.py
	$(PY) $(SRC)/pref_residuals.py
	$(PY) $(SRC)/job_residuals.py
	$(PY) $(SRC)/job_screen.py

# ---------- 市区町村（e-Stat 統計でみる市区町村のすがた） ----------
muni:
	$(PY) $(SRC)/muni_parse.py
	$(PY) $(SRC)/muni_screen.py
	$(PY) $(SRC)/muni_path.py
	$(PY) $(SRC)/model_log.py

# ---------- 図 ----------
figures:
	$(PY) $(SRC)/make_path_diagram.py
	$(PY) $(SRC)/make_pref_diagram.py
	$(PY) $(SRC)/make_job_diagram.py
	$(PY) $(SRC)/make_country2_diagram.py
	$(PY) $(SRC)/make_muni_chart.py
	$(PY) $(SRC)/make_muni_path_diagram.py
	$(PY) $(SRC)/prediction_diagnostics.py
	$(PY) $(SRC)/sem_audit.py
	$(PY) $(SRC)/make_index.py
	$(PY) $(SRC)/make_manifest.py

fetch:
	$(PY) $(SRC)/fetch_data.py
	$(PY) $(SRC)/estat_fetch.py
	$(PY) $(SRC)/muni_fetch.py

clean:
	rm -f results/* figures/*
