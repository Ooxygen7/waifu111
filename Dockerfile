# 使用官方 Python 基础镜像，slim 版本更轻量
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 定义容器启动时区（可选，但推荐）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 定义容器启动命令
CMD ["python", "bot_run.py"]