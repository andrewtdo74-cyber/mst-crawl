"""Tách dữ liệu từ HTML của masothue.com (regex, không cần thư viện parse)."""
import html as htmlmod
import re

_LOC_LINK = re.compile(r"""href=['"](?:https://masothue\.com)?(/tra-cuu-ma-so-thue-theo-tinh/[a-z0-9-]+-\d+)['"]""")
_COMPANY = re.compile(r"""<h3><a href=['"]/([0-9]{10}(?:-[0-9]{3})?)-[^'"]*['"][^>]*>([^<]*)</a>""")


def location_links(page):
    return sorted(set(_LOC_LINK.findall(page)))


def is_listing(page):
    """Trang danh sách hợp lệ luôn có khối tax-listing; thiếu => bị chặn / trang lỗi."""
    return "tax-listing" in page


def companies(page):
    return [{"mst": mst, "name": htmlmod.unescape(name).strip()}
            for mst, name in _COMPANY.findall(page)]
