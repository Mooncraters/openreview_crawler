import argparse
from crawler import Crawler
if __name__ == '__main__':
    site = 'https://openreview.net'
    crawler = Crawler(site)
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description='openreview crawler')
    # 添加 --init 参数
    parser.add_argument(
        '--init',  # 只支持全称 --init
        action='store_true',  # 设置为布尔值，默认 False
        help='initialize database'
    )
    # 添加 --update 参数
    parser.add_argument(
        '-u', '--update',  # 支持缩写 -u 和全称 --update
        type=str,
        choices=['paper', 'list', 'tag', 'all'],  # 限制取值为 paper, tag, all
        default='paper',  # 默认值为 paper
        help='update paper info (choices: paper, list, tag, all)'
    )
    # 添加 --fix_failed 参数
    parser.add_argument(
        '-f', '--fix_failed',  # 支持缩写 -f 和全称 --fix_failed
        action='store_true',  # 设置为布尔值，默认 False
        help='fix failed papers (only applicable when --update is paper)'
    )
    # 解析命令行参数
    args = parser.parse_args()
    try:
        # 检查逻辑：如果 --update 不是 paper，但提供了 --fix_failed，则报错
        if args.update != 'paper' and args.fix_failed:
            parser.error("--fix_failed can only be used when --update is 'paper'.")
        if args.update == 'paper':
            crawler.update_paper(args.fix_failed) 
        if args.update == 'list':
            crawler.update_list()
        if args.update == 'tag':
            crawler.update_tag()
        if args.update == 'all':
            crawler.update_tag()
            crawler.update_list()
            crawler.update_paper(args.fix_failed)
        if args.init:
            crawler.db_manager.save_all()
    except Exception as e:
        print(e)
    finally:
        crawler.db_manager.close()