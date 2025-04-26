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

#除外検索できるようにしたい 語頭のマイナスを検知,フラグを立てる
def make_filter_dict(values: list[str]) -> dict[str,list]:
  output_log("以下の項目でフィルタ辞書を生成します\n "+str(values))
  
  new_dict = {}
  # 小文字も大文字も認識できるようにキーのセットを拡張
  stats_keys = set(BASE_STATS_DICT.keys()).union({k.lower() for k in BASE_STATS_DICT.keys()})
  
  for i in range(len(values)):
    # 合計値の検出（例: 合計<550）
    if values[i].startswith('合計') and any(op in values[i] for op in ['>', '<', '=']):
      if 'STAT_EXPRESSION' not in new_dict:
        new_dict['STAT_EXPRESSION'] = []
      new_dict['STAT_EXPRESSION'].append(values[i])
      continue
    
    # 複雑な式や種族値条件の検出
    first_char_upper = values[i][0].upper() if values[i] else ''
    if first_char_upper in BASE_STATS_DICT or '(' in values[i]:
      if any(op in values[i] for op in ['>', '<', '=']):
        if 'STAT_EXPRESSION' not in new_dict:
          new_dict['STAT_EXPRESSION'] = []
        new_dict['STAT_EXPRESSION'].append(values[i])
        continue
    
    # 既存の処理
    if values[i] in GLOBAL_BRELOOM_DF['進化段階'].unique().tolist():
      dictIndex = '進化段階'
    elif values[i] in ['1','2','3','4','5','6','7','8','9']:
      dictIndex = '初登場世代'
    elif values[i] in GLOBAL_BRELOOM_DF['出身地'].unique().tolist():
      dictIndex = '出身地'
    elif values[i] in GLOBAL_BRELOOM_DF['タイプ1'].unique().tolist():
      dictIndex = 'タイプ'
    elif values[i].upper() in np.unique(GLOBAL_BRELOOM_DF[['特性1','特性2','隠れ特性']].astype(str).values.ravel()):
      dictIndex = '特性'
    else:
      continue
      
    if dictIndex not in new_dict:
      new_dict[dictIndex] = []
      
    new_dict[dictIndex].append(values[i])
    
  output_log("以下のフィルタ辞書を生成しました\n "+str(new_dict))
  return new_dict

def filter_dataframe(filter_dict):
  '''ポケモンの図鑑データをフィルタリングする
  Parameters:
  ----------
  filter_dict : dict
    フィルタリング条件の辞書
  '''
  output_log("以下の条件でデータベースをフィルタリングします\n "+str(filter_dict))
  filteredPokeData = GLOBAL_BRELOOM_DF.copy()
  
  # 表示用の処理済み条件辞書
  processed_conditions = {}
  
  # 数式によるフィルタリング
  if 'STAT_EXPRESSION' in filter_dict:
    for expression_str in filter_dict['STAT_EXPRESSION']:
      expr_dict = parse_stat_expression(expression_str)
      if expr_dict:
        # フィルタリングを実行
        filteredPokeData = evaluate_stat_expression(filteredPokeData, expr_dict)
        
        # 条件を表示用に整理
        if expr_dict['type'] == 'total':
          # 合計値条件
          if '合計' not in processed_conditions:
            processed_conditions['合計'] = []
          processed_conditions['合計'].append(expression_str)
        elif expr_dict['type'] == 'simple':
          # 単純な種族値比較（例: H>=100）
          stat_name = BASE_STATS_DICT[expr_dict['stat']]
          if stat_name not in processed_conditions:
            processed_conditions[stat_name] = []
          processed_conditions[stat_name].append(expression_str)
        elif expr_dict['type'] == 'equality':
          # 等値比較（例: A==C）
          if '数式' not in processed_conditions:
            processed_conditions['数式'] = []
          
          # 使いやすい形式に変換（A→こうげき）
          display_expr = expression_str
          for stat, col_name in BASE_STATS_DICT.items():
            display_expr = re.sub(r'\b' + re.escape(stat) + r'\b', col_name, display_expr, flags=re.IGNORECASE)
          
          processed_conditions['数式'].append(display_expr)
        else:
          # 複雑な数式（例: (H*B*D)/(B+D)<26825）
          if '数式' not in processed_conditions:
            processed_conditions['数式'] = []
            
          # 使いやすい形式に変換（A→こうげき）
          display_expr = expression_str
          for stat, col_name in BASE_STATS_DICT.items():
            display_expr = re.sub(r'\b' + re.escape(stat) + r'\b', col_name, display_expr, flags=re.IGNORECASE)
          
          processed_conditions['数式'].append(display_expr)
  
  # 通常のフィルタリング
  for key, value in filter_dict.items():
    if key == 'STAT_EXPRESSION':
      continue  # 数式は既に処理済み
    
    if key == 'タイプ':
      filteredPokeData = filteredPokeData[(filteredPokeData['タイプ1'].isin(value)) | (filteredPokeData['タイプ2'].isin(value))]
      processed_conditions['タイプ'] = value
    elif key == '特性':
      filteredPokeData = filteredPokeData[(filteredPokeData['特性1'].isin(value)) | (filteredPokeData['特性2'].isin(value)) | (filteredPokeData['隠れ特性'].isin(value))]
      processed_conditions['特性'] = value
    else:
      processed_conditions[key] = value
      try:
        if len(value) > 0 and all(isinstance(v, str) and v.isdecimal() for v in value):
          filteredPokeData = filteredPokeData[filteredPokeData[key].isin([int(v) for v in value])]
        else:
          filteredPokeData = filteredPokeData[filteredPokeData[key].isin(value)]
      except:
        filteredPokeData = filteredPokeData[filteredPokeData[key].isin(value)]
      
  output_log("データのフィルタリングが完了しました 取得行数: "+str(filteredPokeData.shape[0]))
  
  # DataFrameのカスタム属性として条件を保存（このアプローチがうまく行かないため、グローバル変数も使用）
  global LAST_PROCESSED_CONDITIONS
  LAST_PROCESSED_CONDITIONS = processed_conditions
  filteredPokeData.processed_conditions = processed_conditions
  
  return filteredPokeData

def filter_stat_combination(df, combination_str):
  '''複合条件に基づくフィルタリングを行う
  Parameters:
  ----------
  df : pd.DataFrame
    フィルタリング対象のデータフレーム
  combination_str : str
    複合条件の文字列（例：'B+D>=200'）
  
  Returns:
  ----------
  df : pd.DataFrame
    フィルタリング後のデータフレーム
  '''
  # パターンを使って演算子と値を抽出
  operator_match = re.search(r'([><]=?|==|!=)', combination_str)
  if not operator_match:
    return df
  
  operator = operator_match.group(1)
  parts = combination_str.split(operator)
  stats_str = parts[0]
  value = int(parts[1])
  
  # 種族値の列名のリストを作成
  stat_cols = []
  for stat in stats_str.split('+'):
    if stat in BASE_STATS_DICT:
      stat_cols.append(BASE_STATS_DICT[stat])
  
  # 複合条件に基づくフィルタリング
  if not stat_cols:
    return df
    
  if operator == '>=':
    return df[df[stat_cols].sum(axis=1) >= value]
  elif operator == '>':
    return df[df[stat_cols].sum(axis=1) > value]
  elif operator == '<=':
    return df[df[stat_cols].sum(axis=1) <= value]
  elif operator == '<':
    return df[df[stat_cols].sum(axis=1) < value]
  elif operator == '==':
    return df[df[stat_cols].sum(axis=1) == value]
  elif operator == '!=':
    return df[df[stat_cols].sum(axis=1) != value]
  
  return df

def filter_stat_expression(df, expression_str):
  '''数式に基づくフィルタリングを行う
  Parameters:
  ----------
  df : pd.DataFrame
    フィルタリング対象のデータフレーム
  expression_str : str
    条件式の文字列（例：'H>=100'、'B+D>=200'、'(H*B*D)/(B+D)<26825'）
  
  Returns:
  ----------
  df : pd.DataFrame
    フィルタリング後のデータフレーム
  '''
  try:
    # まず単純な種族値の比較演算子の場合を処理
    if expression_str[0].upper() in BASE_STATS_DICT and not '(' in expression_str:
      stat_key = expression_str[0].upper()
      col_name = BASE_STATS_DICT[stat_key]
      rest = expression_str[1:]
      
      # 演算子と値を抽出
      op_match = re.match(r'([><]=?|=)(.+)', rest)
      if op_match:
        op, val = op_match.groups()
        val = float(val)
        
        if op == '>=':
          return df[df[col_name] >= val]
        elif op == '>':
          return df[df[col_name] > val]
        elif op == '<=':
          return df[df[col_name] <= val]
        elif op == '<':
          return df[df[col_name] < val]
        elif op == '=':  # 単独の=も一致として扱う
          return df[df[col_name] == val]
    
    # 複雑な式の場合、式全体をパースして処理
    else:
      # 演算子位置を見つける
      op_match = re.search(r'([><]=?|=)', expression_str)
      if not op_match:
        return df
      
      # 演算子と左右の式を分離
      op_pos = op_match.start()
      op = op_match.group()
      left_expr = expression_str[:op_pos]
      right_val = float(expression_str[op_pos + len(op):])
      
      # 左辺の式を準備（種族値をDataFrameの列参照に置換）
      calc_expr = left_expr
      stat_dict = {k.lower(): v for k, v in BASE_STATS_DICT.items()}  # 小文字のキーも追加
      
      for stat, col_name in {**BASE_STATS_DICT, **stat_dict}.items():
        calc_expr = re.sub(r'\b' + re.escape(stat) + r'\b', f"df['{col_name}']", calc_expr)
      
      # 式を評価
      calculated_values = eval(calc_expr)
      
      # 比較演算に基づいてフィルタリング
      if op == '>=':
        return df[calculated_values >= right_val]
      elif op == '>':
        return df[calculated_values > right_val]
      elif op == '<=':
        return df[calculated_values <= right_val]
      elif op == '<':
        return df[calculated_values < right_val]
      elif op == '=':  # 単独の=も一致として扱う
        return df[calculated_values == right_val]
  
  except Exception as e:
    output_log(f"式の評価中にエラーが発生しました: {e}")
  
  return df

def parse_stat_expression(expression_str):
  '''種族値の数式を解析して辞書を返す
  Parameters:
  ----------
  expression_str : str
    条件式の文字列（例：'H>=100'、'(H*B*D)/(B+D)<26825'、'A==C'、'合計<550'）
  
  Returns:
  ----------
  dict
    解析結果の辞書
  '''
  try:
    # 合計値の検出（例: 合計<550）
    if expression_str.startswith('合計'):
      op_match = re.search(r'([><]=?|=)', expression_str)
      if op_match:
        op = op_match.group()
        val = float(expression_str[op_match.end():])
        return {
          'type': 'total',
          'operator': op,
          'value': val,
          'expression': expression_str
        }
      
    # 等値比較（A==C）や複合等式（A+100==C）の特殊処理
    equal_match = re.search(r'([=]{1,2})', expression_str)
    if equal_match and '>' not in expression_str and '<' not in expression_str:
      op_pos = equal_match.start()
      op = equal_match.group()
      left_expr = expression_str[:op_pos]
      right_expr = expression_str[op_pos + len(op):]
      
      # 左辺と右辺に使用されている種族値を抽出
      used_stats = []
      for stat in BASE_STATS_DICT.keys():
        if stat in left_expr.upper() or stat in right_expr.upper():
          used_stats.append(stat)
      
      return {
        'type': 'equality',
        'left_expr': left_expr,
        'right_expr': right_expr,
        'operator': op,
        'used_stats': used_stats,
        'expression': expression_str
      }
    
    # 単純な種族値の比較演算子の場合
    first_char = expression_str[0].upper()
    if first_char in BASE_STATS_DICT and not '(' in expression_str[:2]:
      stat_key = first_char
      col_name = BASE_STATS_DICT[stat_key]
      rest = expression_str[1:]
      
      # 演算子と値を抽出
      op_match = re.match(r'([><]=?|=)(.+)', rest)
      if op_match:
        op, val = op_match.groups()
        return {
          'type': 'simple',
          'stat': stat_key,
          'column': col_name,
          'operator': op,
          'value': float(val),
          'expression': expression_str
        }
    
    # 複雑な式の場合
    op_match = re.search(r'([><]=?|=)', expression_str)
    if op_match:
      op_pos = op_match.start()
      op = op_match.group()
      left_expr = expression_str[:op_pos]
      right_val = expression_str[op_pos + len(op):]
      
      # 使用されている種族値を抽出
      used_stats = []
      for stat in BASE_STATS_DICT.keys():
        if stat in left_expr.upper():
          used_stats.append(stat)
      
      return {
        'type': 'complex',
        'left_expr': left_expr,
        'operator': op,
        'right_val': right_val,
        'used_stats': used_stats,
        'expression': expression_str
      }
  
  except Exception as e:
    output_log(f"式の解析中にエラーが発生しました: {e}")
  
  return None

def evaluate_stat_expression(df, expr_dict):
  '''種族値の数式を評価してフィルタリングする
  Parameters:
  ----------
  df : pd.DataFrame
    フィルタリング対象のデータフレーム
  expr_dict : dict
    parse_stat_expressionから返される辞書
  
  Returns:
  ----------
  df : pd.DataFrame
    フィルタリング後のデータフレーム
  '''
  
  if not expr_dict:
    return df
  
  try:
    if expr_dict['type'] == 'total':
      # 合計値でのフィルタリング
      op = expr_dict['operator']
      val = expr_dict['value']
      
      if op == '>=':
        return df[df['合計'] >= val]
      elif op == '>':
        return df[df['合計'] > val]
      elif op == '<=':
        return df[df['合計'] <= val]
      elif op == '<':
        return df[df['合計'] < val]
      elif op == '=' or op == '==':
        return df[df['合計'] == val]

    elif expr_dict['type'] == 'simple':
      # 単純な種族値の比較
      col = expr_dict['column']
      op = expr_dict['operator']
      val = expr_dict['value']
      
      if op == '>=':
        return df[df[col] >= val]
      elif op == '>':
        return df[df[col] > val]
      elif op == '<=':
        return df[df[col] <= val]
      elif op == '<':
        return df[df[col] < val]
      elif op == '=' or op == '==':
        return df[df[col] == val]
      
    elif expr_dict['type'] == 'equality':
      # 等式の評価（例: A==C, A+100==C）
      left_expr = preprocess_expression(expr_dict['left_expr'])
      right_expr = preprocess_expression(expr_dict['right_expr'])
      
      output_log(f"等式の評価: {left_expr} == {right_expr}")
      
      # 各行ごとに式を評価
      results = []
      for _, row in df.iterrows():
        # 左辺の式を評価
        left_calc = left_expr
        for stat in BASE_STATS_DICT.keys():
          if stat in left_calc.upper():
            col_name = BASE_STATS_DICT[stat]
            left_calc = re.sub(r'\b' + stat + r'\b', str(row[col_name]), left_calc, flags=re.IGNORECASE)
        
        # 右辺の式を評価
        right_calc = right_expr
        for stat in BASE_STATS_DICT.keys():
          if stat in right_calc.upper():
            col_name = BASE_STATS_DICT[stat]
            right_calc = re.sub(r'\b' + stat + r'\b', str(row[col_name]), right_calc, flags=re.IGNORECASE)
        
        # 両辺を評価して比較
        try:
          left_result = eval(left_calc)
          right_result = eval(right_calc)
          results.append(left_result == right_result)
        except Exception as e:
          output_log(f"等式評価中のエラー: {e} 左辺: {left_calc} 右辺: {right_calc}")
          results.append(False)
      
      # フィルタリング
      return df[results]
      
    elif expr_dict['type'] == 'complex':
      # 複雑な式の評価
      left_expr = preprocess_expression(expr_dict['left_expr'])
      op = expr_dict['operator']
      
      # 右辺が数値か式か判断
      try:
        right_val = float(expr_dict['right_val'])
        is_numeric_right = True
      except:
        right_val = preprocess_expression(expr_dict['right_val'])
        is_numeric_right = False
      
      output_log(f"前処理済み式: {left_expr} {op} {right_val}")
      
      # 各行ごとに式を評価
      results = []
      for _, row in df.iterrows():
        # 式中の種族値を実際の値に置換
        calc_expr = left_expr
        for stat in BASE_STATS_DICT.keys():
          if stat in calc_expr.upper():
            col_name = BASE_STATS_DICT[stat]
            calc_expr = re.sub(r'\b' + stat + r'\b', str(row[col_name]), calc_expr, flags=re.IGNORECASE)
        
        # 右辺が式の場合は評価
        if not is_numeric_right:
          right_calc = right_val
          for stat in BASE_STATS_DICT.keys():
            if stat in right_calc.upper():
              col_name = BASE_STATS_DICT[stat]
              right_calc = re.sub(r'\b' + stat + r'\b', str(row[col_name]), right_calc, flags=re.IGNORECASE)
          try:
            right_val_eval = eval(right_calc)
          except Exception as e:
            output_log(f"右辺評価中のエラー: {e} 式: {right_calc}")
            results.append(False)
            continue
        else:
          right_val_eval = right_val
        
        # 評価
        try:
          left_result = eval(calc_expr)
          
          # 比較演算
          if op == '>=':
            results.append(left_result >= right_val_eval)
          elif op == '>':
            results.append(left_result > right_val_eval)
          elif op == '<=':
            results.append(left_result <= right_val_eval)
          elif op == '<':
            results.append(left_result < right_val_eval)
          elif op == '=' or op == '==':
            results.append(left_result == right_val_eval)
          else:
            results.append(False)
        except Exception as e:
          output_log(f"行の評価中にエラー: {e} 式: {calc_expr}")
          results.append(False)
      
      # フィルタリング
      return df[results]
  
  except Exception as e:
    output_log(f"式の評価中にエラーが発生しました: {e}")
  
  return df

def preprocess_expression(expr):
  '''数式を前処理して、Python構文に合わせる
  Parameters:
  ----------
  expr : str
    元の数式
  
  Returns:
  ----------
  str
    処理後の数式
  '''
  # 数値に変換可能な場合はそのまま返す
  try:
    float(expr)
    return expr
  except:
    pass
  
  # 掛け算の * を明示的に挿入（例: (A+B)(C+D) → (A+B)*(C+D)）
  processed = re.sub(r'\)(\()', ')*(', expr)
  
  # 種族値の後に直接カッコがある場合も * を挿入（例: H(B+D) → H*(B+D)）
  for stat in set(list(BASE_STATS_DICT.keys()) + [k.lower() for k in BASE_STATS_DICT.keys()]):
    processed = re.sub(r'(' + re.escape(stat) + r')(\()', r'\1*\2', processed)
  
  # 数字の後にカッコがある場合も * を挿入（例: 2(B+D) → 2*(B+D)）
  processed = re.sub(r'(\d)(\()', r'\1*\2', processed)
  
  return processed
  '''数式を前処理して、Python構文に合わせる
  Parameters:
  ----------
  expr : str
    元の数式
  
  Returns:
  ----------
  str
    処理後の数式
  '''
  # 掛け算の * を明示的に挿入（例: (A+B)(C+D) → (A+B)*(C+D)）
  processed = re.sub(r'\)(\()', ')*(', expr)
  
  # 種族値の後に直接カッコがある場合も * を挿入（例: H(B+D) → H*(B+D)）
  for stat in set(list(BASE_STATS_DICT.keys()) + [k.lower() for k in BASE_STATS_DICT.keys()]):
    processed = re.sub(r'(' + re.escape(stat) + r')(\()', r'\1*\2', processed)
  
  return processed

def search_pokemon(filter_dict):
  '''フィルター条件に基づいてポケモンを検索し、結果と適用された条件を返す
  Parameters:
  ----------
  filter_dict : dict
    フィルタリング条件の辞書
  
  Returns:
  ----------
  tuple
    (filtered_df, processed_conditions)
  '''
  output_log("以下の条件でデータベースをフィルタリングします\n "+str(filter_dict))
  filteredPokeData = GLOBAL_BRELOOM_DF.copy()
  
  # 表示用の処理済み条件辞書
  processed_conditions = {}
  
  # 数式によるフィルタリング
  if 'STAT_EXPRESSION' in filter_dict:
    for expression_str in filter_dict['STAT_EXPRESSION']:
      expr_dict = parse_stat_expression(expression_str)
      if expr_dict:
        # フィルタリングを実行
        filteredPokeData = evaluate_stat_expression(filteredPokeData, expr_dict)
        
        # 条件を表示用に整理
        if expr_dict['type'] == 'total':
          # 合計値条件
          if '合計' not in processed_conditions:
            processed_conditions['合計'] = []
          processed_conditions['合計'].append(expression_str)
        elif expr_dict['type'] == 'simple':
          # 単純な種族値比較（例: H>=100）
          stat_key = expr_dict['stat'].upper() if 'stat' in expr_dict else expression_str[0].upper()
          if stat_key in BASE_STATS_DICT:
            stat_name = BASE_STATS_DICT[stat_key]
            if stat_name not in processed_conditions:
              processed_conditions[stat_name] = []
            
            # 表示用に整形（A→こうげき）
            display_expr = expression_str
            display_expr = re.sub(r'^' + re.escape(stat_key), stat_name, display_expr, flags=re.IGNORECASE)
            processed_conditions[stat_name].append(display_expr)
        elif expr_dict['type'] == 'equality':
          # 等値比較（例: A==C）
          if '数式' not in processed_conditions:
            processed_conditions['数式'] = []
          
          # 使いやすい形式に変換（A→こうげき）
          display_expr = expression_str
          for stat, col_name in BASE_STATS_DICT.items():
            display_expr = re.sub(r'\b' + re.escape(stat) + r'\b', col_name, display_expr, flags=re.IGNORECASE)
          
          processed_conditions['数式'].append(display_expr)
        else:
          # 複雑な数式（例: (H*B*D)/(B+D)<26825）
          if '数式' not in processed_conditions:
            processed_conditions['数式'] = []
            
          # 使いやすい形式に変換（A→こうげき）
          display_expr = expression_str
          for stat, col_name in BASE_STATS_DICT.items():
            display_expr = re.sub(r'\b' + re.escape(stat) + r'\b', col_name, display_expr, flags=re.IGNORECASE)
          
          processed_conditions['数式'].append(display_expr)
  
  # 通常のフィルタリング
  for key, value in filter_dict.items():
    if key == 'STAT_EXPRESSION':
      continue  # 数式は既に処理済み
    
    if key == 'タイプ':
      filteredPokeData = filteredPokeData[(filteredPokeData['タイプ1'].isin(value)) | (filteredPokeData['タイプ2'].isin(value))]
      processed_conditions['タイプ'] = value
    elif key == '特性':
      filteredPokeData = filteredPokeData[(filteredPokeData['特性1'].isin(value)) | (filteredPokeData['特性2'].isin(value)) | (filteredPokeData['隠れ特性'].isin(value))]
      processed_conditions['特性'] = value
    else:
      processed_conditions[key] = value
      try:
        if len(value) > 0 and all(isinstance(v, str) and v.isdecimal() for v in value):
          filteredPokeData = filteredPokeData[filteredPokeData[key].isin([int(v) for v in value])]
        else:
          filteredPokeData = filteredPokeData[filteredPokeData[key].isin(value)]
      except:
        filteredPokeData = filteredPokeData[filteredPokeData[key].isin(value)]
      
  output_log("データのフィルタリングが完了しました 取得行数: "+str(filteredPokeData.shape[0]))
  output_log(f"処理済みの条件: {processed_conditions}")
  
  return (filteredPokeData, processed_conditions)
