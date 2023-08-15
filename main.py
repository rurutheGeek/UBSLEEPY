
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import discord
from discord import app_commands
from discord.ext import tasks

client = discord.Client(intents=discord.Intents.all(),activity=activity)

// ‚±‚±‚ÉƒR[ƒh‚ğ‘‚­

client.run(os.environ.get('DISCORD_TOKEN'))