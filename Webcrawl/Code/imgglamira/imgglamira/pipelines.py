# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html



import mysql
# useful for handling different item types with a single interface
import mysql.connector
from itemadapter import ItemAdapter
import re


class ImgglamiraPipeline:
    def process_item(self, item, spider):
        return item



class MySQLPipeline:
    def __init__(self, mysql_host, mysql_user, mysql_password, mysql_database):
        self.mysql_host = mysql_host
        self.mysql_user = mysql_user
        self.mysql_password = mysql_password
        self.mysql_database = mysql_database

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mysql_host=crawler.settings.get('MYSQL_HOST'),
            mysql_user=crawler.settings.get('MYSQL_USER'),
            mysql_password=crawler.settings.get('MYSQL_PASSWORD'),
            mysql_database=crawler.settings.get('MYSQL_DATABASE')
        )

    def open_spider(self, spider):
        self.conn = mysql.connector.connect(
            host=self.mysql_host,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_database
        )
        self.cursor = self.conn.cursor()

        # Tạo bảng nếu chưa tồn tại
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_images (
                product_link VARCHAR(255) PRIMARY KEY,
                image_url VARCHAR(255),
                product_name VARCHAR(255),
                product_price DECIMAL(10, 2),
                category VARCHAR(100),
                crawl_timestamp DATETIME
            )
        """)

        self.conn.commit()

    def close_spider(self, spider):
        self.cursor.close()
        self.conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Bỏ dấu $ trong giá trị của product_price
        price = adapter['product_price'].replace('$', '').replace(',', '')

        self.cursor.execute("""
                     INSERT INTO product_images 
                     (product_link, image_url, product_name, product_price, category, crawl_timestamp)
                     VALUES (%s, %s, %s, %s, %s, %s)
                 """, (
            adapter['product_link'],
            adapter['image'],
            adapter['product_name'],
            float(price),
            adapter['category'],
            adapter['crawl_timestamp']
        ))
        self.conn.commit()
        return item

