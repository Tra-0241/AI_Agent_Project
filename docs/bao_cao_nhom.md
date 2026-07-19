# Báo cáo nhóm (bản nháp)

> File này là bản nháp markdown để cả nhóm cùng chỉnh sửa trên GitHub.
> Khi nộp bài, xuất bản hoàn chỉnh sang `.docx` hoặc `.pdf` theo yêu cầu đề bài.

## 1. Mục tiêu đề tài

**AI Agent Deployment Blueprint** là mô hình định lượng nhằm hỗ trợ ra quyết định
triển khai AI Agent (tự động hóa bằng AI) trong khối ngành Công nghệ thông tin (IT),
giải quyết đồng thời hai bài toán mà doanh nghiệp thường tách rời khi đánh giá tự
động hóa:

1. **Bài toán kinh tế** - Task nào trong khối IT mang lại lợi ích kinh tế lớn nhất
   nếu được tự động hóa bằng AI? (đo lường qua **ROI Index**, dựa trên mức lương,
   quy mô nhân sự, và khả năng AI thực sự làm được task đó theo đánh giá chuyên gia).
2. **Bài toán con người** - Task nào, dù có tiềm năng tự động hóa cao, vẫn tiềm ẩn
   **lực cản từ chính người lao động** (lo ngại mất việc, mất ý nghĩa công việc, hoặc
   cho rằng cần sự tham gia của con người)? (đo lường qua **Friction Score**, dựa
   trên khoảng cách giữa mong muốn tự động hóa của chuyên gia và của chính người
   lao động).

Mục tiêu cuối cùng là xây dựng một **bản đồ ưu tiên triển khai AI Agent** cho khối
ngành IT: xác định nhóm task "nên tự động hóa ngay" (ROI cao, Friction thấp), nhóm
"cần quản trị thay đổi kỹ trước khi triển khai" (ROI cao, Friction cao), và nhóm
"chưa nên ưu tiên" (ROI thấp), giúp doanh nghiệp vừa tối ưu chi phí – lợi ích, vừa
giảm rủi ro phản ứng tiêu cực từ nhân sự khi áp dụng AI Agent.

## 2. Nguồn dữ liệu và phương pháp xử lý

### 2.1. Nguồn dữ liệu

Dữ liệu được lấy từ **WORKBank** - bộ dữ liệu khảo sát kết hợp giữa đánh giá của
chuyên gia công nghệ và khảo sát trực tiếp người lao động về mức độ mong muốn/lo
ngại tự động hóa AI đối với từng đầu việc cụ thể (task) trong nhiều ngành nghề
theo chuẩn phân loại nghề **O\*NET-SOC** của Bộ Lao động Hoa Kỳ. Gồm 4 file gốc:

| File | Cấp dữ liệu | Số dòng gốc | Nội dung chính |
|---|---|---|---|
| `task_statement_with_metadata.csv` | 1 dòng / Task ID | 2.131 | Mô tả task, nghề, tần suất/độ quan trọng, lương & quy mô nhân sự theo nghề |
| `expert_rated_technological_capability.csv` | 1 dòng / (Task ID × chuyên gia) | 2.057 | Đánh giá của chuyên gia công nghệ về khả năng AI thực hiện được task |
| `domain_worker_desires.csv` | 1 dòng / (Task ID × worker) | 5.731 | Mong muốn/lo ngại tự động hóa của chính người lao động, kèm lý do |
| `domain_worker_metadata.csv` | 1 dòng / User ID | 1.500 | Hồ sơ nhân khẩu học và thái độ với AI của người lao động |

### 2.2. Phương pháp merge dữ liệu

Dữ liệu được nối theo 2 khóa:

- **`Task ID`**: nối `task_statement` ↔ `expert_rated` ↔ `domain_worker_desires`.
- **`User ID`**: nối `domain_worker_desires` ↔ `domain_worker_metadata` (lưu ý: cột
  `User ID` trong `expert_rated` là **mã định danh chuyên gia** - hoàn toàn khác với
  `User ID` (UUID) của người lao động trong 2 file còn lại, **không được nhầm lẫn
  khi merge**).

Vì một task có thể được **nhiều chuyên gia** và **nhiều người lao động** đánh giá
(1 Task ID ↔ nhiều dòng ở cả `expert_rated` và `domain_worker_desires`), dữ liệu
được **gộp (aggregate) theo Task ID trước khi merge vào bảng task** - lấy trung
bình các điểm đánh giá số và tỷ lệ (%) người chọn từng lý do - nhằm tránh lỗi nhân
bản dữ liệu (tích Descartes) nếu merge trực tiếp mà không gộp trước.

### 2.3. Lọc khối ngành IT

Việc lọc được thực hiện dựa trên **mã nghề chuẩn O\*NET-SOC** thay vì so khớp tên
chuỗi (để tránh sai sót do viết hoa/thường hoặc gõ sai tên nghề). Nhóm nghề IT được
xác định gồm nhóm **15-12xx "Computer Occupations"** theo phân loại SOC, bổ sung mã
**11-3021.00 "Computer and Information Systems Managers"** (quản lý trực tiếp khối
IT). Tổng cộng **18 nghề** được đưa vào phạm vi phân tích, bao gồm: Computer Systems
Analysts, Information Security Analysts, Computer Programmers, Software Quality
Assurance Analysts and Testers, Web Developers, Database Administrators/Architects,
Computer Network Architects, Network and Computer Systems Administrators,
Information Technology Project Managers... (danh sách đầy đủ trong biến
`IT_OCCUPATION_SOC_CODES`, file `src/data_processing.py`).

Các nghề có chữ "Computer" trong tên nhưng **không** thuộc khối IT vận hành/phát
triển phần mềm bị loại có chủ đích: Computer Hardware Engineers (kỹ thuật phần
cứng), Computer Science Teachers (giáo dục), Computer/ATM/Office Machine Repairers
(sửa chữa thiết bị), Computer Numerically Controlled (CNC) Tool
Operators/Programmers (vận hành máy công nghiệp).

Sau khi lọc: **186 task** (trên tổng 2.131 task gốc) thuộc **18 nghề IT**, trong đó
**131 task** có đủ cả đánh giá của chuyên gia lẫn người lao động.

### 2.4. Làm sạch dữ liệu (Data Cleaning)

| Vấn đề phát hiện | Cách xử lý |
|---|---|
| Cột Date lưu dạng chuỗi, 2 định dạng khác nhau giữa các file (`MM/YYYY` và `YYYY/M/D`) | Chuẩn hóa về kiểu `datetime` |
| Cột Reason (Automation Desire / Human Agency) là dạng cờ, dùng để tính tỷ lệ % | Ép kiểu về `boolean` thật |
| Cột tự do "Other Reason for..." khi worker không điền lại lưu chuỗi `"FALSE"` (dễ bị hiểu nhầm là có nội dung) | Convert `"FALSE"` → `NaN` |
| Cột `Skill`, `Skill ID` lưu dưới dạng chuỗi biểu diễn list (`"['4.A.2.a.3']"`) | Parse thành list rồi nối lại bằng `;` để lưu CSV an toàn |
| Zip Code có cả dạng số nguyên và dạng mở rộng ZIP+4 (`85023-6767`) | Chuẩn hóa về string, giữ nguyên ZIP+4, đệm số 0 cho ZIP 5 số |
| 642/2.131 task thiếu `Occupation Mean Annual Wage`/`Employment` | **Không tự ý impute** - chỉ gắn cờ `Wage_Missing`/`Employment_Missing` để nhóm tính ROI (TV2) tự quyết định cách xử lý |
| Dữ liệu trùng lặp hoàn toàn ở `expert_rated`, `domain_worker_desires`, `domain_worker_metadata` | Loại bỏ bằng `drop_duplicates()` |
| Kiểm tra chéo tên Occupation giữa các file theo cùng Task ID | Có hàm cảnh báo tự động (`check_task_occupation_consistency`) - không phát hiện mismatch trong lần chạy hiện tại |

### 2.5. Đầu ra (Output)

Toàn bộ pipeline được đóng gói trong `src/data_processing.py` (script Python/pandas
tái sử dụng, có docstring cho từng hàm), sinh ra 3 file trong `data/processed/`:

- **`it_master.csv`** (186 dòng, 1 dòng/Task ID): bảng tổng hợp cấp task, gồm Wage,
  Employment, điểm đánh giá trung bình từ chuyên gia (`Expert_*`) và từ người lao
  động (`Worker_*`), tỷ lệ lý do (`Share_AutoDesire_*`, `Share_HumanAgency_*`) -
  input chính cho **ROI Index** (TV2) và **Friction Score** (TV3).
- **`it_worker_level.csv`** (1.002 dòng, 1 dòng/Task ID × User ID): dữ liệu chi
  tiết cấp cá nhân, giữ nguyên thông tin nhân khẩu học/thái độ AI - dùng khi TV3
  cần phân tích Friction Score theo nhóm (giới tính, độ tuổi, kinh nghiệm, thái độ
  với AI...).
- **`it_master_data_dictionary.csv`**: bảng tra cứu ý nghĩa từng cột, dùng chung
  cho cả nhóm khi triển khai bước phân tích tiếp theo.

## 3. Phương pháp tính ROI Index

### 3.1. Mục tiêu và phạm vi

ROI Index được xây dựng để **xếp hạng mức độ ưu tiên kinh tế tương đối** của các
task IT khi xem xét triển khai AI Agent. Chỉ số không phải ROI kế toán theo công
thức `(lợi ích - chi phí) / chi phí`, vì WORKBank không cung cấp chi phí phát
triển, hạ tầng, API, bảo trì, đào tạo và giám sát AI. Do đó, kết quả nên được hiểu
là thước đo **Economic Opportunity** phục vụ bước sàng lọc trước khi doanh nghiệp
thực hiện pilot và đo ROI tài chính thực tế.

### 3.2. Biến đầu vào và xử lý dữ liệu thiếu

Chỉ số sử dụng sáu biến trong `it_master.csv`: `Occupation Mean Annual Wage`,
`Occupation Employment`, `Frequency`, `Importance`, `Worker_Time` và
`Expert_Automation Capacity Rating`. Một task chỉ được xếp hạng khi cả sáu biến
có giá trị hợp lệ; các task còn lại được giữ trong bảng kết quả nhưng gắn vùng
`Chưa đủ dữ liệu`, thay vì tự động điền 0 hoặc loại khỏi đầu ra.

Trong 186 task IT, có **102 task đủ dữ liệu** để tính ROI Index và 84 task thiếu
ít nhất một thành phần. Theo codebook WORKBank, `Worker_Time` có thang 1–5, với
1 tương ứng 10% và 5 tương ứng 100% thời gian làm việc. Nghiên cứu nội suy tuyến
tính giữa hai neo để tạo `Time Share Proxy`; biến này không được diễn giải thành
số giờ tiết kiệm thực tế.

### 3.3. Công thức

Quy mô giá trị lao động của nghề được tính bằng:

`Market Scale = percentile-rank(log(1 + Annual Wage × Employment))`

Biến đổi log giúp hạn chế việc các nghề có quy mô nhân sự rất lớn áp đảo toàn bộ
bảng xếp hạng. Phân vị được tính trên danh sách nghề duy nhất để nghề có nhiều
task không tự tạo thêm trọng số. Mức độ hiện diện của task được tính bằng:

`Time Share Proxy = 0,10 + 0,90 × (Worker Time - 1) / 4`

`Frequency Intensity = (Frequency - 1) / 6`

`Importance Intensity = (Importance - 1) / 4`

`Task Exposure = 0,50 × Time Share Proxy + 0,25 × Frequency Intensity + 0,25 × Importance Intensity`

Frequency và Importance được chuẩn hóa theo neo đầy đủ của thang O*NET, thay vì
Min-Max theo mẫu quan sát. Nhờ vậy, Frequency = 3 (hơn một lần mỗi tháng) không
bị gán sai thành mức 0 chỉ vì đây là giá trị nhỏ nhất xuất hiện trong mẫu IT.

Khả năng AI thực hiện task được đưa từ thang 1–5 về 0–1:

`Automation Potential = (Expert Automation Capacity - 1) / 4`

Tiềm năng kinh tế thô và ROI Index cuối cùng được tính như sau:

`Economic Potential Raw = Market Scale × Task Exposure × Automation Potential`

`ROI Index = MinMax(Economic Potential Raw)`

Phép nhân được chọn để một thành phần rất cao không thể che lấp hoàn toàn một
thành phần gần bằng 0. ROI Index cuối cùng nằm trong khoảng 0–1; điểm càng cao
thể hiện mức ưu tiên kinh tế tương đối càng lớn trong phạm vi tập dữ liệu IT.

### 3.4. Phân vùng chiến lược và độ tin cậy

Ngưỡng vùng được xác định theo phân vị của 102 task đủ dữ liệu, thay vì dùng
ngưỡng cố định tùy ý:

| Vùng chiến lược | Quy tắc | Số task |
|---|---:|---:|
| Tự động hóa ngay | ROI Index từ phân vị 75% trở lên | 26 |
| Cân nhắc | Từ phân vị 40% đến dưới phân vị 75% | 35 |
| Giữ nguyên / Theo dõi | Dưới phân vị 40% | 41 |
| Chưa đủ dữ liệu | Thiếu ít nhất một biến bắt buộc | 84 |

Độ tin cậy được gắn `Cao` khi task đủ dữ liệu, có 3 chuyên gia và ít nhất 8 worker
đánh giá; các task đủ dữ liệu còn lại được gắn `Trung bình`. Đây là chỉ báo mô tả
sức mạnh bằng chứng, không phải xác suất thống kê rằng kết quả đúng.

### 3.5. Kết quả nổi bật

Các task đứng đầu ROI Index tập trung vào hỗ trợ người dùng, quản trị hệ thống,
báo cáo vận hành và tài liệu kiểm thử - những hoạt động có quy mô lao động đáng
kể, xuất hiện thường xuyên và được chuyên gia đánh giá có khả năng tự động hóa
cao. Năm task đứng đầu gồm:

| Hạng | Nghề | Task (rút gọn) | ROI Index | Độ tin cậy |
|---:|---|---|---:|---|
| 1 | Computer User Support Specialists | Trả lời yêu cầu phần mềm/phần cứng để xử lý sự cố | 1,000 | Trung bình |
| 2 | Computer User Support Specialists | Giám sát hiệu năng hằng ngày của hệ thống | 0,949 | Trung bình |
| 3 | Computer User Support Specialists | Duy trì hồ sơ giao dịch, sự cố và biện pháp khắc phục | 0,862 | Trung bình |
| 4 | Computer and Information Systems Managers | Quản lý backup, bảo mật và hệ thống hỗ trợ người dùng | 0,837 | Trung bình |
| 5 | Computer User Support Specialists | Nhập lệnh, quan sát vận hành và phát hiện lỗi | 0,832 | Trung bình |

Kết quả trên phản ánh **tiềm năng ưu tiên**, chưa phải khuyến nghị thay thế hoàn
toàn con người. Khi đưa lên dashboard, ROI Index cần được kết hợp với Friction
Score: task ROI cao và Friction thấp phù hợp để pilot sớm; task ROI cao nhưng
Friction cao cần triển khai theo mô hình human-in-the-loop và có kế hoạch quản
trị thay đổi.

### 3.6. Giới hạn và hướng đo ROI thực tế

- Wage và Employment là dữ liệu cấp nghề, vì vậy các task cùng nghề dùng chung
  quy mô thị trường lao động.
- ROI Index nhạy với phạm vi tập dữ liệu và phương pháp chuẩn hóa; không nên so
  sánh trực tiếp với chỉ số được tính trên một ngành khác.
- `Worker_Time` chỉ là tỷ lệ tự báo cáo dạng thang đo; chưa có số giờ làm thực
  tế, tỷ lệ AI được chấp nhận và chi phí triển khai.
- Sau pilot, doanh nghiệp cần đo thời gian xử lý, tỷ lệ lỗi, sản lượng, chi phí
  AI/hạ tầng và thời gian kiểm duyệt. Khi đó ROI tài chính mới được tính bằng
  `(Annual Benefit - Annual Cost) / Annual Cost`.

Mã tính toán được đóng gói trong `src/roi_index.py`, có kiểm tra schema, xử lý
missing value, đánh giá độ tin cậy và xuất `data/processed/roi_index.csv` làm
input cho Tab 1 Dashboard.

## 4. Phương pháp tính Friction Score

## 5. Biểu đồ & Insight

## 6. Đề xuất ứng dụng AI Agent

## 7. Kết luận
