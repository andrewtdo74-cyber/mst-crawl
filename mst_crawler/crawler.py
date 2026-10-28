"""Logic crawl: tìm tỉnh -> xã/phường/đặc khu (phân loại mới), rồi quét trang 1..10 mỗi nơi."""
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import parser
from .fetcher import Blocked

log = logging.getLogger("mst")
INDEX = "/tra-cuu-ma-so-thue-theo-tinh/"
MAX_PAGES = 10   # trang chỉ hiển thị tối đa 10 trang (250 công ty) mỗi danh sách
NEW_UNIT = re.compile(r"/tra-cuu-ma-so-thue-theo-tinh/(xa|phuong|dac-khu)-[a-z0-9-]+-\d+$")


def discover(fetcher, store):
    """Chỉ lấy đơn vị theo phân loại mới (xã / phường / đặc khu), bỏ quận/huyện/thị xã cũ.

    Duyệt cả trang tỉnh cũ vì trang vẫn xếp vài xã mới dưới tỉnh cũ (vd xã Hưng Phú -> Thái Bình).
    """
    provinces = parser.location_links(fetcher.get(INDEX))
    log.info("Tìm thấy %d trang tỉnh/thành (gồm cả tỉnh cũ)", len(provinces))
    for p in provinces:
        links = [l for l in parser.location_links(fetcher.get(p, parser.is_listing)) if NEW_UNIT.match(l)]
        store.add_locations([(l, p) for l in links])
        log.info("%s: %d phường/xã", p, len(links))


def crawl_location(fetcher, path):
    items, first, pages = [], None, 0
    for page in range(1, MAX_PAGES + 1):
        html = fetcher.get(path if page == 1 else f"{path}?page={page}", parser.is_listing)
        found = parser.companies(html)
        if not found:
            break
        if page == 1:
            first = found[0]["mst"]
        elif found[0]["mst"] == first:   # vượt trang cuối -> trang trả lại trang 1
            break
        items += found
        pages = page
        if len(found) < 25:
            break
    return pages, items


def crawl(fetcher, store, workers=1, province=None):
    todo = store.pending(province)
    log.info("Còn %d phường/xã cần quét", len(todo))
    done = 0
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(crawl_location, fetcher, p): p for p in todo}
        try:
            for f in as_completed(futures):
                path = futures[f]
                pages, items = f.result()
                store.save_location(path, pages, items)
                done += 1
                if done % 20 == 0:
                    s = store.stats()
                    log.info("%d/%d xong | %d dòng | %d MST duy nhất",
                             done, len(todo), s["rows_total"], s["companies_unique"])
        except Blocked as e:
            log.error("Bị chặn tại %s -> dừng. Chạy lại lệnh crawl sau để tiếp tục.", e)
            for f in futures:
                f.cancel()
            raise
