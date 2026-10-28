# MST Crawler

Thu thập danh sách doanh nghiệp (MST + tên) từ masothue.com theo **tỉnh → phường/xã** theo **phân loại mới** (34 tỉnh, ~3.300 xã / phường / đặc khu; bỏ quận/huyện cũ).

Mỗi danh sách trên trang chỉ hiển thị tối đa **10 trang × 25 = 250** công ty mới nhất, nên app quét từng đơn vị nhỏ nhất rồi gộp và lọc trùng theo MST.

## Cài đặt

Cần Python 3.10+.

```bash
git clone <repo-url> mst-crawler
cd mst-crawler
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Sử dụng

```bash
python -m mst_crawler discover                  # 1. lấy danh sách tỉnh -> phường/xã (~3.300 xã/phường/đặc khu)
python -m mst_crawler crawl                     # 2. quét công ty lần lượt từng tỉnh (xong tỉnh này mới sang tỉnh kế; tự chạy tiếp chỗ dừng)
python -m mst_crawler crawl --province ha-noi   #    chỉ quét 1 tỉnh
python -m mst_crawler stats                     # 3. thống kê + tỷ lệ trùng
python -m mst_crawler dashboard                 #    web theo dõi tiến độ: http://localhost:8000 (mở terminal khác, chạy song song crawl)
python -m mst_crawler export -o data/companies.csv   # 4. xuất CSV đã lọc trùng
```

Tham số `crawl`: `--workers` (mặc định 1), `--delay` giây giữa request (mặc định 2).

- Dữ liệu lưu trong `data/mst.sqlite`. Ngắt (Ctrl+C) hay bị chặn đều chạy lại được, các phường đã xong sẽ được bỏ qua.
- Khi bị chặn liên tục, app tự dừng với exit code 2. Đợi một lúc rồi chạy lại, hoặc giảm `--workers` / tăng `--delay`.
- Thử nghiệm: 4 luồng × 0,8 s bị chặn sau ~3 phút. Nên giữ 1 luồng, 2 s.

## Docker

```bash
docker build -t mst-crawler .
docker run --rm -v "$PWD/data:/app/data" mst-crawler discover
docker run --rm -v "$PWD/data:/app/data" mst-crawler crawl
docker run --rm -v "$PWD/data:/app/data" mst-crawler stats
```

## Cấu trúc

| File | Vai trò |
|---|---|
| `mst_crawler/__main__.py` | CLI |
| `mst_crawler/crawler.py` | discover / crawl |
| `mst_crawler/fetcher.py` | HTTP, delay, retry, phát hiện bị chặn |
| `mst_crawler/parser.py` | tách link & công ty từ HTML |
| `mst_crawler/storage.py` | SQLite, lọc trùng theo MST |
| `mst_crawler/dashboard.py` | dashboard web (tiến độ theo tỉnh, tỷ lệ trùng) |

Lưu ý: tôn trọng điều khoản sử dụng của trang và giữ tốc độ thấp.
