import utils.db_utils as db
import tiktoken
import logging
from utils.logging_utils import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

def circulate_token(text:str):
    try:
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except Exception as e:
        print(f"错误: 计算token时发生错误 - {e}. 输出为字符串长度。")
        return len(str(text))

def update_user_usage(user:object or int,input_tokens:int,output_tokens:int,trigger_type:str):

    if trigger_type == 'private_chat':
        db.user_info_update(user.id, 'input_tokens', input_tokens, True)
        db.user_info_update(user.id, 'output_tokens', output_tokens, True)
        conv_id = db.user_conv_id_get(user.id)
        conv_turn = db.dialog_turn_get(conv_id, 'private')
        if user.tmp_frequency > 0:
            db.user_sign_info_update(user.id, 'frequency', user.config.multiple * -1)
        else:
            db.user_info_update(user.id, 'remain_frequency', user.config.multiple * -1, True)
        db.conversation_private_arg_update(conv_id , 'turns', conv_turn)  # 增加对话轮次计数
        db.user_info_update(user.id, 'dialog_turns', 1, True)
    elif trigger_type == 'private_photo':
        db.user_info_update(user, 'input_tokens', input_tokens, True)
        db.user_info_update(user, 'output_tokens', output_tokens, True)
        tmp_frequency = db.user_sign_info_get(user).get('frequency')
        if tmp_frequency > 0:
            db.user_sign_info_update(user, 'frequency', -2)
        else:
            db.user_info_update(user, 'remain_frequency', -2, True)
    elif trigger_type == 'group_chat':
        db.group_info_update(user.group.id, 'call_count', 1, True)  # 更新调用计数
        db.conversation_group_update(user.group.id, user.user.id, 'turns', 1)
        db.group_info_update(user.group.id, 'input_token', input_tokens, True)  # 更新输入令牌
        db.group_info_update(user.group.id, 'output_token', output_tokens, True)  # 更新输出令牌
        return
    elif trigger_type == 'group_photo':
        return

