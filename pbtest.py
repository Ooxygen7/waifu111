from utils.LLM_utils import *

test = PromptsBuilder(prompts_set="Default_meeting", input_txt="Hello<你好>", character="cuicuishark_public", dialog=[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hello, I am a student."}], user_nick="脆脆", summary=None)
test._build_base_list()
test._insert_character()
test._insert_input()
test.insert_any({"location":"char_mark_start","mode":"after","content":"\nabc\n"})
test._build_openai_messages()
