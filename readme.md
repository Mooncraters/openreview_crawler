# openreview 爬虫
爬取openreview的论文信息，并保存到数据库中
## 运行环境
`requirements.txt`

## 运行方法
`python main.py`

## 参数解析
- -u, --update 更新，默认值是 paper，可选值如下
  - paper 更新论文，爬取数据库中 id_cache 里面的所有论文 id，把论文信息存储在表 paper 中，如果爬取成功在表 domain_id 里更新已经爬过的论文 id，如果失败，存入表 failed
  - list 更新论文 id，根据表 domain_url_tag，爬取所有 tag 下所有的新论文 id，存储在 id_cache 中
  - tag 更新标签页，从 openreview 主页爬取所有期刊会议种类，打开所有的子链接，找到存有 pdf 链接的 tag 页，更新 tag，存储在表 domain_url_tag 中
  - all 按照 tag list paper 的顺序都调用一遍，可能要很长时间
- -f, --fix_failed 再次爬取失败的论文，把表 failed 的数据导入 id_cache 中，然后删除 failed 的数据，重新爬一遍
- --init 初始化，把已爬取的信息导入数据库

## 数据库结构

### domain_url_tag
存储所有期刊会议种类，打开所有的子链接，找到存有 pdf 链接的 tag 页，更新 tag，存储在表 domain_url_tag 中

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| url | VARCHAR(255) | 链接 |
| tag | VARCHAR(255) | 标签 |
| PRIMARY KEY | (domain, url, tag) | 主键 |

### id_cache
存储待爬取的论文 id

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| id | VARCHAR(255) | 论文 ID |
| PRIMARY KEY | (id) | 主键 |

### domain_id
存储已经爬取的论文 id

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| id | VARCHAR(255) | 论文 ID |
| PRIMARY KEY | (id) | 主键 |

### failed
存储爬取失败的论文 id

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| id | VARCHAR(255) | 论文 ID |
| PRIMARY KEY | (id) | 主键 |

### papers
存储论文信息

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| title | TEXT | 论文标题 |
| author | TEXT | 作者 |
| date | DATE | 日期 |
| state | TEXT | 状态 |
| abstract | TEXT | 摘要 |
| paper_url | VARCHAR(255) | 论文链接 |
| pdf_url | VARCHAR(255) | PDF 链接 |
| PRIMARY KEY | (paper_url) | 主键 |

## 建议运行方法

0. 如果第一次运行，一定要先 init

```shell
python main.py --init
```

1. 检查是否有新论文

```shell
python main.py -u list
```

2. 如果有新论文，爬取，并查看是否有爬取失败的

```shell
python main.py
```

3. 如果有爬取失败的，则继续爬取

```shell
python main.py -u paper -f
```

4. 如果长时间没有更新 tag，则更新一下，这个过程可能比较久

```shell
python main.py -u tag
```
## 函数和类说明

### Crawler 类

#### `__init__(self, site)`
初始化爬虫类，设置网站地址和数据库管理器。

#### `browser_init(self)`
初始化无头浏览器。

#### `crawlPaper(self, sub_url, domain)`
爬取论文详情页，包括论文标题、作者、日期、状态、摘要、主题等信息。
存储在 papers 表中。

#### `crawlList(self, domain, sub_url, tag)`
如果参数的 sub_url 显示为 2025 年之前，则跳过
否则，爬取论文列表页
如果发现连续两个重复的论文 ID，或者爬完所有论文，停止
将非重复的论文链接存入 id_cache 表中。

#### `crawlMiddle(self, sub_url, domain)`
按照广度优先搜索带有 pdf 的标签页，爬取所有链接，得到 tag 并存储在 domain_url_tag 表中。

#### `crawlVenue(self)`
从 all venue 中爬取所有的会议名称 domain。

#### `update_paper(self, fix_failed=False)`
爬取论文信息
如果有参数 fix_failed 为 True，先把 failed 表中的数据导入 id_cache 表中，然后删除 failed 表中的数据。
爬取 id_cache 表中的论文信息，如果爬取成功，则更新 domain_id 表中的论文 ID，如果失败，则存入 failed 表中。

#### `update_list(self)`
爬取论文列表页。

#### `update_tag(self)`
爬取论文标签页。

### MySQLManager 类

#### `__init__(self, user, password, host, port)`
初始化数据库管理器，设置数据库连接配置。

#### `connect_to_mysql(self)`
连接到 MySQL 服务器（不指定数据库）。

#### `ensure_database_exists(self)`
确保数据库存在，如果不存在则创建它。

#### `connect_to_database(self)`
连接到目标数据库。

#### `ensure_table_exists(self)`
确保表存在，如果不存在则创建它。

#### `close(self)`
关闭数据库连接。

#### `savePaper(self, domain, title, author, date, state, abstract, paper_url, pdf_url)`
保存论文信息到数据库。

#### `save_visited(self, domain, url, tag)`
保存已访问的链接和标签到数据库。

#### `load_visited(self)`
从数据库中加载已访问的链接和标签。

#### `save_id(self, domain, forum_list, table='id_cache')`
保存论文 ID 到指定表。

#### `load_failed_to_cache(self)`
将失败的论文 ID 从 `failed` 表加载到 `id_cache` 表。

#### `load_id(self, fix_failed=False)`
从 `id_cache` 表中加载论文 ID。

#### `load_all(self)`
将数据库中的数据导出到 CSV 和 JSON 文件。

#### `save_all(self)`
从 CSV 和 JSON 文件中导入数据到数据库。

### init_db 函数

#### `init_db()`
初始化数据库连接和表结构。