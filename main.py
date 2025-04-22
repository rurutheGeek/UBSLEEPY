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
import json
from PIL import Image

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

# ===================================================================================================
# 事前設定
# main.pyのディレクトリに移動
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# クライアントを作成
tree = discord.app_commands.CommandTree(client)

# ===================================================================================================
# 起動時の処理


@client.event
async def on_ready():
    global BQ_FILTERED_DF
    if DEBUG_MODE:
        ub.output_log("debugモードで起動します")

    if len(GUILD_IDS) == 0:
        ub.output_log("登録済のサーバーが0個です")
    else:
        syncGuildName = ""
        i = 0
        for guild_id in GUILD_IDS:
            #client.get_guild(guild_id)がNoneの場合はスキップ
            if client.get_guild(guild_id) is None:
                ub.output_log(f"登録済のサーバーが見つかりません: {guild_id}")
                continue
            syncGuildName += f"\n#{i} {client.get_guild(guild_id).name}"
            await tree.sync(guild=discord.Object(id=guild_id))
            i += 1
        ub.output_log(
            f"登録済のサーバーを{len(GUILD_IDS)}個読み込みました{syncGuildName}"
        )

    BQ_FILTERED_DF = ub.filter_dataframe(BQ_FILTER_DICT).fillna("なし")

    # 定期処理の開始
    if not post_logs.is_running():
        post_logs.start()
    if not daily_bonus.is_running():
        daily_bonus.start()

    # 時報の投稿済みチェック (5時以降の起動で)
    dairyChannel = client.get_channel(DAIRY_CHANNEL_ID)
    if dairyChannel is not None:
        now = datetime.now(ZoneInfo("Asia/Tokyo"))
        if now.hour >= 5:
            timeSignal = False
            async for message in dairyChannel.history(limit=3):
                if (
                    message.author == client.user
                    and now.strftime("%Y/%m/%d") in message.content
                ):
                    timeSignal = True
                    break

            if not timeSignal:
                ub.output_log("本日の時報が未投稿のようです.時報の投稿を試みます")
                await daily_bonus(now.replace(hour=5, minute=0, second=0, microsecond=0))

        ub.output_log("botが起動しました")
        
# ===================================================================================================
# テスト処理



# ===================================================================================================
# 定期的に実行する処理


@tasks.loop(seconds=30)
async def post_logs():
    try:
        with open(SYSTEMLOG_PATH, "r+", encoding="utf-8") as file:
            file.seek(0)
            logStrs = file.read()
            if logStrs:
                channel = client.get_channel(LOG_CHANNEL_ID)
                # 文字数制限のため,2000以上なら分割して送信
                if len(logStrs) > 2000:
                    for i in range(0, len(logStrs), 2000):
                        await channel.send(logStrs[i : i + 2000])
                else:
                    await channel.send(logStrs)
                file.truncate(0)

    except FileNotFoundError:
        pass


@tasks.loop(seconds=60)
async def daily_bonus(now: datetime = None, channelid: int = DAIRY_CHANNEL_ID):
    if now is None:
        now = datetime.now(ZoneInfo("Asia/Tokyo"))
    if now.hour == 5 and now.minute == 0:
        ub.output_log("ログインジョブを実行します")
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

        dairyChannel = client.get_channel(channelid)
        day = datetime.now(ZoneInfo("Asia/Tokyo"))
        await dairyChannel.send(
            f'日付が変わりました。 {day.strftime("%Y/%m/%d")} ({WEAK_DICT[str(day.weekday())]})',
            embeds=[ub.show_calendar(day), ub.show_senryu(True), dairyIdEmbed],
            view=dairyView,
        )


# ===================================================================================================
# スラッシュコマンド

@tree.command(name="dex", description="ポケモンの図鑑データを表示します")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(name="表示したいポケモンのおなまえ")
async def slash_dex(interaction: discord.Interaction, name: str):
    ub.output_log("図鑑を実行します")
    await display_pokedex(interaction, name)

# ポケモン図鑑表示の共通関数
async def display_pokedex(interaction, name, message=None):
    """ポケモンの図鑑データを表示する共通関数
    
    Parameters:
    ----------
    interaction : discord.Interaction
        インタラクションオブジェクト
    name : str
        表示するポケモン名
    message : discord.Message, optional
        更新する既存のメッセージ（ボタン操作時）
    """
    if (pokedata := ub.fetch_pokemon(name)) is not None:  # データが存在する場合は、図鑑データを返信
        pokedata = pokedata.fillna(" ")
        dexNumber = pokedata.iloc[0]['ぜんこくずかんナンバー']
        dexName = str(pokedata.iloc[0]['おなまえ'])
        dexIndexs = [pokedata.iloc[0]['インデックス1'], pokedata.iloc[0]['インデックス2'], pokedata.iloc[0]['インデックス3']]
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
        dexSum = int(pokedata.iloc[0]['合計'])
        dexGen = str(pokedata.iloc[0]['初登場作品'])
        
        emoji = "🔴"
        
        # Embed作成
        dexEmbed = discord.Embed(
            title=f'{emoji}{dexName}の図鑑データ{emoji}',
            color=TYPE_COLOR_DICT.get(dexType1, 0xdcdcdc),
            description=f'''No.{dexNumber} {dexName} 出身: {dexGen}
タイプ: {dexType1}/{dexType2}
とくせい: {dexAbi1}/{dexAbi2}/{dexAbiH}
```
┌───┬───┬───┬───┬───┬───┰───┐
│ H │ A │ B │ C │ D │ S ┃Tot│
├───┼───┼───┼───┼───┼───╂───┤
│{dexH:3}-{dexA:3}-{dexB:3}-{dexC:3}-{dexD:3}-{dexS:3} {dexSum:3}│
└───┴───┴───┴───┴───┴───┸───┘
```
      ''',
            url=f'https://yakkun.com/sv/zukan/n{dexNumber}'
        )
        
        # サムネイル設定
        dexEmbed.set_thumbnail(url=f'{EX_SOURCE_LINK}art/{dexNumber}.png')
        
        # インデックス情報の追加
        aliases = []
        for dexIndex in dexIndexs:
            if not dexIndex == " ":
                aliases.append(str(dexIndex))

        # 別名フィールドを追加
        if aliases:
            dexEmbed.add_field(name="登録済の別名", value=", ".join(aliases), inline=False)
        else:
            dexEmbed.add_field(name="登録済の別名", value="なし", inline=False)

        # 種族値グラフの生成と設定
        bss = [dexH, dexA, dexB, dexC, dexD, dexS]
        graph_path = ub.generate_graph(bss=bss, name=dexName)
        filename = f"basestats_{dexNumber}_{jaconv.kata2alphabet(jaconv.hira2kata(dexName)).lower()}.png"
        attach_graph = discord.File(graph_path, filename=filename)
        dexEmbed.set_image(url=f"attachment://{filename}")
        
        dexEmbed.set_footer(text=f'No.25 ポケモン図鑑 - {dexNumber}')
        
        current_dex_num = float(dexNumber)
        base_dex_num = int(current_dex_num)  # 小数点以下を切り捨てて基本図鑑番号を取得
        prev_dex_num = str(base_dex_num - 1)
        next_dex_num = str(base_dex_num + 1)


        # ナビゲーションボタンを持つViewの作成
        dex_view = discord.ui.View()

        # 同じ基本図鑑番号を持つポケモン（姿違い）を検索
        # 例: 58.0, 58.1 など同じ基本図鑑番号を持つポケモン
        form_pattern = f'^{base_dex_num}(\\.\\d+)?$'
        form_variants = GLOBAL_BRELOOM_DF[
            GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"].str.match(form_pattern)
        ]
        
        # 姿違いの選択肢がある場合はセレクトメニューを用意
        has_variants = len(form_variants) > 1

        # 姿違いセレクトメニューの追加（姿違いがある場合のみ）
        if has_variants:
            # 選択肢の作成
            form_select = discord.ui.Select(
                placeholder="姿違いを選択",
                custom_id=f"dex_form:{base_dex_num}",
                options=[
                    discord.SelectOption(
                        label=row["おなまえ"],
                        value=row["ぜんこくずかんナンバー"],
                        default=row["ぜんこくずかんナンバー"] == dexNumber
                    ) for _, row in form_variants.iterrows()
                ]
            )
            dex_view.add_item(form_select)

        # GLOBAL_BRELOOM_DFから一度のクエリで前後のポケモンを取得
        adjacent_pokemon = GLOBAL_BRELOOM_DF[
            GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"].isin([prev_dex_num, next_dex_num])
        ]

        # 前後のポケモンの存在確認と名前取得
        has_prev = False
        has_next = False
        prev_name = ""
        next_name = ""

        if not adjacent_pokemon.empty:
            for _, row in adjacent_pokemon.iterrows():
                if row["ぜんこくずかんナンバー"] == prev_dex_num:
                    has_prev = True
                    prev_name = row["おなまえ"]
                elif row["ぜんこくずかんナンバー"] == next_dex_num:
                    has_next = True
                    next_name = row["おなまえ"]

        # 前のポケモンへのボタン
        prev_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="◀",
            label=prev_name,
            custom_id=f"dex_prev:{dexNumber}",
            disabled=not has_prev
        )
        dex_view.add_item(prev_button)

        # 次のポケモンへのボタン
        next_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="▶",
            label=next_name,
            custom_id=f"dex_next:{dexNumber}",
            disabled=not has_next
        )
        dex_view.add_item(next_button)
            
        # 新規メッセージか既存メッセージの更新か
        if message is None:
            # 新規メッセージ
            await interaction.response.send_message(files=[attach_graph], embed=dexEmbed, view=dex_view)
        else:
            # 既存メッセージの更新
            try:
                await message.edit(attachments=[attach_graph], embed=dexEmbed, view=dex_view)
            except discord.HTTPException:
                # エラーが発生した場合は新規メッセージとして送信
                channel = message.channel
                await channel.send(files=[attach_graph], embed=dexEmbed, view=dex_view)
    
    else:  # データが存在しない場合は、エラーメッセージを返信
        ub.output_log("404 NotFound")
        if message is None:
            await interaction.response.send_message(embed=ub_embed.error_404(name))
        else:
            await message.edit(embed=ub_embed.error_404(name), attachments=[], view=None)
               
        

@tree.command(name="comp", description="2~6匹のポケモンの種族値を比較します")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(
    pokemon1="1匹目のポケモン",
    pokemon2="2匹目のポケモン",
    pokemon3="3匹目のポケモン (任意)",
    pokemon4="4匹目のポケモン (任意)",
    pokemon5="5匹目のポケモン (任意)",
    pokemon6="6匹目のポケモン (任意)"
)
async def slash_comp(
    interaction: discord.Interaction, 
    pokemon1: str, 
    pokemon2: str, 
    pokemon3: str = None, 
    pokemon4: str = None, 
    pokemon5: str = None, 
    pokemon6: str = None
):
    # まず応答を遅延させる - これによりタイムアウトを防ぐ
    await interaction.response.defer()
    # 入力された全ポケモン名を配列にまとめる
    pokemon_names = [name for name in [pokemon1, pokemon2, pokemon3, pokemon4, pokemon5, pokemon6] if name]
    
    # ログメッセージの作成
    log_message = "ポケモンの種族値を比較します: " + " / ".join(pokemon_names)
    ub.output_log(log_message)
    
    # 各ポケモンのデータとBSSを格納する辞書
    pokemon_data = {}
    dexnum_list = []
    # 全ポケモンのデータ取得
    for name in pokemon_names:
        poke_data = ub.fetch_pokemon(name)
        if poke_data is None:
            ub.output_log(f"404 NotFound: {name}")
            await interaction.followup.send(embed=ub_embed.error_404(name))
            return
        
        poke_name = poke_data.iloc[0]['おなまえ']
        bss = [
            int(poke_data.iloc[0]['HP']),
            int(poke_data.iloc[0]['こうげき']),
            int(poke_data.iloc[0]['ぼうぎょ']),
            int(poke_data.iloc[0]['とくこう']),
            int(poke_data.iloc[0]['とくぼう']),
            int(poke_data.iloc[0]['すばやさ'])
        ]
        
        dexnum = poke_data.iloc[0]['ぜんこくずかんナンバー']
        dexnum_list.append(dexnum)

        pokemon_data[poke_name] = {
            'bss': bss,
            'data': poke_data
        }
    
    # 一時ファイルのパスを用意
    temp_paths = [f"save/temp{i}.png" for i in range(len(pokemon_data))]
    combined_img_path = "save/compared_graph.png"
    
    # 各ポケモンのグラフを生成
    images = []
    for i, (name, data) in enumerate(pokemon_data.items()):
        graph_path = ub.generate_graph(bss=data['bss'], name=name)
        img = Image.open(graph_path)
        img.save(temp_paths[i])
        img.close()
        img = Image.open(temp_paths[i])
        images.append(img)
    
    # 画像の合成方法を決定
    if len(images) <= 3:
        # 3枚以下なら横に並べる
        width = sum(img.width for img in images)
        height = max(img.height for img in images)
        combined_img = Image.new('RGB', (width, height), color=(255, 250, 227))
        x_offset = 0
        for img in images:
            combined_img.paste(img, (x_offset, 0))
            x_offset += img.width
    else:
        # 4-6枚の場合はグリッドレイアウトを使用
        rows = 2
        cols = (len(images) + 1) // 2  # 切り上げの除算で列数を計算
        
        # 1つの画像のサイズを取得
        img_width = images[0].width
        img_height = images[0].height
        
        # 合成画像のサイズを計算
        combined_width = img_width * cols
        combined_height = img_height * rows
        
        # 新しい画像を作成（背景色を設定）
        combined_img = Image.new('RGB', (combined_width, combined_height), color=(255, 250, 227))  # cornsilk色に近い背景色
        
        # 画像を配置
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            x_offset = col * img_width
            y_offset = row * img_height
            combined_img.paste(img, (x_offset, y_offset))
    
    # 画像を閉じる
    for img in images:
        img.close()
    
    # 一時ファイルを削除
    for path in temp_paths:
        os.remove(path)
    
    # 合成画像を保存
    combined_img.save(combined_img_path)
    combined_img.close()
    
    # グラフ画像をdiscordに添付する
    #dexnumでファイル名を指定
    filename=f"compared_{'_'.join(dexnum_list)}.png"
    attach_image = discord.File(combined_img_path, filename=filename)
    
    # Embedの作成
    title_text = " と ".join([f"**{name}**" for name in pokemon_data.keys()])
    embed = discord.Embed(
        title=f"{title_text} の種族値を比較",
        color=0x00BFFF
    )
    
    # 各ポケモンの種族値情報をフィールドとして追加
    for name, data in pokemon_data.items():
        bss = data['bss']
        embed.add_field(
            name=f"{name}",
            value=f"{bss[0]}-{bss[1]}-{bss[2]}-{bss[3]}-{bss[4]}-{bss[5]} 合計{sum(bss)}",
            inline=True
        )
    
    # 合成画像をEmbedに設定
    embed.set_image(url=f"attachment://{filename}")
    embed.set_footer(text=f"{len(pokemon_data)}匹のポケモンを比較")
    
    # メッセージ送信（defer()を使用しているため、followup.sendを使用）
    await interaction.followup.send(
        files=[attach_image],
        embed=embed
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


# おこづかいランキングを表示するコマンド
@tree.command(name="pocketmoney", description="おこづかいの残高照会をします")
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
    attachImage = ub.attachment_file("resource/image/command/mom_johto.png")
    embed = ub_embed.balance(
        userName=interaction.user.name,
        pocketMoney=money,
        numOfPeople=pdwGuild.approximate_member_count,
        userRank=userRank,
        rank_list=ranking_list,
        sendTime=datetime.now(ZoneInfo("Asia/Tokyo")),
        authorPath=attachImage[1],
    )

    await interaction.response.send_message(
        file=attachImage[0], embed=embed, ephemeral=True
    )


@tree.command(name="calltitle", description="参加中の通話のタイトルを設定します")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(title="参加中の通話の内容や目的")
async def slash_calltitle(interaction: discord.Interaction, title: str):
    if interaction.user.voice is not None:
        if await CallPost(interaction.user.voice.channel).title(title):
            await interaction.response.send_message(
                f"タイトルを`{title}`に変更しました", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "通話通知が見つかりませんでした", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "あなたは通話チュウに見えません", ephemeral=True
        )


@tree.command(name="invite", description="このチャンネルにメンバーを招待します")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.describe(member="招待したいメンバー", anonymity="こっそり招待")
async def slash_invite(
    interaction: discord.Interaction, member: discord.Member, anonymity: bool = False
):
    x = discord.Embed(
        title="招待失敗",
        color=0xFF0000,
        description=f"{member.name}に招待を送信できませんでした",
    )
    if not member.bot:
        try:
            attachImage = ub.attachment_file("resource/image/command/invite_mail.png")
            inviteEmbed = discord.Embed(
                title="おさそいメール",
                color=0xFE71E4,
                description=f"**{interaction.channel}** に招待されています!\n`招待を受け取りたくない場合はこのbotをブロックしてください`",
            )
            inviteEmbed.set_author(
                name=f"{interaction.user.name} からの招待" if not anonymity else ""
            )
            inviteEmbed.set_thumbnail(url=attachImage[1])
            inviteEmbed.set_footer(
                text=datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M:%S")
            )
            inviteLink = f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}"
            linkButton = discord.ui.Button(
                label="参加する", style=discord.ButtonStyle.primary, url=inviteLink
            )
            linkView = discord.ui.View()
            linkView.add_item(linkButton)
            await member.send(file=attachImage[0], embed=inviteEmbed, view=linkView)

            x = discord.Embed(
                title="招待成功",
                color=0x51FF2E,
                description=f"{member.name}に招待を送信しました",
            )

        except discord.errors.Forbidden:
            pass
    await interaction.response.send_message(embed=x, ephemeral=anonymity)


# ---------------------------------------------------------------------------------------------------
# 管理者権限が必要なコマンド
@tree.command(name="devtest", description="開発者用テストコマンド")
@discord.app_commands.describe(channel="投稿するチャンネルID")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.default_permissions(administrator=True)
async def slash_devtest(
    interaction: discord.Interaction, channel: discord.TextChannel = None
):
    # テストしたい処理をここに書く
    await interaction.response.send_message(
        f"テストコマンドが実行されました", ephemeral=True
    )


# 使用注意!デバッグモード時のtokenを知っている管理者しか実行できない
@tree.command(name="devcmd", description="開発者用コンソールを呼び出す")
@discord.app_commands.describe(key="キーワード", value="コマンド")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.default_permissions(administrator=True)
async def slash_devcmd(interaction: discord.Interaction, key: str, value: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            f"管理者権限がありません", ephemeral=True
        )
    elif not DEBUG_MODE:
        await interaction.response.send_message(
            f"デバッグモードでのみ使用可能です", ephemeral=True
        )
    elif not key == os.environ.get("DISCORD_TOKEN"):
        await interaction.response.send_message(f"keyが違います", ephemeral=True)
    else:
        ub.output_log(f"コンソールが呼び出されました: {interaction.user.name}")
        ub.output_log(f"cmd: `{value}`")
        try:
            # 文字列にawaitが入っている場合 awaitを取り除きawait evalする
            if value.startswith("await"):
                await eval(value.split("await ")[1])
            else:
                eval(value)
            await interaction.response.send_message(
                f"`{value}`\n実行完了", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"`{value}`\nエラーが発生しました\n```{e}```", ephemeral=True
            )


@tree.command(name="devlogin", description="ログイン投稿をテストします")
@discord.app_commands.describe(channel="投稿するチャンネル")
@discord.app_commands.guilds(*[discord.Object(id=guild_id) for guild_id in GUILD_IDS])
@discord.app_commands.default_permissions(administrator=True)
async def slash_devlogin(
    interaction: discord.Interaction, channel: discord.TextChannel = None
):
    if channel:
        channelid = channel.id
    else:
        channelid = DAIRY_CHANNEL_ID
    await daily_bonus(
        datetime.now(ZoneInfo("Asia/Tokyo")).replace(hour=5, minute=0), channelid
    )
    await interaction.response.send_message(
        f"ログインジョブを実行しました", ephemeral=True
    )


@tree.command(
    name="devimport", description="このサーバーにギルドコマンドをインポートします"
)
@discord.app_commands.default_permissions(administrator=True)
async def slash_devimport(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        if interaction.guild.id in GUILD_IDS:
            await interaction.response.send_message(
                "このサーバーはすでに登録されています", ephemeral=True
            )
        else:
            GUILD_IDS.append(interaction.guild.id)
            with open("config.json", "r", encoding="utf-8") as file:
                config_dict = json.load(file)

            config_dict["DEVELOP_ID_DICT"]["GUILD_IDS"] = GUILD_IDS
            with open("config.json", "w", encoding="utf-8") as file:
                json.dump(config_dict, file, indent=4, ensure_ascii=False)
                await tree.sync(guild=discord.Object(id={interaction.guild.id}))
                await interaction.response.send_message(
                    "このサーバーにギルドコマンドを登録しました", ephemeral=True
                )


# ===================================================================================================
# イベントで発火する処理


# メッセージの送受信を観測したときの処理
@client.event
async def on_message(message):
    global BAKUSOKU_MODE
    global BQ_FILTER_DICT
    global BQ_FILTERED_DF
    if message.author.bot:  # メッセージ送信者がBotだった場合は無視する
        return

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

    # bot自身へのリプライ(reference)に反応
    elif message.reference is not None:
        # リプライ先メッセージのキャッシュを取得
        message.reference.resolved = await message.channel.fetch_message(
            message.reference.message_id
        )

        # bot自身へのリプライに反応
        if message.reference.resolved.author == client.user:
                embedFooterText = message.reference.resolved.embeds[0].footer.text
                # リプライ先にembedが含まれるかつ未回答のクイズの投稿か
                if (
                    "No.26 ポケモンクイズ" in embedFooterText
                    and not "(done)" in embedFooterText
                ):
                    await quiz(embedFooterText.split()[3]).try_response(message)

                else:
                    ub.output_log("botへのリプライは無視されました")


    #チャンネルのidがQUIZ_CHANNEL_IDの場合
    elif message.channel.id == QUIZ_CHANNEL_ID:
        #メッセージの内容がポケモン名であるか判定
        if ub.fetch_pokemon(message.content) is not None:
            #一番新しいクイズの投稿を探し,未回答の場合は
            async for quizMessage in message.channel.history(limit=10):
                if quizMessage.embeds:
                    embedFooterText = quizMessage.embeds[0].footer.text
                    if (
                    "No.26 ポケモンクイズ - bq" in embedFooterText
                    and not "(done)" in embedFooterText
                    ):
                        #メッセージをリプライに偽装する quizクラスの内容を修正すべき
                        message.reference=discord.MessageReference(
                            message_id=quizMessage.id,
                            channel_id=quizMessage.channel.id,
                            guild_id=quizMessage.guild.id,
                            #resolved=message
                        )
                        message.reference.resolved = quizMessage
                        await quiz(embedFooterText.split()[3]).try_response(message)
                        break
            if not quizMessage.embeds:
                ub.output_log("ポケモン名が投稿されましたがクイズ投稿が見つかりませんでした")


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
                ub.output_log(
                    f"登録の修正を受け付けました\n {member.name}: {studentId}"
                )
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
    #ボタン
    elif (
        "component_type" in interaction.data and interaction.data["component_type"] == 2
    ):
        ub.output_log(
            f'buttonが押されました\n {interaction.user.name}: {interaction.data["custom_id"]}'
        )
        await on_button_click(interaction)

    #セレクトメニュー    
    elif "component_type" in interaction.data and interaction.data["component_type"] == 3:
        custom_id = interaction.data[
            "custom_id"
        ]  # custom_id(インタラクションの識別子)を取り出す
        if custom_id.startswith("dex_form:"):
            base_dex_num = custom_id.split(":")[1]
            selected_form = interaction.data["values"][0]  # 選択された姿違いの図鑑番号
            
            # 選択された姿違いのポケモンデータを取得
            form_data = GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] == selected_form]
            
            if not form_data.empty:
                selected_name = form_data.iloc[0]["おなまえ"]
                
                # 応答を延期
                await interaction.response.defer()
                
                # 共通関数を使用して表示
                await display_pokedex(interaction, selected_name, interaction.message)
            else:
                await interaction.response.send_message("該当するポケモンが見つかりませんでした", ephemeral=True)


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

    elif custom_id.startswith("lotoIdButton"):  # IDくじボタン
        ub.output_log("IDくじを実行します")
        # カスタムIDは,"lotoIdButton:00000:0000/00/00"という形式
        lotoId = custom_id.split(":")[1]
        birth = custom_id.split(":")[2]
        now = datetime.now(ZoneInfo("Asia/Tokyo"))
        today = now.date()
        if now.hour < 5:
            today = today - timedelta(days=1)

        if not birth == str(today):
            # 過去に投稿されたくじの場合
            await interaction.response.send_message(
                f"それは 今日のIDくじ じゃないロ{EXCLAMATION_ICON}", ephemeral=True
            )
        elif ub.report(interaction.user.id, "クジびきけん", 0) == 0:
            # すでにくじを引いている場合
            await interaction.response.send_message(
                "くじが ひけるのは 1日1回 まで なんだロ……", ephemeral=True
            )
        else:
            userId = str(interaction.user.id)[-6:].zfill(5)  # ID下6ケタを取得

            matchCount = 0
            for i in range(1, 6):
                if userId[-i] == lotoId[-i]:
                    matchCount += 1
                else:
                    break

            matchCount = str(matchCount)
            prize = PRIZE_DICT[matchCount]["prize"]
            value = PRIZE_DICT[matchCount]["value"]
            text = PRIZE_DICT[matchCount]["text"]
            place = PRIZE_DICT[matchCount]["place"]

            pocketMoney = ub.report(interaction.user.id, "おこづかい", value)

            dialogText = f"\n"

            try:
                # おこづかいランキングを確認し,1位になっていた場合ロールを付与する
                df = pd.read_csv(REPORT_PATH, dtype={"ユーザーID": str})
                user_wallet = df[["ユーザーID", "おこづかい"]]
                user_wallet_sorted = user_wallet.sort_values(
                    by="おこづかい", ascending=False
                ).reset_index(drop=True)

                if pocketMoney == user_wallet_sorted.loc[0, "おこづかい"]:
                    dialogText = f"ロロ{EXCLAMATION_ICON}{interaction.guild.name}で いちばんの おかねもち だロト{EXCLAMATION_ICON}\n"
                    # おかねもちロール付与の処理
                    menymoneyRole = interaction.user.guild.get_role(MENYMONEY_ROLE_ID)
                    if menymoneyRole not in interaction.user.roles:
                        ub.output_log(
                            f"おこづかい一位が変わりました: {interaction.user.name}"
                        )
                        await interaction.user.add_roles(menymoneyRole)
                        ub.output_log(
                            f"ロールを付与しました: {interaction.user.name}に{menymoneyRole.name}"
                        )

                    # 2位以下のおかねもちロールを剥奪する処理
                    for i in range(0, len(user_wallet_sorted)):
                        lowerUser = interaction.guild.get_member(
                            int(user_wallet_sorted.loc[i, "ユーザーID"])
                        )
                        # インタラクションユーザーには実施しない
                        if lowerUser and not interaction.user == lowerUser:
                            if pocketMoney > user_wallet_sorted.loc[i, "おこづかい"]:
                                if menymoneyRole in lowerUser.roles:
                                    await lowerUser.remove_roles(menymoneyRole)
                                    ub.output_log(
                                        f"ロールを剥奪しました: {lowerUser.name}から{menymoneyRole.name}"
                                    )
                                else:
                                    break

            except Exception as e:
                ub.output_log(f"おこづかいランキングの処理でエラーが発生しました\n{e}")

            attachImage = ub.attachment_file(f"resource/image/prize/{prize}.png")
            lotoEmbed = discord.Embed(
                title=text,
                color=0xFF99C2,
                description=f"{place}の 商品 **{prize}**をプレゼントだロ{BANGBANG_ICON}\n"
                f"{dialogText}"
                f"それじゃあ またの 挑戦を お待ちしてるロ~~{EXCLAMATION_ICON}",
            )
            lotoEmbed.set_thumbnail(url=attachImage[1])
            lotoEmbed.add_field(
                name=f"{interaction.user.name}は {prize}を 手に入れた!",
                value=f"売却価格: {value}えん\nおこづかい: {pocketMoney}えん",
                inline=False,
            )
            lotoEmbed.set_author(name=f"あなたのID: {userId}")
            lotoEmbed.set_footer(text="No.15 IDくじ")

            ub.report(interaction.user.id, "クジびきけん", -1)  # クジの回数を減らす
            await interaction.response.send_message(
                file=attachImage[0], embed=lotoEmbed, ephemeral=True
            )

    # ポケモン図鑑のナビゲーションボタン処理
    elif custom_id.startswith("dex_prev:") or custom_id.startswith("dex_next:"):
        current_number = custom_id.split(":")[1]
        
        if custom_id.startswith("dex_prev:"):
            # 前のポケモンを表示
            target_number = str(int(float(current_number)) - 1)
        else:
            # 次のポケモンを表示
            target_number = str(int(float(current_number)) + 1)
        
        # 目的のポケモンデータを取得
        target_data = GLOBAL_BRELOOM_DF[GLOBAL_BRELOOM_DF["ぜんこくずかんナンバー"] == target_number]
        
        if len(target_data) > 0:
            target_name = target_data.iloc[0]["おなまえ"]
            
            # 応答を延期
            await interaction.response.defer()
            
            # 共通関数を使用して表示
            await display_pokedex(interaction, target_name, interaction.message)
        else:
            await interaction.response.send_message("該当するポケモンが見つかりませんでした", ephemeral=True)


# ボイスチャンネルへの参加・退出を検知
@client.event
async def on_voice_state_update(member, before, after):
    time = datetime.now(ZoneInfo("Asia/Tokyo"))

    if os.path.exists(CALLDATA_PATH):
        call_df = pd.read_csv(CALLDATA_PATH, dtype={"累計参加メンバー": str})
    else:
        call_df = pd.DataFrame(
            columns=[
                "チャンネルID",
                "メッセージID",
                "通話開始",
                "タイトル",
                "名前読み上げ",
                "累計参加メンバー",
            ]
        )
    call_df.set_index("チャンネルID", inplace=True)

    if after.channel:
        if member.bot:
            return
        # ボイスチャンネルにメンバーが入室
        callch = after.channel
        if after.channel.type == discord.ChannelType.voice:
            ub.output_log(f"ボイスチャンネル参加\n {callch.name}: {member.name}")
            if len(after.channel.members) == 1:  # 入室時ひとりなら
                if before.channel and len(before.channel.members) == 1:
                    return
                await asyncio.sleep(5)  # 5秒後に通話開始処理
                if len(callch.members) > 0:
                    member = callch.members[0]
                    await CallPost(callch).start(member, time)

                    if (
                        not member.voice or not member.voice.channel == callch
                    ):  # 参加したメンバーがいなくなっていたら
                        ub.output_log("参加したメンバーが退出しています")
                        return
                else:
                    ub.output_log(
                        f"通話は開始されませんでした\n {callch.name}: {member.name}"
                    )
                    return
            else:
                if not callch.id in call_df.index:
                    await asyncio.sleep(5)
                    call_df = pd.read_csv(
                        CALLDATA_PATH, dtype={"累計参加メンバー": str}
                    ).set_index(
                        "チャンネルID"
                    )  # 更新する

                if callch.id in call_df.index and str(member.id) not in call_df.loc[
                    callch.id, "累計参加メンバー"
                ].split(" "):
                    call_df.loc[callch.id, "累計参加メンバー"] += f" {member.id}"
                    call_df.to_csv(CALLDATA_PATH)

            kinouoff = """
      if callch.id in call_df.index and call_df.loc[callch.id, '名前読み上げ']:
          joinMemberMessage=f"{member.name}さんが参加"
      await callch.send(joinMemberMessage,embed=discord.Embed(title=f"{member.name}さんが 参加しました",color=0xff8e8e).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
      ub.output_log(f"ボイスチャンネル参加\n {callch.name}: {member.name}")
      """

    if before.channel:
        # ボイスチャンネルからメンバーが退室
        if before.channel.type == discord.ChannelType.voice:
            ub.output_log(
                f"ボイスチャンネル退出\n {before.channel.name}: {member.name}"
            )

            kinouoff = """
      if before.channel.id in call_df.index:
        quitMemberMessage=""
        if call_df.loc[before.channel.id,'名前読み上げ']:
          quitMemberMessage=f"{member.name}さんが退出"
        await before.channel.send(quitMemberMessage,embed=discord.Embed(title=f"{member.name}さんが 退出しました",color=0x8e8eff).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
      else:
        await before.channel.send(embed=discord.Embed(title=f"{member.name}さんが 退出しました",color=0x8e8eff).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")))
      """
            if len(before.channel.members) == 0:  # ボイスチャンネルに人がいなくなったら
                await CallPost(before.channel).stop(time)


# ===================================================================================================
# オブジェクト


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
            isMessage = isinstance(self.rm, discord.Message)
            if isMessage:
                await self.rm.add_reaction("⭕")
            result = await self.__disclose(True, fixAns)
            # リアクションは結果に基づいて付ける
            if isMessage and result == 1:
                await self.rm.remove_reaction("⭕", client.user)
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

        if QUIZ_PROCESSING_FLAG == 1:
            ub.output_log(f"{self.quizName}: 応答処理実行中につき処理を中断")
            return 1
        
        QUIZ_PROCESSING_FLAG = 1  # 回答開示処理を始める
        ub.output_log(f"{self.quizName}: 回答開示を実行")
        

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


        # 処理前に最新のメッセージ状態を取得して確認
        try:
            # メッセージを再取得して最新の状態を確認
            updated_message = await self.qm.channel.fetch_message(self.qm.id)
            ub.output_log(f"クイズのフッター:{updated_message.embeds[0].footer.text}")
            if updated_message.embeds and "(done)" in updated_message.embeds[0].footer.text:
                ub.output_log("クイズの処理中にクイズが終了しています")
                QUIZ_PROCESSING_FLAG = 0  # 回答開示処理を終わる
                return 1  # 処理中断（失敗）を示す値
        except Exception as e:
            ub.output_log(f"メッセージ取得中にエラー: {e}")
            # エラーがあっても処理継続

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
        
        return 0 

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


class CallPost:  # await CallPost(*,discord.channel,channelID).start(member,time) /.stop(member,time) /.title(title)
    def __init__(self, channel, sendChannelId: int = None):
        self.channel = channel
        if sendChannelId is None:
            if self.channel.permissions_for(
                channel.guild.default_role
            ).view_channel:  # プライベートなら送信先を変更:
                sendChannelId = CALLSTATUS_CHANNEL_ID
            else:
                sendChannelId = DEBUG_CHANNEL_ID
        self.sendChannel = client.get_channel(sendChannelId)
        self.message = None

        if self.channel.type == discord.ChannelType.stage_voice:
            self.chType = "放送"
        else:
            self.chType = "通話"

        if os.path.exists(CALLDATA_PATH):
            self.call_df = pd.read_csv(
                CALLDATA_PATH, dtype={"累計参加メンバー": str}
            ).set_index("チャンネルID",drop=False)
        else:
            self.call_df = pd.DataFrame(
                columns=[
                    "チャンネルID",
                    "メッセージID",
                    "通話開始",
                    "タイトル",
                    "名前読み上げ",
                    "累計参加メンバー",
                ]
            ).set_index("チャンネルID",drop=False)

    async def start(
        self, member, time: datetime = datetime.now(ZoneInfo("Asia/Tokyo"))
    ):
        defaultTitle = "設定無し"
        if self.chType == "放送":
            embedColor = 0xA7FF8F
        else:
            embedColor = 0xFF8E8E

        attachedImage = ub.attachment_file("resource/image/command/start_call.gif")
        startEmbed = discord.Embed(title=f"{self.chType}開始", color=embedColor)
        startEmbed.set_author(
            name=f"{member.name} さん", icon_url=member.display_avatar.url
        )
        startEmbed.set_thumbnail(url=attachedImage[1])
        startEmbed.add_field(name="タイトル", value=f"`{defaultTitle}`", inline=False)
        startEmbed.add_field(
            name="チャンネル", value=self.channel.mention, inline=False
        )
        startEmbed.add_field(
            name=f"{self.chType}開始",
            value=f'```{time.strftime("%Y/%m/%d")}\n{time.strftime("%H:%M:%S")}```',
            inline=True,
        )

        startMessage = await self.sendChannel.send(
            file=attachedImage[0], embed=startEmbed
        )

        #FutureWarning: In a future version, object-dtype columns with all-bool values will not be included in reductions with bool_only=True. Explicitly cast to bool dtype instead. 
        newBusyData = pd.DataFrame(
            data=[[self.channel.id,startMessage.id,time.strftime("%Y/%m/%d %H:%M:%S"),defaultTitle,False,member.id]],
            index=[self.channel.id],
            columns=["チャンネルID","メッセージID","通話開始","タイトル","名前読み上げ","累計参加メンバー"]
        ).astype({"名前読み上げ":bool})
        if self.channel.id not in self.call_df.index:
            # appendは使用しない AttributeError: 'DataFrame' object has no attribute 'append'
            self.call_df = pd.concat([self.call_df, newBusyData])

        else:
            self.call_df.loc[self.channel.id] = newBusyData
            #self.call_df[self.call_df[self.channel.id]] = newBusyData
            ub.output_log("通話キャッシュを更新しました")

        self.call_df.to_csv(CALLDATA_PATH,index=False)

        await self.channel.send(
            embed=discord.Embed(
                title="通話開始",
                description="`/calltitle` 通話目的を変更できます\n`/invite` メンバーを招待できます",
                color=embedColor,
            ).set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S")),
        )
        ub.output_log(
            f"{self.chType}が開始されました\n {self.channel.name}: {member.name}"
        )

    async def title(self, newTitle: str):
        if not await self.__load():
            return False

        self.message.embeds[0].set_field_at(0, name="タイトル", value=f"`{newTitle}`")

        oldTitle = self.call_df.loc[self.channel.id, "タイトル"]
        self.call_df.loc[self.channel.id, "タイトル"] = newTitle
        self.call_df.to_csv(CALLDATA_PATH)

        await self.message.edit(
            embed=self.message.embeds[0], attachments=self.message.attachments
        )
        ub.output_log(
            f"通話タイトルを更新しました\n{self.channel.name}: [{oldTitle} > {newTitle}]"
        )
        return True

    async def stop(self, time: datetime = datetime.now(ZoneInfo("Asia/Tokyo"))):
        if not await self.__load():
            return False
        if self.chType == "放送":
            embedColor = 0x8FFFF8
        else:
            embedColor = 0x8E8EFF

        diff = (
            time.replace(tzinfo=None)
            - pd.to_datetime(
                self.call_df.loc[self.channel.id, "通話開始"],
                format="%Y/%m/%d %H:%M:%S",
            )
        ).total_seconds()
        hours = int(diff // 3600)
        minutes = int((diff % 3600) // 60)
        seconds = int(diff % 60)
        attachImage = ub.attachment_file("resource/image/command/stop_call.gif")

        stopEmbed = self.message.embeds[0]
        stopEmbed.title = (
            f'{self.chType}終了・{f"{hours}時間 " if hours>0 else " "}{minutes}分'
        )
        stopEmbed.color = embedColor
        stopEmbed.set_thumbnail(url=attachImage[1])
        stopEmbed.set_footer(
            text=f'Total Visitors: {len(self.call_df.loc[self.channel.id,"累計参加メンバー"].split(" "))}'
        )
        stopEmbed.add_field(
            name=f"{self.chType}終了",
            value=f'```{time.strftime("%Y/%m/%d")}\n{time.strftime("%H:%M:%S")}```',
            inline=True,
        )

        await self.message.edit(embed=stopEmbed, attachments=[attachImage[0]])

        self.call_df.drop(self.channel.id).to_csv(CALLDATA_PATH, index=True)

        visitor_ids = self.call_df.loc[self.channel.id, "累計参加メンバー"].split(" ")
        visitor_names = []
        for visitor_id in visitor_ids:
            visitor = await client.fetch_user(visitor_id)
            visitor_names.append(visitor.name)
        visitors = " ".join(visitor_names)

        if os.path.exists(CALLLOG_PATH):
            log_df = pd.read_csv(CALLLOG_PATH)
        else:
            log_df = pd.DataFrame(
                columns=[
                    "通話開始",
                    "通話終了",
                    "通話時間",
                    "タイトル",
                    "チャンネル",
                    "参加メンバー",
                ]
            )

        newLog = pd.DataFrame(
            {
                "通話開始": self.call_df.loc[self.channel.id, "通話開始"],
                "通話終了": time.strftime("%Y/%m/%d %H:%M:%S"),
                "通話時間": f"{hours:02}:{minutes:02}:{seconds:02}",
                "タイトル": self.call_df.loc[self.channel.id, "タイトル"],
                "チャンネル": self.channel.name,
                "参加メンバー": visitors,
            },
            index=[0],
        )
        # log_df = pd.concat([log_df.iloc[:1], newLog, log_df.iloc[1:]], ignore_index=True)
        log_df = pd.concat([newLog, log_df], ignore_index=True)
        log_df.to_csv(CALLLOG_PATH, mode="w", header=True, index=False)

        embed = discord.Embed(title=f"{self.chType}終了", color=embedColor)
        embed.set_footer(text=time.strftime("%Y/%m/%d %H:%M:%S"))

        await self.channel.send(embed=embed)
        ub.output_log(
            f"{self.chType}が終了しました\n {self.channel.name}: {visitor_names[-1]}"
        )
        return True

    async def __load(self):
        #"チャンネルID"列に指定のチャンネルIDがあるか確認 (indexではない)
        if self.channel.id in self.call_df.index:
            try:
                self.message = await self.sendChannel.fetch_message(
                    #指定の"チャンネルID"の"メッセージID"を取得
                    self.call_df.loc[self.channel.id, "メッセージID"]
                )
            except discord.NotFound:
                ub.output_log("ERROR: 指定のメッセージが見つかりませんでした")
                return False
        else:
            ub.output_log("ERROR: 指定チャンネルの通話記録がありません")
            return False
        return True


# ===================================================================================================
# トークンの取得とBOTの起動

load_dotenv(override=True)
client.run(os.environ.get("DISCORD_TOKEN"), reconnect=True)
