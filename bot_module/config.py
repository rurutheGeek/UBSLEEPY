﻿# -*- coding: utf-8 -*-
# config.py
import json
import pandas as pd
import sys
import discord
####################################################################################################
#グローバル変数の宣言
QUIZ_PROCESSING_FLAG = 0  # クイズ処理中フラグ
BAKUSOKU_MODE = True
GLOBAL_BRELOOM_DF=None
BQ_FILTERED_DF = None
BQ_FILTER_DICT = {}
#config.jsonから読み取る変数の宣言
DEVELOPER_GUILD_ID=None
PDW_SERVER_ID=None
DEVELOPER_USER_ID=None
GUILD_IDS= []
DEBUG_CHANNEL_ID=None
GUIDELINE_CHANNEL_ID=None
REACTIONROLE_CHANNEL_ID=None
STAGE_CHANNEL_ID=None
DAIRY_CHANNEL_ID=None
HELLO_CHANNEL_ID=None
QUIZ_CHANNEL_ID=None
CALLSTATUS_CHANNEL_ID=None
LOG_CHANNEL_ID=None
UNKNOWN_ROLE_ID=None
STAGEHOST_ROLE_ID=None
MENYMONEY_ROLE_ID=None
BALL_ICON=None
BANGBANG_ICON=None
EXCLAMATION_ICON=None
EX_SOURCE_LINK=None
REPORT_PATH=None
BSS_GRAPH_PATH=None
NOTFOUND_IMAGE_PATH=None
POKEDEX_PATH=None
POKECALENDAR_PATH=None
POKESENRYU_PATH=None  
FEEDBACK_PATH=None
MEMORY_PATH=None
MEMBERDATA_PATH=None
MEMBERLIST_PATH=None
CALLDATA_PATH=None
CALLLOG_PATH=None
SYSTEMLOG_PATH=None
QUIZNAME_DICT={}
POKENAME_PREFIX_DICT={}
BASE_STATS_DICT={}
WEAK_DICT={}
TYPE_COLOR_DICT={}
PRIZE_DICT={}
DEFAULT_FILTER_DICT={}

client = discord.Client(
    intents=discord.Intents.all(),
    activity=discord.Activity(name="研修チュウ", type=discord.ActivityType.unknown),
)

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