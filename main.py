#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import discord
from discord import app_commands
from discord.ext import tasks

activity = discord.Activity(name='キノコのほうし', type=discord.ActivityType.playing) #アクティビティの設定
client = discord.Client(intents=discord.Intents.all(),activity=activity)
tree = app_commands.CommandTree(client)

#ここにコードを書く

client.run(os.environ.get('DISCORD_TOKEN'))