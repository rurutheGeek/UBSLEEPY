#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import re #正規表現用
import pprint
import asyncio
import pandas as pd #pandas 表形式のデータ処理用
import matplotlib.pyplot as plt #matplotlib
import numpy as np #numpy
import jaconv #jaconv ひらがなカタカナ,半角全角相互変換
#https://github.com/ikegami-yukino/jaconv/blob/master/README_JP.rst
import pypinyin #pypinyin ピンインに変換
#https://www.jianshu.com/p/f926353f3d01
import discord
#from discord import ButtonStyle, Interaction
from discord import app_commands
from discord.ext import tasks

activity = discord.Activity(name='キノコのほうし', type=discord.ActivityType.playing) #アクティビティの設定
client = discord.Client(intents=discord.Intents.all(),activity=activity)
tree = app_commands.CommandTree(client)

async def output_log(logStr): #ログプリント用関数
  dt = datetime.now(ZoneInfo("Asia/Tokyo"))
  logstr = f'[{dt.hour:02}:{dt.minute:02}:{dt.second:02}] {logStr}'
  
  #ログをコンソールに表示する
  print(logstr)
  
  #ログをbot用サーバーに投稿する
  channel = client.get_channel(1140787559325249717)
  await channel.send(logstr)
  
@client.event
async def on_ready():#bot起動時
 await output_log("botが起動しました")

client.run(os.environ.get('DISCORD_TOKEN'),reconnect=True)