from utils.LLM_utils import *

test = PromptsBuilder(prompts_set="NSFW_Dream", input_txt="Hello", character="cuicuishark_public", dialog=[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hello, I am a student."}], user_nick="User", summary=None)
test.build_base_list()
test.insert_character()
test.insert_input()
test.insert_any({"location":"char_mark_start","mode":"after","content":"\nabc\n"})
test.build_openai_messages()
for i in test.messages:
    print(i)
