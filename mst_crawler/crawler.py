"""Logic crawl: tìm tỉnh -> phường/xã (kể cả quận/huyện cũ), rồi quét trang 1..10 mỗi nơi."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import parser
from .fetcher import Blocked

log = logging.getLogger("mst")
INDEX = "/tra-cuu-ma-so-thue-theo-tinh/"
MAX_PAGES = 10   # trang chỉ hiển thị tối đa 10 trang (250 công ty) mỗi danh sách


def discover(fetcher, store):
    provinces = parser.location_links(fetcher.get(INDEX))
    prov_set = set(provinces)
    log.info("Tìm thấy %d tỉnh/thành", len(provinces))
    for p in provinces:
        links = [l for l in parser.location_links(fetcher.get(p, parser.is_listing)) if l not in prov_set]
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
