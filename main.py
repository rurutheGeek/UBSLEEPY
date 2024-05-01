#!/usr/bin/python3
# -*- coding: utf-8 -*-
# main.py

# 標準ライブラリ
import os
#import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import re
import pprint
import json

# 外部ライブラリ
##https://discordpy.readthedocs.io/ja/latest/index.html
import discord
from discord.ext import tasks
import pandas as pd
import numpy as np
import jaconv  # type: ignore
from dotenv import load_dotenv  # type: ignore

# 分割されたモジュール
from bot_module.config import *
import bot_module.func as ub
import bot_module.embed as ub_embed
####################################################################################################

BQ_FILTERED_DF = GLOBAL_BRELOOM_DF.copy
BQ_FILTER_DICT = {"進化段階": ["最終進化", "進化しない"]}

tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():  # bot起動時
    global BQ_FILTERED_DF
    if DEBUG_MODE:
        ub.output_log('debugモードで起動します')
    if len(GUILD_IDS) == 0:
        ub.output_log("登録済のサーバーが0個です")
    else:
        syncGuildName = ""
        i = 0
        for guild_id in GUILD_IDS:
            syncGuildName += f"\n#{i} {client.get_guild(guild_id).name}"
            await tree.sync(guild=discord.Object(id=guild_id))
            i += 1
        ub.output_log(f"登録済のサーバーを{len(GUILD_IDS)}個読み込みました{syncGuildName}")

    BQ_FILTERED_DF = ub.filter_dataframe(BQ_FILTER_DICT).fillna("なし")

    ub.output_log("botが起動しました")
    if not post_logs.is_running():
        post_logs.start()

@tasks.loop(seconds=30)
async def post_logs():
    try:
        with open("log/system_log.txt", "r+", encoding="utf-8") as file:
            file.seek(0)
            logStrs = file.read()
            if logStrs:
                channel = client.get_channel(LOG_CHANNEL_ID)
                await channel.send(logStrs)
                file.truncate(0)
    except FileNotFoundError:
        pass


# スラッシュコマンド登録
@tree.command(
    name="import", description="このサーバーにギルドコマンドをインポートします"
)
async def slash_test(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        if interaction.guild.id in GUILD_IDS:
            await interaction.response.send_message(
                "このサーバーはすでに登録されています", ephemeral=True
            )
        else:
            GUILD_IDS.append(interaction.guild.id)
            # config.jsonに追加
            with open("config.json", "r") as file:
                config_dict = json.load(file)

            config_dict["DEVELOP_ID_DICT"]["GUILD_IDS"] = GUILD_IDS
            with open("config.json", "w") as file:
                json.dump(config_dict, file, indent=4)
                await tree.sync(guild=discord.Object(id={interaction.guild.id}))
                await interaction.response.send_message(
                    "このサーバーにギルドコマンドを登録しました", ephemeral=True
                )


@tree.command(name="notice", description="botのステータスメッセージを変更します")
@discord.app_commands.describe(message="ステータスメッセージ")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
async def slash_notice(
    interaction: discord.Interaction, message: str = "キノコのほうし"
):
    if interaction.user.guild_permissions.administrator:
        if message is not None:
            await client.change_presence(
                activity=discord.Activity(
                    name=message, type=discord.ActivityType.playing
                )
            )
        else:
            await client.change_presence(
                activity=discord.Activity(
                    name="キノコのほうし", type=discord.ActivityType.playing
                )
            )
        await interaction.response.send_message(
            f"アクティビティが **{message}** に変更されました", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"""```{client.user.name}は
{random.choice(["めいれいを むしした!", "なまけている!", "そっぽを むいた!", "いうことを きかない!", "しらんぷりした!"])}```"""
        )


@tree.command(name="q", description="現在の出題設定に基づいてクイズを出題します")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(
    quizname="クイズの種別 未記入で種族値クイズが指定されます"
)
@discord.app_commands.choices(
    quizname=[
        discord.app_commands.Choice(name=val, value=val)
        for val in list(QUIZNAME_DICT.keys())
    ]
)
async def slash_q(interaction: discord.Interaction, quizname: str = "種族値クイズ"):
    seiseiEmbed = discord.Embed(
        title="**妖精さん おしごとチュウ**",
        color=0xFFFFFF,  # デフォルトカラー
        description=f"{quizname}を生成しています",
    )
    await interaction.response.send_message(embed=seiseiEmbed, delete_after=1)
    await quiz(QUIZNAME_DICT[quizname]).post(interaction.channel)


@tree.command(name="quizrate", description="クイズの戦績を表示します")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(
    user="表示したいメンバー名",
    quizname="クイズの種別 未記入で種族値クイズが指定されます",
)
@discord.app_commands.choices(
    quizname=[
        discord.app_commands.Choice(name=val, value=val)
        for val in list(QUIZNAME_DICT.keys())
    ]
)
async def slash_quizrate(
    interaction: discord.Interaction,
    user: discord.Member = None,
    quizname: str = "種族値クイズ",
):
    if user is not None:
        showId = user.id
        showName = client.get_user(showId).name
    else:
        showId = interaction.user.id
        showName = interaction.user.name

    ub.output_log("戦績表示を実行します")
    w = ub.report(showId, f"{QUIZNAME_DICT[quizname]}正答", 0)
    l = ub.report(showId, f"{QUIZNAME_DICT[quizname]}誤答", 0)
    await interaction.response.send_message(
        f"""{showName}さんの{quizname}戦績
正答: {w}回 誤答: {l}回
正答率: {int(w/(w+l)*100) if not w+l==0 else 0}%"""
    )


@tree.command(name="bmode", description="クイズの連続出題モードを切り替えます")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(mode="連続出題モードのオンオフ 未記入でトグル切り替え")
@discord.app_commands.choices(
    mode=[
        discord.app_commands.Choice(name="ON", value="ON"),
        discord.app_commands.Choice(name="OFF", value="OFF"),
    ]
)
async def slash_bmode(interaction: discord.Interaction, mode: str = None):
    global BAKUSOKU_MODE
    if mode == "ON":
        BAKUSOKU_MODE = True
    elif mode == "OFF":
        BAKUSOKU_MODE = False
    else:
        BAKUSOKU_MODE = not BAKUSOKU_MODE
    ub.output_log("爆速モードが" + str(BAKUSOKU_MODE) + "になりました")
    await interaction.response.send_message(
        f"連続出題が{'ON' if BAKUSOKU_MODE else 'OFF'}になりました"
    )


# メッセージの送受信を観測したときの処理
@client.event
async def on_message(message):
    global BAKUSOKU_MODE
    global BQ_FILTER_DICT
    global BQ_FILTERED_DF
    if message.author.bot:  # メッセージ送信者がBotだった場合は無視する
        return

    # senpaiがオンラインである時
    senpai_id = 1076387439410675773
    senpai = message.guild.get_member(senpai_id)
    if senpai and senpai.status == discord.Status.online:
        await client.change_presence(
            activity=discord.Activity(
                name="研修チュウ", type=discord.ActivityType.playing
            )
        )
        return
    else:
        await client.change_presence(
            activity=discord.Activity(
                name="種族値クイズ", type=discord.ActivityType.competing
            )
        )

    if message.content.startswith("/bqdata"):
        bqFilterWords = message.content.split()[1:]

        if bqFilterWords:
            removeWords = [
                "タイプ",
                "特性",
                "出身地",
                "初登場世代",
                "進化段階",
                "HP",
                "こうげき",
                "ぼうぎょ",
                "とくこう",
                "とくぼう",
                "すばやさ",
                "合計",
            ]

            if "リセット" in bqFilterWords:
                BQ_FILTER_DICT = {"進化段階": ["最終進化", "進化しない"]}
                bqFilterWords.remove("リセット")

            if "種族値" in bqFilterWords:
                for key in [
                    "HP",
                    "こうげき",
                    "ぼうぎょ",
                    "とくこう",
                    "とくぼう",
                    "すばやさ",
                    "合計",
                ]:
                    BQ_FILTER_DICT.pop(key, None)
                bqFilterWords.remove("種族値")

            for i in range(len(bqFilterWords)):
                if bqFilterWords[i] in removeWords:  # 絞り込みをリセット
                    del BQ_FILTER_DICT[bqFilterWords[i]]

            bqFilterWords = [x for x in bqFilterWords if x not in removeWords]

            # インデックスの要素が更新されていない項目はそのまま
            BQ_FILTER_DICT.update(ub.make_filter_dict(bqFilterWords))
            BQ_FILTERED_DF = ub.filter_dataframe(BQ_FILTER_DICT).fillna("なし")
            response = "種族値クイズの出題条件が変更されました"
            ub.output_log("出題条件が更新されました")

        else:
            response = "現在の種族値クイズの出題条件は以下の通りです"

        bqFilteredEmbed = discord.Embed(
            title="種族値クイズの出題条件",
            color=0x9013FE,
            description=f"該当ポケモン数: {BQ_FILTERED_DF.shape[0]}匹",
        )

        for i, key in enumerate(BQ_FILTER_DICT.keys()):
            values = "\n".join(BQ_FILTER_DICT[key])
            bqFilteredEmbed.add_field(name=key, value=values, inline=False)

        ub.output_log("出題条件を表示します")
        await message.channel.send(response, embed=bqFilteredEmbed)

    # リプライ(reference)に反応
    elif message.reference is not None:
        # リプライ先メッセージのキャッシュを取得
        message.reference.resolved = await message.channel.fetch_message(
            message.reference.message_id
        )

        # bot自身へのリプライに反応
        """if (
            message.reference.resolved.author == client.user
            and message.reference.resolved.embeds
        ):"""
        if message.reference.resolved.embeds:
            embedFooterText = message.reference.resolved.embeds[0].footer.text
            # リプライ先にembedが含まれるかつ未回答のクイズの投稿か
            if (
                "No.26 ポケモンクイズ" in embedFooterText
                and not "(done)" in embedFooterText
            ):
                await quiz(embedFooterText.split()[3]).try_response(message)

            else:
                ub.output_log("botへのリプライは無視されました")


# 新規メンバーが参加したときの処理
@client.event
async def on_member_join(member):
    if not member.bot:
        await member.add_roles(
            member.guild.get_role(UNKNOWN_ROLE_ID)
        )  # ロールがある場合に付与に変更
        ub.output_log(f"ロールを付与しました: {member.name}にID{UNKNOWN_ROLE_ID}")
        if helloCh := client.get_channel(HELLO_CHANNEL_ID):
            helloEmbed = discord.Embed(
                title="メンバー認証ボタンを押して 学籍番号を送信してね",
                color=0x5EFF24,
                description="送信するとサーバーが使用可能になります\n工学院大学の学生でない人は個別にご相談ください",
            )
            helloEmbed.set_author(name=f"{member.guild.name}の せかいへ ようこそ!")
            helloEmbed.add_field(
                name="サーバーの ガイドラインは こちら",
                value=f"{BALL_ICON}<#1067423922477355048>",
                inline=False,
            )
            helloEmbed.add_field(
                name="みんなにみせるロールを 変更する",
                value=f"{BALL_ICON}<#1068903858790731807>",
                inline=False,
            )
            helloEmbed.set_thumbnail(
                url=f"{EX_SOURCE_LINK}sprites/Gen1/{random.randint(1, 151)}.png"
            )

            authButton = discord.ui.Button(
                label="メンバー認証",
                style=discord.ButtonStyle.primary,
                custom_id="authButton",
            )
            helloView = discord.ui.View()
            helloView.add_item(authButton)

            await helloCh.send(
                f"はじめまして! {member.mention}さん", embed=helloEmbed, view=helloView
            )
            ub.output_log(f"サーバーにメンバーが参加しました: {member.name}")
        else:
            ub.output_log(f"チャンネルが見つかりません: {HELLO_CHANNEL_ID}")


@client.event
async def on_interaction(interaction: discord.Interaction):
    if "custom_id" in interaction.data and interaction.data["custom_id"] == "authModal":
        ub.output_log("学籍番号を処理します")
        listPath = MEMBERDATA_PATH
        studentId = interaction.data["components"][0]["components"][0]["value"]

        if (
            (studentId := studentId.upper()).startswith(
                ("S", "A", "C", "J", "D", "B", "E", "G")
            )
            and re.match(r"^[A-Z0-9]+$", studentId)
            and len(studentId) == 7
        ):
            member = interaction.user
            role = interaction.guild.get_role(UNKNOWN_ROLE_ID)
            favePokeName = interaction.data["components"][1]["components"][0]["value"]
            response = "登録を修正したい場合はもう一度ボタンを押してください"

            if role in member.roles:  # ロールを持っていれば削除
                await member.remove_roles(role)
                response += "\nサーバーが利用可能になりました"
                ub.output_log(f"学籍番号が登録されました\n {member.name}: {studentId}")
            else:
                ub.output_log(f"登録の修正を受け付けました\n {member.name}: {studentId}")
            response += "\n`※このメッセージはあなたにしか表示されていません`"

            thanksEmbed = discord.Embed(
                title="登録ありがとうございました", color=0x2EAFFF, description=response
            )
            thanksEmbed.add_field(name="登録した学籍番号", value=studentId)
            thanksEmbed.add_field(
                name="好きなポケモン",
                value=favePokeName if not favePokeName == "" else "登録なし",
            )

            if not favePokeName == "":
                if (favePokedata := ub.fetch_pokemon(favePokeName)) is not None:
                    favePokeName = favePokedata.iloc[0]["おなまえ"]

            times = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")
            authData = {
                "登録日時": [times],
                "ユーザーID": [str(member.id)],
                "ユーザー名": [member.name],
                "学籍番号": [studentId],
                "好きなポケモン": [favePokeName],
            }
            df = pd.DataFrame(authData)
            df.to_csv(
                MEMBERLIST_PATH,
                mode="a",
                index=False,
                header=not os.path.exists(MEMBERLIST_PATH),
            )

            content = "照合に失敗しました ?\n※メンバーリストにまだ学籍番号のデータがない可能性があります"
            if os.path.exists(listPath):
                member_df = pd.read_csv(listPath).set_index("学籍番号")
                if studentId in member_df.index:
                    memberData = pd.DataFrame(
                        {
                            "ユーザーID": [member.id],
                            "ユーザー名": [member.name],
                            "好きなポケモン": [favePokeName],
                        },
                        index=[studentId],
                    ).iloc[0]
                    member_df.loc[studentId] = memberData
                    member_df["ユーザーID"] = (
                        member_df["ユーザーID"]
                        .dropna()
                        .replace([np.inf, -np.inf], np.nan)
                        .dropna()
                        .astype(int)
                    )

                    member_df.to_csv(listPath, index=True, float_format="%.0f")
                    content = "照合に成功しました"
                    ub.output_log(
                        f"サークルメンバー照合ができました\n {studentId}: {member.name}"
                    )
                else:
                    ub.output_log(
                        f"サークルメンバー照合ができませんでした\n {studentId}: {member.name}"
                    )
            else:
                ub.output_log(f"認証用   ファイルが存在しません: {listPath}")

            await interaction.response.send_message(
                content, embed=thanksEmbed, ephemeral=True
            )

        else:  # 学籍番号が送信されなかった場合の処理
            ub.output_log(f"学籍番号として認識されませんでした: {studentId}")
            errorEmbed = discord.Embed(
                title="401 Unauthorized",
                color=0xFF0000,
                description=f"あなたの入力した学籍番号: **{studentId}**\n申し訳ございませんが、もういちどお試しください。",
            )
            errorEmbed.set_author(
                name="Porygon-Z.com", url="https://wiki.ポケモン.com/wiki/ポリゴンZ"
            )
            errorEmbed.set_thumbnail(url=f"{EX_SOURCE_LINK}art/474.png")
            errorEmbed.add_field(
                name="入力形式は合っていますか?",
                value="半角英数字7ケタで入力してください",
                inline=False,
            )
            errorEmbed.add_field(
                name="工学院生ではありませんか?",
                value="個別にご相談ください",
                inline=False,
            )
            errorEmbed.add_field(
                name="解決しない場合",
                value=f"管理者にお問い合わせください: <@!{DEVELOPER_USER_ID}>",
                inline=False,
            )
            await interaction.response.send_message(embed=errorEmbed, ephemeral=True)

    elif (
        "component_type" in interaction.data and interaction.data["component_type"] == 2
    ):
        ub.output_log(
            f'buttonが押されました\n {interaction.user.name}: {interaction.data["custom_id"]}'
        )
        await on_button_click(interaction)


async def on_button_click(interaction: discord.Interaction):
    custom_id = interaction.data[
        "custom_id"
    ]  # custom_id(インタラクションの識別子)を取り出す

    if custom_id == "authButton":  # メンバー認証ボタン モーダルを送信する
        ub.output_log("学籍番号取得を実行します")
        authModal = discord.ui.Modal(
            title="メンバー認証", timeout=None, custom_id="authModal"
        )
        authInput = discord.ui.TextInput(
            label="学籍番号",
            placeholder="J111111",
            min_length=7,
            max_length=7,
            custom_id="studentIdInput",
        )
        authModal.add_item(authInput)
        favePokeInput = discord.ui.TextInput(
            label="好きなポケモン(任意)",
            placeholder="ヤブクロン",
            required=False,
            custom_id="favePokeInput",
        )
        authModal.add_item(favePokeInput)
        await interaction.response.send_modal(authModal)


comeout = """
elif custom_id.startswith("lotoIdButton"): #IDくじボタン
      ub.output_log("IDくじを実行します")
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
        shun='''prize_dict = {
          0: ["ほしのすな", 1500, "", "残念賞"],
          1: ["きんのたま", 5000, f'やったロ{EXCLAMATION_ICON} 1ケタ おんなじロ{EXCLAMATION_ICON}', "4等"],
          2: ["すいせいのかけら", 12500, f'2ケタが おんなじだったロミ{EXCLAMATION_ICON}', "3等"],
          3: ["ガブリアスドール", 65000, f'ロミ{EXCLAMATION_ICON} 3ケタが おんなじロ{EXCLAMATION_ICON}', "2等"],
          4: ["こだいのせきぞう", 200000, f'すごいロ{EXCLAMATION_ICON} 4ケタも おんなじロミ{EXCLAMATION_ICON}',"1等"],
          5: ["たかそうなカード", 650000, f'ロミ~~{EXCLAMATION_ICON}{EXCLAMATION_ICON}{EXCLAMATION_ICON} 下5ケタ すべてが おんなじロ{EXCLAMATION_ICON}', "特等"],
          6: ["きんのパッチールぞう", 1000000, "", ""]
        }'''
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
      """


class quiz:
    def __init__(self, quizName):
        self.quizName = quizName

    async def post(self, sendChannel):
        ub.output_log(f"{self.quizName}: クイズを出題します")

        quizContent = None
        quizFile = None
        quizEmbed = discord.Embed(title="", color=0x9013FE, description="")
        quizEmbed.set_footer(text=f"No.26 ポケモンクイズ - {self.quizName}")
        quizView = None
        # 必要な要素をクイズごとに編集

        if self.quizName == "bq":
            qDatas = self.__shotgun(BQ_FILTER_DICT)
            if qDatas is not None:
                baseStats = [
                    qDatas["HP"],
                    qDatas["こうげき"],
                    qDatas["ぼうぎょ"],
                    qDatas["とくこう"],
                    qDatas["とくぼう"],
                    qDatas["すばやさ"],
                ]

                quizEmbed.title = "種族値クイズ"
                quizEmbed.description = "こたえ: ???"  # 正答後: こたえ: [ポケモン名](複数いる場合),[ポケモン名]
                quizFile = discord.File(
                    ub.generate_graph(baseStats), filename="image.png"
                )
                quizEmbed.set_image(
                    url="attachment://image.png"
                )  # 種族値クイズ図形の添付
                quizEmbed.set_thumbnail(
                    url=self.__imageLink()
                )  # 正解までDecamark(?)を表示
                quizContent = ub.bss_to_text(qDatas)

            else:
                await sendChannel.send("現在の出題条件に合うポケモンがいません")

        elif self.quizName == "acq":
            qDatas = self.__shotgun({"進化段階": ["最終進化", "進化しない"]})
            quizEmbed.title = "ACクイズ"
            quizEmbed.description = (
                f"{qDatas['おなまえ']} はこうげきととくこうどちらが高い?"
            )
            quizEmbed.set_thumbnail(url=self.__imageLink(qDatas["おなまえ"]))

            quizView = discord.ui.View()
            quizView.add_item(
                discord.ui.Button(
                    label="こうげき",
                    style=discord.ButtonStyle.primary,
                    custom_id="acq_こうげき",
                )
            )
            quizView.add_item(
                discord.ui.Button(
                    label="とくこう",
                    style=discord.ButtonStyle.primary,
                    custom_id="acq_とくこう",
                )
            )
            quizView.add_item(
                discord.ui.Button(
                    label="同値",
                    style=discord.ButtonStyle.secondary,
                    custom_id="acq_同値",
                )
            )

        elif self.quizName == "etojq":
            while 1:
                qDatas = self.__shotgun({"進化段階": ["最終進化", "進化しない"]})
                if pd.notna(qDatas["英語名"]):
                    break

            quizEmbed.title = "英和翻訳クイズ"
            quizEmbed.description = f"{qDatas['英語名']} -> [?]"

        elif self.quizName == "jtoeq":
            while 1:
                qDatas = self.__shotgun({"進化段階": ["最終進化", "進化しない"]})
                if pd.notna(qDatas["英語名"]):
                    break

            quizEmbed.title = "和英翻訳クイズ"
            quizEmbed.description = f"{qDatas['おなまえ']} -> [?]"
            quizEmbed.set_thumbnail(url=self.__imageLink(qDatas["おなまえ"]))

        elif self.quizName == "ctojq":
            while 1:
                qDatas = self.__shotgun({"進化段階": ["最終進化", "進化しない"]})
                if pd.notna(qDatas["中国語繁体"]):
                    break

            quizEmbed.title = "中日翻訳クイズ"
            quizEmbed.description = f"{qDatas['中国語繁体']} -> [?]"

        else:
            ub.output_log(f"不明なクイズ識別子(post): {self.quizName}")
            # ここでエラーを送信
            return

        self.qm = await sendChannel.send(
            content=quizContent, file=quizFile, embed=quizEmbed, view=quizView
        )

    async def try_response(self, response):
        if QUIZ_PROCESSING_FLAG == 1:
            ub.output_log(f"{self.quizName}: 応答処理実行中につき処理を中断")
            return

        # インスタンスがメッセージ/インタラクションかどうかで代入データを変える
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
            # customIDが"acq_こうげき/とくこう/同値"のようなかたちを想定

        self.quizEmbed = self.qm.embeds[0]

        gives = ["ギブ", "ギブアップ", "降参", "敗北"]
        hints = []

        # クイズごとにヒント項目を作成する
        if self.quizName in ["bq", "ctojq"]:
            hints = [
                "ヒント",
                "タイプ",
                "特性",
                "トクセイ",
                "地方",
                "チホウ",
                "分類",
                "ブンルイ",
                "作品",
                "サクヒン",
            ]
        elif self.quizName == "etojq":
            hints = [
                "ヒント",
                "タイプ",
                "特性",
                "トクセイ",
                "地方",
                "チホウ",
                "分類",
                "ブンルイ",
                "作品",
                "サクヒン",
                "語源",
                "ゴゲン",
            ]
        elif self.quizName == "jtoeq":
            hints = ["文字数", "モジスウ", "頭文字", "カシラモジ", "イニシャル"]

        # ここでクイズの問題文を取得する
        if self.quizName == "bq":
            self.examText = self.qm.content.split(" ")[0]
        elif self.quizName == "acq":
            self.examText = self.quizEmbed.description.split(" ")[0]
        elif self.quizName in ["etojq", "jtoeq", "ctojq"]:
            self.examText = re.findall(r"^(.+)\s->", self.quizEmbed.description)[0]

        # ここでクイズの回答を取得する
        self.ansList, self.ansZero = self.__answers()

        if self.ansText in gives:
            await self.__giveup()
        elif self.ansText in hints:
            await self.__hint()
        else:
            await self.__judge()

    async def __giveup(self):
        ub.output_log(f"{self.quizName}: ギブアップを実行")
        if isinstance(self.rm, discord.Message):
            await self.rm.add_reaction("😅")
            await self.rm.reply(f"答えは{self.ansList[0]}でした")
        await self.__disclose(False)

    async def __judge(self):
        ub.output_log(f"{self.quizName}: 正誤判定を実行")

        fixAns = self.ansText
        if self.quizName in ["bq", "etojq", "ctojq"]:
            if (repPokeData := ub.fetch_pokemon(self.ansText)) is not None:
                fixAns = repPokeData.iloc[0]["おなまえ"]
        elif self.quizName == "jtoeq":
            fixAns = jaconv.z2h(
                jaconv.kata2alphabet(fixAns), kana=False, ascii=False, digit=True
            ).lower()
            self.ansList[0] = self.ansList[0].lower()

        if fixAns in self.ansList:
            judge = "正答"
            if isinstance(self.rm, discord.Message):
                await self.rm.add_reaction("⭕")
            await self.__disclose(True, fixAns)
        else:
            judge = "誤答"
            if isinstance(self.rm, discord.Message):
                reaction = "❌"
            if isinstance(
                self.rm, discord.Interaction
            ):  # ボタンで回答しているときはギブアップになる
                await self.__disclose(False)

        if (
            self.quizName in ["bq", "etojq", "ctojq"] and repPokeData is None
        ):  # 例外処理
            judge = None
            if isinstance(self.rm, discord.Message):
                reaction = "❓"
                await self.rm.reply(f"{self.ansText} は図鑑に登録されていません")
        elif (
            judge == "誤答"
            and self.quizName == "jtoeq"
            and len(
                (
                    poke := GLOBAL_BRELOOM_DF[
                        GLOBAL_BRELOOM_DF["英語名"].str.lower() == fixAns
                    ]
                )
            )
            > 0
        ):
            if isinstance(self.rm, discord.Message):
                await self.rm.reply(
                    f"{fixAns} は {poke.iloc[0]['おなまえ']} の英名です"
                )

        if judge != "正答" and isinstance(self.rm, discord.Message):
            await self.rm.add_reaction(reaction)

        if judge is not None:
            ub.report(
                self.opener.id, f"{self.quizName}{judge}", 1
            )  # 回答記録のレポート

        self.__log(judge, self.ansList[0])

    async def __hint(self):
        ub.output_log(f"{self.quizName}: ヒント表示を実行")

        if self.quizName in ["bq", "etojq", "ctojq"]:
            if (
                self.ansText == "ヒント"
            ):  # まだ出ていないヒントからランダムにヒントを出す
                hintIndexs = [
                    "タイプ1",
                    "タイプ2",
                    "特性1",
                    "特性2",
                    "隠れ特性",
                    "出身地",
                    "分類",
                    "初登場作品",
                ]  # ヒントになるインデックスの一覧
                alreadyHints = [
                    field.name for field in self.quizEmbed.fields
                ]  # 既出のヒントの一覧
                stillHints = [
                    x for x in hintIndexs if x not in alreadyHints
                ]  # 未出のヒントの一覧
                if len(stillHints) > 0:
                    while True:
                        hintIndex = random.choice(stillHints)
                        if pd.notna(hintIndex):
                            break
                else:
                    hintIndex = random.choice(alreadyHints)

            elif self.ansText in ["タイプ"]:
                if not any(field.name == "タイプ1" for field in self.quizEmbed.fields):
                    hintIndex = "タイプ1"
                elif not any(
                    field.name == "タイプ2" for field in self.quizEmbed.fields
                ):
                    hintIndex = "タイプ2"
                else:
                    await self.rm.reply(
                        f"タイプは{str(self.ansZero['タイプ1'])}/{str(self.ansZero['タイプ2'])}です"
                    )
                    return

            elif self.ansText in ["特性", "トクセイ"]:
                if not any(field.name == "特性1" for field in self.quizEmbed.fields):
                    hintIndex = "特性1"
                elif not any(field.name == "特性2" for field in self.quizEmbed.fields):
                    hintIndex = "特性2"
                elif not any(
                    field.name == "隠れ特性" for field in self.quizEmbed.fields
                ):
                    hintIndex = "隠れ特性"
                else:
                    await self.rm.reply(
                        f"とくせいは{str(self.ansZero['特性1'])}/{str(self.ansZero['特性1'])}/{str(self.ansZero['隠れ特性'])}です"
                    )
                    return

            elif self.ansText in ["地方", "チホウ"]:
                hintIndex = "出身地"
            elif self.ansText in ["分類", "ブンルイ"]:
                hintIndex = "分類"
            elif self.ansText in ["作品", "サクヒン"]:
                hintIndex = "初登場作品"
            elif self.ansText in ["語源", "ゴゲン"]:
                hintIndex = "英語名由来"
            hintValue = self.ansZero[hintIndex]

        elif self.quizName == "jtoeq":
            if self.ansText in ["文字数", "モジスウ"]:
                hintIndex = "文字数"
                hintValue = len(self.ansZero["英語名"])
            elif self.ansText in ["頭文字", "カシラモジ", "イニシャル"]:
                hintIndex = "イニシャル"
                hintValue = self.ansZero["英語名"][0:1]

        else:
            ub.output_log(f"不明なクイズ識別子(hint): {self.quizName}")
            return

        # 初出のヒントならEmbedにフィールドを追加
        if not any(field.name == hintIndex for field in self.quizEmbed.fields):
            self.quizEmbed.add_field(name=hintIndex, value=hintValue)
            try:
                await self.qm.edit(embed=self.quizEmbed, attachments=[])
            except discord.errors.Forbidden:
                pass

        await self.rm.reply(f"{hintIndex}は{hintValue}です")

    async def __disclose(self, tf, answered=None):
        global QUIZ_PROCESSING_FLAG
        ub.output_log(f"{self.quizName}: 回答開示を実行")
        QUIZ_PROCESSING_FLAG = 1  # 回答開示処理を始める

        if tf:  # 正解者がいる場合
            clearTime = self.rm.created_at - self.qm.created_at  # 所要時間を求める
            days, seconds = divmod(clearTime.total_seconds(), 86400)  # 所要時間を分解
            hours, seconds = divmod(seconds, 3600)
            minutes, seconds = divmod(seconds, 60)
            clearTimes = f"{int(seconds)}秒"
            if days >= 1:
                clearTimes = (
                    f"{int(days)}日 {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
                )
            elif hours >= 1:
                clearTimes = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            elif minutes >= 1:
                clearTimes = f"{int(minutes):02}:{int(seconds):02}"
            authorText = f"{self.opener.name} さんが正解! [TIME {clearTimes}]"
            link = self.__imageLink(answered)

        else:  # 正解者が存在せず,ギブアップされた場合
            authorText = f"{self.opener.name} さんがギブアップ"
            link = self.__imageLink(
                self.ansList[0]
            )  # self.ansZero['おなまえ']でもいいかも

        self.quizEmbed.set_author(name=authorText)  # 回答者の情報を表示

        if self.quizName == "bq":
            self.quizEmbed.description = f'こたえ: {",".join(self.ansList)}'
        elif self.quizName == "acq":
            self.quizEmbed.description = f"{ub.bss_to_text(self.ansZero)}\n"
            if self.ansList[0] == "同値":
                self.quizEmbed.description += (
                    f"{self.examText}はこうげきととくこうが同じ"
                )
            else:
                self.quizEmbed.description += (
                    f"{self.examText}は{self.ansList[0]}の方が高い"
                )

        elif self.quizName in ["etojq", "jtoeq", "ctojq"]:
            self.quizEmbed.description = f"{self.examText} -> [{self.ansList[0]}]"
            if self.quizName == "etojq":
                self.quizEmbed.description += f'\n{str(self.ansZero["英語名由来"])}'
            elif self.quizName == "ctojq":
                self.quizEmbed.description += (
                    f"\n拼音: {ub.pinyin_to_text(self.examText)}"
                )

        if not "Decamark" in link:
            self.quizEmbed.set_thumbnail(url=link)  # サムネイルを変更する
        self.quizEmbed.set_footer(text=self.quizEmbed.footer.text + "(done)")

        if isinstance(self.rm, discord.Message):
            try:
                await self.qm.edit(embed=self.quizEmbed, attachments=[])
            except discord.errors.Forbidden:
                await self.qm.channel.send(embed=self.quizEmbed)

        elif isinstance(self.rm, discord.Interaction):
            fixView = discord.ui.View()
            fixView.from_message(self.qm)
            for child in fixView.children:
                child.disabled = True
            try:
                await self.rm.response.edit_message(
                    embed=self.quizEmbed, attachments=[], view=fixView
                )
            except discord.errors.Forbidden:
                pass

        QUIZ_PROCESSING_FLAG = 0  # 回答開示処理を終わる
        await self.__continue()  # 連続出題を試みる

    async def __continue(self):
        if BAKUSOKU_MODE:
            ub.output_log(f"{self.quizName}: 連続出題を実行")
            loadingEmbed = discord.Embed(
                title="**BAKUSOKU MODE ON**",
                color=0x0000FF,
                description="次のクイズを生成チュウ",
            )
            loadMessage = await self.qm.channel.send(embed=loadingEmbed)
            await quiz(self.quizName).post(self.qm.channel)
            await loadMessage.delete()

    def __answers(self):
        ub.output_log(f"{self.quizName}: 正答リスト生成を実行")
        answers = []
        aData = None

        if self.quizName == "bq":
            H, A, B, C, D, S = map(int, self.examText.split("-"))
            aDatas = GLOBAL_BRELOOM_DF.loc[
                (GLOBAL_BRELOOM_DF["HP"] == H)
                & (GLOBAL_BRELOOM_DF["こうげき"] == A)
                & (GLOBAL_BRELOOM_DF["ぼうぎょ"] == B)
                & (GLOBAL_BRELOOM_DF["とくこう"] == C)
                & (GLOBAL_BRELOOM_DF["とくぼう"] == D)
                & (GLOBAL_BRELOOM_DF["すばやさ"] == S)
            ]
            aData = aDatas.iloc[0]
            for index, row in aDatas.iterrows():
                answer = row["おなまえ"]
                answers.append(answer)

        elif self.quizName == "acq":
            aDatas = ub.fetch_pokemon(self.examText)
            aData = aDatas.iloc[0]
            if (aData["こうげき"] == aData["とくこう"]).all():
                answers.append("同値")
            elif (aData["こうげき"] > aData["とくこう"]).all():
                answers.append("こうげき")
            else:
                answers.append("とくこう")

        elif self.quizName == "etojq":
            aDatas = GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF["英語名"] == self.examText]
            aData = aDatas.iloc[0]
            answers.append(str(aData["おなまえ"]))

        elif self.quizName == "jtoeq":
            aDatas = ub.fetch_pokemon(self.examText)
            aData = aDatas.iloc[0]
            answers.append(str(aData["英語名"]))

        elif self.quizName == "ctojq":
            aDatas = GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF["中国語繁体"] == self.examText]
            aData = aDatas.iloc[0]
            answers.append(str(aData["おなまえ"]))

        else:
            ub.output_log(f"不明なクイズ識別子(answers): {self.quizName}")
            return

        return answers, aData  # 正答のリストと0番目の正答をタプルで返す

    def __shotgun(self, filter_dict):
        ub.output_log(f"{self.quizName}: ランダム選択を実行")
        filteredPokeData = ub.filter_dataframe(filter_dict)  # .fillna('なし')
        selectedPokeData = filteredPokeData.iloc[
            random.randint(0, filteredPokeData.shape[0] - 1)
        ]
        if selectedPokeData is not None:
            return selectedPokeData
        else:
            ub.output_log(f"{self.quizName}: ERROR 正常にランダム選択できませんでした")
            return None

    def __imageLink(self, searchWord=None):
        ub.output_log(f"{self.quizName}: 画像リンク生成を実行")
        link = f"{EX_SOURCE_LINK}Decamark.png"  # デフォルトは(?)マーク
        if searchWord is not None:
            if self.quizName in ["bq", "acq", "etojq", "jtoeq", "ctojq"]:
                displayImage = ub.fetch_pokemon(searchWord)
                if displayImage is not None:  # 回答ポケモンが発見できた場合
                    link = f"{EX_SOURCE_LINK}art/{displayImage.iloc[0]['ぜんこくずかんナンバー']}.png"
            else:
                ub.output_log(f"不明なクイズ識別子(imageLink): {self.quizName}")
        return link

    def __log(self, judge, exAns):
        logPath = f"log/{self.quizName}log.csv"
        ub.output_log(f"{self.quizName}: log生成を実行\n {logPath}")

        if os.path.exists(logPath):
            log_df = pd.read_csv(logPath)
        else:
            log_df = pd.DataFrame(columns=["正誤判定", "内容", "解答", "入力認識可否"])

        nRow = pd.DataFrame(
            {
                "正誤判定": judge,
                "内容": self.examText,
                "解答": self.ansText,
                "入力認識可否": judge is not None,
            },
            index=[0],
        )
        log_df = pd.concat([nRow, log_df]).reset_index(drop=True)
        log_df.to_csv(logPath, mode="w", header=True, index=False)


@tasks.loop(seconds=60)
async def daily_bonus(now: datetime = None):
    if now is None:
        now = datetime.now(ZoneInfo("Asia/Tokyo"))
    if now.hour == 5 and now.minute == 0:
        ub.output_log("ジョブを実行します")
        todayId = str(random.randint(0, 99999)).zfill(5)

        dairyIdEmbed = discord.Embed(
            title="IDくじセンター 抽選コーナー",
            color=0xFF297E,
            description=f"くじのナンバーと ユーザーIDが みごと あってると ステキな 景品を もらえちゃうんだロ{BANGBANG_ICON}",
        )
        dairyIdEmbed.add_field(
            name=f"{BALL_ICON}今日のナンバー", value=f"**{todayId}**", inline=False
        )
        dairyIdEmbed.set_footer(text="No.15 IDくじ")

        lotoButton = discord.ui.Button(
            label="くじをひく",
            style=discord.ButtonStyle.primary,
            custom_id=f'lotoIdButton:{todayId}:{datetime.now(ZoneInfo("Asia/Tokyo")).date()}',
        )
        dairyView = discord.ui.View()
        dairyView.add_item(lotoButton)

        lotoReset = pd.read_csv(REPORT_PATH)
        lotoReset["クジびきけん"] = 1
        lotoReset.to_csv(REPORT_PATH, index=False)

        dairyChannel = client.get_channel(DAIRY_CHANNEL_ID)
        day = datetime.now(ZoneInfo("Asia/Tokyo"))
        weak_dict = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
        await dairyChannel.send(
            f'日付が変わりました。 {day.strftime("%Y/%m/%d")} ({weak_dict[day.weekday()]})',
            embeds=[ub.show_calendar(day), ub.show_senryu(True), dairyIdEmbed],
            view=dairyView,
        )


# おこづかいランキングを表示するコマンド
@tree.command(
    name="pocketmoney", description="おこづかいの残高照会をします"
)
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe()
async def slash_pocketmoney(interaction: discord.Interaction):
    user_id = interaction.user.id
    money = ub.report(user_id, "おこづかい", 0)
    df = pd.read_csv(REPORT_PATH, dtype={"ユーザーID": str})
    user_id = str(user_id)

    user_wallet = df[["ユーザーID", "おこづかい"]]
    user_wallet_sorted = user_wallet.sort_values(
        by="おこづかい", ascending=False
    ).reset_index(drop=True)

    # ランキングを作成し順位を取得
    max_wallet = 0
    userRank = 0
    for i in range(1, len(user_wallet_sorted) + 1):
        if max_wallet == user_wallet_sorted["おこづかい"][i - 1]:
            rank = user_wallet_sorted.loc[i - 2, "rank"]
        else:
            max_wallet = user_wallet_sorted["おこづかい"][i - 1]
            rank = i
        user_wallet_sorted.loc[i - 1, "rank"] = rank
        if user_wallet_sorted.loc[i - 1, "ユーザーID"] == user_id:
            userRank = rank

        if userRank != 0 and i >= 5:
            break
    # ランキングのトップ5を取得
    top_n = 5
    top_users = user_wallet_sorted.head(top_n)

    ranking_list = top_users.values.tolist()

    pdwGuild = await client.fetch_guild(PDW_SERVER_ID, with_counts=True)
    author = ub.attachment_file("resource/image/mom_johto.png")
    embed = ub_embed.balance(
        userName=interaction.user.name,
        pocketMoney=money,
        numOfPeople=pdwGuild.approximate_member_count,
        userRank=userRank,
        rank_list=ranking_list,
        sendTime=datetime.now(ZoneInfo("Asia/Tokyo")),
        authorPath=author[1],
    )

    await interaction.response.send_message(
        file=author[0], embed=embed, ephemeral=True
    )


# BOTの起動
load_dotenv()
client.run(os.environ.get("DISCORD_TOKEN"), reconnect=True)
