# -*- coding: utf-8 -*-
# config.py
import json
import pandas as pd
import sys
####################################################################################################
#グローバル変数の宣言
QUIZ_PROCESSING_FLAG = 0  # クイズ処理中フラグ
BAKUSOKU_MODE = True

DEVELOPER_GUILD_ID=""
PDW_SERVER_ID=""
DEVELOPER_USER_ID=""
GUILD_IDS= []
DEBUG_CHANNEL_ID=""
GUIDELINE_CHANNEL_ID=""
REACTIONROLE_CHANNEL_ID=""
STAGE_CHANNEL_ID=""
DAIRY_CHANNEL_ID=""
HELLO_CHANNEL_ID=""
CALLSTATUS_CHANNEL_ID=""
LOG_CHANNEL_ID=""
UNKNOWN_ROLE_ID=""
STAGEHOST_ROLE_ID=""
MENYMONEY_ROLE_ID=""
BALL_ICON=""
BANGBANG_ICON=""
EXCLAMATION_ICON=""
EX_SOURCE_LINK=""
REPORT_PATH=""
BSS_GRAPH_PATH=""
NOTFOUND_IMAGE_PATH=""
POKEDEX_PATH=""
POKECALENDAR_PATH=""
POKESENRYU_PATH=""  
FEEDBACK_PATH=""
MEMORY_PATH=""
CALLDATA_PATH=""
MEMBERDATA_PATH=""
MEMBERLIST_PATH=""
CALLLOG_PATH=""
SYSTEMLOG_PATH=""
QUIZNAME_DICT={}
POKENAME_PREFIX_DICT={}
BASE_STATS_DICT={}
WEAK_DICT={}
TYPE_COLOR_DICT={}
PRIZE_DICT={}
DEFAULT_FILTER_DICT={}
GLOBAL_BRELOOM_DF=None
BQ_FILTERED_DF = None
BQ_FILTER_DICT = {}

client = None

DEBUG_MODE = False
# 引数'debug'が指定されているとき,デバッグモードで起動
if len(sys.argv) > 1 and sys.argv[1] == "debug":
    DEBUG_MODE = True

def load_config():
    global GLOBAL_BRELOOM_DF, BQ_FILTERED_DF, BQ_FILTER_DICT
    config_dict = []
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            config_dict = json.load(file)
    except FileNotFoundError:
        with open("document/default_config.json", "r") as default_config:
            config_dict = json.load(default_config)

    develop_id_dict=config_dict["DEVELOP_ID_DICT"]
    globals().update(develop_id_dict)

    if DEBUG_MODE:
        guildId = DEVELOPER_GUILD_ID
    else:
        guildId = "1067125843647791114"

    guild_dict = config_dict["GUILD_DICT"][guildId]
    emoji_id_dict = config_dict["EMOJI_ID_DICT"]
    link_dict = config_dict["LINK_DICT"]
    path_dict = config_dict["PATH_DICT"]
    system_dict_dict = config_dict["SYSTEM_DICT_DICT"]
    
    globals().update(guild_dict)
    globals().update(emoji_id_dict)
    globals().update(link_dict)
    globals().update(path_dict)
    globals().update(system_dict_dict)

    # グローバルずかんデータを用意
    GLOBAL_BRELOOM_DF = pd.read_csv(POKEDEX_PATH)
    GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] = GLOBAL_BRELOOM_DF[
        "ぜんこくずかんナンバー"
    ].apply(lambda x: str(int(x)) if x.is_integer() else str(x))
    BQ_FILTERED_DF = GLOBAL_BRELOOM_DF.copy
    BQ_FILTER_DICT = DEFAULT_FILTER_DICT


#config.jsonを読み込む
load_config()