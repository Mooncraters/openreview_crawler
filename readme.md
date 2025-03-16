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

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| url | VARCHAR(255) | 链接 |
| tag | VARCHAR(255) | 标签 |
| PRIMARY KEY | (domain, url, tag) | 主键 |

### id_cache

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| id | VARCHAR(255) | 论文 ID |
| PRIMARY KEY | (id) | 主键 |

### domain_id

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| id | VARCHAR(255) | 论文 ID |
| PRIMARY KEY | (id) | 主键 |

### failed

| 字段名 | 类型 | 描述 |
| ---- | ---- | ---- |
| domain | VARCHAR(255) | 域名 |
| id | VARCHAR(255) | 论文 ID |
| PRIMARY KEY | (id) | 主键 |

### papers

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
