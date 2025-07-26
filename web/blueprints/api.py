import asyncio
import json
import os
import time
from datetime import datetime
from flask import Blueprint, jsonify, request
from utils import db_utils as db
from utils import LLM_utils as llm
from web.factory import admin_required, viewer_required, get_admin_ids, app_logger

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/message_page/<group_id>/<msg_id>")
@admin_required
def get_message_page(group_id, msg_id):
    """获取指定消息所在的页码"""
    try:
        group_id = int(group_id)
    except ValueError:
        return jsonify({"error": "Invalid group ID"}), 400
    per_page = 50
    msg_data = db.query_db(
        "SELECT create_at FROM group_dialogs WHERE group_id = ? AND msg_id = ?",
        (group_id, msg_id),
    )
    if not msg_data:
        return jsonify({"error": "Message not found"}), 404
    msg_create_at = msg_data[0][0]
    count_result = db.query_db(
        "SELECT COUNT(*) FROM group_dialogs WHERE group_id = ? AND create_at > ?",
        (group_id, msg_create_at),
    )
    messages_after = count_result[0][0] if count_result else 0
    page = (messages_after // per_page) + 1
    return jsonify({"page": page})


@api_bp.route("/export_group_dialogs/<group_id>")
@admin_required
def export_group_dialogs(group_id):
    """导出完整的群组对话数据"""
    try:
        group_id = int(group_id)
    except ValueError:
        return jsonify({"error": "Invalid group ID"}), 400
    group_data = db.query_db("SELECT * FROM groups WHERE group_id = ?", (group_id,))
    if not group_data:
        return jsonify({"error": "群组不存在"}), 404
    group_columns = [
        "group_id",
        "members_list",
        "call_count",
        "keywords",
        "active",
        "api",
        "char",
        "preset",
        "input_token",
        "group_name",
        "update_time",
        "rate",
        "output_token",
        "disabled_topics",
    ]
    group = {group_columns[i]: group_data[0][i] for i in range(len(group_columns))}
    dialogs_data = db.query_db(
        "SELECT * FROM group_dialogs WHERE group_id = ? ORDER BY create_at ASC",
        (group_id,),
    )
    conversations = []
    if dialogs_data:
        dialog_columns = [
            "group_id",
            "msg_user",
            "trigger_type",
            "msg_text",
            "msg_user_name",
            "msg_id",
            "raw_response",
            "processed_response",
            "delete_mark",
            "group_name",
            "create_at",
        ]
        for row in dialogs_data:
            dialog_dict = {
                dialog_columns[i]: row[i] for i in range(len(dialog_columns))
            }
            conversation = {
                "dialog_id": dialog_dict["msg_id"],
                "user_message": {
                    "content": dialog_dict["msg_text"],
                    "user_name": dialog_dict["msg_user_name"],
                    "user_id": dialog_dict["msg_user"],
                    "trigger_type": dialog_dict["trigger_type"],
                    "time": dialog_dict["create_at"],
                },
                "ai_response": {
                    "processed_response": dialog_dict["processed_response"],
                    "raw_response": dialog_dict["raw_response"],
                    "time": dialog_dict["create_at"],
                },
            }
            conversations.append(conversation)
    export_data = {
        "group_info": {
            "group_id": group["group_id"],
            "group_name": group["group_name"] or "未命名群组",
            "character": group["char"] or "未设置",
            "preset": group["preset"] or "默认",
            "export_time": datetime.now().isoformat(),
            "total_conversations": len(conversations),
        },
        "conversations": conversations,
    }
    return jsonify(export_data)


@api_bp.route("/user/<int:user_id>")
@admin_required
def api_user_detail(user_id):
    """获取用户详细信息API"""
    user_data = db.query_db("SELECT * FROM users WHERE uid = ?", (user_id,))
    if not user_data:
        return jsonify({"error": "用户不存在"}), 404
    user_config_data = db.query_db(
        "SELECT * FROM user_config WHERE uid = ?", (user_id,)
    )
    conversations_count_data = db.query_db(
        "SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,)
    )
    conversations_count = (
        conversations_count_data[0][0] if conversations_count_data else 0
    )
    user_columns = [
        "uid",
        "first_name",
        "last_name",
        "user_name",
        "create_at",
        "conversations",
        "dialog_turns",
        "update_at",
        "input_tokens",
        "output_tokens",
        "account_tier",
        "remain_frequency",
        "balance",
    ]
    user_dict = {user_columns[i]: user_data[0][i] for i in range(len(user_columns))}
    user_config_dict = None
    if user_config_data:
        config_columns = ["uid", "char", "api", "preset", "conv_id", "stream", "nick"]
        user_config_dict = {
            config_columns[i]: user_config_data[0][i]
            for i in range(len(config_columns))
        }
    return jsonify(
        {
            "user": user_dict,
            "config": user_config_dict,
            "conversations_count": conversations_count,
        }
    )


@api_bp.route("/viewer/api/user/<int:user_id>")
@viewer_required
def viewer_api_user_detail(user_id):
    """浏览者权限获取用户详细信息API"""
    admin_ids = get_admin_ids()
    if user_id in admin_ids:
        return jsonify({"error": "无权限查看此用户信息"}), 403
    user_data = db.query_db("SELECT * FROM users WHERE uid = ?", (user_id,))
    if not user_data:
        return jsonify({"error": "用户不存在"}), 404
    user_config_data = db.query_db(
        "SELECT * FROM user_config WHERE uid = ?", (user_id,)
    )
    conversations_count_data = db.query_db(
        "SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,)
    )
    conversations_count = (
        conversations_count_data[0][0] if conversations_count_data else 0
    )
    user_columns = [
        "uid",
        "first_name",
        "last_name",
        "user_name",
        "create_at",
        "conversations",
        "dialog_turns",
        "update_at",
        "input_tokens",
        "output_tokens",
        "account_tier",
        "remain_frequency",
        "balance",
    ]
    user_dict = {user_columns[i]: user_data[0][i] for i in range(len(user_columns))}
    user_config_dict = None
    if user_config_data:
        config_columns = ["uid", "char", "api", "preset", "conv_id", "stream", "nick"]
        user_config_dict = {
            config_columns[i]: user_config_data[0][i]
            for i in range(len(config_columns))
        }
    return jsonify(
        {
            "user": user_dict,
            "config": user_config_dict,
            "conversations_count": conversations_count,
        }
    )


@api_bp.route("/user/<int:user_id>/update", methods=["POST"])
@admin_required
def api_user_update(user_id):
    """更新用户信息API"""
    try:
        data = request.get_json()
        user_updates = []
        user_params = []
        if "user_name" in data:
            user_updates.append("user_name = ?")
            user_params.append(data["user_name"])
        if "first_name" in data:
            user_updates.append("first_name = ?")
            user_params.append(data["first_name"])
        if "last_name" in data:
            user_updates.append("last_name = ?")
            user_params.append(data["last_name"])
        if "account_tier" in data:
            user_updates.append("account_tier = ?")
            user_params.append(data["account_tier"])
        if "balance" in data:
            user_updates.append("balance = ?")
            user_params.append(data["balance"])
        if "remain_frequency" in data:
            user_updates.append("remain_frequency = ?")
            user_params.append(data["remain_frequency"])
        if user_updates:
            user_params.append(user_id)
            user_sql = f"UPDATE users SET {', '.join(user_updates)}, update_at = datetime('now') WHERE uid = ?"
            db.revise_db(user_sql, tuple(user_params))
        config_updates = []
        config_params = []
        if "char" in data:
            config_updates.append("char = ?")
            config_params.append(data["char"])
        if "api" in data:
            config_updates.append("api = ?")
            config_params.append(data["api"])
        if "preset" in data:
            config_updates.append("preset = ?")
            config_params.append(data["preset"])
        if "stream" in data:
            config_updates.append("stream = ?")
            config_params.append(data["stream"])
        if "nick" in data:
            config_updates.append("nick = ?")
            config_params.append(data["nick"])
        if config_updates:
            existing_config = db.query_db(
                "SELECT uid FROM user_config WHERE uid = ?", (user_id,)
            )
            if existing_config:
                config_params.append(user_id)
                config_sql = (
                    f"UPDATE user_config SET {', '.join(config_updates)} WHERE uid = ?"
                )
                db.revise_db(config_sql, tuple(config_params))
            else:
                config_columns = ["uid"] + [
                    col.split(" = ?")[0] for col in config_updates
                ]
                config_values = [user_id] + config_params
                placeholders = ", ".join(["?"] * len(config_values))
                config_sql = f"INSERT INTO user_config ({', '.join(config_columns)}) VALUES ({placeholders})"
                db.revise_db(config_sql, tuple(config_values))
        return jsonify({"success": True, "message": "用户信息更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/groups/<group_id>", methods=["PUT"])
@admin_required
def api_group_update(group_id):
    """更新群组信息API"""
    try:
        try:
            group_id = int(group_id)
        except ValueError:
            return jsonify({"success": False, "message": "无效的群组ID"}), 400
        data = request.get_json()
        existing_group = db.query_db(
            "SELECT group_id FROM groups WHERE group_id = ?", (group_id,)
        )
        if not existing_group:
            return jsonify({"success": False, "message": "群组不存在"}), 404
        updates = []
        params = []
        if "group_name" in data:
            updates.append("group_name = ?")
            params.append(data["group_name"])
        if "active" in data:
            updates.append("active = ?")
            params.append(int(data["active"]))
        if "char" in data:
            updates.append("char = ?")
            params.append(data["char"])
        if "api" in data:
            updates.append("api = ?")
            params.append(data["api"])
        if "preset" in data:
            updates.append("preset = ?")
            params.append(data["preset"])
        if "rate" in data:
            updates.append("rate = ?")
            params.append(float(data["rate"]) if data["rate"] else None)
        if "members_list" in data:
            updates.append("members_list = ?")
            params.append(data["members_list"])
        if "keywords" in data:
            updates.append("keywords = ?")
            params.append(data["keywords"])
        if "disabled_topics" in data:
            updates.append("disabled_topics = ?")
            params.append(data["disabled_topics"])
        if updates:
            params.append(group_id)
            sql = f"UPDATE groups SET {', '.join(updates)} WHERE group_id = ?"
            db.revise_db(sql, tuple(params))
            return jsonify({"success": True, "message": "群组信息更新成功"})
        else:
            return jsonify({"success": False, "message": "没有提供要更新的字段"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route("/config/list")
@admin_required
def api_config_list():
    """获取配置文件列表"""
    try:
        import os
        import json
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dirs = {
            "characters": "characters",
            "config": "config",
            "prompts": "prompts",
        }
        result = {}
        for category, rel_dir_path in config_dirs.items():
            files = []
            abs_dir_path = os.path.join(base_path, rel_dir_path)
            if os.path.exists(abs_dir_path):
                for filename in os.listdir(abs_dir_path):
                    if filename.endswith(".json"):
                        abs_file_path = os.path.join(abs_dir_path, filename)
                        rel_file_path = f"{rel_dir_path}/{filename}".replace('\\', '/')
                        try:
                            with open(abs_file_path, "r", encoding="utf-8") as f:
                                json.load(f)
                            files.append(
                                {
                                    "name": filename,
                                    "path": rel_file_path,
                                    "size": os.path.getsize(abs_file_path),
                                    "modified": os.path.getmtime(abs_file_path),
                                }
                            )
                        except Exception as e:
                            files.append(
                                {"name": filename, "path": rel_file_path, "error": str(e)}
                            )
            result[category] = files
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/config/read")
@admin_required
def api_config_read():
    """读取配置文件内容"""
    try:
        rel_path = request.args.get("path")
        if not rel_path:
            return jsonify({"error": "缺少文件路径参数"}), 400

        # 规范化路径以防止目录遍历
        rel_path = os.path.normpath(rel_path).replace('\\', '/')
        if rel_path.startswith(('../', './', '/')):
            return jsonify({"error": "不允许的路径格式"}), 403

        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        allowed_dirs = ["characters/", "config/", "prompts/"]
        if not any(rel_path.startswith(d) for d in allowed_dirs):
            return jsonify({"error": "不允许访问此路径"}), 403

        file_path = os.path.join(base_path, rel_path)
        
        # 再次检查最终路径是否在预期基本路径下
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
            return jsonify({"error": "不允许访问此路径"}), 403

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({"error": "文件不存在"}), 404
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        return jsonify(
            {"content": content, "path": rel_path, "name": os.path.basename(file_path)}
        )
    except json.JSONDecodeError as e:
        return jsonify({"error": f"JSON格式错误: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/config/save", methods=["POST"])
@admin_required
def api_config_save():
    """保存配置文件"""
    try:
        data = request.get_json()
        rel_path = data.get("path")
        content = data.get("content")
        if not rel_path or content is None:
            return jsonify({"error": "缺少必要参数"}), 400

        rel_path = os.path.normpath(rel_path).replace('\\', '/')
        if rel_path.startswith(('../', './', '/')):
            return jsonify({"error": "不允许的路径格式"}), 403

        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        allowed_dirs = ["characters/", "config/", "prompts/"]
        if not any(rel_path.startswith(d) for d in allowed_dirs):
            return jsonify({"error": "不允许访问此路径"}), 403

        file_path = os.path.join(base_path, rel_path)
        
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
            return jsonify({"error": "不允许访问此路径"}), 403

        try:
            json.dumps(content)
        except Exception as e:
            return jsonify({"error": f"JSON格式无效: {str(e)}"}), 400
        if os.path.exists(file_path):
            backup_path = file_path + ".backup"
            import shutil
            shutil.copy2(file_path, backup_path)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "message": "文件保存成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/config/create", methods=["POST"])
@admin_required
def api_config_create():
    """创建新配置文件"""
    try:
        data = request.get_json()
        category = data.get("category")
        filename = data.get("filename")
        content = data.get("content", {})
        if not category or not filename:
            return jsonify({"error": "缺少必要参数"}), 400
        if not filename.endswith(".json"):
            filename += ".json"
        
        # 净化文件名
        import re
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)

        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        allowed_categories = ["characters", "config", "prompts"]
        if category not in allowed_categories:
            return jsonify({"error": "无效的分类"}), 400
        
        dir_path = os.path.join(base_path, category)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        file_path = os.path.join(dir_path, filename)

        if not os.path.abspath(file_path).startswith(os.path.abspath(dir_path)):
            return jsonify({"error": "不允许的文件名"}), 403

        if os.path.exists(file_path):
            return jsonify({"error": "文件已存在"}), 409
        try:
            json.dumps(content)
        except Exception as e:
            return jsonify({"error": f"JSON格式无效: {str(e)}"}), 400
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        rel_path = f"{category}/{filename}".replace('\\', '/')
        return jsonify({"success": True, "message": "文件创建成功", "path": rel_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/config/delete", methods=["POST"])
@admin_required
def api_config_delete():
    """删除配置文件"""
    try:
        data = request.get_json()
        rel_path = data.get("path")
        if not rel_path:
            return jsonify({"error": "缺少文件路径参数"}), 400

        rel_path = os.path.normpath(rel_path).replace('\\', '/')
        if rel_path.startswith(('../', './', '/')):
            return jsonify({"error": "不允许的路径格式"}), 403

        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        allowed_dirs = ["characters/", "config/", "prompts/"]
        if not any(rel_path.startswith(d) for d in allowed_dirs):
            return jsonify({"error": "不允许访问此路径"}), 403

        file_path = os.path.join(base_path, rel_path)
        
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
            return jsonify({"error": "不允许访问此路径"}), 403

        if not os.path.exists(file_path):
            return jsonify({"error": "文件不存在"}), 404
        backup_path = file_path + ".deleted." + str(int(time.time()))
        import shutil
        shutil.move(file_path, backup_path)
        return jsonify(
            {"success": True, "message": "文件删除成功", "backup": backup_path}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/generate_summary", methods=["POST"])
@admin_required
def api_generate_summary():
    """生成对话摘要"""
    try:
        app_logger.info(f"收到生成摘要请求，Content-Type: {request.content_type}")
        app_logger.info(f"请求数据: {request.get_data(as_text=True)}")
        if not request.is_json:
            app_logger.error(f"请求不是JSON格式，Content-Type: {request.content_type}")
            return jsonify({"error": "请求必须是JSON格式"}), 400
        data = request.get_json()
        if data is None:
            app_logger.error("无法解析JSON数据")
            return jsonify({"error": "无法解析JSON数据"}), 400
        conversation_id = data.get("conversation_id")
        app_logger.info(f"解析到的conversation_id: {conversation_id}")
        if not conversation_id:
            return jsonify({"error": "缺少对话ID参数"}), 400
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            summary = loop.run_until_complete(llm.LLM.generate_summary(conversation_id))
        finally:
            loop.close()
        if summary:
            db.revise_db(
                "UPDATE conversations SET summary = ? WHERE conv_id = ?",
                (summary, conversation_id),
            )
            return jsonify({"success": True, "summary": summary})
        else:
            return jsonify({"error": "生成摘要失败"}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app_logger.error(f"生成摘要时发生错误: {str(e)}")
        return jsonify({"error": f"生成摘要时发生错误: {str(e)}"}), 500


@api_bp.route("/conversation/<int:conv_id>/summary", methods=["GET"])
@admin_required
def get_conversation_summary(conv_id):
    """获取对话摘要"""
    try:
        conversation_data = db.query_db(
            "SELECT summary FROM conversations WHERE conv_id = ?", (conv_id,)
        )
        if not conversation_data:
            return jsonify({"error": "对话不存在"}), 404
        summary = conversation_data[0][0] if conversation_data[0][0] else "暂无摘要"
        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        app_logger.error(f"获取对话摘要失败: {str(e)}")
        return jsonify({"error": f"获取对话摘要失败: {str(e)}"}), 500


@api_bp.route("/edit_message", methods=["POST"])
@admin_required
def edit_message():
    """编辑消息的processed_content"""
    try:
        data = request.get_json()
        dialog_id = data.get("dialog_id")
        new_content = data.get("content", "").strip()
        if not dialog_id:
            return jsonify({"error": "缺少消息ID"}), 400
        db.revise_db(
            "UPDATE dialogs SET processed_content = ? WHERE id = ?",
            (new_content, dialog_id),
        )
        return jsonify({"success": True, "message": "消息内容已更新"})
    except Exception as e:
        app_logger.error(f"编辑消息失败: {str(e)}")
        return jsonify({"error": f"编辑消息失败: {str(e)}"}), 500