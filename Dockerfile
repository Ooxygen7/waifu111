# 使用官方 Python 基础镜像，slim 版本更轻量
FROM python:3.13-slim

WORKDIR /app
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple


CMD ["python", "bot_run.py"]
