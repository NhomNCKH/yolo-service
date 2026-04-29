# YOLO Proctoring Service

Đây là service dùng `FastAPI` để chạy model YOLO phục vụ proctoring thi online theo thời gian thực. Service hỗ trợ:

- kiểm tra trạng thái hoạt động
- phân tích ảnh qua REST API
- nhận frame qua WebSocket
- dùng Redis để publish các cảnh báo vi phạm

## 1. Cần chuẩn bị trước

Máy chạy service cần có:

- Python `3.10` hoặc `3.11`
- `pip`
- `git`
- Redis

Nếu muốn chạy bằng Docker thì cần cài thêm:

- Docker

## 2. Clone project

```powershell
git clone https://github.com/NhomNCKH/yolo-service.git
cd yolo-service
```

## 3. Cách chạy ở máy local
# Terminal 1: Redis
docker run -d -p 6379:6379 redis

# Terminal 2: YOLO service
cd D:\NCKH\yolo-service
source venv/Scripts/activate
python -m uvicorn app.main:app --reload --port 8001

# Terminal 3: Backend NestJS
cd D:\NCKH\ToeicBoost_BE
npm run start:dev

# Terminal 4: Frontend
cd D:\NCKH\ToeicBoost_FE
npm run dev

### Bước 1: Tạo môi trường ảo

```powershell
python -m venv venv
venv\Scripts\activate
```

### Bước 2: Cài thư viện

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 3: Tạo file cấu hình `.env`

Copy file mẫu:

```powershell
copy .env.example .env
```

Nội dung mặc định:

```env
HOST=0.0.0.0
PORT=8001
MODEL_PATH=models/yolov8n.pt
REDIS_HOST=localhost
REDIS_PORT=6379
CONFIDENCE_THRESHOLD=0.5
MAX_WARNINGS=5
VIOLATION_WINDOW_SECONDS=60
```

Ý nghĩa ngắn gọn:

- `HOST`: địa chỉ service sẽ bind
- `PORT`: cổng chạy API
- `MODEL_PATH`: đường dẫn tới file model
- `REDIS_HOST`, `REDIS_PORT`: thông tin Redis
- `CONFIDENCE_THRESHOLD`: ngưỡng confidence của model

### Bước 4: Chuẩn bị file model

Service hiện đang đọc model tại:

```text
models/yolov8n.pt
```

Nếu chưa có file này thì chạy:

```powershell
mkdir models
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
move yolov8n.pt models\yolov8n.pt
```

Nếu bạn dùng model custom, ví dụ `best.pt`, thì:

1. chép file vào thư mục `models/`
2. sửa `MODEL_PATH` trong `.env`

Ví dụ:

```env
MODEL_PATH=models/best.pt
```

### Bước 5: Chạy Redis

Nếu máy đã cài Redis sẵn thì chỉ cần bật Redis lên trước khi chạy service.

Nếu muốn chạy Redis bằng Docker:

```powershell
docker run -d --name yolo-redis -p 6379:6379 redis:7
```

### Bước 6: Chạy service

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Sau khi chạy xong, service sẽ hoạt động tại:

```text
http://localhost:8001
```

## 4. Chạy bằng Docker

### Build image

```powershell
docker build -t yolo-service .
```

### Chạy container

```powershell
docker run -p 8001:8001 --env-file .env yolo-service
```

Lưu ý:

- `Dockerfile` dùng file model đang có sẵn trong thư mục `models/`
- nếu service cần Redis thì phải đảm bảo `REDIS_HOST` trỏ đúng tới Redis đang chạy

### Chạy production bằng Docker Compose

File `docker-compose.yml` đã đóng gói sẵn:

- `yolo-service`
- `redis`

Chạy:

```bash
cp .env.example .env
docker compose up -d --build
```

Kiểm tra:

```bash
docker compose ps
curl http://localhost:8001/health
```

Tắt:

```bash
docker compose down
```

## 5. Chạy như một service trên server

Repo đã kèm sẵn unit file:

```text
deploy/systemd/yolo-service.service
```

Quy ước deploy:

```bash
mkdir -p /opt/yolo-service
cd /opt/yolo-service
# copy source code vào đây
cp .env.example .env
docker compose up -d --build
cp deploy/systemd/yolo-service.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now yolo-service
```

Lệnh vận hành:

```bash
systemctl status yolo-service
journalctl -u yolo-service -f
docker compose logs -f yolo-service
```

## 6. Kiểm tra service đã chạy chưa

### Kiểm tra health

```powershell
curl http://localhost:8001/health
```

Kết quả mong đợi:

```json
{
  "status": "ok",
  "model_loaded": true,
  "redis_connected": true
}
```

### Kiểm tra trạng thái service

```powershell
curl http://localhost:8001/api/status
```

### Test phân tích một ảnh

```powershell
curl -X POST "http://localhost:8001/api/analyze" `
  -F "file=@test.jpg" `
  -F "user_id=user123" `
  -F "exam_id=exam456"
```

## 7. WebSocket để gửi frame realtime

Endpoint WebSocket:

```text
ws://localhost:8001/ws/{user_id}/{exam_id}
```

Ví dụ:

```text
ws://localhost:8001/ws/user123/exam456
```

Frontend có thể mở kết nối tới endpoint này và gửi frame ảnh dạng base64 để service xử lý.

## 8. Cấu trúc thư mục chính

```text
yolo-service/
|-- app/
|   |-- main.py
|   |-- api.py
|   |-- config.py
|   |-- models/
|   |-- services/
|-- models/
|   |-- yolov8n.pt
|-- requirements.txt
|-- Dockerfile
|-- .env.example
```

## 8. Một số lưu ý

- không nên push `.env`
- không nên push thư mục `venv/`
- nếu model quá nặng thì không nên đẩy trực tiếp lên GitHub, nên dùng link tải ngoài hoặc Git LFS
- lần chạy đầu tiên có thể hơi lâu vì service cần load model
- nếu frontend gọi sang service này thì nhớ kiểm tra lại URL và port cho đúng
