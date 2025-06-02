# 使用官方 Python 基础镜像，slim 版本更轻量
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中，包括所有文件和文件夹
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple


CMD ["python", "bot_run.py"]
