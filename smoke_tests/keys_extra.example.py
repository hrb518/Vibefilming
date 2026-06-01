# 复制为 keys_extra.py 后填入；不填的项对应测试会被自动跳过

# ---- 豆包语音（TTS） ----
# 控制台：https://console.volcengine.com/speech
TTS_APP_ID = ""           # AppID
TTS_ACCESS_TOKEN = ""     # Access Token
TTS_CLUSTER = "volcano_tts"  # 集群，一般不用改
TTS_VOICE = "BV001_streaming"  # 默认音色

# ---- 豆包·音乐 GenBGM ----
# 走火山引擎签名（AK/SK），不是 ARK key
VOLC_AK = ""
VOLC_SK = ""

# ---- 视频点播 VOD ----
# 也是 AK/SK；如已填上面 VOLC_AK/SK 可复用
VOD_AK = ""
VOD_SK = ""
VOD_REGION = "cn-north-1"
