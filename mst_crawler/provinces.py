"""Tên hiển thị tiếng Việt cho slug tỉnh của masothue.com (vd an-giang-93 -> An Giang)."""
import re

NAMES = {
    "an-giang": "An Giang", "ba-ria-vung-tau": "Bà Rịa - Vũng Tàu", "bac-giang": "Bắc Giang",
    "bac-kan": "Bắc Kạn", "bac-lieu": "Bạc Liêu", "bac-ninh": "Bắc Ninh", "ben-tre": "Bến Tre",
    "binh-dinh": "Bình Định", "binh-duong": "Bình Dương", "binh-phuoc": "Bình Phước",
    "binh-thuan": "Bình Thuận", "ca-mau": "Cà Mau", "can-tho": "Cần Thơ", "cao-bang": "Cao Bằng",
    "da-nang": "Đà Nẵng", "dak-lak": "Đắk Lắk", "dak-nong": "Đắk Nông", "dien-bien": "Điện Biên",
    "dong-nai": "Đồng Nai", "dong-thap": "Đồng Tháp", "gia-lai": "Gia Lai", "ha-giang": "Hà Giang",
    "ha-nam": "Hà Nam", "ha-noi": "Hà Nội", "ha-tinh": "Hà Tĩnh", "hai-duong": "Hải Dương",
    "hai-phong": "Hải Phòng", "hau-giang": "Hậu Giang", "ho-chi-minh": "Hồ Chí Minh",
    "hoa-binh": "Hòa Bình", "hue": "Huế", "hung-yen": "Hưng Yên", "khanh-hoa": "Khánh Hòa",
    "kien-giang": "Kiên Giang", "kon-tum": "Kon Tum", "lai-chau": "Lai Châu", "lam-dong": "Lâm Đồng",
    "lang-son": "Lạng Sơn", "lao-cai": "Lào Cai", "long-an": "Long An", "nam-dinh": "Nam Định",
    "nghe-an": "Nghệ An", "ninh-binh": "Ninh Bình", "ninh-thuan": "Ninh Thuận", "phu-tho": "Phú Thọ",
    "phu-yen": "Phú Yên", "quang-binh": "Quảng Bình", "quang-nam": "Quảng Nam",
    "quang-ngai": "Quảng Ngãi", "quang-ninh": "Quảng Ninh", "quang-tri": "Quảng Trị",
    "soc-trang": "Sóc Trăng", "son-la": "Sơn La", "tay-ninh": "Tây Ninh", "thai-binh": "Thái Bình",
    "thai-nguyen": "Thái Nguyên", "thanh-hoa": "Thanh Hóa", "thua-thien-hue": "Thừa Thiên Huế",
    "tien-giang": "Tiền Giang", "tra-vinh": "Trà Vinh", "tuyen-quang": "Tuyên Quang",
    "vinh-long": "Vĩnh Long", "vinh-phuc": "Vĩnh Phúc", "yen-bai": "Yên Bái",
}


def display_name(path_or_slug):
    slug = re.sub(r"-\d+$", "", path_or_slug.rstrip("/").rsplit("/", 1)[-1])
    return NAMES.get(slug, slug.replace("-", " ").title())
