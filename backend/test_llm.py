import requests
import json

url = ""

# 👉 请务必将这里替换为你的真实令牌，注意保留 "Bearer " 和后面的空格！
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer "
}

data = {
    "model": "gpt-5.4",  # 如果报错找不到模型，可换成 gpt-3.5-turbo
    "messages": [
        {"role": "user", "content": "你好，收到请回复1"}
    ]
}

print("🚀 正在发送最纯粹的底层 HTTP 请求...")
try:
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
    print(f"👉 HTTP 状态码: {response.status_code}")
    print(f"👉 服务器返回内容:\n{response.text}")

except Exception as e:
    print(f"❌ 请求发生异常: {e}")