import csv
import os
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, urljoin
import re

# URL cơ sở của API và trang web
base_API = 'https://tiki.vn/api/personalish/v1/blocks/listings'
base_url = 'https://tiki.vn'

# Các header để giả lập một trình duyệt
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0'
}

# Các tham số mặc định cho yêu cầu API
params = {
    'limit': '40',
    'include': 'advertisement',
    'aggregations': '2',
    'trackity_id': '63098562-37b5-d535-39c1-54190bfa9543',
    'category': '8322',
    'page': '1',
    'urlKey': 'nha-cua-doi-song',
}

total_products_crawled = 0  # Tổng số sản phẩm đã được thu thập

def get_url_key(link):
    """Lấy khóa URL từ liên kết"""
    parsed_link = urlparse(link)
    return parsed_link.path.strip('/')

def get_category(link, headers):
    """Lấy danh mục của trang từ meta tag"""
    with requests.get(link, headers=headers) as response:
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tag = soup.find('meta', {'name': 'category'})
            category_value = meta_tag.get('content') if meta_tag else None
            soup.decompose()  # Giải phóng bộ nhớ
            return category_value
        else:
            print(f"Lỗi : {response.status_code}")
            return None

def xu_ly_san_pham(link, headers, writer):
    """Xử lý các sản phẩm từ liên kết và ghi vào file CSV"""
    global total_products_crawled
    params['urlKey'] = get_url_key(link)
    params['category'] = get_category(link, headers)

    params['page'] = '1'
    with requests.get(base_API, headers=headers, params=params) as response:
        if response.status_code == 200:
            paging = response.json().get('paging')
            last_pages = int(paging.get('last_page'))
            print(f"Connect {base_API}\nPage: {params['page']}\nurlKey: {params['urlKey']}\nCategory: {params['category']}")
            print(f"Số page cần crawl : {last_pages}")

            processed_ids = set()
            for page in range(1, last_pages + 1):
                params['page'] = str(page)
                with requests.get(base_API, headers=headers, params=params) as page_response:
                    if page_response.status_code == 200:
                        data = page_response.json().get('data', [])
                        for record in data:
                            product_id = record.get('id')
                            if product_id and product_id not in processed_ids:
                                processed_ids.add(product_id)
                                writer.writerow([product_id])  # Ghi ID sản phẩm vào file CSV
                                total_products_crawled += 1
                                print(f"Thêm sản phẩm có id {product_id} thành công!")
                print(f'Tổng số sản phẩm hiện tại đang được crawl : {total_products_crawled}')
                print(f"Đã xử lý trang {page}, tổng số ID: {len(processed_ids)}")
            print(f"Tổng số lượng Crawl {len(processed_ids)}")
        else:
            print(f"Lỗi khi lấy thông tin trang đầu tiên: {response.status_code}")

def kham_pha_theo_danh_muc(link, headers, writer, explored_urls=None):
    """Khám phá các danh mục và xử lý sản phẩm trong danh mục"""
    if explored_urls is None:
        explored_urls = set()

    if link in explored_urls:
        print(f"URL đã được khám phá trước đó: {link}")
        return

    explored_urls.add(link)
    print(f"Đang khám phá: {link}")

    with requests.get(link, headers=headers) as response:
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            danh_muc = soup.find("div", class_="styles__SubCatesList-sc-rb1auh-1 itjYzS")
            if danh_muc:
                link_danh_muc = danh_muc.find_all("a")
                for next_link in link_danh_muc:
                    href = next_link.get('href')
                    if href:
                        full_link = urljoin(base_url, href)
                        kham_pha_theo_danh_muc(full_link, headers, writer, explored_urls)
            else:
                xu_ly_san_pham(link, headers, writer)
        else:
            print(f"Lỗi khi truy cập {link}: {response.status_code}")

def start_request():
    """Bắt đầu quá trình thu thập dữ liệu"""
    output_path = os.path.join('/home/phankiet/Documents/Coach11/WebCrawler/csv', 'Extract_300k_id_tiki.csv')

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Products_id'])  # Ghi tiêu đề vào file CSV

        try:
            with requests.get(base_url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                links_category = soup.find_all("div", class_="styles__StyledItemV2-sc-oho8ay-1 bHIPhv")

                explored_urls = set()
                for link in links_category[:26]:
                    next_link = link.find("a")
                    if next_link:
                        href = next_link.get('href', '')
                        if href:
                            full_link = urljoin(base_url, href)
                            print(f"Bắt đầu khám phá: {full_link}")
                            kham_pha_theo_danh_muc(full_link, headers, writer, explored_urls)

        except requests.RequestException as e:
            print(f"Lỗi khi bắt đầu yêu cầu: {e}")

    # Ghi tổng số sản phẩm đã crawl vào file CSV
    with open(output_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Tổng số sản phẩm đã crawl:', total_products_crawled])
    print(f"Tổng số sản phẩm đã crawl: {total_products_crawled}")

if __name__ == "__main__":
    start_request()
