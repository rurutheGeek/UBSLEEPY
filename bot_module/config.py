# -*- coding: utf-8 -*-
# config.py
import os
import discord
import pandas as pd
import json
import sys


# activity = discord.Activity(name='キノコのほうし', type=discord.ActivityType.playing)
activity = discord.Activity(name="研修チュウ", type=discord.ActivityType.unknown)
client = discord.Client(intents=discord.Intents.all(), activity=activity)

# main.pyのディレクトリに移動
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# globalsでグローバル変数を用意
globals().update(
    {
        "DEVELOPER_USER_ID": "",
        "GUILD_IDS": [],
        "PDW_SERVER_ID": "",
        "DEBUG_MODE": False,
        "DEBUG_CHANNEL_ID": "",
        "GUIDELINE_CHANNEL_ID": "",
        "REACTIONROLE_CHANNEL_ID": "",
        "STAGE_CHANNEL_ID": "",
        "DAIRY_CHANNEL_ID": "",
        "HELLO_CHANNEL_ID": "",
        "CALLSTATUS_CHANNEL_ID": "",
        "LOG_CHANNEL_ID": "",
        "UNKNOWN_ROLE_ID": "",
        "STAGEHOST_ROLE_ID": "",
        "MENYMONEY_ROLE_ID": "",
        "BALL_ICON": "",
        "BANGBANG_ICON": "",
        "EXCLAMATION_ICON": "",
        "EX_SOURCE_LINK": "",
        "REPORT_PATH": "",
        "BSS_GRAPH_PATH": "",
        "NOTFOUND_IMAGE_PATH": "",
        "POKEDEX_PATH": "",
        "POKECALENDAR_PATH": "",
        "POKESENRYU_PATH": "",
        "FEEDBACK_PATH": "",
        "MEMORY_PATH": "",
        "CALLDATA_PATH": "",
        "MEMBERDATA_PATH": "",
        "MEMBERLIST_PATH": "",
        "CALLLOG_PATH": "",
        "QUIZNAME_DICT": {},
        "POKENAME_PREFIX_DICT": {},
        "BASE_STATS_DICT": {},
        "WEAK_DICT": {},
        "TYPE_COLOR_DICT": {},
        "PRIZE_DICT": {},
        "GLOBAL_BRELOOM_DF": pd.DataFrame(),
    }
)


def load_config():
    global DEVELOPER_USER_ID, GUILD_IDS, PDW_SERVER_ID, DEBUG_MODE, DEBUG_CHANNEL_ID, GUIDELINE_CHANNEL_ID, REACTIONROLE_CHANNEL_ID, STAGE_CHANNEL_ID, DAIRY_CHANNEL_ID, HELLO_CHANNEL_ID, CALLSTATUS_CHANNEL_ID, LOG_CHANNEL_ID, UNKNOWN_ROLE_ID, STAGEHOST_ROLE_ID, MENYMONEY_ROLE_ID, BALL_ICON, BANGBANG_ICON, EXCLAMATION_ICON, EX_SOURCE_LINK, REPORT_PATH, BSS_GRAPH_PATH, NOTFOUND_IMAGE_PATH, POKEDEX_PATH, POKECALENDAR_PATH, POKESENRYU_PATH, FEEDBACK_PATH, MEMORY_PATH, MEMBERLIST_PATH, CALLDATA_PATH, MEMBERDATA_PATH, CALLLOG_PATH, QUIZNAME_DICT, POKENAME_PREFIX_DICT, BASE_STATS_DICT, WEAK_DICT, TYPE_COLOR_DICT, PRIZE_DICT, GLOBAL_BRELOOM_DF
    config_dict = []
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            config_dict = json.load(file)
    except FileNotFoundError:
        with open("document/default_config.json", "r") as default_config:
            config_dict = json.load(default_config)

    # 引数'debug'が指定されているとき,デバッグモードで起動
    if sys.argv[1] == "debug":
        DEBUG_MODE = True
        guildId = config_dict["developer_guild_id"]
    else:
        guildId = "1067125843647791114"

    guild_dict = config_dict["guild_dict"][guildId]
    emoji_id_dict = config_dict["emoji_id_dict"]
    link_dict = config_dict["link_dict"]
    path_dict = config_dict["path_dict"]
    system_dict_dict = config_dict["system_dict_dict"]

    DEVELOPER_USER_ID = config_dict["developer_user_id"]
    # 登録されたサーバーのギルドIDのリストを取得
    GUILD_IDS = config_dict.get("guild_id", [])

    # 各種サーバー固有の変数を設定
    PDW_SERVER_ID = guildId
    ##チャンネルID
    DEBUG_CHANNEL_ID = guild_dict["debug_channel_id"]
    GUIDELINE_CHANNEL_ID = guild_dict["guideline_channel_id"]
    REACTIONROLE_CHANNEL_ID = guild_dict["reactionrole_channel_id"]
    STAGE_CHANNEL_ID = guild_dict["stage_channel_id"]
    DAIRY_CHANNEL_ID = guild_dict["dairy_channel_id"]
    HELLO_CHANNEL_ID = guild_dict["hello_channel_id"]
    CALLSTATUS_CHANNEL_ID = guild_dict["callstatus_channel_id"]
    LOG_CHANNEL_ID = guild_dict["log_channel_id"]
    ##ロールID
    UNKNOWN_ROLE_ID = guild_dict["unknown_role_id"]
    STAGEHOST_ROLE_ID = guild_dict["stagehost_role_id"]
    MENYMONEY_ROLE_ID = guild_dict["menymoney_role_id"]
    ## 絵文字コード
    BALL_ICON = emoji_id_dict["ball_icon"]
    BANGBANG_ICON = emoji_id_dict["bangbang_icon"]
    EXCLAMATION_ICON = emoji_id_dict["exclamation_icon"]
    ## URL
    EX_SOURCE_LINK = link_dict["ex_source_link"]

    ## 各種ファイルのパス
    REPORT_PATH = path_dict["report_path"]
    BSS_GRAPH_PATH = path_dict["bss_graph_path"]
    NOTFOUND_IMAGE_PATH = path_dict["notfound_image_path"]
    POKEDEX_PATH = path_dict["pokedex_path"]
    POKECALENDAR_PATH = path_dict["pokecalendar_path"]
    POKESENRYU_PATH = path_dict["pokesenryu_path"]
    FEEDBACK_PATH = path_dict["feedback_path"]
    MEMORY_PATH = path_dict["memory_path"]
    CALLDATA_PATH = path_dict["calldata_path"]
    MEMBERDATA_PATH = path_dict["memberdata_path"]
    MEMBERLIST_PATH = path_dict["memberlist_path"]
    CALLLOG_PATH = path_dict["calllog_path"]

    ## 各種辞書データ
    # クイズ名を識別子に変換する辞書(スラッシュコマンドも更新される)
    QUIZNAME_DICT = system_dict_dict["quizname_dict"]
    # fetch_pokemonで使用
    POKENAME_PREFIX_DICT = system_dict_dict["pokename_prefix_dict"]
    # make_filter_dictで使用
    BASE_STATS_DICT = system_dict_dict["base_stats_dict"]
    # show_calendarで使用
    WEAK_DICT = system_dict_dict["weak_dict"]
    TYPE_COLOR_DICT = system_dict_dict["type_color_dict"]
    PRIZE_DICT = system_dict_dict["prize_dict"]

    # グローバルずかんデータを用意
    GLOBAL_BRELOOM_DF = pd.read_csv(POKEDEX_PATH)
    GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] = GLOBAL_BRELOOM_DF[
        "ぜんこくずかんナンバー"
    ].apply(lambda x: str(int(x)) if x.is_integer() else str(x))


#起動時にconfig.jsonを読み込む
load_config()
