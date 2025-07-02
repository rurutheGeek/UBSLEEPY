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
        
        # 検索条件を前処理して論理演算子を分離
        processed_groups = self._preprocess_filter_words(filter_words)
        
        # 論理演算子の検出
        logical_ops = ['|', 'OR', 'or', '&', 'AND', 'and']
        has_logical_ops = any(any(op in word for word in group) for group in processed_groups for op in logical_ops)
        
        if has_logical_ops:
            # 論理演算子が含まれている場合は専用の処理
            return {'LOGICAL_GROUPS': processed_groups}
        
        # 論理演算子がない場合の通常処理
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
        
        # 論理演算子グループの処理
        if 'LOGICAL_GROUPS' in filter_dict:
            filtered_df, processed_conditions = self._search_with_logical_groups(filter_dict['LOGICAL_GROUPS'])
        else:
            # 通常の検索処理（既存のコード）
            filtered_df = self.database.copy()
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
        
        # 論理式の特別処理
        if "論理式" in self.processed_conditions and isinstance(self.processed_conditions["論理式"], list):
            for i, expr in enumerate(self.processed_conditions["論理式"]):
                search_embed.add_field(
                    name=f"条件: 論理式 {i+1}",
                    value=f"`{expr}`",
                    inline=False
                )
        else:
            # 通常の条件表示
            for key, value in self.processed_conditions.items():
                if not value:
                    continue
                    
                if isinstance(value, list):
                    value_str = ", ".join(map(str, value))
                else:
                    value_str = str(value)
                    
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

    def _make_logical_filter_dict(self, filter_words):
        """論理演算子を含む検索条件からフィルタ辞書を生成
        
        Parameters:
        ----------
        filter_words : list
            論理演算子を含む検索条件のリスト
            
        Returns:
        ----------
        dict
            フィルタ辞書
        """
        output_log("論理演算子を含む検索条件からフィルタ辞書を生成\n " + str(filter_words))
        
        # 演算子の正規化（小文字のorやandを大文字に変換）
        normalized_words = []
        for word in filter_words:
            if word.lower() == 'or' or word == '|':
                normalized_words.append('OR')
            elif word.lower() == 'and' or word == '&':
                normalized_words.append('AND')
            else:
                normalized_words.append(word)
        
        # 半角スペースで区切られた部分は全てANDで結合される
        # 論理演算子の処理を変更して、半角スペース区切りをANDとして扱う
        restructured_logical_expr = {'AND_groups': []}
        
        # 複数のANDグループに分割
        current_group = []
        
        for word in normalized_words:
            current_group.append(word)
        
        restructured_logical_expr['AND_groups'].append(current_group)
        
        return {'LOGICAL_EXPR': restructured_logical_expr}

    def _search_with_logical_operators(self, logical_expr):
        """論理演算子を含む検索条件を処理
        
        Parameters:
        ----------
        logical_expr : dict
            論理演算子を含む構造化された検索条件
            
        Returns:
        ----------
        tuple
            (検索結果のDataFrame, 処理済み検索条件)
        """
        output_log(f"論理演算子を含む検索条件を処理\n {logical_expr}")
        
        # 結果のDataFrameを初期化
        result_df = self.database.copy()
        processed_conditions = {}
        
        # ANDグループを処理
        for and_group in logical_expr['AND_groups']:
            output_log(f"ANDグループを処理: {and_group}")
            
            # OR条件を処理するためのDataFrameを作成
            or_dfs = []
            or_conditions = []
            
            # ORグループに分割
            or_group = []
            current_cond = []
            
            for i, word in enumerate(and_group):
                if word == 'OR':
                    # ORの前の条件を処理
                    if current_cond:
                        or_group.append(current_cond)
                        current_cond = []
                else:
                    current_cond.append(word)
                
                # 最後の要素を処理
                if i == len(and_group) - 1 and current_cond:
                    or_group.append(current_cond)
            
            # ORグループがない場合は、全体を1つのグループとして扱う
            if not or_group:
                or_group = [and_group]
            
            output_log(f"ORグループ: {or_group}")
            
            # 各OR条件を処理
            for cond in or_group:
                # スペースでAND結合された条件をさらに整理
                if 'OR' in cond:
                    # 'OR'を含む場合は再帰的に処理
                    subconds = []
                    current_subcond = []
                    
                    for word in cond:
                        if word == 'OR':
                            if current_subcond:
                                subconds.append(current_subcond)
                                current_subcond = []
                        else:
                            current_subcond.append(word)
                    
                    if current_subcond:
                        subconds.append(current_subcond)
                    
                    # 各サブ条件を処理して結果をOR結合
                    sub_dfs = []
                    sub_conditions = []
                    
                    for subcond in subconds:
                        filter_dict = self._convert_to_filter_dict(subcond)
                        sub_df, sub_cond = self._search_without_logical(filter_dict)
                        sub_dfs.append(sub_df)
                        sub_conditions.append(sub_cond)
                    
                    # OR結合
                    or_df = pd.concat(sub_dfs).drop_duplicates() if sub_dfs else pd.DataFrame()
                    or_condition = " OR ".join([str(c) for c in sub_conditions])
                    
                    or_dfs.append(or_df)
                    or_conditions.append(or_condition)
                else:
                    # 単純な条件
                    filter_dict = self._convert_to_filter_dict(cond)
                    or_df, or_condition = self._search_without_logical(filter_dict)
                    or_dfs.append(or_df)
                    or_conditions.append(or_condition)
            
            # OR条件を結合
            or_combined_df = pd.concat(or_dfs).drop_duplicates() if or_dfs else pd.DataFrame()
            
            # ANDで絞り込み
            result_df = result_df[result_df.index.isin(or_combined_df.index)]
            
            # 処理済み条件を更新
            or_combined_condition = " OR ".join([str(c) for c in or_conditions])
            processed_conditions.update({"論理条件": or_combined_condition})
        
        output_log(f"論理演算処理結果: {len(result_df)}行, 処理済み条件: {processed_conditions}")
        
        return (result_df, processed_conditions)

    def _search_without_logical(self, filter_dict):
        """論理演算子を含まない検索を実行
        
        Parameters:
        ----------
        filter_dict : dict
            フィルタ辞書
            
        Returns:
        ----------
        tuple
            (検索結果のDataFrame, 処理済み検索条件)
        """
        filtered_df = self.database.copy()
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
        
        return (filtered_df, processed_conditions)

    def _preprocess_filter_words(self, filter_words):
        """検索条件を前処理して論理演算子を適切に分離
        
        Parameters:
        ----------
        filter_words : list
            元の検索条件のリスト
            
        Returns:
        ----------
        list
            前処理後の検索条件リスト（検索条件ごとに分割）
        """
        processed_groups = []
        
        for word in filter_words:
            # 複雑な条件を再帰的に分解
            if '|' in word and ('&' in word or '>=' in word or '>' in word):
                # OR条件で分割
                sub_conditions = word.split('|')
                or_group = []
                
                for i, sub_cond in enumerate(sub_conditions):
                    if '&' in sub_cond:
                        # AND条件をさらに分割
                        and_parts = sub_cond.split('&')
                        for part in and_parts:
                            if part:  # 空でない部分を追加
                                or_group.append(part)
                            or_group.append('&')
                        # 最後の余分な&を削除
                        if or_group and or_group[-1] == '&':
                            or_group.pop()
                    else:
                        or_group.append(sub_cond)
                    
                    if i < len(sub_conditions) - 1:  # 最後以外は|を追加
                        or_group.append('|')
                
                processed_groups.append(or_group)
                
            elif '&' in word:
                # AND条件で分割
                and_parts = word.split('&')
                and_group = []
                
                for i, part in enumerate(and_parts):
                    if part:  # 空でない部分を追加
                        and_group.append(part)
                    if i < len(and_parts) - 1:  # 最後以外は&を追加
                        and_group.append('&')
                
                processed_groups.append(and_group)
                
            elif '|' in word:
                # 単純なOR条件の分割
                or_parts = word.split('|')
                or_group = []
                
                for i, part in enumerate(or_parts):
                    if part:  # 空でない部分を追加
                        or_group.append(part)
                    if i < len(or_parts) - 1:  # 最後以外は|を追加
                        or_group.append('|')
                
                processed_groups.append(or_group)
                
            else:
                # 通常の単語はそのまま1つのグループに
                processed_groups.append([word])
        
        output_log(f"前処理後の検索条件グループ: {processed_groups}")
        return processed_groups

    def _convert_to_filter_dict(self, condition_words):
        """条件リストをフィルタ辞書に変換
        
        Parameters:
        ----------
        condition_words : list
            条件のリスト
            
        Returns:
        ----------
        dict
            フィルタ辞書
        """
        output_log(f"条件リストをフィルタ辞書に変換: {condition_words}")
        
        filter_dict = {}
        
        for word in condition_words:
            # 'OR'や'AND'はスキップ
            if word in ['OR', 'AND']:
                continue
                
            # 種族値の条件
            if any(word.startswith(stat) for stat in BASE_STATS_DICT.keys()) and any(op in word for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in filter_dict:
                    filter_dict['STAT_EXPRESSION'] = []
                filter_dict['STAT_EXPRESSION'].append(word)
                continue
                
            # 合計値の条件
            if word.startswith('合計') and any(op in word for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in filter_dict:
                    filter_dict['STAT_EXPRESSION'] = []
                filter_dict['STAT_EXPRESSION'].append(word)
                continue
                
            # タイプ、世代、進化段階などの条件
            if word in self.database['タイプ1'].unique().tolist():
                if 'タイプ' not in filter_dict:
                    filter_dict['タイプ'] = []
                filter_dict['タイプ'].append(word)
            elif word in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                if '初登場世代' not in filter_dict:
                    filter_dict['初登場世代'] = []
                filter_dict['初登場世代'].append(word)
            elif word in self.database['進化段階'].unique().tolist():
                if '進化段階' not in filter_dict:
                    filter_dict['進化段階'] = []
                filter_dict['進化段階'].append(word)
            elif word in self.database['出身地'].unique().tolist():
                if '出身地' not in filter_dict:
                    filter_dict['出身地'] = []
                filter_dict['出身地'].append(word)
            elif word.upper() in np.unique(self.database[['特性1', '特性2', '隠れ特性']].astype(str).values.ravel()):
                if '特性' not in filter_dict:
                    filter_dict['特性'] = []
                filter_dict['特性'].append(word)
        
        output_log(f"生成されたフィルタ辞書: {filter_dict}")
        return filter_dict

    def _convert_to_human_readable(self, processed_conditions):
        """処理済み条件を人間が読みやすい形式に変換
        
        Parameters:
        ----------
        processed_conditions : dict
            処理済み条件の辞書
            
        Returns:
        ----------
        dict
            人間が読みやすい形式に変換された条件辞書
        """
        readable_conditions = {}
        
        for key, values in processed_conditions.items():
            # 論理条件の処理
            if key == '論理条件':
                logic_parts = []
                
                # タイプの論理条件を抽出して変換
                type_pattern = r'タイプ: ([^\)]+)'
                type_matches = re.findall(type_pattern, values)
                
                if type_matches:
                    types = []
                    for type_match in type_matches:
                        # OR条件を「または」に、AND条件を「かつ」に変換
                        type_text = type_match.replace(' OR ', 'または').replace(' AND ', 'かつ')
                        types.append(type_text)
                    
                    type_text = 'または'.join(types)
                    readable_conditions['タイプ'] = f"{type_text.replace(',', '')}タイプ"
                
                # 種族値条件を抽出
                for stat, stat_name in [
                    ('HP', 'HP'), 
                    ('こうげき', 'こうげき'), 
                    ('ぼうぎょ', 'ぼうぎょ'), 
                    ('とくこう', 'とくこう'), 
                    ('とくぼう', 'とくぼう'), 
                    ('すばやさ', 'すばやさ')
                ]:
                    stat_pattern = rf'{stat_name}: [^,)]+([><]=?\d+)'
                    stat_matches = re.findall(stat_pattern, values)
                    
                    if stat_matches:
                        for stat_match in stat_matches:
                            op = re.search(r'([><]=?)', stat_match).group(1)
                            val = re.search(r'(\d+)', stat_match).group(1)
                            
                            if op == '>':
                                op_text = 'より大きい'
                            elif op == '>=':
                                op_text = '以上'
                            elif op == '<':
                                op_text = 'より小さい'
                            elif op == '<=':
                                op_text = '以下'
                            else:  # ==, =
                                op_text = 'と等しい'
                            
                            readable_conditions[stat_name] = f"{stat_name}が{val}{op_text}"
                
                # 他の条件も抽出（世代、進化段階など）
                for other_key in ['初登場世代', '進化段階', '出身地', '特性']:
                    other_pattern = rf'{other_key}: ([^,)]+)'
                    other_matches = re.findall(other_pattern, values)
                    
                    if other_matches:
                        for other_match in other_matches:
                            readable_conditions[other_key] = other_match.replace(',', '')
            
            # 通常の条件の処理
            elif key == 'すばやさ' and isinstance(values, list):
                for value in values:
                    if '>' in value:
                        op = '>' 
                        op_text = 'より大きい'
                    elif '>=' in value:
                        op = '>='
                        op_text = '以上'
                    elif '<' in value:
                        op = '<'
                        op_text = 'より小さい'
                    elif '<=' in value:
                        op = '<='
                        op_text = '以下'
                    else:
                        op = '='
                        op_text = 'と等しい'
                    
                    val = re.search(r'(\d+)', value).group(1)
                    readable_conditions[key] = f"{key}が{val}{op_text}"
            
            # その他の条件はそのまま
            else:
                readable_conditions[key] = values
        
        return readable_conditions





            # 通常の検索処理（既存のコード）
            # ...略
        
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


    def _search_with_logical_groups(self, logical_groups):
        """論理演算子グループを処理して検索
        
        Parameters:
        ----------
        logical_groups : list
            論理演算子を含む条件グループのリスト
            
        Returns:
        ----------
        tuple
            (検索結果のDataFrame, 処理済み条件)
        """
        output_log(f"論理演算子グループを処理: {logical_groups}")
        
        # 全体の結果（すべてのANDグループの結果をAND結合したもの）
        final_result = self.database.copy()
        
        # OR条件リストを格納
        or_condition_list = []
        
        # 各ANDグループを処理（スペースで区切られた部分）
        for group in logical_groups:
            # グループ内の演算子を正規化
            normalized_group = []
            for item in group:
                if item.lower() == 'or' or item == '|':
                    normalized_group.append('OR')
                elif item.lower() == 'and' or item == '&':
                    normalized_group.append('AND')
                else:
                    normalized_group.append(item)
            
            output_log(f"正規化したグループ: {normalized_group}")
            
            # OR条件で分割
            or_conditions = []
            current_or = []
            
            for item in normalized_group:
                if item == 'OR':
                    if current_or:
                        or_conditions.append(current_or)
                        current_or = []
                else:
                    current_or.append(item)
            
            if current_or:
                or_conditions.append(current_or)
            
            output_log(f"OR条件リスト: {or_conditions}")
            or_condition_list = or_conditions  # OR条件リストを保存
            
            # 各OR条件の結果を結合
            or_results = []
            
            for or_condition in or_conditions:
                # 条件をフィルタ辞書に変換
                condition_dict = self._condition_to_filter_dict(or_condition)
                or_df, _ = self._process_simple_condition(condition_dict)
                or_results.append(or_df)
            
            # OR結果を結合（和集合）
            group_result = pd.concat(or_results).drop_duplicates() if or_results else pd.DataFrame()
            
            # グループの結果を全体の結果にAND結合（積集合）
            final_result = final_result[final_result.index.isin(group_result.index)]
        
        # OR条件リストを処理済み条件として返す
        processed_conditions = {"OR条件リスト": or_condition_list}
        
        return (final_result, processed_conditions)

    def _condition_to_filter_dict(self, condition):
        """条件リストをフィルタ辞書に変換
        
        Parameters:
        ----------
        condition : list
            条件のリスト
            
        Returns:
        ----------
        dict
            フィルタ辞書
        """
        filter_dict = {}
        
        for item in condition:
            # 論理演算子はスキップ
            if item in ['OR', 'AND', '|', '&']:
                continue
            
            # 種族値の条件
            if any(item.startswith(stat) for stat in ['H', 'A', 'B', 'C', 'D', 'S']) and any(op in item for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in filter_dict:
                    filter_dict['STAT_EXPRESSION'] = []
                filter_dict['STAT_EXPRESSION'].append(item)
                continue
            
            # 合計値の条件
            if item.startswith('合計') and any(op in item for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in filter_dict:
                    filter_dict['STAT_EXPRESSION'] = []
                filter_dict['STAT_EXPRESSION'].append(item)
                continue
            
            # タイプ、世代、進化段階などの条件
            if item in self.database['タイプ1'].unique().tolist():
                if 'タイプ' not in filter_dict:
                    filter_dict['タイプ'] = []
                filter_dict['タイプ'].append(item)
            elif item in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                if '初登場世代' not in filter_dict:
                    filter_dict['初登場世代'] = []
                filter_dict['初登場世代'].append(item)
            elif item in self.database['進化段階'].unique().tolist():
                if '進化段階' not in filter_dict:
                    filter_dict['進化段階'] = []
                filter_dict['進化段階'].append(item)
            elif item in self.database['出身地'].unique().tolist():
                if '出身地' not in filter_dict:
                    filter_dict['出身地'] = []
                filter_dict['出身地'].append(item)
            elif item.upper() in np.unique(self.database[['特性1', '特性2', '隠れ特性']].astype(str).values.ravel()):
                if '特性' not in filter_dict:
                    filter_dict['特性'] = []
                filter_dict['特性'].append(item)
        
        return filter_dict
    
    def _process_simple_condition(self, filter_dict):
        """単純な検索条件を処理
        
        Parameters:
        ----------
        filter_dict : dict
            フィルタ辞書
            
        Returns:
        ----------
        tuple
            (検索結果のDataFrame, 処理済み条件)
        """
        filtered_df = self.database.copy()
        processed_conditions = {}
        
        # 数式による処理
        if 'STAT_EXPRESSION' in filter_dict:
            for expr_str in filter_dict['STAT_EXPRESSION']:
                expr_dict = self.parse_stat_expression(expr_str)
                if expr_dict:
                    filtered_df = self.evaluate_stat_expression(filtered_df, expr_dict)
                    self.process_stat_expression_for_display(expr_dict, expr_str, processed_conditions)
        
        # 通常のフィルタリング
        for key, value in filter_dict.items():
            if key == 'STAT_EXPRESSION':
                continue
            
            if key == 'タイプ':
                filtered_df = filtered_df[(filtered_df['タイプ1'].isin(value)) | (filtered_df['タイプ2'].isin(value))]
                processed_conditions['タイプ'] = value
            elif key == '特性':
                filtered_df = filtered_df[(filtered_df['特性1'].isin(value)) | (filtered_df['特性2'].isin(value)) | (filtered_df['隠れ特性'].isin(value))]
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
        
        return (filtered_df, processed_conditions)

    def _format_logical_conditions(self, conditions):
        """論理条件を読みやすい形式に整形
        
        Parameters:
        ----------
        conditions : dict
            条件辞書
            
        Returns:
        ----------
        dict
            整形された条件辞書
        """
        # 論理式のグループを抽出
        logical_expressions = []
        
        # OR条件リストから論理式を抽出
        for group_condition in conditions.values():
            if isinstance(group_condition, str):
                # OR条件リストの処理
                or_conditions = re.findall(r'OR条件リスト: \[(.*?)\]', group_condition)
                if or_conditions:
                    for or_condition in or_conditions:
                        # 個々の条件グループを抽出
                        condition_groups = re.findall(r'\[(.*?)\]', or_condition)
                        for i, group in enumerate(condition_groups):
                            # 'AND'を除去して条件だけを取得
                            parts = []
                            for part in group.split(', '):
                                if part.strip("'") not in ["AND", "OR"]:
                                    parts.append(part.strip("'"))
                            
                            if parts:
                                expr = " & ".join(parts)
                                logical_expressions.append(expr)
        
        # 論理式が抽出できた場合
        if logical_expressions:
            # 「論理式」というキーで返す
            return {"論理式": logical_expressions}
        
        # 通常の条件処理
        return conditions





