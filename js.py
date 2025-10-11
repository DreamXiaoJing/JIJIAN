from DrissionPage import Chromium,ChromiumOptions

o = ChromiumOptions()
o.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
o.set_proxy('http://127.0.0.1:8080')
tab = Chromium(o).latest_tab
tab.get('https://yanglao.mca.gov.cn/#/index/institutionList')
js = """return window.xx("fc7bf098ad854022aa9a4b95261a03b6" + "ylfwxxpt" + new Date().getTime() + "fc7bf098ad854022aa9a4b95261a03b6");"""
result = tab.run_js_loaded(js)
print(result)

