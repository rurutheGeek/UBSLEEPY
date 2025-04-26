# -*- coding: utf-8 -*-
# func.py
from .config import *

import os
import getpass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import re
import jaconv
import pypinyin
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib
import discord
import json

def output_log(logStr):
    """Botの動作ログをコンソールとLOG_CHANNELに出力する
    Parameters:
    ----------
    logStr : str
      出力するログの文字列
    """
    dt = datetime.now(ZoneInfo("Asia/Tokyo"))
    logstr = f"[{dt.hour:02}:{dt.minute:02}:{dt.second:02}|{getpass.getuser()}] {logStr}"
    # ログをコンソールに表示する
    print(logstr)
    # ログをファイルに出力し,30秒ごとに投稿する
    with open(SYSTEMLOG_PATH, "a+", encoding="utf-8") as file:
        file.write(logstr + "\n")

def format_text(input: str) -> str:
  '''テキストの整形(あｱＡa>アアAA)を行う
  Parameters:
  ----------
  input : str
    変換元テキスト

  Returns:
  ----------
  fixed : str
    変換後テキスト
  '''
  fixed = input
  # ひらがなをカタカナに変換
  fixed = jaconv.hira2kata(fixed)
  # 半角カタカナを全角カタカナに変換
  fixed = jaconv.h2z(fixed)
  # 全角英数字を半角英数字に変換
  fixed = jaconv.z2h(fixed,kana=False, ascii=True, digit=True)
  # 英字を大文字に変換
  fixed = fixed.upper()
  
  return fixed


def fetch_pokemon(input: str) -> pd.DataFrame:
  '''ポケモン名から図鑑データを検索する
  Parameters:
  ----------
  input : str
    検索するポケモン名
  '''
  output_log(str(input)+"の図鑑データを検索します")
  fixedName = format_text(input)
  
  #入力文字列先頭を辞書で置換
  if fixedName[0] in POKENAME_PREFIX_DICT and re.match(r'[ァ-ヺー]+',fixedName[1:]):
    fixedName = POKENAME_PREFIX_DICT[fixedName[0]] + fixedName[1:]

  # データベースをカタカナに
  kata_breloom_df = GLOBAL_BRELOOM_DF.iloc[:, 1:5].applymap(lambda x: jaconv.hira2kata(str(x)))
  SearchedData = kata_breloom_df[(kata_breloom_df['おなまえ'] == fixedName) | (kata_breloom_df['インデックス1'] == fixedName) | (kata_breloom_df['インデックス2'] == fixedName) | (kata_breloom_df['インデックス3'] == fixedName)]
  
  if len(SearchedData) > 0:
    return GLOBAL_BRELOOM_DF.iloc[SearchedData.index]
  else:
    output_log(fixedName+"の図鑑データは見つかりませんでした")
    return None

def bss_to_text(values) -> str:
  '''ポケモンの図鑑データから種族値文字列を生成する
  Parameters:
  ----------
  values : list or pd.Series or pd.DataFrame
    種族値のリスト or 種族値のSeries or 種族値のDataFrame
  '''
  if isinstance(values, list):
    bss = values
  elif isinstance(values, pd.Series):
    bss = [int(values['HP']), int(values['こうげき']), int(values['ぼうぎょ']), int(values['とくこう']), int(values['とくぼう']), int(values['すばやさ'])]
  elif isinstance(values, pd.DataFrame):
    bss = [int(values.iloc[0]['HP']), int(values.iloc[0]['こうげき']), int(values.iloc[0]['ぼうぎょ']), int(values.iloc[0]['とくこう']), int(values.iloc[0]['とくぼう']), int(values.iloc[0]['すばやさ'])]
  
  return f'{"-".join(map(str,bss))} 合計{sum(bss)}'


def pinyin_to_text(cw: str) -> str:
  '''中国語の文字からピンイン文字列を生成する
  Parameters:
  ----------
  cw : str
  中国語の文字
  
  Returns:
  ----------
  pinyin : str
  ピンイン文字列
  '''
  pinyins = []
  for pinyin in pypinyin.pinyin(cw, heteronym=True):
    if len(pinyin) == 1:
      pinyins.append(pinyin[0])
    else:
      heteronyms = "("
      for heteronym in pinyin:
        heteronyms += f'{heteronym},'
      pinyins.append(heteronyms[:-1] + ")")

  return " ".join(pinyins)
 

def generate_graph(bss: list[int], name=None) -> str:
    '''種族値グラフを生成する
    
    Parameters:
    ----------
    bss : list[int]
        種族値のリスト
    name : str, optional
        グラフに表示する名前
        
    Returns:
    ----------
    BSS_GRAPH_PATH : str
        生成したグラフのパス
    '''
    output_log(f"{'-'.join(map(str, bss))}の種族値グラフを生成します")
    
    # 値の準備
    values = [bss[0], bss[1], bss[2], bss[5], bss[4], bss[3]]  # HP, A, B, S, D, C の順
    labels = [f'HP{values[0]}', f'A{values[1]}', f'B{values[2]}', 
              f'S{values[3]}', f'D{values[4]}', f'C{values[5]}']
    
    # レーダーチャートのデータ準備
    radar_values = np.concatenate([values, [values[0]]])  # 多角形を閉じるため
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1, endpoint=True)
    
    # メモリ軸の設定
    if max(values) < 150:
        rgrids = [0, 50, 100, 150]
    else:
        a = max(values) / 2
        rgrids = [0, a, 2 * a]
    
    # プロット領域の設定
    fig = plt.figure(facecolor="cornsilk")
    ax = fig.add_subplot(1, 1, 1, polar=True, facecolor="cornsilk")
    
    # レーダーチャートの描画
    ax.plot(angles, radar_values, color="midnightblue", alpha=0.4, linewidth=0.5)
    ax.fill(angles, radar_values, alpha=0.9, color="midnightblue")
    
    # チャートの装飾設定
    ax.set_thetagrids(angles[:-1] * 180 / np.pi, labels, fontweight="roman")
    ax.set_rgrids([])  # 円形の目盛線を消す
    ax.spines['polar'].set_visible(False)  # 一番外側の円を消す
    ax.set_theta_zero_location("N")  # 始点を上(北)に変更
    ax.set_theta_direction(-1)  # 時計回りに変更
    
    # グリッドラインの描画
    for grid_value in rgrids:
        grid_values = [grid_value] * (len(labels) + 1)
        ax.plot(angles, grid_values, color="gray", linewidth=0.5, alpha=0.3)
    
    # メモリ値の表示
    for t in rgrids:
        ax.text(x=0, y=t, s=t, fontweight="ultralight", alpha=0.1)
    
    # グラフの範囲とグリッド設定
    ax.set_rlim([min(rgrids), max(rgrids)])
    ax.grid(True, alpha=0.1)
    
    # タイトルの設定
    total_stats = sum(values)
    if name is not None:
        ax.set_title(f"{name}\n合計{total_stats}", pad=20, fontsize=15)
    else:
        ax.set_title(f"合計{total_stats}", pad=20, fontsize=15)
    
    # グラフの保存
    plt.tight_layout()
    fig.savefig(BSS_GRAPH_PATH, bbox_inches='tight')
    plt.close('all')
    
    output_log(f"種族値グラフ生成完了: {BSS_GRAPH_PATH}")
    return BSS_GRAPH_PATH


#レポートしたり参照する関数 ユーザーIDとレポのインデックスを渡す modifiは増減値
def report(userId, repoIndex: str, modifi: int) -> int:
  '''レポートを行う
  Parameters:
  ----------
  userId : int
  ユーザーID
  repoIndex : str
  レポートのインデックス
  modifi : int
  増減値
  
  Returns:
  ----------
  int
  レポート後の値
  '''
  output_log(f"レポートを確認します: {userId} {repoIndex}")
  reports = pd.read_csv(REPORT_PATH, index_col=0)
  
  if repoIndex not in reports.columns:
    reports[repoIndex] = 0
    reports.to_csv(REPORT_PATH, index=True, index_label="ユーザーID", float_format="%.0f")
    output_log(f"新たな列を作成しました: {repoIndex}")
    
  # 指定されたユーザーIDが既に存在する場合はその行を参照し、そうでなければ新しい行を作成する
  if userId in reports.index:
    row = reports.loc[userId]
  else:
    user = client.get_user(userId)
    row = pd.DataFrame([[0] * len(reports.columns)], columns=reports.columns, index=[userId])
    #先頭列のID以外の初期値を入力
    #reports = reports.append(row)
    reports = pd.concat([reports, row], ignore_index=False)
    
    reports.loc[userId, 'ユーザー名']=user.name
    reports.loc[userId, 'クジびきけん']=1  # レポートに新しい行を追加
    output_log("新たなレポートを作成しました")
    
  if not repoIndex in ['ユーザーID','ユーザー名'] and not modifi == 0 :
    reports.loc[userId, repoIndex] += modifi
    reports.to_csv(REPORT_PATH, index=True, index_label="ユーザーID", float_format="%.0f") # 編集したデータをCSVファイルに書き込む
    output_log("レポートに書き込みました")
  
  return reports.loc[userId, repoIndex]

def attachment_file(file_path: str) -> discord.File:
  '''discordのファイルオブジェクトを生成する
  Parameters:
  ----------
  file_path : str
  元ファイルのパス

  Returns:
  ----------
  file : discord.File
  生成したファイルオブジェクト
  attachment_path : str
  添付ファイルのパス
  '''
  filename = f"attachedImage{os.path.splitext(file_path)[1]}"
  if not os.path.exists(file_path):
      file_path = NOTFOUND_IMAGE_PATH
  file = discord.File(file_path, filename=filename)
  attachment_path=f"attachment://{filename}"
  output_log(f"次のファイルを添付します: {file_path}")
  return file,attachment_path

def show_calendar(day: datetime = datetime.now(ZoneInfo("Asia/Tokyo"))) -> discord.Embed:
  calendarTitle = BALL_ICON
  
  if day.date() == datetime.now(ZoneInfo("Asia/Tokyo")).date():
    calendarTitle += f'{day.strftime("%Y/%m/%d")} ({WEAK_DICT[str(day.weekday())]}) 今日のできごと'
  else:
    calendarTitle += f'{day.strftime("%m/%d")}のできごと'

  history_df = pd.read_csv(POKECALENDAR_PATH, encoding="utf-8")
  history_df['日付'] = pd.to_datetime(history_df['日付'], format='%Y/%m/%d')
  matched_rows = history_df[history_df['日付'].dt.strftime('%m/%d') == day.strftime('%m/%d')].fillna('')

  thumbnailLink = ""
  if len(matched_rows) > 0 :
    calendarDescription = ""
    for index, row in matched_rows.iterrows():
      if row['プロパティ'] == '記念日':
        calendarDescription += f"> **{row['できごと']}**\n"
      else:
        calendarDescription += f"> **{row['日付'].year}年 {row['できごと']}**\nあれから{day.year - row['日付'].year}年\n"
      calendarDescription += f"関連リンク\n{row['関連リンク']}\n"
    if not (eventPokemon := matched_rows.iloc[0]["関連ポケモン"])=="":
      eventDexNum = fetch_pokemon(eventPokemon).iloc[0]["ぜんこくずかんナンバー"]
      thumbnailLink = f"{EX_SOURCE_LINK}art/{eventDexNum}.png"
  else:
    calendarDescription = "なんにもない すばらしい 一日"
    
  createdEmbed = discord.Embed(
    title=calendarTitle,
    color=0x7ED321,
    description=calendarDescription
  )
  createdEmbed.set_thumbnail(url=thumbnailLink)
  createdEmbed.set_footer(text="No.17 カレンダー")

  return createdEmbed

def show_senryu(unique: bool = False) -> discord.Embed:
  senryu_df = pd.read_csv(POKESENRYU_PATH)
  
  if unique:
    if (senryu_df['チェック'] == True).all():
      senryu_df['チェック'] = ''
    selectedSenryu = senryu_df[~(senryu_df['チェック']==True)].sample().fillna('')
    senryu_df.loc[selectedSenryu.index, 'チェック'] = True
    senryu_df.to_csv(POKESENRYU_PATH, index=False)
  else:
    selectedSenryu = senryu_df.sample().fillna('')

  createdEmbed = discord.Embed(
    title=f'{"今日の" if unique else ""}ポケモン川柳',
    color=0xF5A623,
    description=f'''```md
{selectedSenryu.iloc[0]['ポケモン川柳']}
*{selectedSenryu.iloc[0]['出典']} {selectedSenryu.iloc[0]['登場作品']}*```
{BALL_ICON}`みんなもポケモン ゲットじゃぞ!`'''
  )

  if not selectedSenryu.iloc[0]['登場ポケモン'] == '':
    senryuPokeData = fetch_pokemon(selectedSenryu.iloc[0]['登場ポケモン'])
    senryuDexNum = senryuPokeData.iloc[0]['ぜんこくずかんナンバー']
    createdEmbed.set_thumbnail(url=f"{EX_SOURCE_LINK}art/{senryuDexNum}.png")
    
  return createdEmbed


