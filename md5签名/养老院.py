# 报价300
# 极简demo

import hashlib
import time
import requests

def sign_request() -> dict:
    t = "fc7bf098ad854022aa9a4b95261a03b6"
    headers = {"X-Auth-Key":t,"X-Auth-Nonce":t}
    a = str(int(time.time() * 1000))
    i = hashlib.md5((t+"ylfwxxpt"+a+t).encode("utf-8")).hexdigest()
    headers["X-Auth-Timestamp"] = a
    headers["X-Auth-Signature"] = i
    return headers

url="https://yanglao.mca.gov.cn/ylxxptapi/ylfwpt/ylfw/queryOrganizationDataList"
response = requests.post(url, headers=sign_request(),data={"current": "1","size": "10"})
print(response.text)