"""
sensitivity_analysis.py
Phụ trách: Thành viên 3 

Kiểm định độ nhạy (sensitivity) của công thức Friction Score với lựa chọn
bộ trọng số, để trả lời câu hỏi "vì sao chọn trọng số này mà không phải
trọng số khác".

So sánh 3 bộ trọng số trên cùng 4 thành phần đã chuẩn hóa
(Capacity_Desire_Gap, JobSecurity_Concern, Enjoyment_Attachment,
HumanAgency_Resistance):

    1. "ban_dau"   : 40 / 20 / 20 / 20 - trọng số chủ quan ban đầu, ưu tiên
                     Capacity-Desire Gap vì đây là biến định nghĩa trực tiếp
                     "friction" theo đề bài.
    2. "pca"       : trọng số suy ra từ PCA (bình phương hệ số tải của PC1,
                     đã xoay dấu để Capacity_Desire_Gap dương). Chỉ dùng để
                     đối chiếu - xem docstring trong friction_score.py để
                     biết lý do PCA không phù hợp làm trọng số chính thức
                     (4 biến gần trực giao, PC1 chỉ giải thích 33.6% phương
                     sai, PC1 tải âm lên biến quan trọng nhất).
    3. "bang_nhau" : 25 / 25 / 25 / 25 - bộ trọng số CHÍNH THỨC dùng trong
                     friction_score.py, có cơ sở thống kê từ chính tính
                     trực giao giữa 4 biến.

Đo độ ổn định bằng hệ số tương quan hạng Spearman giữa thứ hạng Friction
Score của 3 bộ trọng số, và so sánh trực tiếp danh sách Top-15 task.

Xuất ra:
    data/processed/friction_sensitivity_top15.csv
    data/processed/friction_sensitivity_spearman.csv

Cách chạy:
    python sensitivity_analysis.py
(đọc/ghi vào ../data/processed so với vị trí file này, giống friction_score.py)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from friction_score import (
    PROCESSED_DIR,
    SENSITIVITY_DIR,
    HUMAN_AGENCY_RESISTANCE_COLS,
    load_processed_data,
    filter_scoreable_tasks,
    compute_friction_components,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COMPONENT_COLS = [
    "Capacity_Desire_Gap_Norm",
    "JobSecurity_Concern_Norm",
    "Enjoyment_Attachment_Norm",
    "HumanAgency_Resistance_Norm",
]

# Bộ trọng số cần so sánh 
WEIGHT_SCHEMES: dict[str, dict[str, float]] = {
    "ban_dau": {
        "Capacity_Desire_Gap_Norm": 0.40,
        "JobSecurity_Concern_Norm": 0.20,
        "Enjoyment_Attachment_Norm": 0.20,
        "HumanAgency_Resistance_Norm": 0.20,
    },
    "bang_nhau": {
        "Capacity_Desire_Gap_Norm": 0.25,
        "JobSecurity_Concern_Norm": 0.25,
        "Enjoyment_Attachment_Norm": 0.25,
        "HumanAgency_Resistance_Norm": 0.25,
    },
    # "pca" được tính động từ dữ liệu thực tế bên dưới (compute_pca_weights)
}


def compute_pca_weights(components: pd.DataFrame) -> dict[str, float]:
    """Suy ra trọng số từ PCA trên 4 thành phần đã chuẩn hóa.

    Lấy hệ số tải (loading) của PC1 sau khi standardize, xoay dấu sao cho
    Capacity_Desire_Gap_Norm luôn dương, sau đó bình phương và chuẩn hóa để tổng = 1. 
    Bình phương loading là cách diễn giải "tỷ lệ đóng góp vào phương sai PC1" - 
    luôn không âm nên tránh được vấn đề trọng số âm vô nghĩa.

    """
    X = components[COMPONENT_COLS].values
    std = X.std(axis=0)
    std[std == 0] = 1.0  # tránh chia 0 nếu 1 cột hằng số
    Xc = (X - X.mean(axis=0)) / std

    _, singular_values, Vt = np.linalg.svd(Xc, full_matrices=False)
    explained_var_ratio = (singular_values ** 2) / np.sum(singular_values ** 2)

    pc1_loadings = Vt[0]
    anchor_idx = COMPONENT_COLS.index("Capacity_Desire_Gap_Norm")
    if pc1_loadings[anchor_idx] < 0:
        pc1_loadings = -pc1_loadings

    squared = pc1_loadings ** 2
    weights = squared / squared.sum()

    logger.info(
        "PCA: PC1 giai thich %.1f%% phuong sai (PC2: %.1f%%) -> tin cay thap "
        "vi khong co truc chinh ap dao (4 bien gan truc giao).",
        explained_var_ratio[0] * 100, explained_var_ratio[1] * 100,
    )
    return dict(zip(COMPONENT_COLS, weights))


def score_with_weights(components: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Tính Friction Score (0-100) từ 1 bộ trọng số cho trước."""
    total = sum(weights[c] * components[c] for c in COMPONENT_COLS)
    return (total * 100).round(2)


def build_sensitivity_tables() -> dict[str, pd.DataFrame]:
    """Chạy pipeline: load -> lọc -> tính component -> tính Friction Score
    với cả 3 bộ trọng số -> so sánh Top-15 + tương quan hạng Spearman."""
    data = load_processed_data()
    scoreable = filter_scoreable_tasks(data["master"])
    components = compute_friction_components(scoreable)

    schemes = dict(WEIGHT_SCHEMES)
    schemes["pca"] = compute_pca_weights(components)

    scores = pd.DataFrame({
        "Task ID": components["Task ID"],
        "Occupation (O*NET-SOC Title)": components["Occupation (O*NET-SOC Title)"],
        "Task": components["Task"],
    })
    for name, w in schemes.items():
        scores[f"Friction_{name}"] = score_with_weights(components, w)

    # --- Top-15 theo từng bộ trọng số, đặt cạnh nhau để so sánh trực quan ---
    top15_frames = []
    for name in schemes:
        top = scores.nlargest(15, f"Friction_{name}")[
            ["Task ID", "Occupation (O*NET-SOC Title)", f"Friction_{name}"]
        ].reset_index(drop=True)
        top.insert(0, "Hang", top.index + 1)
        top = top.rename(columns={f"Friction_{name}": "Friction Score"})
        top.insert(1, "Bo_Trong_So", name)
        top15_frames.append(top)
    top15 = pd.concat(top15_frames, ignore_index=True)

    # --- Đo độ ổn định thứ hạng giữa các bộ trọng số bằng Spearman ---
    scheme_names = list(schemes.keys())
    spearman_rows = []
    for i in range(len(scheme_names)):
        for j in range(i + 1, len(scheme_names)):
            a, b = scheme_names[i], scheme_names[j]
            rho, pval = spearmanr(scores[f"Friction_{a}"], scores[f"Friction_{b}"])
            n_overlap_top15 = len(
                set(scores.nlargest(15, f"Friction_{a}")["Task ID"])
                & set(scores.nlargest(15, f"Friction_{b}")["Task ID"])
            )
            spearman_rows.append({
                "So_Sanh": f"{a} vs {b}",
                "Spearman_Rho": round(rho, 4),
                "P_Value": round(pval, 6),
                "Overlap_Top15": f"{n_overlap_top15}/15",
            })
    spearman_table = pd.DataFrame(spearman_rows)

    logger.info("Ket qua tuong quan hang Spearman giua cac bo trong so:\n%s", spearman_table.to_string(index=False))

    return {
        "full_scores": scores,
        "top15": top15,
        "spearman": spearman_table,
        "weight_schemes": pd.DataFrame(schemes).T.rename_axis("Bo_Trong_So").reset_index(),
    }


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SENSITIVITY_DIR.mkdir(parents=True, exist_ok=True)

    tables = build_sensitivity_tables()

    top15_path = SENSITIVITY_DIR / "friction_sensitivity_top15.csv"
    spearman_path = SENSITIVITY_DIR / "friction_sensitivity_spearman.csv"
    weights_path = SENSITIVITY_DIR / "friction_sensitivity_weight_schemes.csv"

    tables["top15"].to_csv(
        top15_path,
        index=False,
        encoding="utf-8-sig",
    )

    tables["spearman"].to_csv(
        spearman_path,
        index=False,
        encoding="utf-8-sig",
    )

    tables["weight_schemes"].to_csv(
        weights_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"[OK] Đã xuất Top-15 -> {top15_path}")
    print(f"[OK] Đã xuất Spearman -> {spearman_path}")
    print(f"[OK] Đã xuất Weight Schemes -> {weights_path}")


if __name__ == "__main__":
    main()