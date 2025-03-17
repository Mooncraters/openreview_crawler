import mysql.connector
import csv
import json
class MySQLManager:
    def __init__(self, user, password, host, port):
        self.config = {
            'user': user,
            'password': password,
            'host': host,
            'port': port
        }
        self.connection = None
        self.cursor = None
        self.database_name = 'openreview'
        self.table_names = ['domain_url_tag', 'domain_id', 'id_cache', 'failed', 'papers']

    def connect_to_mysql(self):
        """连接到 MySQL 服务器（不指定数据库）"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor()
            print("成功连接到 MySQL 服务器！")
        except mysql.connector.Error as err:
            print(f"连接失败: {err}")

    def ensure_database_exists(self):
        """确保数据库存在，如果不存在则创建它"""
        database_name = self.database_name
        try:
            self.cursor.execute(f"SHOW DATABASES LIKE '{database_name}'")
            result = self.cursor.fetchone()

            if not result:
                print(f"数据库 '{database_name}' 不存在，正在创建...")
                self.cursor.execute(f"CREATE DATABASE {database_name}")
                print(f"数据库 '{database_name}' 创建成功！")
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")

    def connect_to_database(self):
        """连接到目标数据库"""
        database_name = self.database_name
        self.config['database'] = database_name
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor()
            print(f"成功连接到数据库 '{database_name}'！")
        except mysql.connector.Error as err:
            print(f"连接失败: {err}")

    def ensure_table_exists(self):
        """确保表存在，如果不存在则创建它"""
        table_names = self.table_names
        try:
            for table_name in table_names:
                self.cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                result = self.cursor.fetchone()
                if not result:
                    print(f"表 '{table_name}' 不存在，正在创建...")
                    cursor = self.cursor
                    # 创建 domain_url_tag 表
                    if table_name == 'domain_url_tag':
                        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS domain_url_tag (
                            domain VARCHAR(255) NOT NULL,
                            url VARCHAR(255) NOT NULL,
                            tag VARCHAR(255) NOT NULL,
                            PRIMARY KEY (domain, url, tag)
                        )
                        """)
                    if table_name == 'id_cache':
                        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS id_cache (
                            domain VARCHAR(255),
                            id VARCHAR(255) NOT NULL,
                            PRIMARY KEY (id)
                        )
                        """)
                    if table_name == 'domain_id':
                        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS domain_id (
                            domain VARCHAR(255),
                            id VARCHAR(255) NOT NULL,
                            PRIMARY KEY (id)
                        )
                        """)
                    # 创建 papers 表
                    if table_name == 'failed':
                        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS failed (
                            domain VARCHAR(255),
                            id VARCHAR(255) NOT NULL,
                            PRIMARY KEY (id)
                        )
                        """)
                    if table_name == 'papers':
                        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS papers (
                            domain VARCHAR(255) NOT NULL,
                            title TEXT NOT NULL,
                            author TEXT,
                            date DATE,
                            state TEXT,
                            abstract TEXT,
                            paper_url VARCHAR(255),
                            pdf_url VARCHAR(255),
                            PRIMARY KEY (paper_url)
                        )
                        """)
                    print(f"表 '{table_name}' 创建成功！")
                else:
                    print(f"表 '{table_name}' 已存在。")
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")

    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭。")
    
    def savePaper(self, domain, title, author, date, state, abstract, paper_url, pdf_url):
        try:
            # 先查询是否已存在
            select_query = """
            SELECT date, pdf_url FROM papers WHERE paper_url = %s
            """
            values = (paper_url,)
            self.cursor.execute(select_query, values)
            row = self.cursor.fetchone()

            if row:
                existing_date, existing_pdf_url = row

                # 判断是否需要更新
                if date != existing_date or (not existing_pdf_url and pdf_url):
                    update_query = """
                    UPDATE papers
                    SET domain = %s, title = %s, author = %s, date = %s, state = %s, 
                        abstract = %s, pdf_url = %s
                    WHERE paper_url = %s
                    """
                    values = (domain, title, author, date, state, abstract, pdf_url, paper_url)
                    self.cursor.execute(update_query, values)
                    self.connection.commit()
                    print("数据更新成功！")
                    return
            # 如果不存在，则插入新数据
            insert_query = """
            INSERT INTO papers (domain, title, author, date, state, abstract, paper_url, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (domain, title, author, date, state, abstract, paper_url, pdf_url)
            self.cursor.execute(insert_query, values)
            self.connection.commit()
            print("数据插入成功！")
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")
            self.connection.rollback()

    def save_visited(self, domain, url, tag):
        """
        导入期刊、子链接和标签的数据
        """
        try:
            insert_query = """
            INSERT INTO domain_url_tag (domain, url, tag)
            VALUES (%s, %s, %s)
            """
            values = (domain, url, tag)
            self.cursor.execute(insert_query, values)
            self.connection.commit()
            return True
        except mysql.connector.Error as err:
            self.connection.rollback()
            return False
    
    def load_visited(self):
        """
        从数据库中加载已访问的链接和标签
        """
        try:
            select_query = """
            SELECT domain, url, tag
            FROM domain_url_tag
            """
            self.cursor.execute(select_query)
            rows = self.cursor.fetchall()
            for row in rows:
                yield row
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")
    
    def save_id(self, domain, forum_list, table = 'id_cache'):
        try:
            length = len(forum_list)
            for id in forum_list:
                insert_query = f"""
                INSERT INTO {table} (domain, id)
                VALUES (%s, %s)
                """
                values = (domain, id)
                self.cursor.execute(insert_query, values)
                self.connection.commit()
            print(f"成功插入{length}条数据到{table}表！")
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")
            self.connection.rollback()
    
    def load_failed_to_cache(self):
        try:
            # 从 failed 表中选择所有数据
            select_query = """
            SELECT domain, id
            FROM failed
            """
            self.cursor.execute(select_query)
            rows = self.cursor.fetchall()
            # 将数据插入 id_cache 表，如果重复则跳过
            for row in rows:
                domain, id_value = row
                try:
                    insert_query = """
                    INSERT INTO id_cache (domain, id)
                    VALUES (%s, %s)
                    """
                    self.cursor.execute(insert_query, (domain if domain else None, id_value))
                except mysql.connector.IntegrityError:
                    print(f"ID {id_value} 已存在，跳过插入")
                    continue
            # 提交事务
            self.connection.commit()
            # 删除 failed 表中的数据
            delete_query = """
            DELETE FROM failed
            """
            self.cursor.execute(delete_query)
            # 提交事务
            self.connection.commit()
            print("数据从 failed 表迁移到 id_cache 表完成，并已删除 failed 表中的数据。")
        except Exception as e:
            # 回滚事务
            self.connection.rollback()
            print(f"操作失败: {e}")
    
    def load_id(self, fix_failed = False):
        """
        :param fix_failed: 如果为 True，则先将 failed 导入 id_cache 表中
        :return: None
        从 id_cache 中加载已访问的链接和标签
        """
        table = 'id_cache'
        if fix_failed:
            self.load_failed_to_cache()
        try:
            select_query = f"""
            SELECT domain, id
            FROM {table}
            """
            self.cursor.execute(select_query)
            rows = self.cursor.fetchall()
            for row in rows:
                yield row
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")
    def load_all(self):
        """
        把 domain_id 导入文件 domain_id.csv 中
        把 domain_url_tag 导入文件 domain_url_tag.csv 中
        把 papers 导入文件 papers.csv 中
        """
        try:
            select_query = """
            SELECT domain, id
            FROM domain_id
            """
            self.cursor.execute(select_query)
            rows = self.cursor.fetchall()
            with open('domain_id.csv', 'w', encoding='utf-8') as f:
                for row in rows:
                    f.write(','.join(row) + '\n')
            print("成功导出 domain_id 表到 domain_id.csv 文件！")
            select_query = """
            SELECT domain, url, tag
            FROM domain_url_tag
            """
            self.cursor.execute(select_query)
            rows = self.cursor.fetchall()
            with open('domain_url_tag.csv', 'w', encoding='utf-8') as f:
                for row in rows:
                    f.write(','.join(row) + '\n')
            print("成功导出 domain_url_tag 表到 domain_url_tag.csv 文件！")
            # 查询数据
            select_query = """
                SELECT domain, title, author, date, state, abstract, paper_url, pdf_url
                FROM papers
            """
            self.cursor.execute(select_query)
            rows = self.cursor.fetchall()
            # 将数据转换为 JSON 格式
            papers_data = []
            for row in rows:
                domain, title, author, date, state, abstract, paper_url, pdf_url = row
                # 构造每篇论文的 JSON 对象，保持 author 为字符串
                paper = {
                    "domain": domain,
                    "title": title,
                    "author": author,  # 保持 author 为字符串
                    "date": str(date),
                    "state": state,
                    "abstract": abstract,
                    "paper_url": paper_url,
                    "pdf_url": pdf_url
                }
                papers_data.append(paper)
            # 将数据写入 JSON 文件
            with open('papers.json', 'w', encoding='utf-8') as f:
                json.dump(papers_data, f, ensure_ascii=False, indent=4)
            print("成功导出 papers 表到 papers.json 文件！")
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")
    
    def save_all(self):
        """
        从文件 domain_id.csv 中导入数据到 domain_id 表
        从文件 domain_url_tag.csv 中导入数据到 domain_url_tag 表
        从文件 papers.csv 中导入数据到 papers 表
        """
        from datetime import datetime
        try:
            insert_query = """
            INSERT INTO domain_id (domain, id)
            VALUES (%s, %s)
            """
            with open('domain_id.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    values = (row[0], row[1])
                    self.cursor.execute(insert_query, values)
            print("成功导入 domain_id.csv 文件到 domain_id 表！")
            insert_query = """
            INSERT INTO domain_url_tag (domain, url, tag)
            VALUES (%s, %s, %s)
            """
            with open('domain_url_tag.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    values = (row[0], row[1], row[2])
                    self.cursor.execute(insert_query, values)
            print("成功导入 domain_url_tag.csv 文件到 domain_url_tag 表！")
                # 读取 JSON 文件
            with open("papers.json", "r", encoding="utf-8") as file:
                papers = json.load(file)
            # 逐个存入数据库
            for paper in papers:
                """将单个论文记录存入数据库"""
                paper_date = datetime.strptime(paper["date"], "%Y-%m-%d")
                sql = """
                INSERT INTO papers (domain, title, author, date, state, abstract, paper_url, pdf_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    paper["domain"],
                    paper["title"],
                    paper["author"],
                    paper_date,
                    paper["state"],
                    paper["abstract"],
                    paper["paper_url"],
                    paper["pdf_url"]
                )
                self.cursor.execute(sql, values)
            print("成功导入 papers.json 文件到 papers 表！")
            self.connection.commit()
        except mysql.connector.Error as err:
            print(f"操作失败: {err}")
            self.connection.rollback()

def init_db():
    import json
    with open('db_info.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    user = config['user']
    password = config['password']
    host = config['host']
    port = config['port']
    db_manager = MySQLManager(user, password, host, port)
    db_manager.connect_to_mysql()
    db_manager.ensure_database_exists()
    db_manager.connect_to_database()
    db_manager.ensure_table_exists()
    return db_manager