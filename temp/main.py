#!/usr/bin/python3
# -*- coding: utf-8 -*-
# main.py

# 標準ライブラリ
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import re
import asyncio
import pprint
# 外部ライブラリ
##https://discordpy.readthedocs.io/ja/latest/index.html
import discord
from discord.ext import tasks
import pandas as pd
import numpy as np
import jaconv
from dotenv import load_dotenv
# 分割されたモジュール
import bot_module.func as ub
import bot_module.embed as ub_embed
from bot_module.config import *
#botの連続稼働用
#from server import keep_alive

#"""デバッグ用設定
LOG_CHANNEL_ID = 1140787559325249717
PDW_SERVER_ID = DEV_SERVER_ID
DEBUG_CHANNEL_ID = LOG_CHANNEL_ID
GUIDELINE_CHANNEL_ID = LOG_CHANNEL_ID
STAGE_CHANNEL_ID = LOG_CHANNEL_ID
DAIRY_CHANNEL_ID = LOG_CHANNEL_ID
HELLO_CHANNEL_ID = LOG_CHANNEL_ID
CALLSTATUS_CHANNEL_ID = LOG_CHANNEL_ID
#"""

#参照データ
BQ_FILTERED_DF = GLOBAL_BRELOOM_DF.copy
BQ_FILTER_DICT={'進化段階':['最終進化','進化しない']}

QUIZ_PROCESSING_FLAG=0 #クイズ処理中フラグ
BAKUSOKU_MODE=True

tree = discord.app_commands.CommandTree(client)

@tree.command(name="test", description="開発中")
@discord.app_commands.guilds(PDW_SERVER_ID)
async def slash_test(interaction: discord.Interaction):
  lotoReset = pd.read_csv(ub.report_PATH)
  lotoReset["クジびきけん"] = 1
  lotoReset.to_csv(REPORT_PATH, index=False)
  await interaction.response.send_message("テストは作動しました",ephemeral=True)

@tree.command(name="help", description="botの操作方法を表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
async def slash_help(interaction: discord.Interaction):
  with open("document/manual.txt", "r") as file:
     manual = file.read()

  helpEmbed = discord.Embed(
    title="",
    color=0xffffff,
    description=manual
    #url=""
  )
  helpEmbed.set_author(name='BOT せつめいしょ',
    icon_url=f"{EX_SOURCE_LINK}icon/Breloom.png"
  )
  helpEmbed.set_footer(text="No.00 せつめいしょ")
  
  if interaction.user.guild_permissions.administrator:
    with open("document/admin_manual.txt", "r") as file:
     adminManual = file.read()
     
    helpEmbed.add_field(name="管理者専用コマンド",value=adminManual)
    
  await interaction.response.send_message(embed=helpEmbed,ephemeral=True)


@tree.command(name="q", description="現在の出題設定に基づいてクイズを出題します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(quizname='クイズの種別 未記入で種族値クイズが指定されます')
@discord.app_commands.choices(quizname=[discord.app_commands.Choice(name=val, value=val) for val in list(QUIZNAME_DICT.keys())])
async def slash_q(interaction: discord.Interaction, quizname: str="種族値クイズ"):
  seiseiEmbed = discord.Embed(
            title="**妖精さん おしごとチュウ**",
            color=0xFFFFFF,#デフォルトカラー
            description=f'{quizname}を生成しています'
          )
  await interaction.response.send_message(embed=seiseiEmbed,delete_after=1)
  await quiz(QUIZNAME_DICT[quizname]).post(interaction.channel)
  
@tree.command(name="quizrate", description="クイズの戦績を表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(user='表示したいメンバー名',quizname='クイズの種別 未記入で種族値クイズが指定されます')
@discord.app_commands.choices(quizname=[discord.app_commands.Choice(name=val, value=val) for val in list(QUIZNAME_DICT.keys())])
async def slash_quizrate(interaction: discord.Interaction, user: discord.Member=None,quizname: str="種族値クイズ"):
  if user is not None:
    showId=user.id
    showName=client.get_user(showId).name
  else:
    showId=interaction.user.id
    showName=interaction.user.name
    
  await ub.output_log("戦績表示を実行します")
  w=ub.report(showId, f'{QUIZNAME_DICT[quizname]}正答', 0)
  l=ub.report(showId, f'{QUIZNAME_DICT[quizname]}誤答', 0)
  await interaction.response.send_message(f'''{showName}さんの{quizname}戦績
正答: {w}回 誤答: {l}回
正答率: {int(w/(w+l)*100) if not w+l==0 else 0}%''')


@tree.command(name="bmode", description="クイズの連続出題モードを切り替えます")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(mode='連続出題モードのオンオフ 未記入でトグル切り替え')
@discord.app_commands.choices(
  mode=[discord.app_commands.Choice(name="ON", value="ON"),discord.app_commands.Choice(name="OFF", value="OFF")]
)
async def slash_bmode(interaction: discord.Interaction, mode: str=None):
  global BAKUSOKU_MODE
  if mode=="ON":
    BAKUSOKU_MODE=True
  elif mode=="OFF":
    BAKUSOKU_MODE=False
  else:
    BAKUSOKU_MODE= not BAKUSOKU_MODE
  await ub.output_log("爆速モードが"+str(BAKUSOKU_MODE)+"になりました")
  await interaction.response.send_message(f"連続出題が{'ON' if BAKUSOKU_MODE else 'OFF'}になりました")
  

@tree.command(name="graph", description="ポケモン名から種族値グラフを表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(name='表示したいポケモンのおなまえ')
async def slash_graph(interaction: discord.Interaction, name: str):
  graphDatas = ub.fetch_pokemon(name)
  baseStats = [int(graphDatas['HP']),int(graphDatas['こうげき']),int(graphDatas['ぼうぎょ']),int(graphDatas['とくこう']),int(graphDatas['とくぼう']),int(graphDatas['すばやさ'])]
  if graphDatas is not None:    
    await interaction.response.defer() #レスポンス遅延のおまじない
    graphEmbed = discord.Embed(
      title=graphDatas.iloc[0]['おなまえ']+"の種族値グラフ",
      description=ub.bss_to_text(graphDatas)
    )
    file = discord.File(ub.generate_graph(baseStats), filename="image.png")
    graphEmbed.set_image(url="attachment://image.png")
    await interaction.followup.send(file=file,embed=graphEmbed)
  else:
    await interaction.response.send_message(name+"は図鑑に存在しません")


@tree.command(name="graphbss", description="種族値から種族値グラフを表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(h="HP種族値",a="こうげき種族値",b="ぼうぎょ種族値",c="とくこう種族値",d="とくぼう種族値",s="すばやさ種族値")
async def slash_graphbss(
  interaction: discord.Interaction,
  h: discord.app_commands.Range[int, 1,255], a:  discord.app_commands.Range[int, 1,255],
  b:  discord.app_commands.Range[int, 1,255], c:  discord.app_commands.Range[int, 1,255],
  d:  discord.app_commands.Range[int, 1,255], s:  discord.app_commands.Range[int, 1,255]
):
  baseStats = [h,a,b,c,d,s]
  await interaction.response.defer() #レスポンス遅延のおまじない
  graphEmbed = discord.Embed(
    title="種族値グラフ",
    description=ub.bss_to_text(baseStats)
  )
  file = discord.File(ub.generate_graph(baseStats), filename="image.png")
  graphEmbed.set_image(url="attachment://image.png")
  await interaction.followup.send(file=file,embed=graphEmbed)


@tree.command(name="pass", description="8ケタの乱数を生成します")
@discord.app_commands.guilds(PDW_SERVER_ID)
async def slash_pass(interaction: discord.Interaction):
  await ub.output_log("あいことば生成を実行します")
  await interaction.response.send_message(f"あいことば: {random.randint(10000000, 99999999)}")


@tree.command(name="dex", description="ポケモンの図鑑データを表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(name="表示したいポケモンのおなまえ")
async def slash_dex(interaction: discord.Interaction, name: str):
  await ub.output_log("図鑑を実行します")

  if (pokedata:= ub.fetch_pokemon(name))is not None: #データが存在する場合は、図鑑データを返信
    pokedata = pokedata.fillna(" ")
    dexNumber = pokedata.iloc[0]['ぜんこくずかんナンバー']
    dexName = str(pokedata.iloc[0]['おなまえ'])
    dexIndexs = [pokedata.iloc[0]['インデックス1'],pokedata.iloc[0]['インデックス2'],pokedata.iloc[0]['インデックス3']]
    dexType1 = str(pokedata.iloc[0]['タイプ1'])
    dexType2 = str(pokedata.iloc[0]['タイプ2'])
    dexAbi1 = str(pokedata.iloc[0]['特性1'])
    dexAbi2 = str(pokedata.iloc[0]['特性2'])
    dexAbiH = str(pokedata.iloc[0]['隠れ特性'])
    dexH = int(pokedata.iloc[0]['HP'])
    dexA = int(pokedata.iloc[0]['こうげき'])
    dexB = int(pokedata.iloc[0]['ぼうぎょ'])
    dexC = int(pokedata.iloc[0]['とくこう'])
    dexD = int(pokedata.iloc[0]['とくぼう'])
    dexS = int(pokedata.iloc[0]['すばやさ'])
    dexSum = str(pokedata.iloc[0]['合計'])
    dexGen = str(pokedata.iloc[0]['初登場作品'])
    #dexSpecies = str(pokedata.iloc[0]['ぶんるい'])

    dexEmbed = discord.Embed(
      title=f'{BALL_ICON}{dexName}の図鑑データ{BALL_ICON}',
      color=TYPE_COLOR_DICT[dexType1],
      description=f'''No.{dexNumber} {dexName} 出身: {dexGen}
タイプ: {dexType1}/{dexType2}
とくせい: {dexAbi1}/{dexAbi2}/{dexAbiH}
```
┌───┬───┬───┬───┬───┬───┰───┐
│ H │ A │ B │ C │ D │ S ┃Tot│
├───┼───┼───┼───┼───┼───╂───┤
│{dexH:3}-{dexA:3}-{dexB:3}-{dexC:3}-{dexD:3}-{dexS:3}-{dexSum:3}│
└───┴───┴───┴───┴───┴───┸───┘
```
      ''',
      url=f'https://yakkun.com/sv/zukan/?national_no={dexNumber}'
    )
    dexEmbed.set_thumbnail(url=f'{EX_SOURCE_LINK}art/{dexNumber}.png')

    indexCount = 0
    for dexIndex in dexIndexs:
      if not dexIndex == " ":
        dexEmbed.add_field(name="INDEX",value=dexIndex)
        indexCount += 1
    if indexCount > 0:
      dexEmbed.fields[indexCount-1].inline = False
    
    if (GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] == int(dexNumber)-1).any():
      dexEmbed.add_field(
        name=f'No.{int(dexNumber)-1}',
        value=f'**<**  {GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] == int(dexNumber)-1]["おなまえ"].values[0]:12}'
      )

    if (GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] == int(dexNumber)+1).any():
      dexEmbed.add_field(
        name=f'No.{int(dexNumber)+1}',
        value=f'{GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] == int(dexNumber)+1]["おなまえ"].values[0]:12} **>**'
      )
    
    dexEmbed.set_footer(text=f'dex - {dexNumber}')
    
    await interaction.response.send_message(embed=dexEmbed)
    
  else: #データが存在しない場合は、エラーメッセージを返信
    await ub.output_log(f'404 NotFound name:{name}')
    await interaction.response.send_message(embed=ub_embed.error_404(name))
    
@tree.command(name="chn", description="ポケモンの中国語名(繁体)を表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(name="表示したいポケモンのおなまえ")
async def slash_chn(interaction: discord.Interaction, name: str):
  await ub.output_log("図鑑を実行します")

  if (pokedata := ub.fetch_pokemon(name)) is not None:
      pokedata = pokedata.fillna(" ")
      dexNumber = pokedata.iloc[0]['ぜんこくずかんナンバー']

      thumbnailUrl = f'{EX_SOURCE_LINK}art/{dexNumber}.png'

      dexNameZh = str(pokedata.iloc[0]['中国語繁体'])
      dexUrl = f'https://yakkun.com/sv/zukan/?national_no={dexNumber}'

      dexEmbed = discord.Embed(
          title=f'{BALL_ICON}{dexNameZh}的圖鑑資料{BALL_ICON}',
          color=0x000000,
          description=f'図鑑番号: {dexNumber}\n中国語繁体名: {dexNameZh}\n拼音: {ub.pinyin_to_text(dexNameZh)}',
          url=dexUrl
      )
      dexEmbed.set_thumbnail(url=thumbnailUrl)
      dexEmbed.set_footer(text=f'chn - {dexNumber}')

      await interaction.response.send_message(embed=dexEmbed)
    
  else: #データが存在しない場合は、エラーメッセージを返信
    await ub.output_log("404 NotFound")
    await interaction.response.send_message(embed=ub_embed.error_404(name))


@tree.command(name="stats", description="ポケモンの実数値を計算します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(name="ポケモンの名前",stats="計算するステータス(初期値: すばやさ)",build="努力値と個体値と性格のショートカット",ev="努力値(初期値: 0)",iv="個体値(初期値: 31)",nature="性格補正(初期値: 無補正)",modifier="ランク補正(初期値: 0)",lv="ポケモンのレベル(初期値: 50)")
@discord.app_commands.choices(
  stats = [discord.app_commands.Choice(name=val, value=val) for val in ["HP", "こうげき", "ぼうぎょ", "とくこう","とくぼう","すばやさ"]],
  build = [discord.app_commands.Choice(name=val, value=val) for val in ["無振", "最高値", "最低値", "ぶっぱ"]],
  nature = [discord.app_commands.Choice(name=val, value=val) for val in ["無補正", "上昇補正", "下降補正"]],
  #other=[discord.app_commands.Choice(name=val, value=val) for val in ["こだわりアイテム", "いのちのたま", "ダイマックス","天候特性","おいかぜ"]]
)
async def slash_stats(
  interaction: discord.Interaction,
  name: str,
  stats: str = "すばやさ",
  build: str = None,
  ev: discord.app_commands.Range[int, 0,252] = 0,
  iv: discord.app_commands.Range[int, 0,31] = 31,
  nature: str = "無補正",
  modifier: discord.app_commands.Range[int, -6,6] = 0,
  lv: discord.app_commands.Range[int, 1,100] = 50
):
  if build is not None:
    build_dict = {"無振":{"ev":0,"iv":31,"nature":"無補正"}, "最高値":{"ev":252,"iv":31,"nature":"上昇補正"}, "最低値":{"ev":0,"iv":0,"nature":"下降補正"}, "ぶっぱ":{"ev":252,"iv":31,"nature":"無補正"}}
    ev = build_dict[build]["ev"]
    iv = build_dict[build]["iv"]
    nature = build_dict[build]["nature"]

  if (statsPokeData := ub.fetch_pokemon(name)) is not None:
    bs = statsPokeData.iloc[0][stats]
    correct_dict = {"無補正":1, "上昇補正":1.1, "下降補正":0.9}
    natureCorrect = correct_dict[nature]
    top = 2
    bottom = 2
      
    if stats == "HP":
      result = int((bs*2+iv+int(ev/4))*lv/100)+lv+10
    else:
      if modifier > 0:
        top += modifier
      else:
        bottom += modifier
      result = int(int((int((bs*2+iv+int(ev/4))*lv/100)+5)*natureCorrect)*top/bottom)
      
    statsEmbed = discord.Embed(
      title="実数値計算",
      color=0x0000ff,
      description=f"**{statsPokeData.iloc[0]['おなまえ']}** の **{stats}** は __**{result}**__ です。"
    )
    statsEmbed.add_field(name="種族値", value=bs, inline=True)
    statsEmbed.add_field(name="努力値", value=ev, inline=True)
    statsEmbed.add_field(name="個体値", value=iv, inline=True)
    statsEmbed.add_field(name="レベル", value=lv, inline=True)
    statsEmbed.add_field(name="性格", value=nature, inline=True)
    statsEmbed.add_field(name="ランク補正", value=modifier, inline=True)
    
    await interaction.response.send_message(embed=statsEmbed)
  else:
    await interaction.response.send_message(embed=ub_embed.error_404(name))

  
@tree.command(name="poll", description="投票を取ることができます")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(a='選択肢1',b='選択肢2',o='選択肢3(任意)',ab='選択肢4(任意)',title='投票のタイトル(任意)',multiple='複数回答の可否')
async def slash_poll(
  interaction: discord.Interaction,
  a: str, b: str, o: str = None, ab: str = None,
  title: str = "アンケート", multiple: bool = False
):
  description = f'🅰️ {a}\n🅱️ {b}'
  if o is not None:
    description += f'\n🅾️ {o}'
  if ab is not None:
    description += f'\n🆎 {ab}'
    
  pollEmbed = discord.Embed(
    title=title,
    description=description,
    color=0x955c87
  )
  pollEmbed.set_footer(text=f'No.27 アンケート ({"MA" if multiple else "SA"})')
  
  await interaction.response.send_message(embed=pollEmbed)
  
  message = await interaction.original_response()
  await message.add_reaction('🅰️')
  await message.add_reaction('🅱️')
  if o is not None:
    await message.add_reaction('🅾️')
  if ab is not None:
    await message.add_reaction('🆎')


@client.event
async def on_raw_reaction_add(payload):
  if payload.member.bot:
    return
  message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
  
  if (message.author == client.user and message.embeds):
    embedFooterText = message.embeds[0].footer.text
    if ("No.27 アンケート" in embedFooterText  and "(SA)" in embedFooterText):
      botChoices = []
      yourChoices = []
      for reaction in message.reactions:
        async for user in reaction.users():
          if user == client.user:
            botChoices.append(reaction.emoji)
          if user == payload.member:
            yourChoices.append(reaction.emoji)
            
      for yourChoice in yourChoices:
        if (
          not yourChoice in botChoices
          or yourChoice != str(payload.emoji) and sum(1 for x in yourChoices if x in botChoices) > 1
        ):
          await message.remove_reaction(yourChoice, payload.member)


@tree.command(name="wish", description="botのねがいごとを送信します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(feedback='バグ報告やご意見、ご要望を記述')
async def slash_wish(interaction: discord.Interaction, feedback: str):
  await ub.output_log("ご意見受け付けを実行します")
  timeStr = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")
  
  userFeedback = pd.DataFrame({"time":[timeStr], "Name":[interaction.user.name], "Feedback": [feedback]})
  userFeedback.to_csv(FEEDBACK_PATH, mode='a', index=False,header=not os.path.exists(FEEDBACK_PATH))
  await interaction.response.send_message(f"以下のねがいごとを受け付けました。```\n{feedback}```ありがとうございます☻")
  
  if not interaction.channel.id == DEBUG_CHANNEL_ID: #開発チャンネル外での投稿なら開発チャンネルに送信
    await client.get_channel(DEBUG_CHANNEL_ID).send(f"""ねがいごとが届きました!
送信ch: <#{interaction.channel.id}>
送信者: <@!{interaction.user.id}>
内容: {feedback}""")


@tree.command(name="spore", description="botをねむらせます")
@discord.app_commands.guilds(PDW_SERVER_ID)
async def slash_spore(interaction: discord.Interaction):
  if interaction.user.guild_permissions.administrator:
    # データを保存するDataFrameを作成
    memorys = pd.DataFrame({"channel_id": [interaction.channel.id], "bakusoku_mode": [BAKUSOKU_MODE], "BQ_FILTER_DICT": [str(BQ_FILTER_DICT)]})
    # csvファイルに書き込み
    memorys.to_csv(MEMORY_PATH, index=False)
    await interaction.response.send_message(f'''```{client.user.name}は
眠ってしまった!```''')
    await ub.output_log("botは"+interaction.channel.name+"で眠りにつきました")
    await client.close()
  else:
    await interaction.response.send_message(f"""```{client.user.name}は
{random.choice(["めいれいを むしした!","なまけている!","そっぽを むいた!","いうことを きかない!","しらんぷりした!"])}```""")


@tree.command(name="getmessage", description="メッセージIDからメッセージオブジェクトを取得します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(id='メッセージID',ch='メッセージが存在するチャンネル')
async def slash_getmessage(interaction: discord.Interaction,id: str, ch: discord.TextChannel=None):
  if ch is None:
    ch=interaction.channel
  if id.isdigit():
    try:
      message = await ch.fetch_message(id)
      response=f'60秒後に自動削除されます```{pprint.pformat(message.embeds[0].to_dict())}```'
    except discord.NotFound:
      response="メッセージが見つかりませんでした"
  else:
    response="有効なメッセージIDではありません"
    
  await interaction.response.send_message(response,ephemeral=True,delete_after=60)


@tree.command(name="calendar", description="ポケモンで今日はなんのひ(別の日も指定できます)")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(month='なん月',data='なん日')
async def slash_calendar(interaction: discord.Interaction,month: discord.app_commands.Range[int, 1,12]=None,data: discord.app_commands.Range[int, 1,31]=None):
  if month is not None and data is not None:
    embed = await ub.show_calendar(datetime(datetime.now(ZoneInfo("Asia/Tokyo")).year, month, data, tzinfo=ZoneInfo("Asia/Tokyo")).date())
  else:
    embed = await ub.show_calendar()
  await interaction.response.send_message(embed=embed)


@tree.command(name="senryu", description="ランダムでポケモン川柳を表示します")
@discord.app_commands.guilds(PDW_SERVER_ID)
async def slash_senryu(interaction: discord.Interaction):
  embed = await ub.show_senryu()
  sendSenryu = embed.description.split("\n")[1]
  await interaction.response.send_message(sendSenryu,embed=embed)


@tree.command(name="notice", description="botのステータスメッセージを変更します")
@discord.app_commands.describe(message='ステータスメッセージ')
@discord.app_commands.guilds(PDW_SERVER_ID)
async def slash_notice(interaction: discord.Interaction, message: str = "キノコのほうし"):
  if interaction.user.guild_permissions.administrator:
    if message is not None:
      await client.change_presence(activity=discord.Activity(name=message, type=discord.ActivityType.playing))
    else:
      await client.change_presence(activity=discord.Activity(name='キノコのほうし', type=discord.ActivityType.playing))
    await interaction.response.send_message(f"アクティビティが **{message}** に変更されました", ephemeral=True)
  else:
    await interaction.response.send_message(f"""```{client.user.name}は
{random.choice(["めいれいを むしした!", "なまけている!", "そっぽを むいた!", "いうことを きかない!", "しらんぷりした!"])}```""")


@tree.command(name="guideline", description="ガイドラインを投稿します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(mode='ガイドラインの編集方法を設定します',num='ガイドラインの番号を指定します(未入力ですべてを対象)',channel='編集対象のチャンネルを指定します')
@discord.app_commands.choices(mode=[
  discord.app_commands.Choice(name="post", value="post"),
  discord.app_commands.Choice(name="update", value="update"),
  discord.app_commands.Choice(name="delete", value="delete")
])
async def slash_guideline(interaction: discord.Interaction, mode: str = 'post', num: int = None, channel: discord.TextChannel = None):
  if channel == None:
    channel = interaction.channel
  await interaction.response.send_message(f'{channel.name}でガイドラインの{mode}を実行します', ephemeral=True)
  
  if mode == 'post':
    await GuidelinePost(channel.id,interaction.user.id).post(num)
  elif mode == 'update':
    await GuidelinePost(channel.id,interaction.user.id).update(num)
  elif mode == 'delete':
    await GuidelinePost(channel.id,interaction.user.id).delete(num)
  await ub.output_log(f'ガイドラインが{mode}されました\n{channel.name}: {interaction.user.name}')


@tree.command(name="invite", description="このチャンネルにメンバーを招待します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(member='招待したいメンバー',anonymity='招待者の匿名化')
async def slash_invite(interaction: discord.Interaction, member: discord.Member, anonymity: bool = False):
  x = discord.Embed(
    title="招待失敗",
    color=0xff0000,
    description=f'{member.name}に招待を送信できませんでした'
  )
  if not member.bot:
    try:
      inviteLink = f'https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}'
      linkButton = discord.ui.Button(label="参加する", style=discord.ButtonStyle.primary, url=inviteLink)
      linkView = discord.ui.View()
      linkView.add_item(linkButton)
      await member.send(embed=ub_embed.invite(interaction.channel,anonymity),view=linkView)
      
      x = discord.Embed(
        title="招待成功",
        color=0x51ff2e,
        description=f'{member.name}に招待を送信しました'
       )
      
    except discord.errors.Forbidden:
      pass
  await interaction.response.send_message(embed=x,ephemeral=anonymity)


@tree.command(name="title", description="参加中の通話のタイトルを設定します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(goal="参加中の通話の内容や目的")
async def slash_title(interaction: discord.Interaction, goal: str):
  if interaction.user.voice is not None:
    if await CallPost(interaction.user.voice.channel).title(goal):
      await interaction.response.send_message(f'タイトルを`{goal}`に変更しました',ephemeral=True)
    else:
      await interaction.response.send_message("通話通知が見つかりませんでした",ephemeral=True)
  else:
    await interaction.response.send_message("あなたは通話チュウに見えません",ephemeral=True)


@tree.command(name="johto", description="ステージチャンネルのホストを譲渡します")
@discord.app_commands.guilds(PDW_SERVER_ID)
@discord.app_commands.describe(user='譲渡したいメンバー')
async def slash_johto(interaction: discord.Interaction, user:  discord.Member):
  giver=interaction.user
  receiver=user
  stageGiveRole = discord.utils.get(interaction.guild.roles,name='🔈エレキトリカル☆ストリーマー')
  #stageChannel = client.get_channel(STAGE_CHANNEL_ID)
  
  if stageGiveRole in giver.roles:
    if receiver and receiver.voice and receiver.voice.channel.type == discord.ChannelType.stage_voice:
      await receiver.add_roles(stageGiveRole)
      await giver.remove_roles(stageGiveRole)
      await interaction.response.send_message(f"{giver.mention} が {receiver.mention} へホストをジョウトしました")
      await ub.output_log(f"{giver.name} が {receiver.name}へホストをジョウトしました")
    else:
      await interaction.response.send_message(embed=ub_embed.error_502(),ephemeral=True)
      
  else:
    await interaction.response.send_message(embed=ub_embed.error_403(stageGiveRole.name),ephemeral=True)

@client.event
async def on_ready():#bot起動時
  global BQ_FILTERED_DF
  daily_bonus.start()
  await tree.sync(guild=discord.Object(id=DEV_SERVER_ID))
  
  try : #前回コマンドで終了していたなら
    reminders = pd.read_csv(MEMBERDATA_PATH)
    if not reminders.empty:
      global BQ_FILTER_DICT
      global BAKUSOKU_MODE
      
      channel = client.get_channel(int(reminders["channel_id"][0]))
      BAKUSOKU_MODE = reminders["bakusoku_mode"][0]
      BQ_FILTER_DICT = eval(reminders["BQ_FILTER_DICT"][0])
      
      if channel is not None:
        await ub.output_log(f"botは{channel.name}で目を覚ましました\n BAKUSOKU_MODE: {BAKUSOKU_MODE}\n BQ_FILTER_DICT: {BQ_FILTER_DICT}")
        await channel.send(f"```{client.user.name}は\n目を 覚ました!```")
    os.remove(MEMORY_PATH)
  except FileNotFoundError:
    pass
  
  BQ_FILTERED_DF = ub.ub.filter_dataframe(BQ_FILTER_DICT).fillna('なし')

  #時報の投稿済みチェック (5時以降の起動で)
  now = datetime.now(ZoneInfo("Asia/Tokyo"))
  if(now.hour >= 5):
    dairyChannel = client.get_channel(DAIRY_CHANNEL_ID)
    timeSignal=False
    async for message in dairyChannel.history(limit=3):
      if message.author == client.user and now.strftime("%Y/%m/%d") in message.content:
        timeSignal=True
        break
    
    if not timeSignal:
      await ub.output_log('本日の時報が取得されませんでした.時報の投稿を試みます')
      await daily_bonus(now.replace(hour=5, minute=0, second=0, microsecond=0))
  
  await ub.output_log("botが起動しました")


#新規メンバーが参加したときの処理
@client.event
async def on_member_join(member):
  if not member.bot:
    await member.add_roles(member.guild.get_role(UNKNOWN_ROLE_ID))
    if (helloCh := client.get_channel(HELLO_CHANNEL_ID)):
      url = f'{EX_SOURCE_LINK}sprites/Gen1/{random.randint(1, 151)}.png'

      authButton = discord.ui.Button(label="メンバー認証",style=discord.ButtonStyle.primary,custom_id="authButton")
      helloView = discord.ui.View()
      helloView.add_item(authButton)
      
      await helloCh.send(f"はじめまして! {member.mention}さん",embed=ub_embed.welcome(member.guild.name,url),view=helloView)
      await ub.output_log(f'サーバーにメンバーが参加しました: {member.name}')

#メッセージの送受信を観測したときの処理
@client.event
async def on_message(message):
  if message.author.bot: #メッセージ送信者がBotだった場合は無視する
    return
    
  global BAKUSOKU_MODE
  global BQ_FILTER_DICT
  global BQ_FILTERED_DF
  
  greetings = ['おはよ','こんにち','こんにち','こんばん','こんばん','やあ','やっほー','おっはー','おはこん','うぽつ','こんぱんわ','おやす','ねます','もーにん','あろーら!','good morning','hello','はろー','good evening','早上好','你好','にーはお','晩上好','bonjour','ぼんじゅー','bonsoir','Доброе утро','Здравствуйте','Добрый вечер','guten morgen','ぐーてんもる','hallo','guten abend'] #あいさつリスト
  pattern = '|'.join(map(re.escape, greetings))

  #メンションされたときに種族値クイズを出す
  #if message.content=="<@1076387439410675773>":
  #  await quiz("bq").post(message.channel)

  #334に反応
  if message.content=="334":
    altaria = datetime.now(ZoneInfo("Asia/Tokyo")).replace(hour=3, minute=34, second=0, microsecond=0)
    time = message.created_at.astimezone(ZoneInfo("Asia/Tokyo"))
    diff = (time-altaria).total_seconds()

    altariaEmbed=discord.Embed(description="チルタリスタイムに ピッタリ送信 できると すごい", color=0x70e2ff)
    altariaEmbed.set_thumbnail(url="https://www.pokencyclopedia.info/sprites/gen5/ani_black-white/ani_bw_334.gif")
    altariaEmbed.add_field(
      name="タイム",
      value=f"```{'cs' if int(diff)>0 else 'md'}\n{time.strftime('%H:%M:%S.%f')[:-3]} {'+' if diff>0 else '-'}{abs(diff)}s```", 
      inline=False
    )
    altariaEmbed.set_footer(text="No.24 チルタリスレポーター")
    await message.reply(embed=altariaEmbed)

  #リプライ(reference)に反応
  elif message.reference is not None:
    #リプライ先メッセージのキャッシュを取得
    message.reference.resolved = await message.channel.fetch_message(message.reference.message_id)

    #bot自身へのリプライに反応
    if (message.reference.resolved.author == client.user and message.reference.resolved.embeds):
      embedFooterText = message.reference.resolved.embeds[0].footer.text
      #リプライ先にembedが含まれるかつ未回答のクイズの投稿か
      if ("No.26 ポケモンクイズ" in embedFooterText  and not "(done)" in embedFooterText):
        await quiz(embedFooterText.split()[3]).try_response(message)
        
      else :
        await ub.output_log("botへのリプライは無視されました")

  elif message.content == "<:botan:1082971898293522482>":
    BAKUSOKU_MODE = not BAKUSOKU_MODE
    await ub.output_log("爆速モードが"+str(BAKUSOKU_MODE)+"になりました")
    await message.channel.send(f'連続出題が{"ON" if BAKUSOKU_MODE else "OFF"}になりました')
    
  elif message.content.startswith("/bqdata"):
    bqFilterWords = message.content.split()[1:]
    
    if bqFilterWords:
      removeWords = ['タイプ','特性', '出身地','初登場世代','進化段階','HP','こうげき','ぼうぎょ','とくこう','とくぼう','すばやさ','合計']
      
      if 'リセット' in bqFilterWords:
        BQ_FILTER_DICT={'進化段階':['最終進化','進化しない']}
        bqFilterWords.remove('リセット')
        
      if '種族値' in bqFilterWords:
        for key in ['HP', 'こうげき', 'ぼうぎょ', 'とくこう', 'とくぼう', 'すばやさ', '合計']:
          BQ_FILTER_DICT.pop(key, None)
        bqFilterWords.remove('種族値')
        
      for i in range(len(bqFilterWords)):
        if bqFilterWords[i] in removeWords: #絞り込みをリセット
            del BQ_FILTER_DICT[bqFilterWords[i]]
          
      bqFilterWords = [x for x in bqFilterWords if x not in removeWords]

      #インデックスの要素が更新されていない項目はそのまま
      BQ_FILTER_DICT.update(ub.make_filter_dict(bqFilterWords))
      BQ_FILTERED_DF = ub.ub.filter_dataframe(BQ_FILTER_DICT).fillna('なし')
      response="種族値クイズの出題条件が変更されました"
      await ub.output_log("出題条件が更新されました")
      
    else:
      response="現在の種族値クイズの出題条件は以下の通りです"
      
    bqFilteredEmbed = discord.Embed(
      title='種族値クイズの出題条件',
      color=0x9013FE,
      description=f'該当ポケモン数: {BQ_FILTERED_DF.shape[0]}匹'
    )
    
    for i, key in enumerate(BQ_FILTER_DICT.keys()):
      values = "\n".join(BQ_FILTER_DICT[key])
      bqFilteredEmbed.add_field(name=key, value=values, inline=False)
      
    await ub.output_log("出題条件を表示します")
    await message.channel.send(response,embed=bqFilteredEmbed)
        
  elif message.content.startswith("/search"):
    FilterWords = message.content.split()[1:]
    searchedPokeDatas = ub.ub.filter_dataframe(ub.make_filter_dict(FilterWords)).fillna('なし')

    if len(searchedPokeDatas) > 0 : #検索結果が0件超過だった場合
      results = []
      for index, row in searchedPokeDatas.iterrows():
        results.append([row['おなまえ'],ub.bss_to_text(row)])

      searchEmbed = discord.Embed(title=f'条件に該当するポケモン: {len(results)}匹', color=0x00ff7f)
      
      names = [] 
      values = []
      resultCount = 0
      for result in results:
        if resultCount == 5:
          names[-1] += " など"
        elif resultCount < 5:
          names.append(result[0])
        resultCount += 1
        searchEmbed.add_field(name=result[0],value=result[1])
      searchResults=f'該当ポケモンは、{",".join(names)}です'
      
      await message.channel.send(searchResults,embed=searchEmbed)

    else: #検索結果が0件だった場合
      searchResults="該当するポケモンはいません" #検索結果コンテンツ
      await message.channel.send(searchResults)
      
  elif message.content=="<:migawari:1077833724361703444>":
    await ub.output_log("みがわりを検知しました")
    await message.channel.send(f"""```{message.author.name}の
身代わりが 現れた!```""")
  elif message.content=="<:think:1082748611252731924> <:idontsee:1082742344798965872>":
    await ub.output_log("thinkidontseeを検知しました")
    await message.add_reaction('😎')
  elif message.content=="<:item_tabenokoshi:1077833732502847568>":
    await ub.output_log("たべのこしを検知しました")
    await message.channel.send(f'''```{message.author.name}は
たべのこしで 少し 回復```''')
    
  elif re.search(pattern, jaconv.z2h(jaconv.kata2hira(message.content), kana=False, ascii=True, digit=False)): #こんばんワナイダー機能
    await ub.output_log("あいさつを検知しました")
    if any(word in jaconv.kata2hira(message.content) for word in ['おやすみ', 'ねます', 'ねる']):
      hello = "おやす"+random.choice(GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['おなまえ'].str.startswith('ミ')]['おなまえ'].tolist())
      await message.reply("`(つ∀-)"+hello+"ー`")
    else:
      h=datetime.now(ZoneInfo("Asia/Tokyo")).hour
      if h<6:
        hello = "いい夜です"+random.choice(GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['おなまえ'].str.startswith('ネ')]['おなまえ'].tolist())
      elif h<12:
        hello = "おはよ"+random.choice(GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['おなまえ'].str.startswith('ウ')]['おなまえ'].tolist())
      elif h<19:
        hello = "こんにち"+random.choice(GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['おなまえ'].str.startswith('ワ')]['おなまえ'].tolist())
      elif h<20:
        hello = "インテル入って"+random.choice(GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['おなまえ'].str.startswith('ル')]['おなまえ'].tolist())
      else:
        hello = "こんばん"+random.choice(GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['おなまえ'].str.startswith('ワ')]['おなまえ'].tolist())
      await message.reply(f'`{hello}👋😄`')
    await ub.output_log("こんにちワニノコ/こんばんワナイダーを実行しました")


#参加したメンバー数を記録
@client.event
async def on_voice_state_update(member, before, after):
  time = datetime.now(ZoneInfo("Asia/Tokyo"))
    
  if os.path.exists(CALLDATA_PATH):
    call_df = pd.read_csv(CALLDATA_PATH, dtype={"累計参加メンバー": str}).set_index("チャンネルID")
  else:
    call_df = pd.DataFrame(columns=["チャンネルID", "メッセージID", "通話開始", "タイトル", "名前読み上げ", "累計参加メンバー"]).set_index("チャンネルID")
        
  if after.channel:
    if member.bot:
      return
    #ボイスチャンネルにメンバーが入室
    callch=after.channel
    if after.channel.type == discord.ChannelType.voice:
      await ub.output_log(f'ボイスチャンネル参加\n {callch.name}: {member.name}')
      if len(after.channel.members) == 1: #入室時ひとりなら
        if before.channel and len(before.channel.members) == 1:
          return
        await asyncio.sleep(5) #5秒後に通話開始処理
        if len(callch.members)>0:
          member=callch.members[0]
          await CallPost(callch).start(member,time)
          
          if not member.voice or not member.voice.channel == callch: #参加したメンバーがいなくなっていたら
            await ub.output_log("参加したメンバーが退出しています")
            return
        else:
          await ub.output_log(f'通話は開始されませんでした\n {callch.name}: {member.name}')
          return
      else:
        if not callch.id in call_df.index:
          await asyncio.sleep(5)
          call_df = pd.read_csv(CALLDATA_PATH, dtype={"累計参加メンバー": str}).set_index("チャンネルID") #更新する
          
        if callch.id in call_df.index and str(member.id) not in call_df.loc[callch.id, "累計参加メンバー"].split(' '):
          call_df.loc[callch.id, "累計参加メンバー"] += f' {member.id}'
          call_df.to_csv(CALLDATA_PATH)

      """
      if callch.id in call_df.index and call_df.loc[callch.id, '名前読み上げ']:
          joinMemberMessage=f"{member.name}さんが参加"
      await callch.send(joinMemberMessage,embed=discord.Embed(title=f"{member.name}さんが 参加しました",color=0xff8e8e).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
      await ub.output_log(f"ボイスチャンネル参加\n {callch.name}: {member.name}")
      """
    #ステージチャンネルにメンバーが入室
    if after.channel.type == discord.ChannelType.stage_voice:
      stageGiveRole = discord.utils.get(member.guild.roles,name='🔈エレキトリカル☆ストリーマー')
      if len(after.channel.members) == 1:
        if stageGiveRole:
          await member.add_roles(stageGiveRole)
          await ub.output_log(f'{member.name}がステージのホストになりました')
        else:
          await ub.output_log("ホストロールが存在しませんでした")
      else:
        if not callch.id in call_df.index:
          call_df = pd.read_csv(CALLDATA_PATH, dtype={"累計参加メンバー": str}).set_index("チャンネルID") #更新する
        if callch.id in call_df.index and not member.id in call_df.loc[callch.id, "累計参加メンバー"].split(' '):
          call_df.loc[callch.id, "累計参加メンバー"] += f" {member.id}"
          call_df.to_csv(CALLDATA_PATH, index=False)
  
  if before.channel:
    #ボイスチャンネルからメンバーが退室
    if before.channel.type == discord.ChannelType.voice:
      await ub.output_log(f'ボイスチャンネル退出\n {before.channel.name}: {member.name}')

      kinouoff="""
      if before.channel.id in call_df.index:
        quitMemberMessage=""
        if call_df.loc[before.channel.id,'名前読み上げ']:
          quitMemberMessage=f"{member.name}さんが退出"
        await before.channel.send(quitMemberMessage,embed=discord.Embed(title=f"{member.name}さんが 退出しました",color=0x8e8eff).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
      else:
        await before.channel.send(embed=discord.Embed(title=f"{member.name}さんが 退出しました",color=0x8e8eff).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
      """  
      if len(before.channel.members) == 0: #ボイスチャンネルに人がいなくなったら
        await CallPost(before.channel).stop(time)
    #ステージチャンネルからメンバーが退室
    if before.channel.type == discord.ChannelType.stage_voice:
      speakers = before.channel.speakers
      
      if (stageGiveRole := discord.utils.get(member.guild.roles,name='🔈エレキトリカル☆ストリーマー')) in member.roles:
        await member.remove_roles(stageGiveRole)
        if len(speakers)==0:
          for listener in before.channel.listeners:
            await listener.move_to(None)
          if (stageInstance := client.get_stage_instance(before.channel.id)) is not None:
            await stageInstance.delete()
          await ub.output_log("ステージが終了しました")
        else:
          nextSpeaker=random.choice(speakers)
          await nextSpeaker.add_roles(stageGiveRole)
          #await before.channel.send(f"{nextSpeaker.mention}がステージのホストになりました")
          await ub.output_log(f'{member.name}が抜けたことで{nextSpeaker.name}がステージのホストになりました')


@client.event
async def on_stage_instance_create(stage_instance):
  await CallPost(stage_instance.channel).start(stage_instance.channel.members[0])


@client.event
async def on_stage_instance_delete(stage_instance):
  await CallPost(stage_instance.channel).stop()


@client.event
async def on_stage_instance_update(before, after):
  if before.topic == after.topic:
    await CallPost(after.channel).title(after.topic)


#全てのインタラクションを取得
@client.event
async def on_interaction(interaction:discord.Interaction):
  if "custom_id" in interaction.data and interaction.data["custom_id"] == "authModal":
    await ub.output_log("学籍番号を処理します")
    studentId = interaction.data['components'][0]['components'][0]['value']
    
    if (studentId := studentId.upper()).startswith(('S', 'A', 'C', 'J', 'D')) and re.match(r'^[A-Z0-9]+$', studentId) and len(studentId) == 7:  
      member = interaction.user
      role = interaction.guild.get_role(UNKNOWN_ROLE_ID)
      favePokeName = interaction.data['components'][1]['components'][0]['value']
      response = "登録を修正したい場合はもう一度ボタンを押してください"

      if role in member.roles: #ロールを持っていれば削除
        await member.remove_roles(role)
        response += "\nサーバーが利用可能になりました"
        await ub.output_log(f'学籍番号が登録されました\n {member.name}: {studentId}') 
      else:
        await ub.output_log(f'登録の修正を受け付けました\n {member.name}: {studentId}') 
      response += "\n`※このメッセージはあなたにしか表示されていません`"
      
      thanksEmbed=discord.Embed(
        title="登録ありがとうございました",
        color=0x2eafff,
        description=response
      )
      thanksEmbed.add_field(name="登録した学籍番号", value=studentId)
      thanksEmbed.add_field(name="好きなポケモン", value=favePokeName if not favePokeName=="" else "登録なし")

      if not favePokeName == "":
        if (favePokedata := ub.fetch_pokemon(favePokeName))is not None:
          favePokeName = favePokedata.iloc[0]['おなまえ']

      times = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")
      authData = {'登録日時':[times], 'ユーザーID': [str(member.id)], 'ユーザー名': [member.name],'学籍番号': [studentId],'好きなポケモン':[favePokeName]}
      df = pd.DataFrame(authData)
      df.to_csv('save/studentid.csv', mode='a', index=False, header=not os.path.exists('save/studentid.csv'))
        
      content = "照合に失敗しました ?\n※メンバーリストにまだ学籍番号のデータがない可能性があります"
      if os.path.exists(MEMBERDATA_PATH):
        member_df = pd.read_csv(MEMBERDATA_PATH).set_index("学籍番号")
        if studentId in member_df.index:
          memberData = pd.DataFrame({
            'ユーザーID': [member.id],
            'ユーザー名':[member.name],
            '好きなポケモン': [favePokeName]
          }, index=[studentId]).iloc[0]
          member_df.loc[studentId] = memberData
          member_df['ユーザーID'] = member_df['ユーザーID'].dropna().replace([np.inf, -np.inf], np.nan).dropna().astype(int)
          
          member_df.to_csv(MEMBERDATA_PATH, index=True, float_format="%.0f")
          content = "照合に成功しました"
          await ub.output_log(f'サークルメンバー照合ができました\n {studentId}: {member.name}')
        else:
          await ub.output_log(f'サークルメンバー照合ができませんでした\n {studentId}: {member.name}')
      
      await interaction.response.send_message(content, embed=thanksEmbed, ephemeral=True)

    else: #学籍番号が送信されなかった場合の処理
      await ub.output_log(f'学籍番号として認識されませんでした: {studentId}')
      await interaction.response.send_message(embed=ub_embed.error_401(studentId), ephemeral=True)
    
  elif "component_type" in interaction.data and interaction.data["component_type"] == 2:
    await ub.output_log(f'buttonが押されました\n {interaction.user.name}: {interaction.data["custom_id"]}')
    await on_button_click(interaction)


async def on_button_click(interaction:discord.Interaction):
    custom_id = interaction.data["custom_id"] #custom_id(インタラクションの識別子)を取り出す
  
    if custom_id == "authButton": #メンバー認証ボタン モーダルを送信する
      await ub.output_log("学籍番号取得を実行します")
      authModal = discord.ui.Modal(
        title="メンバー認証",
        timeout=None,
        custom_id="authModal"
      )
      authInput = discord.ui.TextInput(
        label="学籍番号",
        placeholder="J111111",
        min_length=7,
        max_length=7,
        custom_id="studentIdInput"
      )
      authModal.add_item(authInput)
      favePokeInput = discord.ui.TextInput(
        label="好きなポケモン(任意)",
        placeholder="ヤブクロン",
        required=False,
        custom_id="favePokeInput"
      )
      authModal.add_item(favePokeInput)
      await interaction.response.send_modal(authModal)
      
    elif custom_id.startswith("lotoIdButton"): #IDくじボタン
      await ub.output_log("IDくじを実行します")
      #カスタムIDは,"lotoIdButton:00000:0000/00/00"という形式
      lotoId = custom_id.split(":")[1]
      birth = custom_id.split(":")[2]
      now = datetime.now(ZoneInfo("Asia/Tokyo"))
      today = now.date()
      if(now.hour < 5):
        today = today - timedelta(days=1)
      
      if ub.report(interaction.user.id,"クジびきけん",0) == 0:
        await interaction.response.send_message("くじが ひけるのは 1日1回 まで なんだロ……",ephemeral=True)
      elif not birth   == str(today):
        await interaction.response.send_message(f'それは 今日のIDくじ じゃないロ{EXCLAMATION_ICON}',ephemeral=True)
      else:
        userId = str(interaction.user.id)[-6:].zfill(5) #ID下6ケタを取得
        
        count = 0
        for i in range(1, 6):
          if userId[-i] == lotoId[-i]:
            count += 1
          else:
            break
        prize = PRIZE_DICT[count][0]
        value = PRIZE_DICT[count][1]
        text = PRIZE_DICT[count][2]
        place = PRIZE_DICT[count][3]
        
        lotoEmbed = discord.Embed(
          title=text,
          color=0xff99c2,
          description=f'{place}の 商品 **{prize}**をプレゼントだロ{BANGBANG_ICON}\nそれじゃあ またの 挑戦を お待ちしてるロ~~{EXCLAMATION_ICON}'
        )
        lotoEmbed.set_thumbnail(url=f'{EX_SOURCE_LINK}icon/{prize}.png')
        lotoEmbed.add_field(
          name=f'{interaction.user.name}は {prize}を 手に入れた!',
          value=f'売却価格: {value}えん\nおこづかい: {ub.report(interaction.user.id,"おこづかい",value)}えん',
          inline=False
        )
        lotoEmbed.set_author(name=f'あなたのID: {userId}')
        lotoEmbed.set_footer(text="No.15 IDくじ")
        
        ub.report(interaction.user.id,"クジびきけん",-1) #クジの回数を減らす
        await interaction.response.send_message(embed=lotoEmbed,ephemeral=True)
        
    elif custom_id.startswith("acq"):
      await quiz("acq").try_response(interaction)
      
#毎日5時に実行する処理
@tasks.loop(seconds=60)
async def daily_bonus(now : datetime = None):
  if now is None:
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
  if now.hour == 5 and now.minute == 0:
    await ub.output_log("ジョブを実行します")
    todayId = str(random.randint(0, 99999)).zfill(5)
    
    dairyIdEmbed=discord.Embed(
      title="IDくじセンター 抽選コーナー",
      color=0xff297e,
      description=f'くじのナンバーと ユーザーIDが みごと あってると ステキな 景品を もらえちゃうんだロ{BANGBANG_ICON}'
    )
    dairyIdEmbed.add_field(
      name=f'{BALL_ICON}今日のナンバー',
      value=f'**{todayId}**',
      inline=False
    )
    dairyIdEmbed.set_footer(text="No.15 IDくじ")
    
    day = datetime.now(ZoneInfo("Asia/Tokyo"))
    embeds = [await ub.show_calendar(day),await ub.show_senryu(True),dairyIdEmbed]

    lotoButton = discord.ui.Button(label="くじをひく",style=discord.ButtonStyle.primary,custom_id=f'lotoIdButton:{todayId}:{datetime.now(ZoneInfo("Asia/Tokyo")).date()}')
    dairyView = discord.ui.View()
    dairyView.add_item(lotoButton)

    lotoReset = pd.read_csv(ub.report_PATH)
    lotoReset["クジびきけん"] = 1
    lotoReset.to_csv(ub.report_PATH, index=False)
    
    dairyChannel = client.get_channel(DAIRY_CHANNEL_ID)
    
    await dairyChannel.send(f'日付が変わりました。 {day.strftime("%Y/%m/%d")} ({WEAK_DICT[day.weekday()]})',embeds=embeds, view=dairyView)

class CallPost: #await CallPost(*,discord.channel,channelID).start(member,time) /.stop(member,time) /.title(title)
  def __init__(self,channel,sendChannelId: int = None):
    self.channel = channel
    if sendChannelId is None:
      if self.channel.permissions_for(channel.guild.default_role).view_channel: #プライベートなら送信先を変更:
        sendChannelId = CALLSTATUS_CHANNEL_ID
      else:
        sendChannelId = DEBUG_CHANNEL_ID
    self.sendChannel = client.get_channel(sendChannelId)
    self.message = None

    if self.channel.type == discord.ChannelType.stage_voice:
      self.chType="放送"
    else:
      self.chType="通話"
    
    self.path=CALLDATA_PATH
    if os.path.exists(self.path):
      self.call_df = pd.read_csv(self.path, dtype={"累計参加メンバー": str}).set_index("チャンネルID")
    else:
      self.call_df = pd.DataFrame(columns=["チャンネルID", "メッセージID", "通話開始", "タイトル", "名前読み上げ", "累計参加メンバー"]).set_index("チャンネルID")
            
  async def start(self,member,time: datetime = datetime.now(ZoneInfo("Asia/Tokyo"))):
    defaultTitle = "設定無し"
    if self.chType == "放送":
      embedColor = 0xa7ff8f
    else:
      embedColor = 0xff8e8e
    
    startEmbed = discord.Embed(title=f'{self.chType}開始', color=embedColor)
    startEmbed.set_author(name=f'{member.name} さん', icon_url=member.display_avatar.url)
    startEmbed.set_thumbnail(url="https://www.pokencyclopedia.info/sprites/gen5/ani_black-white/ani_bw_441.gif")
    startEmbed.add_field(name="タイトル", value=f'`{defaultTitle}`', inline=False)
    startEmbed.add_field(name="チャンネル", value=self.channel.mention, inline=False)
    startEmbed.add_field(name=f'{self.chType}開始', value=f'```{time.strftime("%Y/%m/%d")}\n{time.strftime("%H:%M:%S")}```', inline=True)
    
    startMessage = await self.sendChannel.send(embed=startEmbed)

    newBusyData = pd.DataFrame({
      "メッセージID": [startMessage.id],
      "通話開始":[time.strftime("%Y/%m/%d %H:%M:%S")],
      "タイトル": [defaultTitle],
      "名前読み上げ": [False],
      "累計参加メンバー": [member.id]
    }, index=[self.channel.id]).iloc[0]
    
    if self.channel.id not in self.call_df.index:
      self.call_df = self.call_df.append(newBusyData)
    else:
      self.call_df.loc[self.channel.id] = newBusyData
    self.call_df.to_csv(self.path)

    await self.channel.send(embed=discord.Embed(title="通話開始", description="`/title` 通話目的を変更できます\n`/invite` メンバーを招待できます",color=embedColor).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
    await ub.output_log(f'{self.chType}が開始されました\n {self.channel.name}: {member.name}')

  async def title(self,newTitle:str):
    if not await self.__load():
      return False
      
    self.message.embeds[0].set_field_at(0, name='タイトル', value=f'`{newTitle}`')

    oldTitle = self.call_df.loc[self.channel.id, 'タイトル']
    self.call_df.loc[self.channel.id, 'タイトル'] = newTitle
    self.call_df.to_csv(self.path)
  
    await self.message.edit(embed=self.message.embeds[0])
    await ub.output_log(f'通話タイトルを更新しました\n{self.channel.name}: [{oldTitle} > {newTitle}]')
    return True

  async def stop(self,time: datetime = datetime.now(ZoneInfo("Asia/Tokyo"))):
    if not await self.__load():
      return False
    if self.chType=="放送":
      embedColor=0x8ffff8
    else:
      embedColor=0x8e8eff
    stopEmbed=self.message.embeds[0]
    
    diff = (time.replace(tzinfo=None)-pd.to_datetime(self.call_df.loc[self.channel.id,"通話開始"], format='%Y/%m/%d %H:%M:%S')).total_seconds()
    hours = int(diff // 3600)
    minutes = int((diff % 3600) // 60)
    seconds = int(diff % 60)
    
    stopEmbed.title = f'{self.chType}終了・{f"{hours}時間 " if hours>0 else " "}{minutes}分'
    stopEmbed.color = embedColor
    stopEmbed.set_thumbnail(url="https://www.pokencyclopedia.info/sprites/gen5/ani-b_black-white/a-b_bw_441.gif")
    stopEmbed.set_footer(text=f'Total Visitors: {len(self.call_df.loc[self.channel.id,"累計参加メンバー"].split(" "))}')
    stopEmbed.add_field(name=f'{self.chType}終了', value=f'```{time.strftime("%Y/%m/%d")}\n{time.strftime("%H:%M:%S")}```', inline=True)
    
    await self.message.edit(embed=stopEmbed)

    self.call_df.drop(self.channel.id).to_csv(self.path, index=True)

    visitor_ids = self.call_df.loc[self.channel.id, "累計参加メンバー"].split(' ')
    visitor_names = []
    for visitor_id in visitor_ids:
      visitor = await client.fetch_user(visitor_id)
      visitor_names.append(visitor.name)
    visitors = ' '.join(visitor_names)
    
    if os.path.exists(CALLLOG_PATH):
      log_df = pd.read_csv(CALLLOG_PATH)
    else:  
      log_df = pd.DataFrame(columns=['通話開始','通話終了','通話時間','タイトル','チャンネル','参加メンバー'])
      
    newLog = pd.DataFrame({
      '通話開始': self.call_df.loc[self.channel.id, '通話開始'],
      '通話終了': time.strftime("%Y/%m/%d %H:%M:%S"),
      '通話時間': f'{hours:02}:{minutes:02}:{seconds:02}' ,
      'タイトル': self.call_df.loc[self.channel.id,'タイトル'],
      'チャンネル': self.channel.name,'参加メンバー': visitors
    }, index=[0])
    #log_df = pd.concat([log_df.iloc[:1], newLog, log_df.iloc[1:]], ignore_index=True)
    log_df = pd.concat([newLog, log_df], ignore_index=True)
    log_df.to_csv(CALLLOG_PATH, mode='w', header=True, index=False)
    
    embed=discord.Embed(
      title=f'{self.chType}終了',
      color=embedColor
    )
    embed.set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S"))
    
    await self.channel.send(embed=embed)
    await ub.output_log(f'{self.chType}が終了しました\n {self.channel.name}: {visitor_names[-1]}')
    return True
      
  async def __load(self):
    if self.channel.id in self.call_df.index:
      try:
        self.message = await self.sendChannel.fetch_message(self.call_df.loc[self.channel.id, 'メッセージID'])
      except discord.NotFound:
        await ub.output_log("ERROR: 指定のメッセージが見つかりませんでした")
        return False
    else:
      await ub.output_log("ERROR: 指定チャンネルの通話記録がありません")
      return False
    return True

class GuidelinePost:
  def __init__(self,sendChannelId: int=GUIDELINE_CHANNEL_ID,changerId=DEVELOPER_USER_ID):
    self.channel = client.get_channel(sendChannelId)
    self.changer = client.get_user(changerId)
    self.guidelineColor = 0xF8E71C
    self.today = datetime.now(ZoneInfo("Asia/Tokyo"))

  async def post(self,num=None):
    if num is not None:
      content, embed, file = self.__guidelines(num)
      await self.channel.send(content=content, embed=embed, file=file)
    else:
      messages=[]
      for num in range(9):
        content, embed, file = self.__guidelines(num)
        messages.append(await self.channel.send(content=content, embed=embed, file=file))
  
      addLinkEmbed=messages[0].embeds[0]
      for i, message in enumerate(messages[1:]):
        addLinkEmbed.description = addLinkEmbed.description.replace(f"@{i+1}", message.jump_url)
      addLinkEmbed.set_image(url=messages[0].embeds[0].image.url)
      await messages[0].edit(embed=addLinkEmbed,attachments=[])
      
      addLinkEmbed=messages[8].embeds[0]
      addLinkEmbed.add_field(name="更新日・ユーザー", value=f'{self.today.strftime("%Y/%m/%d")} {self.changer.mention}', inline=False)
      addLinkEmbed.add_field(name="[**目次にもどる**]", value=messages[0].jump_url, inline=False)
      await messages[8].edit(embed=addLinkEmbed)
      await ub.output_log(f'ガイドラインの投稿に成功しました\n {self.channel.name}: {self.changer.name}')
      
  async def update(self,num=None):
    async for message in self.channel.history(limit=None):
      if message.author == client.user and message.embeds:
        for embed in message.embeds:
            if embed.footer and embed.footer.text == f"guidelines: {num}":
              newContent, newEmbed, newFile = self.__guidelines(num)
              await message.edit(content=newContent, embed=newEmbed)
              await ub.output_log(f'{num}番目のガイドラインが更新されました')
              return
              
  async def delete(self,num=None):
      async for message in self.channel.history(limit=None):
        if message.author == client.user and message.embeds:
          for embed in message.embeds:
            if num is not None:
              if embed.footer and embed.footer.text == f'guideline: {num}':
                await message.delete()
                return
            else:
              if embed.footer and 'guideline' in embed.footer.text:
                await message.delete()

  async def __guidelines(self,num: int):
    content=None
    fileName=None
    
    match num:
      case 0:
        content=f"""
        
**ポーガクインドリームワールド** (以下、本サーバーとする)** のガイドライン**

※保護者の方と一緒にお読みください
※ガイドラインをみるときは、部屋をあかるくして、近づきすぎないようにしてみてくださいね

最終更新日：{self.today.strftime("%Y/%m/%d")}
        """
        title="目次 (リンクを踏むとジャンプできます)"
        description="""
1. 本サーバーについて
@1
2. 注意事項
@2
3. 各チャンネルの説明(1)
@3
4. 各チャンネルの説明(2)
@4
5. 導入済botの説明
@5
6. 関連リンク
@6
7. おまけ
@7
8. ガイドライン更新日
@8
        """
        fileName="HELLO.gif"
        
      case 1:
        title=f"{num}. 本サーバーについて"
        description="""
本サーバーは、工学院大学に存在する学生団体のひとつである**工学院ポケモンだいすきクラブ**(以下、当団体とする)のメンバーが、オンライン上で交流するため2023年春に設立されたサーバーです。ポケモンに関する話題であれば、どんなことでも投稿が可能です。
当団体に所属する、または所属していたメンバーのみが参加することができます。
このサーバーを利用するためには、学籍番号を登録する必要があります。サーバーへの初回参加時に、未認証を示す`なぞのポケモン`ロールが付与されます。
このロールを所持している間は、チャンネルの多くを使用することができません。所属と照合するためですので、ご協力お願いします。
        """
        fileName="pogakuinlogo.png"
        
      case 2:
        title=f"{num}. 注意事項"
        description=f"""
{BALL_ICON} ポケモン愛を欠いた言動はしないでください。
{BALL_ICON} 工学院大学の学則や日本の法律に違反することや、それを想起させる言動はしないでください。
{BALL_ICON} 本人の許可なく個人の特定につながる情報を送信しないでください。
{BALL_ICON} 当団体のメンバー歴がない人物を参加させないでください。
{BALL_ICON} 当サーバーはネタバレ(spoiler)の制限が存在しないため、意図せずネタバレを見てしまうおそれがあります。
{BALL_ICON} リーク情報/バグ利用/マイコン自動化/乱数調整/解析/改造/その他NSFWといったデリケートな話題は控えるか、チャンネル開設要望を出してください。
{BALL_ICON} じぶんがされたらいやなことをひとにしないでね
{BALL_ICON} キノココにキノコのほうしを覚えさせずに進化させないでください。

問題行為が改善されないメンバーは、~~行動制限やキックなどの処罰の対象となる~~ ||めのまえがまっくら||になることがあります。

**注意事項 (ポケモンの方向け)**
{BALL_ICON} ピカピーカ！ピカ…ピカーチュ！

**ルールを 守って 安全 運転**{BANGBANG_ICON}
        """
        fileName="ITSFUN.gif"

      case 3:
        title=f"{num}. 各チャンネルの説明(1)"
        description=f"""
話題が混ざることなく話しやすいように、チャンネルが分類されています。以下に各チャンネルの利用目的を示しますので、できるだけ用途に合った投稿を心がけてください。**まちがえてもペナルティはありません**
チャンネル名をクリック・タップすると、そのチャンネルに移動できます。
新たなチャンネルがほしいといったご要望は<#1067408772298969099>に投稿してください。


<#{HELLO_CHANNEL_ID}>
 本サーバーに新たなメンバーが参加したとき自動で投稿されます。学籍番号の認証もここで行うことができます。
 
{BALL_ICON}__**たいせつなもの**__
 おしらせやガイドライン、サーバーに必要なチャンネルが含まれるカテゴリです。リアクションは可能ですが、権限を持たない方は書き込みができないように設定されています。

<#1069197424578535475>
 本サーバーや、当団体についてのおしらせが投稿されます。
<#{GUIDELINE_CHANNEL_ID}>
 このチャンネルです。本サーバーのガイドラインが投稿されます。
<#1075239927324872814>
 当団体の公式SNSなどの投稿が共有されます。IFTTTのWebhook機能を使用しており、反映には最大1時間ほどかかります。
<#1068903858790731807>
 ProBotのリアクションロールの機能を用いて、メンバーがロールをもらうことができます。ロールの選択は必須ではありませんが、興味があれば利用してみてください。

{BALL_ICON}__**全般**__
 作品を問わず投稿ができるチャンネルが含まれるカテゴリです。

<#1067421333727744022>
 ポケモン、当団体、本サーバーに関するすべての雑談を行うためのテキストチャンネルです。
**投稿チャンネルに困ったらココ!**
<#1069197769434218558>
 ポケモン、当団体、本サーバーに関するすべての質問を行うためのフォーラムチャンネルです。雑談用の各チャンネルで質問を行っても問題ありませんが、テキストチャンネルと違い質問が流れづらく、アーカイブも閲覧しやすくなっています。
<#1067425152440209529>
 本サーバーのメンバーに情報を共有するためのテキストチャンネルです。たとえば、配信ポケモン情報や、カードの拡張パックの販売状況などといったおとくな情報を周知するため、**是非どしどし投稿してください**。
<#1067408772298969099>
 当団体や本サーバーに対する要望や期待を投稿するためのテキストチャンネルです。まじめな内容だけではなく、夢物語のような内容であっても、**ジラーチにねがいごとをするように**投稿してください。叶えられるとは限りませんが、たくさんのねがいごとをお待ちしております。
<#1094729583187722300>
 BOTの機能を試したり、BOTと遊んだりするためのチャンネルです。ここでないと使用してはいけないということはありません。

{BALL_ICON}__**ポケットモンスターシリーズ**__
 ポケモン本編作品についての投稿ができるチャンネルが含まれるカテゴリです。'ポケットモンスター'と作品名に入るゲームと、Pokémon LEGENDS アルセウスが本編作品に該当します。

<#1067424609537896449>
 ポケモン本編作品についての雑談を行うためのテキストチャンネルです。
<#1067406944110923776>
 ポケモン本編作品における対戦や交換募集を行うためのテキストチャンネルです。
<#1069197299521175702>
 ほしいポケモンや、勝てないレイドなどがあるときに、助けを求めるためのチャンネルです。いわゆる「乞食行為」専用チャンネルです。対価を提示する必要はありませんが、提示しても問題はありません。自ら募集者に対価を要求するような行為は避けてください。また、誰かの助けになるような投稿をする「布施行為」もすることができます。
以下のように、内容を示せるタグが用意されています。
**タグの使用例**```md
#🤲ポケモンほしい
 ほしいポケモンがある
#🤲アイテムほしい
 ほしいアイテムがある
#🤕勝てない
 クリアできないイベント等がある
#🎁配布
 配れるものがある
#📸図鑑埋め
 図鑑埋めをしたい・手伝える
#💪力になりたい
 だれかの助けになりたいきもち
#🏃コイン500枚
 とにかく困っている
```
{BALL_ICON}__**ポケモンカード**__
 ポケモンカードゲームシリーズについて投稿できるチャンネルが含まれるカテゴリです。PTCGOやPTCGL、ポケモンカードゲームGBの話題についてもこちらを使用してください。

<#1067405650025521152>
 スタンダードレギュレーションについての雑談を行うためのテキストチャンネルです。
<#1067406022215487608>
 その他のレギュレーションについての雑談を行うためのテキストチャンネルです。
当団体ではスタンダード以外のプレイ人口が少ないため、ひとまとめにされています。需要があればレギュレーションの個別チャンネルが新設されます。
<#1072155780758904902>
 ポケカのデッキレシピを共有したり、意見交換をしたりするためのチャンネルです。レギュレーションを問わず投稿可能です。
絞り込みのために、デッキレシピのレギュレーションを指定するタグを付けることを推奨します。
**タグの使用例**
```md
#スタンダード
 最新のカードを中心に使用範囲を定めている、スタンダードで使用するデッキ。
#エクストラ
 「BW」シリーズから最新のカードまで使用可能な、エクストラで使用するデッキ。
#殿堂
 「DP」シリーズから最新のカードまで使用可能な、殿堂で使用するデッキ。
#レガシー
「LEGEND」「BW」シリーズのカードのみが使用可能な、レガシーで使用するデッキ。
#レギュレーション外
「PCG」シリーズ以前のカードを使用するデッキなど、どのレギュレーションにも属さないデッキ。
```<#1067811669822160987>
 ポケカの対戦募集をすることができるチャンネルです。
下記は例であり、投稿形式に決まりはありません。
```md
#目的
 新しく組んだデッキの試運転のため など
#レギュレーション
 スタンダード/エクストラ など
#場所・時間
 オンライン上/サークル活動中/その他 など
#備考
 プロキシ(代用)の有無/プロキシ🆗or🆖 など
```
        """

      case 4:
        title=f"{num}. 各チャンネルの説明(2)"
        description=f"""
{BALL_ICON}__**その他の作品**__
 ポケモン本編作品やポケモンカードゲームシリーズを除く、ポケモン関連作品について広く投稿できるチャンネルが含まれるチャンネルです。
```md
#ポケモン関連作品の例
 ポケモンダンジョン、ポケモンスクランブル、ポケモンレンジャーなどの外伝ゲーム作品
 ポケモンだいすきクラブのミニゲームなどのwebゲーム作品
 メザスタ、ポッ拳などのアーケード作品
 ポケGO、ポケマス、ポケまぜ、UNITEなどのモバイル作品
 アニポケ、ポケモン映画などの映像作品
 スマブラ、バッジとれ〜るセンター、太鼓の達人、マリオメーカーなどのゲスト参加作品
```その他、ポケモンに関連するものであればオフィシャル・ファンメイドを問わず投稿可能です。
作品の需要に合わせ、都度チャンネルを新設したり撤廃したりすることがあります。ここだけの話、このカテゴリは||ポケモンにこじつけられればなんでも使用できる||ということになっています。

<#1073254628096999466>
 ポケモン関連作品についての雑談を行うためのテキストチャンネルです。
<#1068316105036288030>
 ポケモン関連作品のマルチプレイの募集投稿ができるテキストチャンネルです。対象作品が多いチャンネルなので、募集する時は作品名を明記してください。
<#1068314180597321740>
 ポケモンMOD(Pixelmon)を導入したMinecraftについての雑談を行うためのテキストチャンネルです。
<#1068903384846958593>
 アニメ「ポケットモンスター」や、劇場版ポケットモンスターについての雑談を行うためのテキストチャンネルです。

{BALL_ICON}__**ボイスチャンネル**__
 ボイスチャットや画面共有をすることができるボイスチャンネルが含まれるカテゴリです。
 各ボイスチャンネルではそれぞれ個別のテキストチャットが併設されています。通話内容に関係する投稿や、ミュートのメンバーが発言するために使用してください。
 また、本サーバーには読み上げbotが導入されているので、チャットを使用するミュートのメンバーがいるときは使用してみてください。詳しくはガイドラインの4. 導入済botの説明を参照してください。
 
<#{CALLSTATUS_CHANNEL_ID}>
 本サーバーのボイスチャンネルにメンバーが参加した際と、すべてのメンバーが抜けたときに、botによっておしらせが投稿されるテキストチャンネルです。このチャンネルの通知をオンにすると、通話開始に気づきやすくなります。
誤参加でおしらせされることを防ぐため、最初に参加したメンバーが5秒以上ボイスチャンネルに接続したときに投稿されます。
ボイスチャンネルに参加した状態で`/title`を使用すると,通話のタイトルを編集することができます。

<#1067125844465688640>
<#1067410255706861638>
<#1067410433197228164>
<#1067448136232079390>
<#1067410539476701204>
<#1067415740568846426>
<#1067416316178341908>
<#1067417029352632320>
<#1067416391008923658>
 どのような用途にも使用できる一般的なボイスチャンネルです。チャンネルの名称は通話内容を制限するものではないので、好きなチャンネルを使用してください。
<#{STAGE_CHANNEL_ID}>
 スピーカーのメンバーを制限してボイスチャットができるステージチャンネルです。使用制限はなく、誰でもステージを開始することができます。
ボイスチャンネルと比べ、スピーカーのメンバーを制限でき、トピック(タイトルのようなもの)が指定でき、アクティブなときはチャンネル上部にピン留めされるため、企画やイベントなどに向いています。
最初に参加したメンバーがホストになり、botにホストロール🔈エレキトリカル☆ストリーマーを付与されます。ホスト以外のメンバーはスピーカーリクエストがホストに承認されるとスピーカーになることができます。
※本サーバーで管理者権限を持っているメンバーは、常にホスト権限を持っています

{BALL_ICON}__**その他**__
 ポケモンのおたのしみを共有することができるチャンネルが含まれるカテゴリです。

<#1067409796417998848>
 ポケモン、登場人物、BGMなどのポケモン関連のだいすきなことについて投稿できるテキストチャンネルです。
**キミのだいすきを見せてくれ!**
<#1067423830156525569>
 日常生活で見かけた**ポケモンのアレ**とか**ポケモンのアレっぽいナニカ**を投稿できるテキストチャンネルです。
意外と身の回りには**ポケモンのアレっぽいナニカ**が溢れています。
<#1067423743699341342>
 ポケモン関連のイラストを投稿できるテキストチャンネルです。
基本的に自分の作品を投稿する想定ですが、**作者の許可があれば**そうでない作品も投稿可能です。
<#1069197621316562974>
 ポケモン関連のクイズを投稿できるフォーラムチャンネルです。クイズ難易度や正解者の有無を示すタグが用意されています。
**タグの使用例**
```md
#🟢かんたん
Q. BWの水御三家であるミジュマルが持っている貝はなんと呼ばれているか答えよ
A. ホタチ
#🟡ふつう
Q. 初代で全く同じなきごえのポケモンの組をすべて答えよ(2組)
A. リザードンとサイホーン ニョロモとメタモン
#🟠むずかしい
Q. RSとFRLGの徘徊ポケモンが取ることのできる個体値の範囲と、その理由を答えよ
A. 0~31-0~7-0-0-0-0
 個体値はメモリ上ではSDCBAHの順で各5bit(2進数5桁=10進数では0~31を表せる)、合計30bitで表現されている。通常、ポケモンとエンカウントした時に30bitを読み込むところを、徘徊ポケモンとエンカウントした時には下位8bitしか読み込まないバグがあるため。
#🔴むげん
Q. HGSSでけいびいんから預けられるオニスズメ「ひきゃく」が持っているグラスメールの内容を答えよ
A. てがみ ありがとう!  ぼうけん たのしかったねー  ズバット だけは いやだった…… ユウジ
#⭕あたり です!
 クイズの正解者がいた場合、このタグをつけて投稿をクローズすることを推奨します。
#❌あたり ならず…
 もうクイズの正解者が出ないと思ったら、答えを公開してください。その後、このタグをつけて投稿をクローズすることを推奨します。
```※難易度別クイズの例は執筆者の主観です。出題者が思う難易度タグを選択してください。
<#1067411959097589840>
 ポケモン関連のステキなサイト、自作ファイルの共有リンクなどの外部リンクを投稿できるチャンネルです。
<#1069520616849416202>
 ポケモン関連のステキな動画を投稿できるチャンネルです。共有方法は、動画へのリンク・動画ファイルどちらでも大丈夫です。
ゲームのクリップ、公式動画はもちろん、ファンメイドの映像作品や、ポケモンのゲーム実況、自分の制作した動画でも問題ありません。
<#1082026583109419018>
 BOTによって毎日5時に時報が投稿されるチャンネルです。IDくじを引くことができます。

{BALL_ICON}__**過去ログ**__
 諸般の理由で廃止になったチャンネルや、イベント使用後不要になったチャンネルが格納されるカテゴリです。書き込み不可に設定されており、不要なログは削除されることがあります。
        """
      case 5:
        title=f'{num}. 導入済botの説明'
        description=f"""
本サーバーにはさまざまな便利機能を持つbotが導入されています。以下では、現在導入済みのbotについての説明を記載しています。
botの追加や削除・変更点などがあれば更新していきます。

{BALL_ICON}<@!1076387439410675773>
 当団体メンバーによって、本サーバーのために開発されているbotです。意図しない動作をすることもしばしばあり、開発途中の段階です。不具合などは管理者へ問い合わせるか、後述のコマンドを使用して報告をくださると嬉しいです。
 また、本サーバー用のBotの制作に興味がある・作りたいものがある方も管理者へお声がけください。言語はPythonで、開発環境はReplitです。
現在の管理者: <@!{DEVELOPER_USER_ID}>
> **コマンド例**
```md
#botのコマンドを確認する
/help
#不具合・要望などのフィードバックを報告
/wish
#ポケモンの図鑑情報を表示する
/dex ポケモン名
*入力効率化のため、先頭の特定の文字を変換する機能があります。*
変換辞書 'A': 'アローラ', 'G': 'ガラル', 'H': 'ヒスイ', 'P': 'パルデア', 'M': 'メガ', '霊獣': 'れいじゅう', '化身': 'けしん', '古来': 'コライ', '未来': 'ミライ'
*正式名称以外の入力にも一部対応*
例: 水ロトム,ミトム>ロトム(ウォッシュロトム) ガルド,シールドフォルム>ギルガルド(シールドフォルム)
#種族値クイズを出題 (全ポケモンから最終進化を出題)
/bq または botにメンション
#前回の種族値クイズに解答 (正誤判定)
クイズの投稿にポケモン名を返信
```
{BALL_ICON}<@!282859044593598464>
 サーバー管理用多機能Botです。リアクションロールを付与したり、ガイドラインを投稿したり、テキスト・ボイスチャットでよく発言するメンバーに称号ロールを付与したりします。管理者のみが公式リンクのダッシュボードから操作が可能です。
> **コマンド例**
```md
#自分のけいけんちを表示
/rank
#けいけんちランキングを表示
/top
```
> **公式リンク**
https://probot.io/ja


> **読み上げbot**
```xl
 以下の4つのbotは、ボイスチャンネルで、テキストチャンネルに投稿されたメッセージを読み上げるbotです。ミュートの人も会話に参加しやすくなります。
 使用する場合は'読み上げ開始コマンドを使用したいボイスチャンネルのチャットに投稿'してください。
 読み上げ終了のコマンドもありますが、ボイスチャンネルからメンバーがいなくなると自動で終了します。

 1つのbotにつき1つのボイスチャンネルにしか参加できません。そのため、読み上げbotを4つ導入していますが、どれを使っても問題ありません。
※'他のボイスチャンネルに参加中のbotを読み上げ開始/終了してしまうと、そのチャンネルから抜けてしまいます!'
```
> ボイスチャンネルのチャットへの入り方
```md
#PC
 右クリック>チャットを開く または ボイスチャンネルにカーソルを合わせ💬をクリック
#スマホ
 ボイスチャンネルをホールドし、チャットを開くをタップ または ボイスチャットに参加後、右上の💬をタップ
```

{BALL_ICON}<@!533698325203910668>
 読み上げbotです。先頭に`;`(セミコロン)がついているメッセージは読み上げられません。
> **コマンド例**
```md
#読み上げ開始
!sh s
#読み上げ終了
!sh e
#辞書に単語を登録
!sh aw 単語 よみ
#辞書の単語を削除
!sh dw 単語
#投稿者名読み上げ設定
!sh read_name onまたはoff_
#読み上げ文字数を変更
!sh read_limit 読み上げ文字数_
#複数行読み上げ設定
!sh read_multi onまたはoff_
*その他にも詳細設定があります。詳しくは公式リンクをご確認ください*
```
> **公式リンク**
https://cod-sushi.com/shovel-how-to-use/


{BALL_ICON}<@!917633605684056085>
 読み上げbotです。VOICEVOXのずんだもんが読み上げ音声として使用されています。
> **コマンド例**
```md
#読み上げ開始/終了
/vc
#読み上げ設定変更
/set voice pitch speed

- voice デフォルト: 3
数値で読み上げ音声を変更できます。
以下はバリエーションずんだもんの値の一覧です。
1  ずんだもん(あまあま)
3  デフォルトずんだもん
5  ずんだもん(セクシー)
7  ずんだもん(ツンツン)
22 ずんだもん(ささやき)
38 ずんだもん(ヒソヒソ)
*実は、ずんだもんの他にも多くのVOICEVOXやCOEIROINKの音声が用意されています。詳しくは公式リンクを確認してください*

- pitch デフォルト: 0
読み上げ音声の高さです。-10から10の間で設定することが推奨されています。

- speed デフォルト: 100
読み上げ音声の速さです。
```
> **公式リンク**
https://lenlino.com/?page_id=2171

{BALL_ICON}**その他**
・PogakuinTwitter
 当団体のTwitterアカウントの投稿を<#1075239927324872814>に共有するWebhookです。
・PogakuinInstagram (工事中)
 当団体のInstagramアカウントの投稿を<#1075239927324872814>に共有するWebhookです。
・ポケモンKidsTV
 ポケモン公式のおたのしみ動画の最新投稿を<#1069520616849416202>に共有するWebhookです。
        """

      case 6:
        title="6. 関連リンク"
        description="""
> __**工学院ポケモンだいすきクラブ 公式Twitterアカウント**__
工学院ポケモンだいすきクラブ (@Pogakuin) / Twitter
Link: https://twitter.com/Pogakuin
 サークル活動について発信するTwitterアカウントです。サークルに関するお問い合わせやサークル参加申請も受け付けています。サークル長を中心に複数のメンバーが管理しているようです。

> __**工学院ポケモンだいすきクラブ 公式Instagramアカウント**__
工学院ポケモンだいすきクラブ - Instagram
Link: https://www.instagram.com/pogakuin_568
 サークル活動について発信するInstagramアカウントです。サークルに関するお問い合わせやサークル参加申請も受け付けています。サークル長が管理しています。

**Googleのサービスは、Googleアカウント'pogakuin@gmail.com'によって管理されています。**
> __**工学院ポケモンだいすきクラブ GoogleForms**__
工学院ポケモンだいすきクラブ フォーム
Link: https://forms.gle/Lm1FZjhqy946f3nw9
 SNSアカウントを使用しなくてもお問い合わせやサークル参加申請が可能なフォームです。現在、副サークル長が管理しています。

> __**工学院ポケモンだいすきクラブ 共有ドライブ**__
Link: https://drive.google.com/drive/folders/1jDPVEuU5-Z5W0HF4YeXkDW3Wpvuzqkxe?usp=sharing
 Googleアカウントがあれば誰でもファイルの共有・閲覧が可能です。さまざまなファイルを共有する際に使用してください。

> __**工学院ポケモンだいすきクラブ 共有カレンダー**__
Link: https://calendar.google.com/calendar/u/3?cid=cG9nYWt1aW5AZ21haWwuY29t
 サークルや大学、ポケモンに関する日程を書き込めるカレンダーです。今後、サークルで使用する教室の予約状況を共有していく予定です。

> __**SHAiR**__
工学院大学学生団体ポータルサイト｜SHAiR
Link: http://www.ns.kogakuin.ac.jp/~wws5023/index.html
 工学院大学の学生団体についての公開情報がまとめられているポータルサイトです。学生団体工学院大学学生自治会常任委員会SHAiR局が管理しています。

> __**サークル活動規約**__
Link: http://www.ns.kogakuin.ac.jp/~wws5023/download/download/circlekatudoukiyaku2022.pdf
 工学院大学学生自治会常任委員会サークル局が出している、サークルの活動規約です。サークル活動に関しての問い合わせ先も乗っています。

> __**SHAiR Blog**__
SHAiR Blog TOP - 工学院大学学生団体ポータルサイト
Link: http://www.ns.kogakuin.ac.jp/~wws5023/blog/2023/index.html
 学生団体が活動について投稿し発信できるブログです。
          """
        
      case 7:
        title=f'{num}. おまけ'
        description="""
> __**Discord用語など**__
操作方法はスマートフォン版に準じます。PC版の方は調べてください。
(タップ >左クリック 長押し > 右クリック で代替できるかも)


> テキストチャンネル
 テキストチャンネルは、テキストメッセージ、画像、リンクを投稿することができます。 
```md
#絵文字を使用する
 テキストボックスの右にある☻をタップ
 またはメッセージに :絵文字ID: を含める
#メンション(メッセージを通知する)
 メッセージに @ユーザー名 または @ロール名 を含める
#チャンネルへのリンク
 メッセージに #チャンネル名 を含める
#リアクション
 メッセージを長押しし、絵文字を選択する
```
> 投稿の文章を装飾する (Markdown)
斜体(英数字): `*テキスト*`
 *Hello world*
太字: `**テキスト**`
 **Hello world**
 斜体(英数字)&太字: `***テキスト***`
 ***Hello world***
下線: `__テキスト__` 
 __Hello world__
取り消し線: `~~テキスト~~`
 ~~Hello world~~
Spoiler(クリックで表示): `||テキスト||`
 ||Hello world||
黒背景:  `` `テキスト` ``
 `Hello world`
引用: `> テキスト`
>   Hello world
記号のエスケープ: `\*\*テキスト\*\*`
  \*\*Hello world\*\*
インラインコードブロック: `` `テキスト` ``
 `Hello world`
コードブロック:  
\`\`\` 
テキスト
 \`\`\`
```
 Hello world
```

> ボイスチャンネル
 ボイスチャンネルは、音声で会話をしたり、画面やカメラに映したものを配信したりすることができます。
```md
#ミュートの切り替え
 参加した状態で、🎙のアイコンをタップ
#画面共有
 参加した状態で、iPhoneはコントロールセンターの画面収録からDiscordを選択
 Androidは📱→のアイコンをタップ
#Youtube動画を同時視聴 (WatchTogather PC版のみ)
 参加した状態で、🚀のアイコンをクリックし、WatchTogatherを選択する
 再生したい動画を検索して再生する
```
> フォーラムチャンネル
 フォーラムチャンネルは、特定の話題についてスレッドを作成できるチャンネルです。タグ付けをすることで、投稿の絞り込みができるようになります。
```md
#タグ付け
 投稿する際の編集画面にある🏷のアイコンをタップ または、自分の投稿を長押しし、「タグを編集」を選択する
#投稿をクローズ
 自分の投稿を長押しし、「投稿をクローズ」を選択
```
> ステージチャンネル
 ステージチャンネルは、音声イベントを開くことができるチャンネルです。スピーカーとオーディエンスの区別があり、スピーカーメンバーを限定することができます。ステージのトピックを用い放送にタイトルをつけることができます。Twitterスペースのような仕様です。
ステージが始まると、チャンネルリストのトップに固定されます。
基本操作はボイスチャンネルに準じます。
```md
#スピーカーリクエスト
 参加した状態で、✋のアイコンをタップ
```
> チャンネルの通知設定
`チャンネル一覧から設定したいチャンネルを長押しし、「チャンネルを通知オフ/オン」または「通知設定」を選択する`
 
> オンライン公開設定
`自分のアイコンをタップし、設定画面から「ステータスを設定」を選択する`

> アカウント連携
 DiscordにSteam、Twitter、Instagramといった外部アカウントを連携し、他のメンバーがプロフィールから確認できるようにすることができます。
 
> ロール
 ロールはメンバーの属性を表します。色が設定されたロールを所持するメンバーの名前には色が付きます。(上の方のロールが優先されます)
チャンピオンからサーバフリークまでのロールと一部のBotが、サーバーの設定を変更することができる管理者権限を持っています。
```md
#本団体で役職を持っているメンバー
 サークル長: チャンピオン #明るい赤
 その他: ポケモンはかせ など #明るい青
#サーバー管理者のメンバー
 サーバフリーク #明るい緑
#Botのメンバー
 UB SLEEPY など #暗い緑
#新規参加ロール
 なぞのポケモン #黒
#なんらかの権限を持っているメンバー
 🔈エレキトリカル☆ストリーマー,🪵ジオヅムのたみ など #明るい黄
#サーバーをブースト(課金)しているメンバー
 🔥マグマブースター #明るい橙
#称号を持っているメンバー
 🎀バトルチャンプリボン など #明るい紫
#その他のロール
 りかけいのおとこ など #色なし
```その他のロールは<#1068903858790731807>で自由にもらうことができます。当団体のイベントの優勝者にチャンプリボンロールを付与することも考えています。ロールは随時、追加・削除されることがあります。
        """
      case 8:
        title= f'{num}. ガイドライン更新日'
        description=f"""
ガイドラインの更新日を降順で記載します。
ガイドラインについての質問・要望は<#1069197769434218558>、<#1067408772298969099>、工学院ポケモンだいすきクラブ フォーム,編集メンバーのDMなどをご利用ください。
        """
        
      case x:
        await ub.output_log(f"{x}は有効なガイドラインナンバーではありません")
        return None,None,None
        
    embed = discord.Embed(
      title=title,
      color=self.guidelineColor,
      description=description
    )
    embed.set_footer(text=f'guidelines: {num}')
    
    if fileName == None:
      file = None
    else:
      file = discord.File(f'images/{fileName}', filename=fileName)
      embed.set_image(url=f'attachment://{fileName}')
    
    return content,embed,file

class quiz():
  def __init__(self,quizName):
    self.quizName = quizName

  async def post(self,sendChannel):
    await ub.output_log(f'{self.quizName}: クイズを出題します')
    
    quizContent = None
    quizFile = None
    quizEmbed = discord.Embed(
      title="",
      color=0x9013FE,
      description=""
    )
    quizEmbed.set_footer(text=f'No.26 ポケモンクイズ - {self.quizName}')
    quizView = None
    #必要な要素をクイズごとに編集
    
    if self.quizName == "bq":
      qDatas = self.__shotgun(BQ_FILTER_DICT)
      if qDatas is not None:
        baseStats = [qDatas['HP'],qDatas['こうげき'],qDatas['ぼうぎょ'],qDatas['とくこう'],qDatas['とくぼう'],qDatas['すばやさ']]
        
        quizEmbed.title = "種族値クイズ"
        quizEmbed.description = "こたえ: ???" #正答後: こたえ: [ポケモン名](複数いる場合),[ポケモン名]
        quizFile = discord.File(ub.generate_graph(baseStats), filename="image.png")
        quizEmbed.set_image(url="attachment://image.png") #種族値クイズ図形の添付
        quizEmbed.set_thumbnail(url=self.__imageLink()) #正解までDecamark(?)を表示
        quizContent = ub.bss_to_text(qDatas)
        
      else:
        await sendChannel.send("現在の出題条件に合うポケモンがいません")

    elif self.quizName == "acq":
      qDatas = self.__shotgun({'進化段階':['最終進化','進化しない']})
      quizEmbed.title = "ACクイズ"
      quizEmbed.description = f"{qDatas['おなまえ']} はこうげきととくこうどちらが高い?"
      quizEmbed.set_thumbnail(url=self.__imageLink(qDatas['おなまえ']))
      
      quizView = discord.ui.View()
      quizView.add_item(discord.ui.Button(label="こうげき",style=discord.ButtonStyle.primary,custom_id='acq_こうげき'))
      quizView.add_item(discord.ui.Button(label="とくこう",style=discord.ButtonStyle.primary,custom_id='acq_とくこう'))
      quizView.add_item(discord.ui.Button(label="同値",style=discord.ButtonStyle.secondary,custom_id='acq_同値'))

    elif self.quizName == "etojq":
      while 1:
        qDatas = self.__shotgun({'進化段階':['最終進化','進化しない']})
        if pd.notna(qDatas['英語名']):
          break
          
      quizEmbed.title = "英和翻訳クイズ"
      quizEmbed.description = f"{qDatas['英語名']} -> [?]"
      
    elif self.quizName == "jtoeq":
      while 1:
        qDatas = self.__shotgun({'進化段階':['最終進化','進化しない']})
        if pd.notna(qDatas['英語名']):
          break
          
      quizEmbed.title = "和英翻訳クイズ"
      quizEmbed.description = f"{qDatas['おなまえ']} -> [?]"
      quizEmbed.set_thumbnail(url=self.__imageLink(qDatas['おなまえ']))

    elif self.quizName == "ctojq":
      while 1:
        qDatas = self.__shotgun({'進化段階':['最終進化','進化しない']})
        if pd.notna(qDatas['中国語繁体']):
          break
          
      quizEmbed.title = "中日翻訳クイズ"
      quizEmbed.description = f"{qDatas['中国語繁体']} -> [?]"
      
    else:
      await ub.output_log(f'不明なクイズ識別子(post): {self.quizName}')
      #ここでエラーを送信
      return
      
    self.qm = await sendChannel.send(content=quizContent,file=quizFile,embed=quizEmbed,view=quizView)
  
  async def try_response(self,response):
    if QUIZ_PROCESSING_FLAG == 1:
      await ub.output_log(f'{self.quizName}: 応答処理実行中につき処理を中断')
      return
      
    #インスタンスがメッセージ/インタラクションかどうかで代入データを変える
    if isinstance(response, discord.Message):
      self.rm = response
      self.qm = response.reference.resolved
      self.ansText = ub.format_text(response.content)
      self.opener = self.rm.author
      
    elif isinstance(response, discord.Interaction):
      self.rm = response
      self.qm = response.message
      self.ansText = self.rm.data["custom_id"].split("_")[1]
      self.opener = self.rm.user
      #customIDが"acq_こうげき/とくこう/同値"のようなかたちを想定

    self.quizEmbed = self.qm.embeds[0]
      
    gives = ["ギブ","ギブアップ","降参","敗北"]
    hints = []
    
    #クイズごとにヒント項目を作成する
    if self.quizName in ["bq","ctojq"]:
      hints = ['ヒント','タイプ','特性','トクセイ','地方','チホウ','分類','ブンルイ', '作品', 'サクヒン']
    elif self.quizName == "etojq":
      hints = ['ヒント','タイプ','特性','トクセイ','地方','チホウ','分類','ブンルイ', '作品', 'サクヒン','語源','ゴゲン']
    elif self.quizName == "jtoeq":
      hints = ['文字数','モジスウ','頭文字','カシラモジ','イニシャル']

    #ここでクイズの問題文を取得する
    if self.quizName == "bq":
      self.examText = self.qm.content.split(" ")[0]
    elif self.quizName == "acq":
      self.examText = self.quizEmbed.description.split(" ")[0]
    elif self.quizName in ["etojq","jtoeq","ctojq"]:
      self.examText = re.findall(r"^(.+)\s->", self.quizEmbed.description)[0]
      
    #ここでクイズの回答を取得する
    self.ansList,self.ansZero = self.__answers()
    
    if self.ansText in gives:
      await self.__giveup()
    elif self.ansText in hints:
      await self.__hint()
    else:
      await self.__judge()
    
    
  async def __giveup(self):
    await ub.output_log(f'{self.quizName}: ギブアップを実行')
    if isinstance(self.rm, discord.Message):
      await self.rm.add_reaction('😅')
      await self.rm.reply(f'答えは{self.ansList[0]}でした')
    await self.__disclose(False)

  async def __judge(self):
    await ub.output_log(f'{self.quizName}: 正誤判定を実行')
    
    fixAns = self.ansText
    if self.quizName in ["bq","etojq","ctojq"]:
      if (repPokeData := ub.fetch_pokemon(self.ansText)) is not None:
        fixAns = repPokeData.iloc[0]["おなまえ"]
    elif self.quizName == "jtoeq":
      fixAns = jaconv.z2h(jaconv.kata2alphabet(fixAns), kana=False, ascii=False, digit=True).lower()
      self.ansList[0] = self.ansList[0].lower()

    if fixAns in self.ansList:
      judge = "正答"
      if isinstance(self.rm, discord.Message):
        await self.rm.add_reaction('⭕')
      await self.__disclose(True,fixAns)
    else:
      judge = "誤答"
      if isinstance(self.rm, discord.Message):
        reaction = '❌'
      if isinstance(self.rm, discord.Interaction): #ボタンで回答しているときはギブアップになる
        await self.__disclose(False)
      
    if self.quizName in ["bq","etojq","ctojq"] and repPokeData is None: #例外処理
      judge = None
      if isinstance(self.rm, discord.Message):
        reaction = '❓'
        await self.rm.reply(f'{self.ansText} は図鑑に登録されていません')
    elif judge == "誤答" and self.quizName == "jtoeq" and len((poke := GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['英語名'].str.lower() == fixAns])) > 0:
      if isinstance(self.rm, discord.Message):
        await self.rm.reply(f"{fixAns} は {poke.iloc[0]['おなまえ']} の英名です")

    if judge != "正答" and isinstance(self.rm, discord.Message):
      await self.rm.add_reaction(reaction)
      
    if judge is not None:
      ub.report(self.opener.id, f'{self.quizName}{judge}', 1) #回答記録のレポート
      
    self.__log(judge,self.ansList[0])
    
  async def __hint(self):
    await ub.output_log(f"{self.quizName}: ヒント表示を実行")
    
    if self.quizName in ["bq","etojq","ctojq"]:
      if self.ansText == 'ヒント': #まだ出ていないヒントからランダムにヒントを出す
        hintIndexs = ['タイプ1','タイプ2','特性1','特性2','隠れ特性', '出身地', '分類','初登場作品'] #ヒントになるインデックスの一覧
        alreadyHints = [field.name for field in self.quizEmbed.fields] #既出のヒントの一覧
        stillHints = [x for x in hintIndexs if x not in alreadyHints] #未出のヒントの一覧
        if len(stillHints)>0:
          while True:
            hintIndex = random.choice(stillHints)
            if pd.notna(hintIndex):
              break
        else:
          hintIndex = random.choice(alreadyHints)
          
      elif self.ansText in ['タイプ']:
        if not any(field.name == "タイプ1" for field in self.quizEmbed.fields):
          hintIndex = 'タイプ1'
        elif not any(field.name == "タイプ2" for field in self.quizEmbed.fields):
          hintIndex = 'タイプ2'
        else:
          await self.rm.reply(f"タイプは{str(self.ansZero['タイプ1'])}/{str(self.ansZero['タイプ2'])}です")
          return
          
      elif self.ansText in ['特性','トクセイ']:
        if not any(field.name == "特性1" for field in self.quizEmbed.fields):
          hintIndex = "特性1"
        elif not any(field.name == "特性2" for field in self.quizEmbed.fields):
          hintIndex = "特性2"
        elif not any(field.name == "隠れ特性" for field in self.quizEmbed.fields):
          hintIndex = "隠れ特性"
        else:
          await self.rm.reply(f"とくせいは{str(self.ansZero['特性1'])}/{str(self.ansZero['特性1'])}/{str(self.ansZero['隠れ特性'])}です")
          return
          
      elif self.ansText in ['地方','チホウ']:
        hintIndex = "出身地"
      elif self.ansText in ['分類','ブンルイ']:
        hintIndex = "分類"
      elif self.ansText in ['作品','サクヒン']:
        hintIndex = "初登場作品"
      elif self.ansText in  ['語源','ゴゲン']:
        hintIndex = "英語名由来"
      hintValue = self.ansZero[hintIndex]
      
    elif self.quizName == "jtoeq":
      if self.ansText in ['文字数','モジスウ']:
        hintIndex = "文字数"
        hintValue = len(self.ansZero['英語名'])
      elif self.ansText in  ['頭文字','カシラモジ','イニシャル']:
        hintIndex = "イニシャル"
        hintValue = self.ansZero['英語名'][0:1]
      
    else:
      await ub.output_log(f"不明なクイズ識別子(hint): {self.quizName}")
      return

    #初出のヒントならEmbedにフィールドを追加
    if not any(field.name == hintIndex for field in self.quizEmbed.fields):
      self.quizEmbed.add_field(name=hintIndex,value=hintValue)
      await self.qm.edit(embed=self.quizEmbed,attachments=[])
      
    await self.rm.reply(f'{hintIndex}は{hintValue}です')
      
  async def __disclose(self,tf,answered=None):
    global QUIZ_PROCESSING_FLAG
    await ub.output_log(f'{self.quizName}: 回答開示を実行')
    QUIZ_PROCESSING_FLAG = 1 #回答開示処理を始める
      
    if tf: #正解者がいる場合
      clearTime = self.rm.created_at - self.qm.created_at #所要時間を求める
      days, seconds = divmod(clearTime.total_seconds(), 86400) #所要時間を分解
      hours, seconds = divmod(seconds, 3600)
      minutes, seconds = divmod(seconds, 60)
      clearTimes = f"{int(seconds)}秒"
      if days >= 1:
          clearTimes = f"{int(days)}日 {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
      elif hours >= 1:
          clearTimes = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
      elif minutes >= 1:
          clearTimes = f"{int(minutes):02}:{int(seconds):02}"
      authorText = f'{self.opener.name} さんが正解! [TIME {clearTimes}]'
      link = self.__imageLink(answered)
      
    else: #正解者が存在せず,ギブアップされた場合
      authorText = f'{self.opener.name} さんがギブアップ'
      link = self.__imageLink(self.ansList[0]) #self.ansZero['おなまえ']でもいいかも
      
    self.quizEmbed.set_author(name = authorText) #回答者の情報を表示
    
    if self.quizName == "bq":
      self.quizEmbed.description = f'こたえ: {",".join(self.ansList)}'
    elif self.quizName == "acq":
      self.quizEmbed.description = f'{ub.bss_to_text(self.ansZero)}\n'
      if self.ansList[0] == "同値":
        self.quizEmbed.description += f'{self.examText}はこうげきととくこうが同じ'
      else:
        self.quizEmbed.description += f'{self.examText}は{self.ansList[0]}の方が高い'
        
    elif self.quizName in ["etojq","jtoeq","ctojq"]:
      self.quizEmbed.description = f'{self.examText} -> [{self.ansList[0]}]'
      if self.quizName == "etojq":
        self.quizEmbed.description += f'\n{str(self.ansZero["英語名由来"])}'
      elif self.quizName == "ctojq":
        self.quizEmbed.description += f'\n拼音: {ub.pinyin_to_text(self.examText)}'

    if not "Decamark" in link:
      self.quizEmbed.set_thumbnail(url=link) #サムネイルを変更する
    self.quizEmbed.set_footer(text=self.quizEmbed.footer.text + "(done)")
    
    if isinstance(self.rm, discord.Message):
      await self.qm.edit(embed=self.quizEmbed,attachments=[])
      
    elif isinstance(self.rm, discord.Interaction):
      fixView = discord.ui.View()
      fixView.from_message(self.qm)
      for child in fixView.children:
        child.disabled = True
      await self.rm.response.edit_message(embed=self.quizEmbed,attachments=[],view=fixView)

    QUIZ_PROCESSING_FLAG = 0 #回答開示処理を終わる
    await self.__continue() #連続出題を試みる
  
  async def __continue(self):
    if BAKUSOKU_MODE:
      await ub.output_log(f"{self.quizName}: 連続出題を実行")
      loadingEmbed = discord.Embed(
        title="**BAKUSOKU MODE ON**",
        color=0x0000FF,
        description="次のクイズを生成チュウ"
      )
      loadMessage = await self.qm.channel.send(embed=loadingEmbed)
      await quiz(self.quizName).post(self.qm.channel)
      await loadMessage.delete()

  async def __answers(self):
    await ub.output_log(f'{self.quizName}: 正答リスト生成を実行')
    answers = []
    aData = None
    
    if self.quizName == "bq":
      H, A, B, C, D, S = map(int, self.examText.split("-"))
      aDatas = GLOBAL_BRELOOM_DF.loc[
          (GLOBAL_BRELOOM_DF['HP'] == H) &
          (GLOBAL_BRELOOM_DF['こうげき'] == A) &
          (GLOBAL_BRELOOM_DF['ぼうぎょ'] == B) &
          (GLOBAL_BRELOOM_DF['とくこう'] == C) &
          (GLOBAL_BRELOOM_DF['とくぼう'] == D) &
          (GLOBAL_BRELOOM_DF['すばやさ'] == S)
      ]
      aData = aDatas.iloc[0]
      for index, row in aDatas.iterrows():
        answer = row['おなまえ']
        answers.append(answer)
        
    elif self.quizName == "acq":
      aDatas = ub.fetch_pokemon(self.examText)
      aData = aDatas.iloc[0]
      if (aData['こうげき'] == aData['とくこう']).all():
        answers.append("同値")
      elif (aData['こうげき'] > aData['とくこう']).all():
        answers.append("こうげき")
      else:
        answers.append("とくこう")
        
    elif self.quizName == "etojq":
      aDatas = GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['英語名'] == self.examText]
      aData = aDatas.iloc[0]
      answers.append(str(aData['おなまえ']))
    
    elif self.quizName == "jtoeq":
      aDatas = ub.fetch_pokemon(self.examText)
      aData = aDatas.iloc[0]
      answers.append(str(aData['英語名']))
 
    elif self.quizName == "ctojq":
      aDatas = GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF['中国語繁体'] == self.examText]
      aData = aDatas.iloc[0]
      answers.append(str(aData['おなまえ']))
    
    else:
      await ub.output_log(f'不明なクイズ識別子(answers): {self.quizName}')
      return
      
    return answers,aData #正答のリストと0番目の正答をタプルで返す

  async def __shotgun(self,filter_dict):
    await ub.output_log(f'{self.quizName}: ランダム選択を実行')
    filteredPokeData = ub.ub.filter_dataframe(filter_dict)#.fillna('なし')
    selectedPokeData = filteredPokeData.iloc[random.randint(0,filteredPokeData.shape[0] - 1)]
    if selectedPokeData is not None:
      return selectedPokeData
    else:
      await ub.output_log(f'{self.quizName}: ERROR 正常にランダム選択できませんでした')
      return None
      
  async def __imageLink(self,searchWord=None):
    await ub.output_log(f'{self.quizName}: 画像リンク生成を実行')
    link=f"{EX_SOURCE_LINK}Decamark.png" #デフォルトは(?)マーク
    if searchWord is not None:
      if self.quizName in ["bq","acq","etojq","jtoeq","ctojq"]:
        displayImage = ub.fetch_pokemon(searchWord)
        if displayImage is not None: #回答ポケモンが発見できた場合
          link=f"{EX_SOURCE_LINK}art/{displayImage.iloc[0]['ぜんこくずかんナンバー']}.png"
      else:
        await ub.output_log(f'不明なクイズ識別子(imageLink): {self.quizName}')
    return link
    
  async def __log(self,judge,exAns):
    logPath=f'log/{self.quizName}log.csv'
    await ub.output_log(f'{self.quizName}: log生成を実行\n {logPath}')
    
    if os.path.exists(logPath):
      log_df = pd.read_csv(logPath)
    else:  
      log_df = pd.DataFrame(columns=['正誤判定','内容','解答','入力認識可否'])
      
    nRow = pd.DataFrame({'正誤判定': judge, '内容': self.examText, '解答': self.ansText, '入力認識可否': judge is not None}, index=[0])
    log_df = pd.concat([nRow, log_df]).reset_index(drop=True)
    log_df.to_csv(logPath, mode='w', header=True, index=False)
  
  
#keep_alive()
# BOTの起動
load_dotenv()
client.run(os.environ.get('DISCORD_TOKEN'),reconnect=True)