# -*- coding: utf-8 -*-
"""リポジトリ内のファイル配置を一箇所にまとめる。

    data/raw/        公的機関から落としてきた生データ（改変しない）
    data/processed/  それを機械可読に整形したもの
    results/         分析の出力（推定値・適合度・ブートストラップ等）
    figures/         図（SVG）

どのスクリプトも作業ディレクトリに依存しないよう、ここ経由でパスを作る。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

ESTAT_PREF_XLS = RAW / "estat_pref"      # 社会生活統計指標－都道府県の指標－2024
ESTAT_MUNI_XLS = RAW / "estat_muni"      # 統計でみる市区町村のすがた2026（基礎データ）

for _d in (RAW, PROCESSED, RESULTS, FIGURES, ESTAT_PREF_XLS, ESTAT_MUNI_XLS):
    _d.mkdir(parents=True, exist_ok=True)


def raw(name):
    """data/raw/<name> を Path で返す。"""
    return RAW / name


def processed(name):
    """data/processed/<name> を Path で返す。"""
    return PROCESSED / name


def result(name):
    """results/<name> を Path で返す。"""
    return RESULTS / name


def figure(name):
    """figures/<name> を Path で返す。"""
    return FIGURES / name
