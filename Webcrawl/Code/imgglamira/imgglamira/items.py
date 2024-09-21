import scrapy

class imageItem(scrapy.Item):
    product_link = scrapy.Field() # Đường link dẫn đến sản phẩm
    image = scrapy.Field() # Ảnh Sản phẩm
    product_name = scrapy.Field()  # Tên Sản phẩm
    product_price = scrapy.Field() # Giá tiền
    category = scrapy.Field() # Thể loại
    crawl_timestamp = scrapy.Field() # thời gian
