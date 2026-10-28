"""CLI: python -m mst_crawler {discover|crawl|stats|export}"""
import argparse
import csv
import logging
import sys

from . import crawler
from .fetcher import Blocked, Fetcher
from .storage import Store


def main():
    ap = argparse.ArgumentParser(prog="mst_crawler", description="Crawl danh sách doanh nghiệp masothue.com")
    ap.add_argument("--db", default="data/mst.sqlite", help="file SQLite (mặc định data/mst.sqlite)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="lấy danh sách tỉnh -> phường/xã")
    c = sub.add_parser("crawl", help="quét công ty từng phường/xã (tự chạy tiếp chỗ dừng)")
    c.add_argument("--workers", type=int, default=1, help="số luồng song song (khuyến nghị 1-2)")
    c.add_argument("--delay", type=float, default=2.0, help="giây nghỉ giữa các request mỗi luồng")
    c.add_argument("--province", help="chỉ quét tỉnh có slug chứa chuỗi này, vd ha-noi")
    sub.add_parser("stats", help="thống kê + tỷ lệ trùng")
    e = sub.add_parser("export", help="xuất CSV công ty (đã lọc trùng)")
    e.add_argument("-o", "--out", default="data/companies.csv")

    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    store = Store(a.db)

    if a.cmd == "discover":
        crawler.discover(Fetcher(), store)
        print(store.stats())
    elif a.cmd == "crawl":
        try:
            crawler.crawl(Fetcher(delay=a.delay), store, a.workers, a.province)
        except Blocked:
            sys.exit(2)
    elif a.cmd == "stats":
        s = store.stats()
        dup = s["rows_total"] - s["companies_unique"]
        for k, v in s.items():
            print(f"{k:18}: {v:,}")
        print(f"{'duplicate_rate':18}: {dup:,} ({100 * dup / max(s['rows_total'], 1):.2f}%)")
    elif a.cmd == "export":
        rows = store.db.execute(
            "SELECT c.mst, c.name, l.province, c.first_location FROM companies c "
            "LEFT JOIN locations l ON l.path = c.first_location ORDER BY c.mst")
        with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["mst", "name", "province", "location"])
            w.writerows(rows)
        print("Đã xuất", a.out)


if __name__ == "__main__":
    main()
