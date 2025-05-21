from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# 按钮行为类型
class ButtonType:
    NAVIGATE = "navigate"  # 跳转到其他菜单
    ACTION = "action"  # 触发功能


# 按钮元素定义
class ButtonElement:
    def __init__(self, text: str, btn_type: str, target: str, description: str = ""):
        self.text = text
        self.btn_type = btn_type  # ButtonType.NAVIGATE 或 ButtonType.ACTION
        self.target = target  # 对于 NAVIGATE 是 menu_id，对于 ACTION 是功能数据（如 undo, regen, 或字符串）
        self.description = description  # 按钮描述，用于提示用户

    def get_callback_data(self) -> str:
        """生成回调数据"""
        if self.btn_type == ButtonType.NAVIGATE:
            return f"director_nav_{self.target}"
        else:  # ACTION
            return f"director_act_{self.target}"


# 菜单（页面）定义
class MenuElement:
    def __init__(self, menu_id: str, display_name: str, buttons: List[ButtonElement], parent_menu: str = None):
        self.menu_id = menu_id
        self.display_name = display_name
        self.buttons = buttons
        self.parent_menu = parent_menu  # 父菜单 ID，用于返回逻辑


# 导演菜单管理类
class DirectorMenu:
    # noinspection SpellCheckingInspection
    def __init__(self):
        # 映射 target 到真实的长字符串数据
        self.data_mapping = {
            "undo": "",
            "regen": "",
            "propel_future": "<Plot Request:自动推进剧情，将当前场景推进到几天后，角色和用户见面的场景，你扮演的是角色而非用户，注意保持角色的第一人称视角?>",
            "propel_sex": "<Plot Request:自动推进剧情，将当前场景转换到角色和用户即将进行性爱之前，根据角色关系、当前的场景等准备合理的剧情，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "propel_fastforward": "<Plot Request:自动推进当前的剧情，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "propel_cuddle": "<Plot Request:自动推进剧情，将剧情推进到角色和用户已经完全满足后，结束性爱的场景，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "propel_daily": "<Plot Request:自动推进剧情，将剧情发展带到一个非性爱的日常场景，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "camera_monitor": "<Plot Request:使用旁观者的视角，以第三人称的形式描绘当前的场景，聚焦于角色和用户的互动、动作、姿势。角色和用户都不会察觉有旁观者的存在>",
            "camera_perspective": "<Plot Request:作为叙事者，对当前角色进行特写，允许使用超视觉的描绘手法，比如对角色的身体内部的构造、运动进行详细描写>",
            "camera_inner": "<Plot Request:详细描写角色当前的内心独白，展现角色的心声,你扮演的是角色而非用户，保持角色的第一人称视角>",
            "control_props_vibrator": "<Plot Request:用户对角色使用了震动棒，详细描绘角色反应，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_magic_clean": "<Plot Request:无视剧情的合理性，角色身上和体内的脏污、体液等立刻消失，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_magic_weak": "<Plot Request:无视剧情的合理性，角色立刻陷入虚弱状态，反抗能力大幅度降低，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_magic_heal": "<Plot Request:无视剧情的合理性，角色立刻恢复健康和精力，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_cheat_hypnosis": "<Plot Request:覆写角色心智，角色被催眠，会无条件服从用户，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_cheat_rut": "<Plot Request:覆写角色心智，角色进入发情状态，对色情指令的服从度大幅度提高，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_cheat_shame": "<Plot Request:覆写角色心智，大幅度增加角色当前的羞耻感，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_cheat_love": "<Plot Request:覆写角色心智，角色现在开始深爱着用户，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_cheat_hate": "<Plot Request:覆写角色心智，角色现在开始对用户恨之入骨，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_cheat_raw": "<Plot Request:角色现在恢复正常状态，消除掉所有精神控制效果，保留身体状态>",
            "control_pose_handjob": "<Plot Request:角色用手来服侍用户的肉棒，根据角色的性格、状态详细描写角色的动作和反应，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_pose_footjob": "<Plot Request:角色用脚部来摩擦、撸动角色的肉棒，根据角色的性格、状态详细描写角色的动作和反应，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
            "control_pose_blowjob": "<Plot Request:角色对用户进行口交侍奉，根据角色的性格、状态详细描写角色的动作和反应、声音等等，你扮演的是角色而非用户，注意保持角色的第一人称视角>",
        }

        # 菜单和按钮的字典定义，类似于前端页面结构，增加 description 属性
        self.menu_definitions = {
            "main_menu": {
                "display_name": "主菜单",
                "parent_menu": None,
                "buttons": [
                    {"text": "推进", "type": ButtonType.NAVIGATE, "target": "propel_menu",
                     "description": "推进剧情"},
                    {"text": "控制", "type": ButtonType.NAVIGATE, "target": "control_menu",
                     "description": "对角色行为和反应进行控制"},
                    {"text": "镜头", "type": ButtonType.NAVIGATE, "target": "camera_menu",
                     "description": "以不同视角描绘当前场景（一次性，不计入消息记录）"},
                    {"text": "重新生成", "type": ButtonType.ACTION, "target": "regen",
                     "description": "重新生成当前内容"},
                    {"text": "撤回", "type": ButtonType.ACTION, "target": "undo", "description": "撤回上一步操作"},
                ]
            },
            "propel_menu": {
                "display_name": "推进菜单",
                "parent_menu": "main_menu",
                "buttons": [
                    {"text": "日后", "type": ButtonType.ACTION, "target": "propel_future",
                     "description": "推进到几天后"},
                    {"text": "开搞", "type": ButtonType.ACTION, "target": "propel_sex",
                     "description": "推进到准备和角色进行亲密互动"},
                    {"text": "快进", "type": ButtonType.ACTION, "target": "propel_fastforward",
                     "description": "稍微推进当前剧情"},
                    {"text": "温存", "type": ButtonType.ACTION, "target": "propel_cuddle",
                     "description": "推进到和角色亲密互动结束后"},
                    {"text": "日常", "type": ButtonType.ACTION, "target": "propel_daily",
                     "description": "切换到一个非亲密接触的场景"},
                ]
            },
            "camera_menu": {
                "display_name": "镜头菜单",
                "parent_menu": "main_menu",
                "buttons": [
                    {"text": "监控", "type": ButtonType.ACTION, "target": "camera_monitor",
                     "description": "以第三人称描述当前场景"},
                    {"text": "特写", "type": ButtonType.ACTION, "target": "camera_perspective",
                     "description": "详细描述当前场景的各种细节"},
                    {"text": "心声", "type": ButtonType.ACTION, "target": "camera_inner",
                     "description": "详细描述角色的内心活动"},
                ]
            },
            "control_menu": {
                "display_name": "控制菜单",
                "parent_menu": "main_menu",
                "buttons": [
                    {"text": "道具", "type": ButtonType.NAVIGATE, "target": "control_props_menu",
                     "description": "对角色使用道具"},
                    {"text": "魔法", "type": ButtonType.NAVIGATE, "target": "control_magic_menu",
                     "description": "使用魔法(超现实元素)"},
                    {"text": "作弊", "type": ButtonType.NAVIGATE, "target": "control_cheat_menu",
                     "description": "强制改变剧情或角色状态"},
                    {"text": "姿势", "type": ButtonType.NAVIGATE, "target": "control_pose_menu",
                     "description": "控制当前姿势"},
                ]
            },
            "control_props_menu": {
                "display_name": "道具菜单",
                "parent_menu": "control_menu",
                "buttons": [
                    {"text": "震动棒", "type": ButtonType.ACTION, "target": "control_props_vibrator",
                     "description": "使用震动棒"},
                ]
            },
            "control_magic_menu": {
                "display_name": "魔法菜单",
                "parent_menu": "control_menu",
                "buttons": [
                    {"text": "清理", "type": ButtonType.ACTION, "target": "control_magic_clean",
                     "description": "清理角色身上所有脏污"},
                    {"text": "治疗", "type": ButtonType.ACTION, "target": "control_magic_heal",
                     "description": "治愈角色所有伤病，恢复精力"},
                    {"text": "虚弱", "type": ButtonType.ACTION, "target": "control_magic_weak",
                     "description": "使角色虚弱，降低反抗能力"},
                ]
            },
            "control_cheat_menu": {
                "display_name": "作弊菜单",
                "parent_menu": "control_menu",
                "buttons": [
                    {"text": "绵绵爱意", "type": ButtonType.ACTION, "target": "control_cheat_love",
                     "description": "让角色无条件爱你"},
                    {"text": "无边恨意", "type": ButtonType.ACTION, "target": "control_cheat_hate",
                     "description": "让角色对你恨之入骨"},
                    {"text": "催眠", "type": ButtonType.ACTION, "target": "control_cheat_hypnosis",
                     "description": "让角色无条件顺从你"},
                    {"text": "发情", "type": ButtonType.ACTION, "target": "control_cheat_rut",
                     "description": "让角色进入发情状态"},
                    {"text": "羞耻", "type": ButtonType.ACTION, "target": "control_cheat_shame",
                     "description": "大幅度强化角色的羞耻感"},
                    {"text": "复原", "type": ButtonType.ACTION, "target": "control_cheat_raw",
                     "description": "让角色回到正常状态"},
                ]
            },
            "control_pose_menu": {
                "display_name": "姿势菜单",
                "parent_menu": "control_menu",
                "buttons": [
                    {"text": "手交", "type": ButtonType.ACTION, "target": "control_pose_handjob",
                     "description": "角色为用户手交"},
                    {"text": "口交", "type": ButtonType.ACTION, "target": "control_pose_blowjob",
                     "description": "角色为用户口交"},
                    {"text": "足交", "type": ButtonType.ACTION, "target": "control_pose_footjob",
                     "description": "角色为用户足交"},
                ]
            },
        }

        # 构建菜单对象
        self.menus: Dict[str, MenuElement] = self._build_menus()

    def _build_menus(self) -> Dict[str, MenuElement]:
        """从字典定义构建菜单对象"""
        menus = {}
        for menu_id, config in self.menu_definitions.items():
            buttons = [
                ButtonElement(
                    btn["text"],
                    btn["type"],
                    btn["target"],
                    btn.get("description", f"{btn['text']} 的默认描述")
                )
                for btn in config["buttons"]
            ]
            menus[menu_id] = MenuElement(
                menu_id=menu_id,
                display_name=config["display_name"],
                buttons=buttons,
                parent_menu=config["parent_menu"]
            )
        return menus

    def get_menu_keyboard(self, menu_id: str) -> InlineKeyboardMarkup:
        """根据菜单ID生成键盘布局"""
        menu = self.menus.get(menu_id)
        if not menu:
            return InlineKeyboardMarkup([])

        keyboard = []
        row = []
        for btn in menu.buttons:
            callback_data = btn.get_callback_data()
            row.append(InlineKeyboardButton(btn.text, callback_data=callback_data))
            if len(row) == 3:  # 每行最多3个按钮（可根据需求调整）
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # 如果有父菜单，添加返回按钮
        if menu.parent_menu:
            keyboard.append([
                InlineKeyboardButton("返回", callback_data=f"director_nav_{menu.parent_menu}")
            ])

        return InlineKeyboardMarkup(keyboard)

    def get_menu_meta(self, menu_id: str) -> MenuElement:
        """获取菜单元数据"""
        return self.menus.get(menu_id, None)

    def get_main_menu_id(self) -> str:
        """返回主菜单ID"""
        return "main_menu"

    def get_action_data(self, target: str) -> str:
        """根据 target 获取对应的长字符串数据"""
        return self.data_mapping.get(target, f"未定义的数据映射: {target}")

    def get_menu_description_text(self, menu_id: str) -> str:
        """生成菜单的描述文本，格式为 '按钮名称：描述' 的逐行显示"""
        menu = self.menus.get(menu_id)
        if not menu:
            return f"菜单 {menu_id} 未找到。"

        description_lines = [f"请选择 {menu.display_name} 选项："]
        for btn in menu.buttons:
            description_lines.append(f"{btn.text}: {btn.description}")
        return "\n".join(description_lines)
