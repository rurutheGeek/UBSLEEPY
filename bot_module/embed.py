# -*- coding: utf-8 -*-
import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .config import *
import json
#bot_module/func.pyをas ubでインポート
import bot_module.func as ub

ERROR_COLOR = 0xFF0000


def balance(userName: str, pocketMoney: int,numOfPeople:int,userRank: int,rank_list: list = [], sendTime: datetime = None,authorPath: str="") -> discord.Embed:
    '''残高照会Embedを生成する
    Parameters:
    ----------
        name : str
            ユーザー名
        pocketMoney : int
            おこづかい残高
        numOfPeople : int
            ユーザー数
        rank : int
            ユーザーの順位
        rank_list : list
            ユーザーランキングリスト
        sendTime : datetime
            メッセージ送信時刻
        authorPath : str
            アイコン画像パス
    '''
    embed = discord.Embed(
        title="おこづかい銀行",
        color=0x00FF00,
        description=f"``` {userName} おかえりなさい! しっかり やってる みたいね ```\n"\
            f"{BALL_ICON}**あずけている きんがく    {pocketMoney}円**\n\n　"\
    )
    rankMsg=""
    for i in range(0, 5):
        id=rank_list[i][0]
        money=rank_list[i][1]
        rank=rank_list[i][2]
        rankMsg+=f"#{rank:.0f}  I <@!{id}> "
        rankMsg+='\N{Military Medal}' if rank == 1 else ''
        rankMsg+=f"`{money}円`\n"

    embed.add_field(name=f"おこづかいランキング ({sendTime.strftime('%Y/%m/%d %H:%M:%S')}現在)", value=rankMsg+f"\nあなたの順位: {numOfPeople}人中 {userRank}位\n", inline=False)
    embed.add_field(name="",value="``` たいせつに あずかっておくから あなたも しっかりね! ```", inline=False)
    if authorPath:
        embed.set_author(name="おかあさん",
            icon_url=authorPath
        )
    embed.set_footer(text="No.x おこづかい銀行")
    return embed

def welcome(name: str, url: str) -> discord.Embed:
    embed = discord.Embed(
        title="メンバー認証ボタンを押して 学籍番号を送信してね",
        color=0x5EFF24,
        description="送信するとサーバーが使用可能になります\n工学院大学の学生でない人は個別にご相談ください",
    )
    embed.set_author(name=f"{name}の せかいへ ようこそ!")
    embed.add_field(
        name="サーバーの ガイドラインは こちら",
        value=f"{BALL_ICON}<#{GUIDELINE_CHANNEL_ID}>",
        inline=False,
    )
    embed.add_field(
        name="みんなにみせるロールを 変更する",
        value=f"{BALL_ICON}<#{REACTIONROLE_CHANNEL_ID}>",
        inline=False,
    )
    embed.set_author(url=url)

    return embed


def invite(
    channel: discord.abc.GuildChannel,
    sendTime: datetime = None,
    anonymity: bool = True,
    name: str = None,
) -> discord.Embed:
    if sendTime is None:
        sendTime = datetime.now(ZoneInfo("Asia/Tokyo"))

    embed = discord.Embed(
        title="おさそいメール",
        color=0xFE71E4,
        description=f"**{channel}** に招待されています!\n`招待を受け取りたくない場合はこのbotをブロックしてください`",
    )
    embed.set_author(name=f"{name} からの招待" if not anonymity else "")
    embed.set_thumbnail(url=f"{EX_SOURCE_LINK}icon/RSVP_Mail.png")
    embed.set_footer(text=sendTime.strftime("%Y/%m/%d %H:%M:%S"))

    return embed


def error_401(inputId: int) -> discord.Embed:
    embed = discord.Embed(
        title="401 Unauthorized",
        color=ERROR_COLOR,
        description=f"あなたの入力した学籍番号: **{inputId}**\n申し訳ございませんが、もういちどお試しください。",
    )
    embed.set_author(
        name="Porygon-Z.com",
        url="https://wiki.ポケモン.com/wiki/ポリゴンZ",
    )
    embed.set_thumbnail(url=f"{EX_SOURCE_LINK}art/474.png")
    embed.add_field(name="入力形式は合っていますか?", value="半角英数字7ケタで入力してください", inline=False)
    embed.add_field(name="工学院生ではありませんか?", value="個別にご相談ください", inline=False)
    embed.add_field(
        name="解決しない場合", value=f"管理者にお問い合わせください: <@!{DEVELOPER_USER_ID}>", inline=False
    )

    return embed


def error_404(name: str) -> discord.Embed:
    # JSONファイルを読み込みます
    with open("document/error_embeds.json", "r", encoding="utf-8") as template_file:
        template_data = json.load(template_file)

    error_data = template_data["error_404"]
    
    # テンプレート内の変数 {name} を実際の値に置換
    error_data["description"] = error_data["description"].format(name=name)
    error_data["thumbnail"]["url"] = error_data["thumbnail"]["url"].format(EX_SOURCE_LINK=EX_SOURCE_LINK)
    
    # discord.Embedのfrom_dictメソッドを使用してEmbedを生成
    embed = discord.Embed.from_dict(error_data)

    return embed


"""テスト中につきコメントアウト
def error_404(name: str) -> discord.Embed:
    embed = discord.Embed(
        title="404 NotFound",
        color=ERROR_COLOR,
        description=f"The requested {name} was not found on this world",
    )
    embed.set_author(
        name='Wanaider.com',
        url="https://wiki.ポケモン.com/wiki/ワナイダー",
    )
    embed.set_thumbnail(url=f"{EX_SOURCE_LINK}art/918.png")
    embed.add_field(name="表記揺れ?", value="別表記を試す")
    embed.add_field(name="不具合?", value="全体チャットで報告")
    
    return embed"""


def error_502() -> discord.Embed:
    embed = discord.Embed(
        title="502 Bad Gateway",
        color=ERROR_COLOR,
        description="nginx",
    )
    embed.set_author(
        name="Strinder.com",
        url="https://wiki.ポケモン.com/wiki/ストリンダー",
    )
    embed.set_thumbnail(url=f"{EX_SOURCE_LINK}art/849.1.png")
    embed.add_field(name="Receiver is not on stage.", value="ステージチャンネルにいるメンバーを指定してください")

    return embed


def error_403(name: str) -> discord.Embed:
    embed = discord.Embed(
        title="403 Fobbidon",
        color=ERROR_COLOR,
        description=f"You don’t have permission to access / {name} on this server",
    )
    embed.set_author(name="Porygon-Z.com", url="https://wiki.ポケモン.com/wiki/ポリゴンZ")
    embed.set_thumbnail(url=f"{EX_SOURCE_LINK}art/474.png")
    embed.add_field(name="You are not Host", value="ホスト以外はジョウトできません")

    return embed
