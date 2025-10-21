# run_proxy.py
import asyncio
import logging.config
import time
import requests
import random
from mitmproxy import options, http
from mitmproxy.tools import dump
from DrissionPage import Chromium, ChromiumOptions
import colorlog

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'color_full': {
            '()': 'colorlog.ColoredFormatter',
            'format': (
                "%(log_color)s %(asctime)s %(levelname)-8s  [%(name)s:%(lineno)d %(funcName)s] %(message)s"
            ),
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'color_full',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("boss")
# ========== mitmproxy 业务脚本 ==========



def request(flow: http.HTTPFlow) -> None:
    print(flow.request.url)
    if flow.request.host != "www.baidu.com" or not flow.request.path.startswith("/s"):
        return
    if "wd" not in flow.request.query:
        return
    print(f"[request] 原始搜索词: {flow.request.query.get('wd')}")
    flow.request.query["wd"] = "360搜索"


def response(flow: http.HTTPFlow) -> None:
    if flow.request.url == "https://static.zhipin.com/fe-zhipin-geek/web/chat/v6109/static/js/app.f4d10f1c.js":
        with open("js.js", "r", encoding="utf-8") as f:
            text = f.read() # 动态调整
        flow.response.text = text


# ========== mitmproxy 业务脚本结束 ==========

# ========== 爬虫功能 ==========
def dn():
    # 获取当前时间戳（毫秒）并转换为16进制
    o = hex(int(time.time() * 1000))[2:]
    r = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    a = ''.join(random.choice(r) for _ in range(10))
    return "F-" + o[-6:] + a


def run_spider():
    """运行爬虫获取数据"""
    logger.info("启动浏览器并配置代理...")

    # 配置浏览器选项
    o = ChromiumOptions()
    o.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    o.set_proxy('http://127.0.0.1:8080')

    # 启动浏览器
    tab = Chromium(o).latest_tab
    tab.get("https://www.zhipin.com/web/geek/jobs?city=101210100&query=%E5%A4%A7%E6%95%B0%E6%8D%AE")
    # 等待代理完全启动
    time.sleep(3)

    try:
        # 第一次请求获取 zpData
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"141\", \"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"141\"",
            "sec-ch-ua-mobile": "?0",
            "x-requested-with": "XMLHttpRequest",
            "traceid": dn(),
            "dnt": "1",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "priority": "u=1, i"
        }
        cookies = {}
        url = "https://www.zhipin.com/wapi/zpgeek/job/detail.json"
        params = {
            "securityId": "xD4W3KbTCwiHA-I1mAvi5muCafSyo_hA5aZbhz6yD0e4FHWHcdFfEu0H3pVDL0D8V66I60H9chxFFetmKE3ygkfeofQ7P4xZVvfnpi7hC4unbrIf1g~~",
            "lid": "93iKO1L1Ckq.search.3",
        }

        logger.info("发送第一次请求...")
        response = requests.get(url, headers=headers, cookies=cookies, params=params, verify=False)

        if response.status_code == 200:
            zpData = response.json()["zpData"]
            js = f"""return window._xxx("{zpData["seed"]}",{zpData["ts"]});"""

            logger.info("在浏览器中执行JS...")
            result = tab.run_js_loaded(js)
            logger.info(f"JS执行结果: {result}")

            # 第二次请求
            headers["traceid"] = dn()
            cookies["__zp_stoken__"] = result

            logger.info("发送第二次请求...")
            response = requests.get(url, headers=headers, cookies=cookies, params=params, verify=False)

            logger.info("最终响应数据:")
            logger.info(response.json())
            logger.info("Cookies:")
            logger.info(response.cookies.get_dict())
        else:
            logger.error(f"第一次请求失败，状态码: {response.status_code}")

    except Exception as e:
        logger.error(f"爬虫执行出错: {e}")
    finally:
        logger.info("爬虫执行完成")


# ========== 主程序 ==========
async def start_proxy():
    """启动 mitmproxy 代理"""
    logger.info("启动 mitmproxy 代理...")
    opts = options.Options(listen_host='127.0.0.1', listen_port=8080)
    master = dump.DumpMaster(opts, with_termlog=True, with_dumper=True)
    master.addons.add(__import__(__name__))
    await master.run()


async def main():
    """主函数"""
    # 启动代理和爬虫
    proxy_task = asyncio.create_task(start_proxy())

    # 等待代理启动
    await asyncio.sleep(2)

    # 在后台线程中运行爬虫
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_spider)

    # 等待代理任务完成（实际上会一直运行直到手动停止）
    await proxy_task


if __name__ == '__main__':
    # 禁用 SSL 警告（因为使用了 mitmproxy 的 CA）
    import urllib3
    #
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    asyncio.run(main())