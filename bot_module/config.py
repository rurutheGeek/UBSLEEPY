# -*- coding: utf-8 -*-
# config.py

import os
import discord
import pandas as pd

#client
activity = discord.Activity(name='キノコのほうし', type=discord.ActivityType.playing)
client = discord.Client(intents=discord.Intents.all(),activity=activity)

##サーバーID
PDW_SERVER_ID = 1067125843647791114
DEV_SERVER_ID = 1140787268370583634
SERVER_IDS = [PDW_SERVER_ID, DEV_SERVER_ID]
##チャンネルID
DEBUG_CHANNEL_ID = 1081568799624536085
GUIDELINE_CHANNEL_ID = 1067423922477355048
REACTIONROLE_CHANNEL_ID = 1068903858790731807
STAGE_CHANNEL_ID = 1088518773461491892
DAIRY_CHANNEL_ID = 1082026583109419018
HELLO_CHANNEL_ID = 1067125844465688637
CALLSTATUS_CHANNEL_ID = 1089708019677409330
LOG_CHANNEL_ID = 1140787559325249717
##ユーザーID
DEVELOPER_USER_ID = 563436616811675658
##ロールID
UNKNOWN_ROLE_ID = 1083312357226336307
STAGEHOST_ROLE_ID = 1079328119992893490
## 絵文字コード
BALL_ICON = '<:bullet:1077833761313525820> '
BANGBANG_ICON='<:unown_bangbang:1095570764415123508>' 
EXCLAMATION_ICON='<:unown_exclamation:1095570767984480489>'

#URL
EX_SOURCE_LINK = "https://pokecries.nobody.jp/content/resources/"

## 各種辞書データ
# クイズ名を識別子に変換する辞書(スラッシュコマンドも更新される)
QUIZNAME_DICT={"種族値クイズ": "bq","物理特殊クイズ": "acq","英和翻訳クイズ": "etojq","和英翻訳クイズ": "jtoeq","中日翻訳クイズ": "ctojq"}
# fetch_pokemonで使用
POKENAME_PREFIX_DICT = {'A': 'アローラ', 'G': 'ガラル', 'H': 'ヒスイ', 'P': 'パルデア', 'M': 'メガ', '霊獣': 'れいじゅう', '化身': 'けしん', '古来': 'コライ', '未来': 'ミライ'}
# make_filter_dictで使用
BASE_STATS_DICT = {
'H': 'HP', 'HP': 'HP',
'A': 'こうげき', '攻撃': 'こうげき', 'こうげき': 'こうげき',
'B': 'ぼうぎょ', '防御': 'ぼうぎょ', 'ぼうぎょ': 'ぼうぎょ',
'C': 'とくこう', '特攻': 'とくこう', 'とくこう': 'とくこう',
'D': 'とくぼう', '特防': 'とくぼう', 'とくぼう': 'とくぼう',
'S': 'すばやさ', '素早さ': 'すばやさ', 'すばやさ': 'すばやさ',
'T': '合計', 'ごうけい': '合計', '合計': '合計'
}
# show_calendarで使用
WEAK_DICT = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
TYPE_COLOR_DICT = {
      'ノーマル': 0xdcdcdc,'ほのお': 0xff4500,'みず': 0x0000ff,'くさ': 0x32cd32,
      'こおり': 0x00ffff,'かくとう': 0xffa500,'どく': 0xff00ff,'じめん': 0xBBA48C,
      'ひこう': 0xC9DAF8,'エスパー': 0xFCDDE9,'むし': 0x98fb98,'いわ': 0xd2691e,
      'ゴースト': 0x4b0082,'ドラゴン': 0x7b68ee,'あく': 0x191970,'はがね': 0xCCCCCC,
      'でんき': 0xFFF2CC,'フェアリー': 0xFFF0F5
}
PRIZE_DICT = {
          0: ["ほしのすな", 1500, "", "残念賞"],
          1: ["きんのたま", 5000, f'やったロ{EXCLAMATION_ICON} 1ケタ おんなじロ{EXCLAMATION_ICON}', "4等"],
          2: ["すいせいのかけら", 12500, f'2ケタが おんなじだったロミ{EXCLAMATION_ICON}', "3等"],
          3: ["ガブリアスドール", 65000, f'ロミ{EXCLAMATION_ICON} 3ケタが おんなじロ{EXCLAMATION_ICON}', "2等"],
          4: ["こだいのせきぞう", 200000, f'すごいロ{EXCLAMATION_ICON} 4ケタも おんなじロミ{EXCLAMATION_ICON}',"1等"],
          5: ["たかそうなカード", 650000, f'ロミ~~{EXCLAMATION_ICON}{EXCLAMATION_ICON}{EXCLAMATION_ICON} 下5ケタ すべてが おんなじロ{EXCLAMATION_ICON}', "特等"],
          6: ["きんのパッチールぞう", 1000000, "", ""]
}

## 各種ファイルのパス
# main.pyのディレクトリ
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))#os.getcwd()#os.path.dirname(os.path.abspath(__file__))
#
REPORT_PATH = os.path.join(PROJECT_ROOT, "save/report.csv")
BSS_GRAPH_PATH = os.path.join(PROJECT_ROOT, 'save/graph.png')
POKEDEX_PATH = os.path.join(PROJECT_ROOT, "resource/pokedata_breloom.csv")
POKECALENDAR_PATH = os.path.join(PROJECT_ROOT, "resource/pokecalendar_breloom.csv")
POKESENRYU_PATH = os.path.join(PROJECT_ROOT, "resource/pokesenryu_breloom.csv")
FEEDBACK_PATH = os.path.join(PROJECT_ROOT, "save/feedback.csv")
MEMORY_PATH = os.path.join(PROJECT_ROOT, "save/restMemorychannel.csv")
CALLDATA_PATH = os.path.join(PROJECT_ROOT, "save/busychannel.csv")
MEMBERDATA_PATH = os.path.join(PROJECT_ROOT, "resource/member_breloom.csv")
CALLLOG_PATH = os.path.join(PROJECT_ROOT, "log/calllog.csv")
print(PROJECT_ROOT)
print(REPORT_PATH)
#グローバルずかんデータ
GROBAL_BRELOOM_DF = pd.read_csv(POKEDEX_PATH)
GROBAL_BRELOOM_DF['ぜんこくずかんナンバー'] = GROBAL_BRELOOM_DF['ぜんこくずかんナンバー'].apply(lambda x: str(int(x)) if x.is_integer() else str(x))