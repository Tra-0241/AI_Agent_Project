# AI Agent Deployment Blueprint — Khối ngành IT

Mô hình tối ưu hóa ROI kinh tế và quản trị lực cản nhân sự khi triển khai AI Agent trong khối ngành IT, dựa trên bộ dữ liệu [WORKBank](https://huggingface.co/datasets/SALT-NLP/WORKBank).

## 1. Mục tiêu

- Đo lường **ROI Index**: mức độ đáng tự động hóa của từng task IT (dựa trên lương, số nhân sự, tần suất, khả năng AI làm được).
- Đo lường **Friction Score**: độ lệch pha giữa "AI làm được" (expert rating) và "người lao động muốn" (worker desire).
- Gợi ý **vai trò AI Agent** phù hợp cho từng nhóm task, và kỹ năng con người cần nâng cấp.
- Trực quan hóa toàn bộ qua **Streamlit Dashboard** 2 tab (Doanh nghiệp / Nhân sự).

## 2. Cấu trúc thư mục

```
ai-agent-it-roi-dashboard/
├── data/
│   ├── raw/                 # 4 file CSV gốc từ WORKBank (không commit dữ liệu lớn, xem .gitignore)
│   └── processed/           # it_master.csv và các bảng kết quả trung gian
├── src/                     # Logic xử lý dữ liệu, tách theo phân công từng thành viên
│   ├── data_processing.py   # TV1 - merge, lọc IT, làm sạch dữ liệu
│   ├── roi_index.py         # TV2 - tính ROI Index
│   ├── friction_score.py    # TV3 - tính Friction Score
│   └── agent_rules.py       # TV4 - bộ luật gợi ý AI Agent & kỹ năng cần học
├── app/
│   └── app.py                # TV4 - Streamlit Dashboard (Tab 1 & Tab 2)
├── notebooks/
│   └── 01_exploration.ipynb  # EDA, thử nghiệm trước khi đưa vào src/
├── docs/
│   ├── bao_cao_nhom.md       # Báo cáo nhóm (nháp, xuất .docx/.pdf khi nộp)
│   ├── slides/                # Slide trình bày (10-15 slide)
│   └── screenshots/           # Ảnh chụp dashboard để nộp kèm báo cáo
├── tests/
│   └── test_data_processing.py
├── requirements.txt
├── .gitignore
└── README.md
```

## 3. Phân công (tương ứng file `phan_cong_nhiem_vu.docx`)

| Thành viên | Vai trò | File chính phụ trách |
|---|---|---|
| TV1 | Data Engineer | `src/data_processing.py` → xuất `data/processed/it_master.csv` |
| TV2 | Data Analyst (Kinh tế) | `src/roi_index.py` |
| TV3 | Data Analyst (Nhân sự & Rủi ro) | `src/friction_score.py` |
| TV4 | Product/Dashboard Developer | `src/agent_rules.py`, `app/app.py` |

Chi tiết nhiệm vụ xem trong `docs/phan_cong_nhiem_vu.docx`.

## 4. Cài đặt & chạy thử

```bash
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Đặt 4 file CSV gốc vào data/raw/
#    task_statement_with_metadata.csv
#    expert_rated_technological_capability.csv
#    domain_worker_desires.csv
#    domain_worker_metadata.csv

# 4. Chạy pipeline xử lý dữ liệu (tạo it_master.csv)
python -m src.data_processing

# 5. Chạy Streamlit Dashboard
streamlit run app/app.py
```

## 5. Deploy

Deploy miễn phí qua [Streamlit Community Cloud](https://streamlit.io/cloud):
1. Push repo này lên GitHub (public hoặc kết nối repo private).
2. Vào Streamlit Community Cloud → New app → chọn repo, branch `main`, file `app/app.py`.
3. Thêm 4 file CSV vào `data/raw/` trong repo (hoặc dùng cơ chế upload/secrets nếu dữ liệu nhạy cảm).

## 6. Nguồn dữ liệu

- https://huggingface.co/datasets/SALT-NLP/WORKBank
- https://futureofwork.saltlab.stanford.edu/
- https://github.com/SALT-NLP/workbank
