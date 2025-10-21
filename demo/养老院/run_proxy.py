# run_proxy.py
import asyncio
from mitmproxy import options
from mitmproxy.tools import dump   # 控制台模式，换成 mitmproxy.tools.web 可启动 WebUI

# ========== 业务脚本 ==========
from mitmproxy import http
with open("js.js", "r", encoding="utf-8") as f:
    text = f.read()

def request(flow: http.HTTPFlow) -> None:
    print(flow.request.url)
    if flow.request.host != "www.baidu.com" or not flow.request.path.startswith("/s"):
        return
    if "wd" not in flow.request.query:
        return
    print(f"[request] 原始搜索词: {flow.request.query.get('wd')}")
    flow.request.query["wd"] = "360搜索"

def response(flow: http.HTTPFlow) -> None:
    if flow.request.url == "https://yanglao.mca.gov.cn/js/app.9fe37aff.js":
        # text = flow.response.text
        # text = text.replace("搜索", "请使用谷歌")

        flow.response.text = text
# ========== 业务脚本结束 ==========

async def main():
    # 1. 创建配置 http://mitm.it/  certutil.exe -addstore root mitmproxy-ca-cert.cer
    opts = options.Options(listen_host='127.0.0.1', listen_port=8080)
    # 2. 创建 dump 主实例（控制台模式；想换 WebUI 用 mitmproxy.tools.web.WebMaster）
    master = dump.DumpMaster(opts, with_termlog=True, with_dumper=True)
    # 3. 把上面的脚本作为 addon 加进去
    master.addons.add(__import__(__name__))   # 当前文件自己就是 addon
    # 4. 一直跑，直到 Ctrl-C
    await master.run()

if __name__ == '__main__':
    asyncio.run(main())