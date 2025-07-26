import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from web.factory import create_app, app_logger

app = create_app()

if __name__ == "__main__":
    app_logger.info("启动Web管理界面，地址: http://0.0.0.0:8081")
    app.run(debug=False, host="0.0.0.0", port=8081, use_reloader=False)
