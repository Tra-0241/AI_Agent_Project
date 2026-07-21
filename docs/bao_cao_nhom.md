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

### 4.1. Định nghĩa và phạm vi dữ liệu nghiên cứu

**Friction Score** được xây dựng nhằm **định lượng mức độ xung đột hoặc lực cản tâm lý** khi áp dụng AI Agent vào các tác vụ công nghệ thông tin. Chỉ số này phản ánh khoảng cách giữa:

- **Năng lực thực tế của AI** (dựa trên đánh giá chuyên gia),
- **Nguyện vọng giữ lại tác vụ của người lao động** (dựa trên khảo sát thực tế).

Nói cách khác, Friction Score đo lường mức độ mà AI có khả năng đảm nhiệm, nhưng nhân sự vận hành **không sẵn sàng chuyển giao**.

Để đảm bảo tính chính xác và khách quan, chỉ số được tính trên **131/186 task IT** đáp ứng đủ dữ liệu đồng thời từ cả hai phía: đánh giá chuyên gia và khảo sát người lao động. 55 task còn lại bị loại bỏ khỏi phạm vi phân tích do thiếu dữ liệu ở một trong hai nguồn, thay vì áp dụng các phương pháp gán thế (imputation). Hướng tiếp cận này giúp giảm thiểu nguy cơ **sai lệch phân bổ tự nhiên** hoặc tạo ra **nhiễu sai số hệ thống** trong mô hình.

### 4.2. Công thức và mô hình toán học

**Friction Score** (chuẩn hóa về thang điểm 0–100) được cấu thành từ **tổng có trọng số của 4 chỉ báo thành phần**. Mỗi thành phần được **chuẩn hóa Min-Max về miền [0, 1]** dựa trên phân bố thực nghiệm của 131 task được chọn.

Các thành phần bao gồm:

- **Capacity–Desire Gap**: phản ánh trạng thái AI vượt trội hơn so với mong muốn chuyển giao của con người.
  - Công thức: `max(0, Automation Capacity - Automation Desire)`
  - Sau đó chuẩn hóa Min-Max.
- **Job Security Concern**: đo lường áp lực tâm lý lo ngại mất việc.
  - Công thức: `1 - min-max(Job Security Rating)`.
- **Enjoyment Attachment**: biểu thị xu hướng giữ lại tác vụ mang lại niềm vui hoặc giá trị tự thân.
  - Công thức: `min-max(Enjoyment Rating)`.
- **Human Agency Resistance**: phản ánh nhu cầu duy trì quyền kiểm soát, sự thấu cảm và trách nhiệm đạo đức.
  - Công thức: trung bình của ba tỷ lệ thành phần `Control Ratio`, `Empathy Ratio`, `Ethical Ratio`, sau đó chuẩn hóa Min-Max.

Công thức tổng quát:

`Friction Score = 100 × [0.25 × Gap + 0.25 × Job Security Concern + 0.25 × Enjoyment Attachment + 0.25 × Human Agency Resistance]`

### 4.3. Cơ sở lựa chọn trọng số

Trong giai đoạn thiết kế mô hình, nhóm đã cân nhắc dùng **PCA** để xác định trọng số khách quan dựa trên cấu trúc biến động. Tuy nhiên, kết quả thực nghiệm cho thấy PCA không phù hợp với bản chất lý thuyết của bài toán bởi:

- **Tính độc lập của các chỉ báo**: hệ số tương quan giữa 4 thành phần rất thấp (`|r| = 0,10–0,22`), cho thấy chúng gần như trực giao, không có dư thừa để PCA khai thác.
- **Không có trục chính chi phối**: PC1 chỉ giải thích `33,6%` phương sai, gần bằng PC2 (`31,2%`), không đủ để đại diện cho toàn bộ cấu trúc dữ liệu.
- **Mâu thuẫn logic**: PCA tải âm lên biến *Capacity–Desire Gap* — biến hạt nhân của lý thuyết lực cản — khiến PC1 chỉ gán `3,0%` trọng số cho biến này, trong khi chuyển phần lớn sang *Job Security* (`24,6%`), *Enjoyment* (`57,3%`) và *Human Agency* (`15,1%`).

Vì các thành phần có tính độc lập cao, mô hình trọng số bằng phương sai như PCA sẽ **sai lệch bản chất lý thuyết**. Do đó, nhóm chọn **trọng số bằng nhau**: mỗi thành phần đóng góp **25%**, đảm bảo vai trò ngang hàng của cả 4 khía cạnh lực cản.

### 4.4. Kiểm định độ nhạy

Để đánh giá độ bền vững của cấu trúc trọng số đồng đều, nhóm thực hiện kiểm định độ nhạy giữa ba kịch bản:

| Kịch bản | Hệ số Spearman (ρ) | Tỷ lệ trùng lặp Top-15 |
|---|---:|---:|
| Trọng số giả định ban đầu (40/20/20/20) vs. trọng số đồng đều (25/25/25/25) | 0.905 | 12 / 15 |
| Trọng số giả định ban đầu vs. trọng số thực nghiệm PCA | 0.428 | 4 / 15 |
| Trọng số đồng đều vs. trọng số thực nghiệm PCA | 0.687 | 7 / 15 |

Kết quả cho thấy mô hình **ổn định cao** khi chuyển từ bộ trọng số ban đầu sang bộ trọng số đồng đều (`ρ = 0.905`), với **Top 1 giữ nguyên** là task `14647` (Software Quality Assurance Analysts and Testers). Ngược lại, so với mô hình PCA, tương quan chỉ đạt `0.43–0.69`, khẳng định PCA không phản ánh đúng cấu trúc và bản chất của bài toán.

### 4.5. Thiết lập ngưỡng cảnh báo vận hành

Nhóm thiết lập ngưỡng vận hành dựa trên **phân vị dữ liệu** để phục vụ công tác quản trị và ra quyết định:

- **Ngưỡng Đỏ (Cảnh báo Cao)**: 25% task có Friction Score cao nhất, tương ứng với giá trị thực nghiệm từ **47.64 điểm trở lên**.
- **Ngưỡng Xanh (An toàn / Lực cản thấp)**: các task còn lại dưới ngưỡng này.

Đây là ngưỡng **vận hành chủ động**, nhằm tối ưu hóa tài nguyên sàng lọc và giám sát. Đây không phải là một ranh giới phân tách thống kê tự nhiên mà là ngưỡng thực nghiệm phù hợp với mục tiêu quản lý rủi ro.

### 4.6. Kết quả thực nghiệm

Với công thức trên, phân bố Friction Score của 131 task cho kết quả:

- **Trung bình**: 41,92
- **Độ lệch chuẩn**: 9,30
- **Thấp nhất**: 22,21
- **Cao nhất**: 66,54

Trong đó:

- **33/131 task** (25%) được gắn cờ **Đỏ**.
- Các task Đỏ tập trung nhiều ở nhóm **Software Quality Assurance Analysts and Testers**, **Computer Systems Engineers/Architects**, **Computer User Support Specialists**.

Phân bố **“Lý do chính”** của 131 task:

- **Job Security**: 62 task (47%)
- **Enjoyment**: 57 task (44%)
- **Capacity–Desire Gap**: 10 task (8%)
- **Human Agency**: 2 task (1%)

Kết quả này cho thấy lực cản chủ yếu đến từ **lo ngại mất việc** và **mức độ gắn bó với công việc**, nhiều hơn so với khoảng cách “AI làm được vs muốn nhường” hoặc nhu cầu giữ quyền con người.

## 5. Biểu đồ & Insight

## 6. Đề xuất ứng dụng AI Agent

## 7. Kết luận
