import csv
from pymongo import MongoClient
import re

path = '/home/phankiet/Downloads/200k_comments.csv'
listComments = set()
keyword_type = ['từ thiện', 'giúp', 'lũ', 'vu khống']
keywords_name = ['công vinh', 'thủy tiên', 'cv', 'tt', 'anh chị', 'ac']
unwanted_keywords = ['http', 'www', 'zalo', 'sdt', 'xinh', 'giới thiệu', 'mua', 'bán']


# Hàm kiểm tra nếu bình luận chứa từ khóa không mong muốn
def is_unwanted(comment):
    return any(unwanted_keyword in comment.lower() for unwanted_keyword in unwanted_keywords)


def clean_comment(comment):
    # Chuyển thành chữ thường
    comment = comment.lower()
    # Xóa ký tự đặc biệt và dấu câu
    comment = re.sub(r'[^\w\s]', '', comment)
    return comment


# Đọc file và lọc bình luận
with open(path, 'r', encoding='utf8') as file:
    reader = csv.reader(file)
    for row in reader:
        if len(row) > 0:
            comment = row[0]
            cleaned_comments = clean_comment(comment)
            # Kiểm tra xem bình luận có liên quan đến từ thiện
            if any(keyword in cleaned_comments for keyword in keyword_type):
                # Kiểm tra xem bình luận có liên quan đến Công Vinh hoặc Thủy Tiên
                if any(keyword in cleaned_comments for keyword in keywords_name):
                    # Kiểm tra nếu bình luận không chứa các từ khóa không mong muốn
                    if not is_unwanted(cleaned_comments):
                        listComments.add(comment.strip())


# Kết nối đến MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['phankiet']
collection = db['Comments']

# Kết nối đến MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['phankiet']
collection = db['Comments']

# Đẩy dữ liệu lên MongoDB
try:
    collection.delete_many({})

    if listComments:
        # Chuyển danh sách bình luận thành danh sách dictionary để insert vào MongoDB
        data_to_insert = [{"comment": comment} for comment in listComments]
        result = collection.insert_many(data_to_insert)
        print(f"Đã thêm {len(result.inserted_ids)} documents vào MongoDB.")
    else:
        print("Không có dữ liệu để thêm vào MongoDB.")
except Exception as e:
    print(f"Đã xảy ra lỗi khi thêm dữ liệu vào MongoDB: {e}")

for comment in listComments:
    print(comment)
