# MST Crawler

Thu tháº­p danh sÃ¡ch doanh nghiá»‡p (MST + tÃªn) tá»« masothue.com theo **tá»‰nh â†’ phÆ°á»ng/xÃ£** theo **phÃ¢n loáº¡i má»›i** (34 tá»‰nh, ~3.300 xÃ£ / phÆ°á»ng / Ä‘áº·c khu; bá» quáº­n/huyá»‡n cÅ©).

Má»—i danh sÃ¡ch trÃªn trang chá»‰ hiá»ƒn thá»‹ tá»‘i Ä‘a **10 trang Ã— 25 = 250** cÃ´ng ty má»›i nháº¥t, nÃªn app quÃ©t tá»«ng Ä‘Æ¡n vá»‹ nhá» nháº¥t rá»“i gá»™p vÃ  lá»c trÃ¹ng theo MST.

## CÃ i Ä‘áº·t

Cáº§n Python 3.10+.

```bash
git clone <repo-url> mst-crawler
cd mst-crawler
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Sá»­ dá»¥ng

```bash
python -m mst_crawler discover                  # 1. láº¥y danh sÃ¡ch tá»‰nh -> phÆ°á»ng/xÃ£ (~3.300 xÃ£/phÆ°á»ng/Ä‘áº·c khu)
python -m mst_crawler crawl                     # 2. quÃ©t cÃ´ng ty láº§n lÆ°á»£t tá»«ng tá»‰nh (xong tá»‰nh nÃ y má»›i sang tá»‰nh káº¿; tá»± cháº¡y tiáº¿p chá»— dá»«ng)
python -m mst_crawler crawl --province ha-noi   #    chá»‰ quÃ©t 1 tá»‰nh
python -m mst_crawler stats                     # 3. thá»‘ng kÃª + tá»· lá»‡ trÃ¹ng
python -m mst_crawler dashboard                 #    web theo dÃµi tiáº¿n Ä‘á»™: http://localhost:8000 (má»Ÿ terminal khÃ¡c, cháº¡y song song crawl)
python -m mst_crawler export -o data/companies.csv   # 4. xuáº¥t CSV Ä‘Ã£ lá»c trÃ¹ng
```

Tham sá»‘ `crawl`: `--workers` (máº·c Ä‘á»‹nh 1), `--delay` giÃ¢y giá»¯a request (máº·c Ä‘á»‹nh 2).

- Dá»¯ liá»‡u lÆ°u trong `data/mst.sqlite`. Ngáº¯t (Ctrl+C) hay bá»‹ cháº·n Ä‘á»u cháº¡y láº¡i Ä‘Æ°á»£c, cÃ¡c phÆ°á»ng Ä‘Ã£ xong sáº½ Ä‘Æ°á»£c bá» qua.
- Khi bá»‹ cháº·n liÃªn tá»¥c, app tá»± dá»«ng vá»›i exit code 2. Äá»£i má»™t lÃºc rá»“i cháº¡y láº¡i, hoáº·c giáº£m `--workers` / tÄƒng `--delay`.
- Thá»­ nghiá»‡m: 4 luá»“ng Ã— 0,8 s bá»‹ cháº·n sau ~3 phÃºt. NÃªn giá»¯ 1 luá»“ng, 2 s.

## Docker

```bash
docker build -t mst-crawler .
docker run --rm -v "$PWD/data:/app/data" mst-crawler discover
docker run --rm -v "$PWD/data:/app/data" mst-crawler crawl
docker run --rm -v "$PWD/data:/app/data" mst-crawler stats
```

## Cáº¥u trÃºc

| File | Vai trÃ² |
|---|---|
| `mst_crawler/__main__.py` | CLI |
| `mst_crawler/crawler.py` | discover / crawl |
| `mst_crawler/fetcher.py` | HTTP, delay, retry, phÃ¡t hiá»‡n bá»‹ cháº·n |
| `mst_crawler/parser.py` | tÃ¡ch link & cÃ´ng ty tá»« HTML |
| `mst_crawler/storage.py` | SQLite, lá»c trÃ¹ng theo MST |
| `mst_crawler/dashboard.py` | dashboard web (tiáº¿n Ä‘á»™ theo tá»‰nh, tá»· lá»‡ trÃ¹ng) |

LÆ°u Ã½: tÃ´n trá»ng Ä‘iá»u khoáº£n sá»­ dá»¥ng cá»§a trang vÃ  giá»¯ tá»‘c Ä‘á»™ tháº¥p.

