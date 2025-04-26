# -*- coding: utf-8 -*-
# func.py
from .config import *
import re
import discord
import numpy as np
from .func import output_log, bss_to_text

async def show_search_ui(interaction: discord.Interaction):
    """検索条件入力用のUIを表示する"""
    searcher = PokemonSearcher()
    
    # 検索UI用のEmbed
    search_embed = discord.Embed(
        title="ポケモンサーチャー",
        description="下のメニューから検索条件を選択するか、テキスト入力フィールドに直接検索条件を入力してください。",
        color=0x00FF7F
    )
    search_embed.set_footer(text="No.27 ポケモンサーチャー")

    # クエリフィールドを追加（ここに選択内容が表示される）
    search_embed.add_field(
        name="現在の検索条件",
        value="```\n(なし)\n```",
        inline=False
    )
    
    search_embed.add_field(
        name="検索条件の入力方法",
        value="**タイプ**: タイプ名を入力（例: みず）\n"
              "**特性**: 特性名を入力（例: ふゆう）\n"
              "**世代**: 世代の数字を入力（例: 8）\n"
              "**比較演算子**: 種族値の条件指定（H/A/B/C/D/S）\n"
              "- `H>=100` `A>150` `S<=80` `D=90`\n"
              "**等値演算子**: 種族値同士の比較\n"
              "- `A==C` `A+100==C` `H==B==D`\n"
              "**算術演算子**: 種族値を使った計算式\n"
              "- `H+S>=200` `(H*B*D)/(B+D)<26825`\n"
              "**進化段階**: 「最終進化」「進化しない」など\n"
              "**地方**: 「ジョウト」「ホウエン」など\n"
              "```\n/search query: かくとう テクニシャン 3 A>=130 S>=70 最終進化\n```",
        inline=False
    )
   
    # 検索UIビューを作成
    search_view = discord.ui.View(timeout=None)
    
    # コンポーネントを取得して追加
    components = searcher.create_search_ui_components()
    for component in components.values():
        search_view.add_item(component)
    
    # UIを表示
    await interaction.response.send_message(
        embed=search_embed,
        view=search_view,
        ephemeral=True  # ユーザーだけに表示
    )

async def perform_search(interaction: discord.Interaction, filter_words):
    """ポケモン検索を実行し結果を表示する"""
    # 応答を遅延
    await interaction.response.defer()

    # 検索クラスのインスタンス化
    searcher = PokemonSearcher()
    
    # 検索の実行
    filter_dict = searcher.make_filter_dict(filter_words)
    searched_df, _ = searcher.search(filter_dict)
    
    if len(searcher.current_results) > 0:
        # 検索結果がある場合
        # Embedの生成
        search_embed = searcher.create_search_embed(0, filter_words)
        
        # ページネーションが必要かどうか
        if len(searcher.current_results) > 10:
            # ビューの生成
            nav_view = searcher.create_pagination_view(0)
            await interaction.followup.send(embed=search_embed, view=nav_view)
        else:
            await interaction.followup.send(embed=search_embed)
    else:
        # 検索結果が0件の場合
        no_result_embed = discord.Embed(
            title="検索結果なし",
            description=f"条件「{' '.join(filter_words)}」に一致するポケモンは見つかりませんでした。",
            color=0xFF0000
        )
        await interaction.followup.send(embed=no_result_embed)

async def handle_search_button(interaction, button_id):
    """検索関連ボタンの処理を行う"""
    if button_id == "search_execute_button":
        # 検索実行
        embed = interaction.message.embeds[0]
        query_field = embed.fields[0]
        query_text = query_field.value.strip("```\n")
        
        if query_text == "" or query_text == "(なし)":
            await interaction.response.send_message(
                "検索条件が指定されていません。タイプや世代などを選択してください。",
                ephemeral=True
            )
            return
        
        filter_words = query_text.split()
        await perform_search(interaction, filter_words)
        
    elif button_id == "search_reset_button":
        # 条件リセット
        embed = interaction.message.embeds[0]
        embed.set_field_at(
            0,
            name="現在の検索条件",
            value="```\n(なし)\n```",
            inline=False
        )
        await interaction.response.edit_message(embed=embed)
        
    elif button_id == "search_modal_button":
        # 検索モーダル表示
        embed = interaction.message.embeds[0]
        current_query = embed.fields[0].value.strip("```\n")
        if current_query == "(なし)":
            current_query = ""
        
        search_modal = discord.ui.Modal(title="検索条件の入力", custom_id="search_modal")
        search_input = discord.ui.TextInput(
            label="検索条件を入力",
            placeholder="例: みず はがね ふゆう 8",
            style=discord.TextStyle.paragraph,
            default=current_query,
            custom_id="search_input",
            required=True
        )
        search_modal.add_item(search_input)
        await interaction.response.send_modal(search_modal)
        
    elif button_id == "search_new_button":
        # 新しい検索UI表示
        await show_search_ui(interaction)

async def handle_search_select_menu(interaction, custom_id, values):
    """検索選択メニューの処理を行う"""
    # 現在のEmbedを取得
    embed = interaction.message.embeds[0]
    current_query_field = embed.fields[0]
    
    # 現在のクエリ内容を取得
    current_query = current_query_field.value.strip("```\n")
    if current_query == "(なし)":
        current_query = ""
    
    # 選択内容をクエリに追加
    new_query = current_query
    
    # 選択メニューのタイプに応じた処理
    if custom_id == "search_type_select":
        for type_name in values:
            if type_name not in new_query.split():
                new_query += f" {type_name}"
        output_log(f"ユーザー {interaction.user.name} がタイプ {values} を選択しました")
    
    elif custom_id == "search_gen_select" and values:
        # 世代は数字のみで指定
        selected_gen = values[0]
        if selected_gen not in new_query.split():
            new_query += f" {selected_gen}"
        output_log(f"ユーザー {interaction.user.name} が世代 {selected_gen} を選択しました")
    
    elif custom_id == "search_evo_select" and values:
        selected_evo = values[0]
        if selected_evo not in new_query.split():
            new_query += f" {selected_evo}"
        output_log(f"ユーザー {interaction.user.name} が進化段階 {selected_evo} を選択しました")
    
    # 空白を整理してクエリを更新
    new_query = new_query.strip()
    if not new_query:
        new_query = "(なし)"
    
    # Embedを更新
    embed.set_field_at(
        0,
        name="現在の検索条件",
        value=f"```\n{new_query}\n```",
        inline=False
    )
    
    # メッセージを更新
    await interaction.response.edit_message(embed=embed)

async def handle_pagination(interaction, current_page, direction, total_results, filter_words):
    """ページネーションを処理する関数"""
    # 検索クラスのインスタンス化
    searcher = PokemonSearcher()
    
    # 次のページ番号を計算
    if direction == "prev":
        next_page = max(0, current_page - 1)
    else:  # "next"
        next_page = current_page + 1
    
    # 応答を遅延
    await interaction.response.defer()
    
    # 検索の実行
    filter_dict = searcher.make_filter_dict(filter_words)
    searcher.search(filter_dict)
    
    # Embedの生成
    search_embed = searcher.create_search_embed(next_page, filter_words)
    
    # ページネーションボタンの生成
    nav_view = searcher.create_pagination_view(next_page)
    
    # メッセージを更新
    await interaction.followup.edit_message(
        message_id=interaction.message.id,
        embed=search_embed,
        view=nav_view
    )


class PokemonSearcher:
    """ポケモン検索機能を管理するクラス"""
    
    def __init__(self, database=None):
        """初期化メソッド
        
        Parameters:
        ----------
        database : pandas.DataFrame, optional
            検索対象のデータベース（デフォルト: GLOBAL_BRELOOM_DF）
        """
        self.database = database or GLOBAL_BRELOOM_DF
        self.current_filter = {}  # 現在の検索フィルタ
        self.current_results = []  # 現在の検索結果
        self.processed_conditions = {}  # 処理済み検索条件
        
    def make_filter_dict(self, filter_words):
        """検索条件をフィルタ辞書に変換
        
        Parameters:
        ----------
        filter_words : list
            検索条件のリスト
            
        Returns:
        ----------
        dict
            フィルタ辞書
        """
        output_log("以下の項目でフィルタ辞書を生成します\n " + str(filter_words))
        
        new_dict = {}
        # 小文字も大文字も認識できるようにキーのセットを拡張
        stats_keys = set(BASE_STATS_DICT.keys()).union({k.lower() for k in BASE_STATS_DICT.keys()})
        
        for i in range(len(filter_words)):
            # 合計値の検出（例: 合計<550）
            if filter_words[i].startswith('合計') and any(op in filter_words[i] for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in new_dict:
                    new_dict['STAT_EXPRESSION'] = []
                new_dict['STAT_EXPRESSION'].append(filter_words[i])
                continue
            
            # 複雑な式や種族値条件の検出
            first_char_upper = filter_words[i][0].upper() if filter_words[i] else ''
            if first_char_upper in BASE_STATS_DICT or '(' in filter_words[i]:
                if any(op in filter_words[i] for op in ['>', '<', '=']):
                    if 'STAT_EXPRESSION' not in new_dict:
                        new_dict['STAT_EXPRESSION'] = []
                    new_dict['STAT_EXPRESSION'].append(filter_words[i])
                    continue
            
            # 既存の処理
            if filter_words[i] in self.database['進化段階'].unique().tolist():
                dictIndex = '進化段階'
            elif filter_words[i] in ['1','2','3','4','5','6','7','8','9']:
                dictIndex = '初登場世代'
            elif filter_words[i] in self.database['出身地'].unique().tolist():
                dictIndex = '出身地'
            elif filter_words[i] in self.database['タイプ1'].unique().tolist():
                dictIndex = 'タイプ'
            elif filter_words[i].upper() in np.unique(self.database[['特性1','特性2','隠れ特性']].astype(str).values.ravel()):
                dictIndex = '特性'
            else:
                continue
                
            if dictIndex not in new_dict:
                new_dict[dictIndex] = []
                
            new_dict[dictIndex].append(filter_words[i])
        
        output_log("以下のフィルタ辞書を生成しました\n " + str(new_dict))
        self.current_filter = new_dict
        return new_dict
    
    def search(self, filter_dict=None):
        """検索を実行して結果を保存
        
        Parameters:
        ----------
        filter_dict : dict, optional
            フィルタ辞書（デフォルト: None、その場合は現在のフィルタを使用）
            
        Returns:
        ----------
        tuple
            (検索結果のDataFrame, 処理済み検索条件)
        """
        if filter_dict is None:
            filter_dict = self.current_filter
            
        output_log("以下の条件でデータベースをフィルタリングします\n " + str(filter_dict))
        filtered_df = self.database.copy()
        
        # 表示用の処理済み条件辞書
        processed_conditions = {}
        
        # 数式によるフィルタリング
        if 'STAT_EXPRESSION' in filter_dict:
            for expression_str in filter_dict['STAT_EXPRESSION']:
                expr_dict = self.parse_stat_expression(expression_str)
                if expr_dict:
                    # フィルタリングを実行
                    filtered_df = self.evaluate_stat_expression(filtered_df, expr_dict)
                    
                    # 条件を表示用に整理
                    self.process_stat_expression_for_display(expr_dict, expression_str, processed_conditions)
        
        # 通常のフィルタリング
        for key, value in filter_dict.items():
            if key == 'STAT_EXPRESSION':
                continue  # 数式は既に処理済み
            
            if key == 'タイプ':
                filtered_df = filtered_df[(filtered_df['タイプ1'].isin(value)) | 
                                         (filtered_df['タイプ2'].isin(value))]
                processed_conditions['タイプ'] = value
            elif key == '特性':
                filtered_df = filtered_df[(filtered_df['特性1'].isin(value)) | 
                                         (filtered_df['特性2'].isin(value)) | 
                                         (filtered_df['隠れ特性'].isin(value))]
                processed_conditions['特性'] = value
            else:
                processed_conditions[key] = value
                try:
                    if len(value) > 0 and all(isinstance(v, str) and v.isdecimal() for v in value):
                        filtered_df = filtered_df[filtered_df[key].isin([int(v) for v in value])]
                    else:
                        filtered_df = filtered_df[filtered_df[key].isin(value)]
                except:
                    filtered_df = filtered_df[filtered_df[key].isin(value)]
        
        output_log("データのフィルタリングが完了しました 取得行数: " + str(filtered_df.shape[0]))
        output_log(f"処理済みの条件: {processed_conditions}")
        
        # 結果の保存
        self.processed_conditions = processed_conditions
        
        # 検索結果の整形
        results = []
        for _, row in filtered_df.iterrows():
            results.append([row['おなまえ'], bss_to_text(row)])
        
        self.current_results = results
        return (filtered_df, processed_conditions)
    
    def get_results_page(self, page=0, page_size=10):
        """指定ページの検索結果を取得
        
        Parameters:
        ----------
        page : int, optional
            ページ番号（デフォルト: 0）
        page_size : int, optional
            1ページあたりの結果数（デフォルト: 10）
            
        Returns:
        ----------
        list
            ページに含まれる検索結果
        """
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(self.current_results))
        return self.current_results[start_idx:end_idx]
    
    def create_search_embed(self, current_page=0, filter_words=None, page_size=10):
        """検索結果からEmbedを生成
        
        Parameters:
        ----------
        current_page : int, optional
            現在のページ番号（デフォルト: 0）
        filter_words : list, optional
            検索条件の元のリスト（デフォルト: None）
        page_size : int, optional
            1ページあたりの結果数（デフォルト: 10）
            
        Returns:
        ----------
        discord.Embed
            生成されたEmbed
        """
        # 検索結果の総数
        total_results = len(self.current_results)
        
        # 総ページ数を計算
        total_pages = (total_results + page_size - 1) // page_size
        
        # 該当ページの結果を取得
        page_results = self.get_results_page(current_page, page_size)
        
        # 結果表示用のEmbedを作成
        search_embed = discord.Embed(
            title=f'検索結果: {total_results}匹 (ページ {current_page + 1}/{total_pages})', 
            color=0x00FF7F,
            description=f'```\nquery: {" ".join(filter_words) if filter_words else ""}\n```'
        )
        search_embed.set_author(name="ポケモンサーチャー")
        search_embed.set_footer(text=f"No.27 ポケモンサーチャー - ページ {current_page + 1}")
        
        # フィルター条件を表示
        for key, values in self.processed_conditions.items():
            if not values:
                continue
                
            if isinstance(values, list):
                value_str = ", ".join(map(str, values))
            elif isinstance(values, str):
                value_str = values
            else:
                value_str = ", ".join(map(str, values))
                
            search_embed.add_field(
                name=f"条件: {key}",
                value=f"`{value_str}`",
                inline=True
            )
        
        # 結果リスト
        for result in page_results:
            search_embed.add_field(
                name=result[0],
                value=result[1],
                inline=False
            )
        
        return search_embed
    
    def create_pagination_view(self, current_page=0, page_size=10):
        """ページネーションボタンを含むビューを生成
        
        Parameters:
        ----------
        current_page : int, optional
            現在のページ番号（デフォルト: 0）
        page_size : int, optional
            1ページあたりの結果数（デフォルト: 10）
            
        Returns:
        ----------
        discord.ui.View
            生成されたビュー
        """
        total_results = len(self.current_results)
        nav_view = discord.ui.View(timeout=None)
        
        # 総ページ数を計算
        total_pages = (total_results + page_size - 1) // page_size
        
        # 前のページボタン
        prev_button = discord.ui.Button(
            label="前へ", 
            style=discord.ButtonStyle.secondary,
            custom_id=f"search_prev:{current_page}:{total_results}",
            disabled=current_page <= 0
        )
        nav_view.add_item(prev_button)
        
        # 次のページボタン
        next_button = discord.ui.Button(
            label="次へ", 
            style=discord.ButtonStyle.primary,
            custom_id=f"search_next:{current_page}:{total_results}",
            disabled=current_page >= total_pages - 1
        )
        nav_view.add_item(next_button)
        
        # 新しい検索ボタン
        new_search_button = discord.ui.Button(
            label="新しい検索", 
            style=discord.ButtonStyle.success,
            custom_id="search_new_button"
        )
        nav_view.add_item(new_search_button)
        
        return nav_view
    
    def create_search_ui_components(self):
        """検索UI用のコンポーネントを生成
        
        Returns:
        ----------
        dict
            UI要素の辞書
        """
        # タイプ選択用のセレクトメニュー
        type_select = discord.ui.Select(
            placeholder="タイプで絞り込む",
            custom_id="search_type_select",
            min_values=0,
            max_values=2,
            options=[
                discord.SelectOption(label=type_name, value=type_name)
                for type_name in sorted(self.database['タイプ1'].unique().tolist())
            ]
        )
        
        # 世代選択用のセレクトメニュー
        gen_select = discord.ui.Select(
            placeholder="世代で絞り込む",
            custom_id="search_gen_select",
            min_values=0,
            options=[
                discord.SelectOption(label=f"第{gen}世代", value=str(gen))
                for gen in sorted(self.database['初登場世代'].unique().tolist())
            ]
        )
        
        # 進化段階選択用のセレクトメニュー
        evo_select = discord.ui.Select(
            placeholder="進化段階で絞り込む",
            custom_id="search_evo_select",
            min_values=0,
            options=[
                discord.SelectOption(label=evo_stage, value=evo_stage)
                for evo_stage in sorted(self.database['進化段階'].unique().tolist())
            ]
        )
        
        # 検索関連ボタン
        search_button = discord.ui.Button(
            label="検索する",
            style=discord.ButtonStyle.primary,
            custom_id="search_execute_button"
        )
        
        reset_button = discord.ui.Button(
            label="条件をリセット",
            style=discord.ButtonStyle.secondary,
            custom_id="search_reset_button"
        )
        
        modal_button = discord.ui.Button(
            label="直接入力",
            style=discord.ButtonStyle.success,
            custom_id="search_modal_button"
        )
        
        return {
            "type_select": type_select,
            "gen_select": gen_select,
            "evo_select": evo_select,
            "search_button": search_button,
            "reset_button": reset_button,
            "modal_button": modal_button
        }
    
    def process_stat_expression_for_display(self, expr_dict, expression_str, processed_conditions):
        """種族値条件をUI表示用に整理する補助関数
        
        Parameters:
        ----------
        expr_dict : dict
            parse_stat_expressionの結果辞書
        expression_str : str
            元の条件式文字列
        processed_conditions : dict
            処理済みの条件辞書
        """
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
    
    # 以下は既存の関数をクラスメソッドとして移植したもの
    def parse_stat_expression(self, expression_str):
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
    
    def preprocess_expression(self, expr):
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
    
    def evaluate_stat_expression(self, df, expr_dict):
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
                left_expr = self.preprocess_expression(expr_dict['left_expr'])
                right_expr = self.preprocess_expression(expr_dict['right_expr'])
                
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
                left_expr = self.preprocess_expression(expr_dict['left_expr'])
                op = expr_dict['operator']
                
                # 右辺が数値か式か判断
                try:
                    right_val = float(expr_dict['right_val'])
                    is_numeric_right = True
                except:
                    right_val = self.preprocess_expression(expr_dict['right_val'])
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


