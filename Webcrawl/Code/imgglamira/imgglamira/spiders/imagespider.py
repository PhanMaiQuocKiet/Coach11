import jsonimport scrapyfrom scrapy_splash import SplashRequestfrom urllib.parse import urlparse, parse_qs, urlencode, urlunparsefrom imgglamira.items import imageItemimport gcfrom scrapy.spidermiddlewares.httperror import HttpErrorfrom twisted.internet.error import DNSLookupError, TimeoutError, TCPTimedOutErrorimport datetimedef luu_checkpoint(tien_trinh, ten_file='checkpoint.json'):    """Lưu trạng thái checkpoint vào file."""    with open(ten_file, 'w') as f:        json.dump(tien_trinh, f)class ImageSpider(scrapy.Spider):    name = "image"    allowed_domains = ["glamira.com"]    start_urls = ["https://www.glamira.com/"]    custom_settings = {        'FEEDS': {'output.json': {'format': 'json', 'overwrite': True}},        'SPLASH_URL': 'http://localhost:8050',        'CONCURRENT_REQUESTS': 50,        'ROBOTSTXT_OBEY': True,        'HTTPCACHE_ENABLED': True,        'HTTPCACHE_EXPIRATION_SECS': 86400,        'FEED_EXPORT_BATCH_ITEM_COUNT': 1000,        'RETRY_ENABLED': True,        'RETRY_TIMES': 3,        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],        'DOWNLOADER_MIDDLEWARES': {            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,        },        'SPIDER_MIDDLEWARES': {            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,        },        'MYSQL_HOST': '192.168.1.15',        'MYSQL_USER': 'phankiet',        'MYSQL_PASSWORD': 'Gihoichi01@',        'MYSQL_DATABASE': 'galamira',        'ITEM_PIPELINES': {            'imgglamira.pipelines.MySQLPipeline': 300,        },    }    headers = {        'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"    }    def __init__(self, *args, **kwargs):        super(ImageSpider, self).__init__(*args, **kwargs)        self.checkpoint_file = 'checkpoint.json'        self.tien_trinh = self.doc_checkpoint()        if self.tien_trinh is None:            self.tien_trinh = {'url_da_crawl': set(), 'hinh_anh_da_lay': set(), 'url_dang_cho': set()}        else:            self.tien_trinh['url_da_crawl'] = set(self.tien_trinh['url_da_crawl'])            self.tien_trinh['hinh_anh_da_lay'] = set(self.tien_trinh.get('hinh_anh_da_lay', []))            self.tien_trinh['url_dang_cho'] = set(self.tien_trinh.get('url_dang_cho', []))    def doc_checkpoint(self):        """Đọc trạng thái checkpoint từ file."""        try:            with open(self.checkpoint_file, 'r') as f:                return json.load(f)        except FileNotFoundError:            self.logger.info("Không tìm thấy file checkpoint. Bắt đầu crawl từ đầu.")            return None        except json.JSONDecodeError:            self.logger.error("File checkpoint không hợp lệ. Bắt đầu crawl từ đầu.")            return None    def start_requests(self):        """Bắt đầu các request, ưu tiên URL đang chờ từ checkpoint."""        if self.tien_trinh['url_dang_cho']:            self.logger.info(f"Tiếp tục crawl từ {len(self.tien_trinh['url_dang_cho'])} URL đang chờ.")            for url in list(self.tien_trinh['url_dang_cho']):                yield SplashRequest(url, self.parse, headers=self.headers, errback=self.errback_httpbin)        else:            self.logger.info("Bắt đầu crawl từ start_urls.")            for url in self.start_urls:                if url not in self.tien_trinh['url_da_crawl']:                    yield SplashRequest(url, self.parse, headers=self.headers, errback=self.errback_httpbin)    def parse(self, response):        """Xử lý các trang và thu thập hình ảnh."""        if response.url not in self.tien_trinh['url_da_crawl']:            yield from self.extract_images(response)            self.tien_trinh['url_da_crawl'].add(response.url)            self.tien_trinh['url_dang_cho'].discard(response.url)            top_menu_links = response.css('div.top-menu a::attr(href)').getall()            jewelry_link = response.css('div.top-menu a[href*="jewelry"]::attr(href)').get()            for link in top_menu_links:                if link:                    absolute_link = response.urljoin(link)                    if absolute_link not in self.tien_trinh['url_da_crawl'] and absolute_link not in self.tien_trinh['url_dang_cho']:                        self.tien_trinh['url_dang_cho'].add(absolute_link)                        if jewelry_link and link == jewelry_link:                            yield SplashRequest(absolute_link, callback=self.parse_jewelry_page, headers=self.headers,                                                errback=self.errback_httpbin)                        else:                            yield SplashRequest(absolute_link, callback=self.parse, headers=self.headers,                                                errback=self.errback_httpbin)        self.luu_checkpoint()    def parse_jewelry_page(self, response):        """Xử lý trang trang sức và các danh mục con."""        if response.url not in self.tien_trinh['url_da_crawl']:            yield from self.parse_category_page(response)            sub_categories = response.css('nav#menu_mega li.main__item a::attr(href)').getall()            for sub_link in sub_categories[:10]:  # Giới hạn 10 danh mục con                absolute_link = response.urljoin(sub_link)                if absolute_link not in self.tien_trinh['url_da_crawl'] and absolute_link not in self.tien_trinh['url_dang_cho']:                    self.tien_trinh['url_dang_cho'].add(absolute_link)                    yield SplashRequest(absolute_link, callback=self.parse_category_page, headers=self.headers,                                        errback=self.errback_httpbin)        self.luu_checkpoint()    def parse_category_page(self, response):        """Xử lý trang danh mục, thu thập hình ảnh và liên kết sản phẩm."""        if response.url not in self.tien_trinh['url_da_crawl']:            yield from self.extract_images(response)            yield from self.extract_product_links(response)            yield from self.handle_pagination(response)            self.tien_trinh['url_da_crawl'].add(response.url)            self.tien_trinh['url_dang_cho'].discard(response.url)        self.luu_checkpoint()    def extract_images(self, response):        """Trích xuất và xử lý hình ảnh từ trang."""        # Lấy thể loại của sản phẩm        category = response.css('li strong::text').get()        category = category.strip() if category else "null"        products = response.css('li.item')        for product in products:            image_url = product.css('img.product-image-photo::attr(src)').get()            product_name = product.css('a.product-link h2.product-item-details::text').get()            # Loại bỏ khoảng trắng thừa trong tên sản phẩm và giá sản phẩm (nếu có)            product_name = product_name.strip() if product_name else "null"            product_price = product.css('span.price::text').get()            product_link = product.css('a.product-link::attr(href)').get()            if image_url and image_url not in self.tien_trinh['hinh_anh_da_lay']:                item = imageItem()                item['image'] = image_url                item['product_name'] = product_name                item['product_price'] = product_price                item['product_link'] = product_link                item['category'] = category                item['crawl_timestamp'] = datetime.datetime.now()                self.tien_trinh['hinh_anh_da_lay'].add(image_url)                yield item    def extract_product_links(self, response):        """Trích xuất liên kết sản phẩm từ trang danh mục."""        product_links = response.css('li.item div.product-item-info a.product-link::attr(href)').getall()        for link in product_links:            absolute_link = response.urljoin(link)            if absolute_link not in self.tien_trinh['url_da_crawl'] and absolute_link not in self.tien_trinh['url_dang_cho']:                self.tien_trinh['url_dang_cho'].add(absolute_link)                yield SplashRequest(absolute_link, callback=self.parse_product_page, headers=self.headers,                                    errback=self.errback_httpbin)    def handle_pagination(self, response):        """Xử lý phân trang và gửi request cho trang tiếp theo nếu có."""        total_items = response.css('li.item::attr(data-total-items)').get()        if total_items:            total_items = int(total_items)            items_per_page = len(response.css('ol.products li.item img::attr(src)').getall())            self.logger.info(f"Total items: {total_items}, Items on page {response.url}: {items_per_page}")            current_page = self.get_current_page(response.url)            if current_page * items_per_page < total_items:                next_page_url = self.get_next_page_url(response.url, current_page + 1)                if next_page_url not in self.tien_trinh['url_da_crawl'] and next_page_url not in self.tien_trinh['url_dang_cho']:                    self.tien_trinh['url_dang_cho'].add(next_page_url)                    yield SplashRequest(next_page_url, callback=self.parse_category_page, headers=self.headers,                                        errback=self.errback_httpbin)    def parse_product_page(self, response):        """Xử lý trang sản phẩm và thu thập hình ảnh."""        if response.url not in self.tien_trinh['url_da_crawl']:            yield from self.extract_images(response)            self.tien_trinh['url_da_crawl'].add(response.url)            self.tien_trinh['url_dang_cho'].discard(response.url)        self.luu_checkpoint()    def get_next_page_url(self, current_url, next_page):        """Tạo URL cho trang tiếp theo."""        parsed_url = urlparse(current_url)        query_params = parse_qs(parsed_url.query)        query_params['p'] = [str(next_page)]        new_query_string = urlencode(query_params, doseq=True)        return urlunparse(parsed_url._replace(query=new_query_string))    def get_current_page(self, url):        """Lấy số trang hiện tại từ URL."""        parsed_url = urlparse(url)        query_params = parse_qs(parsed_url.query)        return int(query_params.get('p', [1])[0])    def get_path_information(self, url):        parsed_url = urlparse(url)        getUrlKey = parsed_url[2]        getUrlKey = getUrlKey.replace('/', '')        if getUrlKey:            print(f"Đã lấy được product_link_information là : {getUrlKey}")            return getUrlKey        else:            return None    def errback_httpbin(self, failure):        """Xử lý lỗi khi gửi request."""        if failure.check(HttpError):            response = failure.value.response            self.logger.error(f'HttpError on {response.url}: {response.status}')        elif failure.check(DNSLookupError):            request = failure.request            self.logger.error(f'DNSLookupError on {request.url}')        elif failure.check(TimeoutError, TCPTimedOutError):            request = failure.request            self.logger.error(f'TimeoutError on {request.url}')        else:            self.logger.error(f'Unexpected error: {failure}')        # Đảm bảo URL gặp lỗi vẫn được giữ trong danh sách chờ xử lý        if hasattr(failure, 'request'):            self.tien_trinh['url_dang_cho'].add(failure.request.url)        self.luu_checkpoint()    def luu_checkpoint(self):        """Lưu trạng thái checkpoint."""        checkpoint_data = {            'url_da_crawl': list(self.tien_trinh['url_da_crawl']),            'hinh_anh_da_lay': list(self.tien_trinh['hinh_anh_da_lay']),            'url_dang_cho': list(self.tien_trinh['url_dang_cho'])        }        with open(self.checkpoint_file, 'w') as f:            json.dump(checkpoint_data, f)        self.logger.info(f"Đã lưu checkpoint: {len(checkpoint_data['url_da_crawl'])} URL đã crawl, {len(checkpoint_data['hinh_anh_da_lay'])} hình ảnh đã lấy, {len(checkpoint_data['url_dang_cho'])} URL đang chờ.")    def closed(self, reason):        """Xử lý khi spider đóng."""        self.logger.info(f"Spider đóng: {reason}")        self.logger.info(f"Tổng số hình ảnh duy nhất đã tìm thấy: {len(self.tien_trinh['hinh_anh_da_lay'])}")        self.luu_checkpoint()        gc.collect()