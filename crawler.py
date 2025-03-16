from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from collections import deque
import json
from db_manager import init_db

class Crawler:
    def __init__(self, site):
        self.site = site
        self.driver = self.browser_init()
        self.db_manager = init_db()
    def browser_init(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return driver
    
    def crawlPaper(self, sub_url, domain):
        """
        爬取论文详情页
        包括论文标题，作者，日期，状态，摘要，主题
        """
        def formatted_date(text):
            """
            正则表达式匹配日期（格式：21 Feb 2025）
            如果有 Published time 和其他时间，选取最新的
            """
            from datetime import datetime
            try:
                # 正则表达式匹配日期（支持 Sept 等缩写）
                date_pattern = r"\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec) \d{4}"
                # 提取所有日期
                dates = re.findall(date_pattern, text, re.IGNORECASE)
                if not dates:
                    return None  # 如果没有匹配到日期，返回 None
                # 将日期字符串转换为 datetime 对象
                date_objects = []
                for date in dates:
                    # 替换 Sept 为 Sep，因为 datetime.strptime 不支持 Sept
                    date = date.replace("Sept", "Sep")
                    dt = datetime.strptime(date, "%d %b %Y")
                    date_objects.append(dt)
                # 找到最新的日期
                latest_date = max(date_objects)
                # 格式化输出
                formatted_date = latest_date.strftime("%Y-%m-%d")
                return formatted_date
            except:
                return text
        
        def get_pdf_url(bs, site):
            # 定义可能的查找方式
            find_methods = [
                # 尝试从 h2 标签获取
                lambda: bs.find('h2', class_='citation_pdf_url')['href'],
                # 尝试从 meta 标签获取
                lambda: bs.find('meta', attrs={'name': 'citation_pdf_url'})['content'],
                # 尝试从 a 标签获取
                lambda: bs.find('a', class_='citation_pdf_url')['href'],
            ]
            # 依次尝试每种方法
            for method in find_methods:
                try:
                    pdf_url = method()
                    # 如果是相对路径，加上 site 前缀
                    if not pdf_url.startswith(('http://', 'https://')):
                        pdf_url = site + pdf_url
                    return pdf_url
                except (AttributeError, TypeError, KeyError):
                    continue  # 如果失败，继续尝试下一种方法
            # 如果所有方法都失败，返回空字符串
            return ''
        
        def get_abstract(note_content):
            # 定义可能的查找方式
            find_methods = [
                # 尝试从 span 标签获取
                lambda: note_content.find('span', class_='note-content-value'),
                # 尝试从 div 标签获取
                lambda: note_content.find('div', class_='note-content-value'),
            ]
            # 依次尝试每种方法
            for method in find_methods:
                element = method()
                if element:
                    # 如果找到元素，尝试提取文本
                    if element.text.strip():  # 检查元素是否存在且内容非空
                        return element.text.strip()  # 返回去除空格的文本
                    # 如果元素没有文本，尝试从子标签（如 p）提取
                    p_tag = element.find('p')
                    if p_tag and p_tag.text.strip():
                        return p_tag.text.strip()
            # 如果所有方法都失败，返回空字符串
            return ''
        
        site = self.site + sub_url
        self.driver.get(site)
        try:
            req = self.driver.page_source
            bs = BeautifulSoup(req, 'html.parser')
            title = bs.find('h2', class_ = 'citation_title').text
            pdf_url = get_pdf_url(bs, self.site)
            authors = bs.find('div', class_ = 'forum-authors mb-2').text
            meta = bs.find('div', class_ = 'forum-meta')
            spans = meta.find_all('span', class_ = 'item')
            date = formatted_date(spans[0].text.strip())
            state = spans[1].text.strip()
            note_content = bs.find('div', class_ = 'note-content')
            abstract = get_abstract(note_content)
            if not domain:
                venue_homepage = bs.find('a', attrs={'title': 'Venue Homepage'})
                strong_tag = venue_homepage.find('strong')
                domain = strong_tag.get_text(strip = True)
            info = [domain, title, authors, date, state, abstract, self.site + sub_url, pdf_url]
            print(f'爬取文章{title}')
            print(sub_url)
            print('=====================')
            return info
        except:
            return []

    def crawlList(self, domain, sub_url, tag):
        """
        爬取列表页
        翻页
        """
        print(f'========正在爬取{domain}/{tag}的论文ID========')
        def get_page():
            try:
                page_ul = bs.find('ul', class_ = 'pagination')
                page = page_ul.find('li', class_ = 'active').text
                return int(page)
            except:
                return -1
        def get_right_button():
            page_ul = bs.find('ul', class_ = 'pagination')
            for index, child in enumerate(page_ul.children):
                if '›' in child.text:
                    return index + 1
        def forum_repeat(forum):
            select_query = """
            SELECT id FROM domain_id where id = %s;
            """
            self.db_manager.cursor.execute(select_query, (forum,))
            result = self.db_manager.cursor.fetchone()
            if result:
                return True
            return False
        site = self.site + sub_url + '#tab-' + tag
        self.driver.get(site)
        time.sleep(5) # 延时，等待页面加载完成
        old_page = 0
        cur_page = 1
        right_button = 0 # 右翻页在页面中的位置
        forum_list = []
        flag = True
        repeat_papers = 0
        while flag:
            time.sleep(1)
            try:
                req = self.driver.page_source
                bs = BeautifulSoup(req, 'html.parser')
                tab_content = bs.find('div', class_ = 'tab-content')
                active = tab_content.find('div', id = tag)
                ul = active.find('ul', class_ = 'list-unstyled list-paginated')
                # 获取当前页面的所有论文链接
                for child in ul.children:
                    if child.name == 'li':
                        a = child.find('a')
                        href = a['href']
                        if forum_repeat(href):
                            repeat_papers += 1
                            print(f'爬取重复论文{repeat_papers}篇')
                        if repeat_papers == 2:
                            print('重复论文过多，停止爬取')
                            print(f'爬取{domain}成功，共爬取{len(forum_list)}论文ID')
                            self.db_manager.save_id(domain, forum_list)
                            return
                        forum_list.append(href)
                cur_page = get_page() # 获取当前页码
                if cur_page == -1:
                    page = 1
                else:
                    page = cur_page
                print(f'目前页数是{page}\t')
                print(f'总共有{len(forum_list)}个论文')
                print('==============')
                if cur_page == -1:
                    print('没有翻页按钮，停止爬取')
                    break
                elif cur_page == 1:
                    right_button = get_right_button()
                if cur_page == old_page:
                    flag = False
                    print(f'目前页数是{cur_page}\t停止翻页')
                    break
                else:
                    old_page = cur_page
                try:
                    page_xpath = f'//*[@id="{tag}"]/div/div/nav/ul/li[{right_button}]/a'
                    button = self.driver.find_element(By.XPATH, page_xpath)
                    if button.is_enabled():
                        button.click()
                    time.sleep(1)
                except:
                    print('翻页按钮不可点击，停止翻页')
                    flag = False
            except:
                print('停止翻页')
                break
        # 这里会修改，如果爬取相同的论文就停止翻页
        # 要检测是否翻页成功，不成功则返回
        print(f'爬取{domain}成功，共爬取{len(forum_list)}论文ID')
        self.db_manager.save_id(domain, forum_list)

    def crawlMiddle(self, sub_url, domain):
        """
        找到所有会议里面，包含 pdf 的标签页，得到 tag
        存储在 domain_url_tag 表中
        """
        site = self.site
        to_check = deque()
        to_check.append(sub_url)
        url_tag = []
        update_num = 0
        while to_check:
            sub_url = to_check.popleft()
            cur_site = site + sub_url
            self.driver.get(cur_site)
            time.sleep(1)
            req = self.driver.page_source
            bs = BeautifulSoup(req, 'html.parser')
            try:
                # 检测是否有 pdf
                # 如果有，则保存
                tab_content = bs.find('div', class_ = 'tab-content')
                for child in tab_content.children:
                    try:
                        a = child.find('a', class_ = 'pdf-link')
                        if a:
                            url_tag.append((sub_url, child['id']))
                    except:
                        print(f"{child['id']} has no pdf")
                        continue
            except:
                None
            try:
                # 检测是否有子页面
                # 如果有，则加入队列
                ul = bs.find('ul', class_ = 'list-unstyled venues-list')
                for child in ul.children:
                    if child.name == 'li':
                        a = child.find('a')
                        if a:
                            href = a['href']
                            # text = a.text
                            # print(text, href)
                            to_check.append(href)
                        else:
                            continue
            except:
                continue
            for item in url_tag:
                success = self.db_manager.save_visited(domain, item[0], item[1])
                if success:
                    update_num += 1
        print(f'爬取{domain}成功，共更新{update_num}个url_tag')
        return update_num
    
    def crawlVenue(self):
        """
        爬取所有的会议名称 domain
        """
        total = 0
        self.driver.get(self.site)
        time.sleep(4)
        req = self.driver.page_source
        bs = BeautifulSoup(req, 'html.parser')
        section = bs.find('section', id = 'all-venues-mobile')
        ul = section.find('ul', class_ = 'conferences list-inline')
        lis = ul.find_all('li')
        for li in lis:
            a = li.find('a')
            href = re.sub(r'&referrer=.*','',a['href'])
            text = a.text
            total += self.crawlMiddle(href, text)
        print(f'爬取所有会议成功，共更新{total}个 tag')

    def update_paper(self, fix_failed = False):
        """
        爬取论文信息并根据结果更新缓存和失败记录。
        参数:
            fix_failed (bool): 是否修复之前失败的论文爬取任务。默认为 False。
                如果为 True，会将表 failed 中的数据重新导入表 id_cache 中，然后尝试重新爬取。
        返回值:
            None
        行为:
            - 每次爬取 id_cache 中的数据。
            - 如果爬取成功，将论文信息插入 papers，并将 domain 和 id 插入 domain_id 中，表示已成功爬取。
            - 如果爬取失败，将 domain 和 id 插入 failed 中，表示爬取失败。
        """
        success = fail = 0
        MAX_RETRIES = 5
        for row in self.db_manager.load_id(fix_failed = fix_failed):
            domain = row[0]
            href = row[1]
            retry_count = 0
            paper_got = False
            while retry_count < MAX_RETRIES:
                try:
                    # 尝试爬取论文信息
                    info = self.crawlPaper(href, domain)
                    if info:
                        paper_got = True
                        self.db_manager.savePaper(*info)
                        break  # 成功则跳出重试循环
                    else:
                        print(f'爬取失败，href: {href}, 尝试次数: {retry_count + 1}')
                except Exception as e:
                    print(f'爬取失败，href: {href}, 尝试次数: {retry_count + 1}, 错误信息: {e}')
                # 如果失败，等待一段时间后重试
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    print("5 秒后重试")                
                    time.sleep(5)  # 等待 5 秒后重试
            # 根据是否成功更新计数器
            if paper_got:
                success += 1
                self.db_manager.save_id(domain, [href], table = 'domain_id')
            else:
                fail += 1
                self.db_manager.save_id(domain, [href], table = 'failed')
                print(f'爬取失败，href: {href}, 已达到最大尝试次数 {MAX_RETRIES}')
            delete = f"""
            DELETE FROM id_cache WHERE id = '{href}';
            """
            self.db_manager.cursor.execute(delete)
            print(f'目前爬取 {success} 条论文信息，失败 {fail} 条论文信息')
        print(f'总共成功爬取 {success} 条论文信息，失败 {fail} 条论文信息')
    
    def update_list(self):
        """
        爬取论文列表页
        """
        for row in self.db_manager.load_visited():
            if row:
                domain = row[0]
                sub_url = row[1]
                tag = row[2]
                self.crawlList(domain, sub_url, tag)
            else:
                print('没有需要爬取的论文列表')

    def update_tag(self):
        """
        爬取论文标签页
        """
        self.crawlVenue()