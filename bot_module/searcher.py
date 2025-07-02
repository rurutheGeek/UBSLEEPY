# -*- coding: utf-8 -*-
"""
ポケモン検索機能を提供するモジュール

このモジュールは、Discordボットのポケモン検索機能を実装します。
検索条件の解析、検索実行、結果の表示、UIの管理を行います。
"""

from typing import Dict, List, Tuple, Optional, Union
import re
import discord
import numpy as np
from .config import *
from .func import output_log, bss_to_text

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
        self.current_filter: Dict = {}  # 現在の検索フィルタ
        self.current_results: List = []  # 現在の検索結果
        self.processed_conditions: Dict = {}  # 処理済み検索条件
        self.logical_groups: List[Dict] = []  # 論理演算子グループ
        
    def _preprocess_filter_words(self, filter_words: List[str]) -> List[Dict]:
        """検索条件を前処理して論理演算子を分離
        
        Parameters:
        ----------
        filter_words : List[str]
            検索条件のリスト
            
        Returns:
        ----------
        List[Dict]
            論理演算子グループのリスト
        """
        output_log(f"[DEBUG] 前処理開始: {filter_words}")
        logical_groups = []
        
        # AND条件を含む条件を分離
        and_conditions = []
        non_and_conditions = []
        
        for word in filter_words:
            if '&' in word:
                and_conditions.append(word)
            else:
                non_and_conditions.append(word)
        
        # AND条件を処理
        if and_conditions:
            and_group = {"type": "AND", "conditions": []}
            for and_condition in and_conditions:
                # AND条件を個別の条件として追加
                and_group["conditions"].append(and_condition)
            logical_groups.append(and_group)
        
        # 数式を含む条件を分離
        expression_conditions = []
        non_expression_conditions = []
        
        for word in non_and_conditions:
            if any(op in word for op in ['>', '<', '=', '(', ')', '+', '-', '*', '/']):
                expression_conditions.append(word)
            else:
                non_expression_conditions.append(word)
        
        # 数式以外の条件をORグループとして処理
        if non_expression_conditions:
            or_group = {"type": "OR", "conditions": non_expression_conditions}
            if logical_groups:
                logical_groups[0]["conditions"].append(or_group)
            else:
                logical_groups.append({"type": "AND", "conditions": [or_group]})
        
        # 数式条件をAND条件として追加
        for expr in expression_conditions:
            if logical_groups:
                logical_groups[0]["conditions"].append(expr)
            else:
                logical_groups.append({"type": "AND", "conditions": [expr]})
        
        output_log(f"[DEBUG] 前処理結果: {logical_groups}")
        return logical_groups
    
    def _search_with_logical_groups(self, logical_groups: List[Dict]) -> 'pd.DataFrame':
        """論理演算子グループを処理して検索
        
        Parameters:
        ----------
        logical_groups : List[Dict]
            論理演算子グループのリスト
            
        Returns:
        ----------
        pd.DataFrame
            検索結果のDataFrame
        """
        output_log(f"[DEBUG] 論理グループ検索開始: {logical_groups}")
        result_df = self.database.copy()
        
        # 処理済み条件をリセット
        self.processed_conditions = {}
        
        for group in logical_groups:
            if group["type"] == "AND":
                # カテゴリごとのマスクを保持
                category_masks = {}
                
                for condition in group["conditions"]:
                    if isinstance(condition, dict) and condition["type"] == "OR":
                        # ORグループの処理
                        for or_condition in condition["conditions"]:
                            # 各条件をフィルタ辞書に変換
                            filter_dict = self._condition_to_filter_dict([or_condition])
                            
                            if filter_dict:
                                # カテゴリごとに条件を分類
                                for key, values in filter_dict.items():
                                    if key not in category_masks:
                                        category_masks[key] = []
                                    
                                    if key == 'タイプ':
                                        # タイプの条件はORで結合
                                        type_mask = (result_df['タイプ1'].isin(values)) | (result_df['タイプ2'].isin(values))
                                        category_masks[key].append(type_mask)
                                    elif key == '特性':
                                        # 特性の条件はORで結合
                                        ability_mask = (result_df['特性1'].isin(values)) | (result_df['特性2'].isin(values)) | (result_df['隠れ特性'].isin(values))
                                        category_masks[key].append(ability_mask)
                                    elif key == '進化段階':
                                        # 進化段階の条件はORで結合
                                        evo_mask = result_df[key].isin(values)
                                        category_masks[key].append(evo_mask)
                                    else:
                                        # その他の条件（世代など）はORで結合
                                        other_mask = result_df[key].astype(str).isin(values)
                                        category_masks[key].append(other_mask)
                                    
                                    # 処理済み条件に追加
                                    if key not in self.processed_conditions:
                                        self.processed_conditions[key] = []
                                    self.processed_conditions[key].extend(values)
                    
                    elif isinstance(condition, str) and any(op in condition for op in ['>', '<', '=', '(', ')', '+', '-', '*', '/']):
                        # 数式条件の処理
                        expr_dict = StatExpressionParser.parse(condition)
                        if expr_dict:
                            mask = StatExpressionParser.evaluate_mask(result_df, expr_dict)
                            if '数式' not in category_masks:
                                category_masks['数式'] = []
                            category_masks['数式'].append(mask)
                            
                            # 数式条件を処理済み条件に追加
                            if '数式' not in self.processed_conditions:
                                self.processed_conditions['数式'] = []
                            self.processed_conditions['数式'].append(condition)
                
                # 各カテゴリのマスクをANDで結合
                final_mask = pd.Series(True, index=result_df.index)
                for masks in category_masks.values():
                    if masks:
                        # カテゴリ内のマスクをORで結合
                        category_mask = pd.concat(masks, axis=1).any(axis=1)
                        # カテゴリ間のマスクをANDで結合
                        final_mask &= category_mask
                
                # 最終的なマスクを適用
                result_df = result_df[final_mask]
        
        if '初登場世代' in self.processed_conditions:
            output_log(f"[DEBUG] 最終的な世代条件: {self.processed_conditions['初登場世代']}")
            output_log(f"[DEBUG] 最終結果の世代分布:\n{result_df['初登場世代'].value_counts()}")
        
        return result_df
    
    def _condition_to_filter_dict(self, conditions: List[str]) -> Dict:
        """条件リストをフィルタ辞書に変換
        
        Parameters:
        ----------
        conditions : List[str]
            条件のリスト
            
        Returns:
        ----------
        Dict
            フィルタ辞書
        """
        output_log(f"[DEBUG] 条件をフィルタ辞書に変換: {conditions}")
        filter_dict = {}
        
        for condition in conditions:
            # 明示的なAND条件の処理
            if '&' in condition:
                and_conditions = condition.split('&')
                for and_condition in and_conditions:
                    and_condition = and_condition.strip()
                    if and_condition in self.database['タイプ1'].unique().tolist():
                        if 'タイプ' not in filter_dict:
                            filter_dict['タイプ'] = []
                        filter_dict['タイプ'].append(and_condition)
                    elif and_condition.upper() in np.unique(self.database[['特性1','特性2','隠れ特性']].astype(str).values.ravel()):
                        if '特性' not in filter_dict:
                            filter_dict['特性'] = []
                        filter_dict['特性'].append(and_condition)
                    else:
                        output_log(f"[DEBUG] 未分類のAND条件: {and_condition}")
                continue
            
            if condition.startswith('合計') and any(op in condition for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in filter_dict:
                    filter_dict['STAT_EXPRESSION'] = []
                filter_dict['STAT_EXPRESSION'].append(condition)
                continue
            
            first_char_upper = condition[0].upper() if condition else ''
            if first_char_upper in BASE_STATS_DICT or '(' in condition:
                if any(op in condition for op in ['>', '<', '=']):
                    if 'STAT_EXPRESSION' not in filter_dict:
                        filter_dict['STAT_EXPRESSION'] = []
                    filter_dict['STAT_EXPRESSION'].append(condition)
                    continue
            
            if condition in self.database['進化段階'].unique().tolist():
                dictIndex = '進化段階'
            elif condition in ['1','2','3','4','5','6','7','8','9']:
                dictIndex = '初登場世代'
            elif condition in self.database['出身地'].unique().tolist():
                dictIndex = '出身地'
            elif condition in self.database['タイプ1'].unique().tolist():
                dictIndex = 'タイプ'
            elif condition.upper() in np.unique(self.database[['特性1','特性2','隠れ特性']].astype(str).values.ravel()):
                dictIndex = '特性'
            else:
                output_log(f"[DEBUG] 未分類の条件: {condition}")
                continue
                
            if dictIndex not in filter_dict:
                filter_dict[dictIndex] = []
                
            filter_dict[dictIndex].append(condition)
            output_log(f"[DEBUG] フィルタ辞書に追加: {dictIndex} -> {condition}")
        
        output_log(f"[DEBUG] フィルタ辞書生成結果: {filter_dict}")
        return filter_dict
    
    def _apply_filters(self, df: 'pd.DataFrame', filter_dict: Dict) -> 'pd.DataFrame':
        """フィルタを適用してデータフレームをフィルタリング
        
        Parameters:
        ----------
        df : pd.DataFrame
            フィルタリング対象のデータフレーム
        filter_dict : Dict
            フィルタ辞書
            
        Returns:
        ----------
        pd.DataFrame
            フィルタリング後のデータフレーム
        """
        filtered_df = df.copy()
        
        if 'STAT_EXPRESSION' in filter_dict:
            for expression_str in filter_dict['STAT_EXPRESSION']:
                expr_dict = StatExpressionParser.parse(expression_str)
                if expr_dict:
                    filtered_df = StatExpressionParser.evaluate(filtered_df, expr_dict)
                    # 数式条件を処理済み条件に追加
                    if '数式' not in self.processed_conditions:
                        self.processed_conditions['数式'] = []
                    self.processed_conditions['数式'].append(expression_str)
        
        for key, value in filter_dict.items():
            if key == 'STAT_EXPRESSION':
                continue
            
            if key == 'タイプ':
                # タイプは同一カテゴリ内でOR条件
                type_conditions = []
                for type_name in value:
                    type_conditions.append(
                        (filtered_df['タイプ1'] == type_name) | 
                        (filtered_df['タイプ2'] == type_name)
                    )
                if type_conditions:
                    filtered_df = filtered_df[pd.concat(type_conditions, axis=1).any(axis=1)]
            elif key == '特性':
                # 特性は同一カテゴリ内でOR条件
                ability_conditions = []
                for ability in value:
                    ability_conditions.append(
                        (filtered_df['特性1'] == ability) |
                        (filtered_df['特性2'] == ability) |
                        (filtered_df['隠れ特性'] == ability)
                    )
                if ability_conditions:
                    filtered_df = filtered_df[pd.concat(ability_conditions, axis=1).any(axis=1)]
            else:
                # その他の条件（世代、進化段階など）は同一カテゴリ内でOR条件
                if value:
                    filtered_df = filtered_df[filtered_df[key].astype(str).isin(value)]
        
        return filtered_df
    
    def _format_logical_conditions(self, logical_groups: List[Dict]) -> List[str]:
        """論理条件を読みやすい形式に整形
        
        Parameters:
        ----------
        logical_groups : List[Dict]
            論理演算子グループのリスト
            
        Returns:
        ----------
        List[str]
            整形された条件のリスト
        """
        formatted_conditions = []
        
        for i, group in enumerate(logical_groups, 1):
            if group["type"] == "AND":
                conditions = []
                has_logical_operators = False
                
                for condition in group["conditions"]:
                    if isinstance(condition, dict):
                        # ORグループの処理
                        or_conditions = []
                        for or_condition in condition["conditions"]:
                            if isinstance(or_condition, dict):
                                # ANDグループの処理
                                and_conditions = " & ".join(or_condition["conditions"])
                                or_conditions.append(and_conditions)
                            else:
                                or_conditions.append(or_condition)
                        conditions.append(" | ".join(or_conditions))
                        has_logical_operators = True
                    else:
                        conditions.append(condition)
                
                if has_logical_operators:
                    formatted_conditions.append(f"条件: 論理式 {i}\n" + "\n".join(conditions))
        
        return formatted_conditions
    
    def make_filter_dict(self, filter_words: List[str]) -> Dict:
        """検索条件をフィルタ辞書に変換
        
        Parameters:
        ----------
        filter_words : List[str]
            検索条件のリスト
            
        Returns:
        ----------
        Dict
            フィルタ辞書
        """
        output_log("以下の項目でフィルタ辞書を生成します\n " + str(filter_words))
        
        # 論理演算子の処理
        self.logical_groups = self._preprocess_filter_words(filter_words)
        
        # 論理条件を整形して保存
        formatted_conditions = self._format_logical_conditions(self.logical_groups)
        if formatted_conditions:
            self.processed_conditions['論理式'] = formatted_conditions
            return {}  # 論理演算子を含む場合は空の辞書を返す
        
        # 通常のフィルタ処理
        new_dict = {}
        for word in filter_words:
            if word.startswith('合計') and any(op in word for op in ['>', '<', '=']):
                if 'STAT_EXPRESSION' not in new_dict:
                    new_dict['STAT_EXPRESSION'] = []
                new_dict['STAT_EXPRESSION'].append(word)
                continue
            
            first_char_upper = word[0].upper() if word else ''
            if first_char_upper in BASE_STATS_DICT or '(' in word:
                if any(op in word for op in ['>', '<', '=']):
                    if 'STAT_EXPRESSION' not in new_dict:
                        new_dict['STAT_EXPRESSION'] = []
                    new_dict['STAT_EXPRESSION'].append(word)
                    continue
            
            if word in self.database['進化段階'].unique().tolist():
                dictIndex = '進化段階'
            elif word in ['1','2','3','4','5','6','7','8','9']:
                dictIndex = '初登場世代'
            elif word in self.database['出身地'].unique().tolist():
                dictIndex = '出身地'
            elif word in self.database['タイプ1'].unique().tolist():
                dictIndex = 'タイプ'
            elif word.upper() in np.unique(self.database[['特性1','特性2','隠れ特性']].astype(str).values.ravel()):
                dictIndex = '特性'
            else:
                continue
                
            if dictIndex not in new_dict:
                new_dict[dictIndex] = []
                
            new_dict[dictIndex].append(word)
        
        output_log("以下のフィルタ辞書を生成しました\n " + str(new_dict))
        self.current_filter = new_dict
        return new_dict
    
    def search(self, filter_dict: Optional[Dict] = None) -> Tuple:
        """検索を実行して結果を保存
        
        Parameters:
        ----------
        filter_dict : Dict, optional
            フィルタ辞書（デフォルト: None、その場合は現在のフィルタを使用）
            
        Returns:
        ----------
        Tuple
            (検索結果のDataFrame, 処理済み検索条件)
        """
        if filter_dict is None:
            filter_dict = self.current_filter
            
        # 論理演算子を含む検索の実行
        if self.logical_groups:
            filtered_df = self._search_with_logical_groups(self.logical_groups)
        else:
            filtered_df = self.database.copy()
        
            # 通常のフィルタリング
        if 'STAT_EXPRESSION' in filter_dict:
            for expression_str in filter_dict['STAT_EXPRESSION']:
                    expr_dict = StatExpressionParser.parse(expression_str)
                    if expr_dict:
                            filtered_df = StatExpressionParser.evaluate(filtered_df, expr_dict)
                            SearchResultFormatter.process_stat_expression_for_display(
                                expr_dict, expression_str, self.processed_conditions
                            )
            
        for key, value in filter_dict.items():
            if key == 'STAT_EXPRESSION':
                    continue
            
            if key == 'タイプ':
                    # タイプは同一カテゴリ内でOR条件
                    type_conditions = []
                    for type_name in value:
                        type_conditions.append(
                            (filtered_df['タイプ1'] == type_name) | 
                            (filtered_df['タイプ2'] == type_name)
                        )
                    if type_conditions:
                        filtered_df = filtered_df[pd.concat(type_conditions, axis=1).any(axis=1)]
                    self.processed_conditions['タイプ'] = value
            elif key == '特性':
                    # 特性は同一カテゴリ内でOR条件
                    ability_conditions = []
                    for ability in value:
                        ability_conditions.append(
                            (filtered_df['特性1'] == ability) |
                            (filtered_df['特性2'] == ability) |
                            (filtered_df['隠れ特性'] == ability)
                        )
                    if ability_conditions:
                        filtered_df = filtered_df[pd.concat(ability_conditions, axis=1).any(axis=1)]
                    self.processed_conditions['特性'] = value
            else:
                    # その他の条件（世代、進化段階など）は同一カテゴリ内でOR条件
                    self.processed_conditions[key] = value
                    if value:
                        filtered_df = filtered_df[filtered_df[key].isin(value)]
        
        output_log("ポケモンデータのフィルタリングが完了 取得行数: " + str(filtered_df.shape[0]))
        output_log(f"処理済みの条件: {self.processed_conditions}")
        
        results = []
        for _, row in filtered_df.iterrows():
            results.append([row['おなまえ'], bss_to_text(row)])
        
        self.current_results = results
        return (filtered_df, self.processed_conditions)
    
    def get_results_page(self, page: int = 0, page_size: int = 10) -> List:
        """指定ページの検索結果を取得
        
        Parameters:
        ----------
        page : int, optional
            ページ番号（デフォルト: 0）
        page_size : int, optional
            1ページあたりの結果数（デフォルト: 10）
            
        Returns:
        ----------
        List
            ページに含まれる検索結果
        """
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(self.current_results))
        return self.current_results[start_idx:end_idx]
    
    
class StatExpressionParser:
    """種族値の数式を解析・評価するクラス"""
    
    @staticmethod
    def parse(expression_str: str) -> Optional[Dict]:
        """種族値の数式を解析して辞書を返す
        
        Parameters:
        ----------
        expression_str : str
            条件式の文字列（例：'H>=100'、'(H*B*D)/(B+D)<26825'、'A==C'、'合計<550'）
        
        Returns:
        ----------
        Optional[Dict]
            解析結果の辞書
        """
        try:
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
            
            equal_match = re.search(r'([=]{1,2})', expression_str)
            if equal_match and '>' not in expression_str and '<' not in expression_str:
                op_pos = equal_match.start()
                op = equal_match.group()
                left_expr = expression_str[:op_pos]
                right_expr = expression_str[op_pos + len(op):]
                
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
            
            first_char = expression_str[0].upper()
            if first_char in BASE_STATS_DICT and not '(' in expression_str[:2]:
                stat_key = first_char
                col_name = BASE_STATS_DICT[stat_key]
                rest = expression_str[1:]
                
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
            
            op_match = re.search(r'([><]=?|=)', expression_str)
            if op_match:
                op_pos = op_match.start()
                op = op_match.group()
                left_expr = expression_str[:op_pos]
                right_val = expression_str[op_pos + len(op):]
                
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
    
    @staticmethod
    def preprocess_expression(expr: str) -> str:
        """数式を前処理して、Python構文に合わせる
        
        Parameters:
        ----------
        expr : str
            元の数式
        
        Returns:
        ----------
        str
            処理後の数式
        """
        try:
            float(expr)
            return expr
        except:
            pass
        
        processed = re.sub(r'\)(\()', ')*(', expr)
        
        for stat in set(list(BASE_STATS_DICT.keys()) + [k.lower() for k in BASE_STATS_DICT.keys()]):
            processed = re.sub(r'(' + re.escape(stat) + r')(\()', r'\1*\2', processed)
        
        processed = re.sub(r'(\d)(\()', r'\1*\2', processed)
        
        return processed
    
    @staticmethod
    def evaluate_mask(df: 'pd.DataFrame', expr_dict: Dict) -> 'pd.Series':
        """種族値の数式を評価してマスクを返す
        
        Parameters:
        ----------
        df : pd.DataFrame
            フィルタリング対象のデータフレーム
        expr_dict : Dict
            parseから返される辞書
        
        Returns:
        ----------
        pd.Series
            条件に一致する行を示すブールマスク
        """
        if not expr_dict:
            return pd.Series(True, index=df.index)
        
        try:
            if expr_dict['type'] == 'total':
                op = expr_dict['operator']
                val = expr_dict['value']
                
                if op == '>=':
                    return df['合計'] >= val
                elif op == '>':
                    return df['合計'] > val
                elif op == '<=':
                    return df['合計'] <= val
                elif op == '<':
                    return df['合計'] < val
                elif op == '=' or op == '==':
                    return df['合計'] == val

            elif expr_dict['type'] == 'simple':
                col = expr_dict['column']
                op = expr_dict['operator']
                val = expr_dict['value']
                
                if op == '>=':
                    return df[col] >= val
                elif op == '>':
                    return df[col] > val
                elif op == '<=':
                    return df[col] <= val
                elif op == '<':
                    return df[col] < val
                elif op == '=' or op == '==':
                    return df[col] == val
                
            elif expr_dict['type'] == 'equality':
                left_expr = StatExpressionParser.preprocess_expression(expr_dict['left_expr'])
                right_expr = StatExpressionParser.preprocess_expression(expr_dict['right_expr'])
                
                # pandas.evalを使用してベクトル化された評価
                try:
                    left_result = df.eval(left_expr)
                    right_result = df.eval(right_expr)
                    return left_result == right_result
                except Exception as e:
                    output_log(f"等式評価中のエラー: {e}")
                    return pd.Series(False, index=df.index)
                
            elif expr_dict['type'] == 'complex':
                left_expr = StatExpressionParser.preprocess_expression(expr_dict['left_expr'])
                op = expr_dict['operator']
                
                try:
                    right_val = float(expr_dict['right_val'])
                    is_numeric_right = True
                except:
                    right_val = StatExpressionParser.preprocess_expression(expr_dict['right_val'])
                    is_numeric_right = False
                
                try:
                    left_result = df.eval(left_expr)
                    
                    if not is_numeric_right:
                        right_result = df.eval(right_val)
                    else:
                        right_result = right_val
                    
                    if op == '>=':
                        return left_result >= right_result
                    elif op == '>':
                        return left_result > right_result
                    elif op == '<=':
                        return left_result <= right_result
                    elif op == '<':
                        return left_result < right_result
                    elif op == '=' or op == '==':
                        return left_result == right_result
                except Exception as e:
                    output_log(f"複雑な式の評価中にエラー: {e}")
                    return pd.Series(False, index=df.index)
        
        except Exception as e:
            output_log(f"式の評価中にエラーが発生しました: {e}")
        
        return pd.Series(False, index=df.index)

class SearchResultFormatter:
    """検索結果の表示形式を管理するクラス"""
    
    @staticmethod
    def build_search_embed(searcher: PokemonSearcher, current_page: int = 0, 
                          filter_words: Optional[List[str]] = None, page_size: int = 10) -> discord.Embed:
        """検索結果からEmbedを生成
        
        Parameters:
        ----------
        searcher : PokemonSearcher
            検索クラスのインスタンス
        current_page : int, optional
            現在のページ番号（デフォルト: 0）
        filter_words : List[str], optional
            検索条件の元のリスト（デフォルト: None）
        page_size : int, optional
            1ページあたりの結果数（デフォルト: 10）
            
        Returns:
        ----------
        discord.Embed
            生成されたEmbed
        """
        total_results = len(searcher.current_results)
        total_pages = (total_results + page_size - 1) // page_size
        page_results = searcher.get_results_page(current_page, page_size)
        
        search_embed = discord.Embed(
            title=f'検索結果: {total_results}匹 (ページ {current_page + 1}/{total_pages})', 
            color=0x00FF7F,
            description=f'```\nquery: {" ".join(filter_words) if filter_words else ""}\n```'
        )
        search_embed.set_author(name="ポケモンサーチャー")
        search_embed.set_footer(text=f"No.27 ポケモンサーチャー - ページ {current_page + 1}")
        
        for key, values in searcher.processed_conditions.items():
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
        
        for result in page_results:
            search_embed.add_field(
                name=result[0],
                value=result[1],
                inline=False
            )
        
        return search_embed
    
    @staticmethod
    def build_pagination_view(current_page: int = 0, total_results: int = 0, 
                            page_size: int = 10) -> discord.ui.View:
        """ページネーションボタンを含むビューを生成
        
        Parameters:
        ----------
        current_page : int, optional
            現在のページ番号（デフォルト: 0）
        total_results : int, optional
            検索結果の総数（デフォルト: 0）
        page_size : int, optional
            1ページあたりの結果数（デフォルト: 10）
            
        Returns:
        ----------
        discord.ui.View
            生成されたビュー
        """
        nav_view = discord.ui.View(timeout=None)
        total_pages = (total_results + page_size - 1) // page_size
        
        prev_button = discord.ui.Button(
            label="前へ", 
            style=discord.ButtonStyle.secondary,
            custom_id=f"search_prev:{current_page}:{total_results}",
            disabled=current_page <= 0
        )
        nav_view.add_item(prev_button)
        
        next_button = discord.ui.Button(
            label="次へ", 
            style=discord.ButtonStyle.primary,
            custom_id=f"search_next:{current_page}:{total_results}",
            disabled=current_page >= total_pages - 1
        )
        nav_view.add_item(next_button)
        
        new_search_button = discord.ui.Button(
            label="新しい検索", 
            style=discord.ButtonStyle.success,
            custom_id="search_new_button"
        )
        nav_view.add_item(new_search_button)
        
        return nav_view
    
    @staticmethod
    def build_search_ui_components(database) -> Dict:
        """検索UI用のコンポーネントを生成
        
        Parameters:
        ----------
        database : pd.DataFrame
            検索対象のデータベース
            
        Returns:
        ----------
        Dict
            UI要素の辞書
        """
        # タイプの選択肢を取得
        type_options = sorted(database['タイプ1'].unique().tolist())
        type_select = discord.ui.Select(
            placeholder="タイプで絞り込む",
            custom_id="search_type_select",
            min_values=0,
            max_values=2,
            options=[
                discord.SelectOption(label=type_name, value=type_name)
                for type_name in type_options
            ]
        )
        
        # 世代の選択肢を取得
        gen_options = sorted(database['初登場世代'].unique().tolist())
        gen_select = discord.ui.Select(
            placeholder="世代で絞り込む",
            custom_id="search_gen_select",
            min_values=0,
            max_values=len(gen_options),  # 実際の世代数に合わせる
            options=[
                discord.SelectOption(label=f"第{gen}世代", value=str(gen))
                for gen in gen_options
            ]
        )
        
        # 進化段階の選択肢を取得
        evo_options = sorted(database['進化段階'].unique().tolist())
        evo_select = discord.ui.Select(
            placeholder="進化段階で絞り込む",
            custom_id="search_evo_select",
            min_values=0,
            max_values=len(evo_options),  # 実際の進化段階数に合わせる
            options=[
                discord.SelectOption(label=evo_stage, value=evo_stage)
                for evo_stage in evo_options
            ]
        )
        
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
    
    @staticmethod
    def process_stat_expression_for_display(expr_dict: Dict, expression_str: str, 
                                          processed_conditions: Dict) -> None:
        """種族値条件をUI表示用に整理する
        
        Parameters:
        ----------
        expr_dict : Dict
            parse_stat_expressionの結果辞書
        expression_str : str
            元の条件式文字列
        processed_conditions : Dict
            処理済みの条件辞書
        """
        if expr_dict['type'] == 'total':
            if '合計' not in processed_conditions:
                processed_conditions['合計'] = []
            processed_conditions['合計'].append(expression_str)
        elif expr_dict['type'] == 'simple':
            stat_key = expr_dict['stat'].upper() if 'stat' in expr_dict else expression_str[0].upper()
            if stat_key in BASE_STATS_DICT:
                stat_name = BASE_STATS_DICT[stat_key]
                if stat_name not in processed_conditions:
                    processed_conditions[stat_name] = []
                
                display_expr = expression_str
                display_expr = re.sub(r'^' + re.escape(stat_key), stat_name, display_expr, flags=re.IGNORECASE)
                processed_conditions[stat_name].append(display_expr)
        elif expr_dict['type'] == 'equality':
            if '数式' not in processed_conditions:
                processed_conditions['数式'] = []
            
            display_expr = expression_str
            for stat, col_name in BASE_STATS_DICT.items():
                display_expr = re.sub(r'\b' + re.escape(stat) + r'\b', col_name, display_expr, flags=re.IGNORECASE)
            
            processed_conditions['数式'].append(display_expr)
        else:
            if '数式' not in processed_conditions:
                processed_conditions['数式'] = []
                
            display_expr = expression_str
            for stat, col_name in BASE_STATS_DICT.items():
                display_expr = re.sub(r'\b' + re.escape(stat) + r'\b', col_name, display_expr, flags=re.IGNORECASE)
            
            processed_conditions['数式'].append(display_expr)

async def show_search_ui(interaction: discord.Interaction) -> None:
    """検索条件入力用のUIを表示する
    
    Parameters:
    ----------
    interaction : discord.Interaction
        Discordのインタラクションオブジェクト
    """
    searcher = PokemonSearcher()
    
    search_embed = discord.Embed(
        title="ポケモンサーチャー",
        description="下のセレクトメニューから検索条件を選択するか、直接入力ボタンから条件を追加してください。",
        color=0x00FF7F
    )
    search_embed.set_footer(text="No.27 ポケモンサーチャー")

    search_embed.add_field(
        name="現在の検索条件(query)",
        value="```\n(なし)\n```",
        inline=False
    )
    
    search_embed.add_field(
        name="検索条件(query)の入力方法",
        value="**検索条件の基本ルール**\n"
              "- 検索条件はスペース区切りで羅列してください\n"
              "- 上書きしない場合, 同一カテゴリ内の条件は自動的にOR条件になります\n"
              "- 上書きしない場合, 異なるカテゴリ間の条件は自動的にAND条件になります\n"
              "**対応カテゴリ**\n"
              "- タイプ: タイプ名を入力（例: みず）\n"
              "- 地方: 「ジョウト」「ホウエン」など\n"
              "- 世代: 世代の数字を入力（例: 8）\n"
              "- 進化段階: 「最終進化」「進化しない」など\n"
              "- 特性: 「ふゆう」「テクニシャン」など\n"
              "- 種族値: 「こうげき130」「S102」など\n"
              "**種族値演算**: 種族値の条件指定（H/A/B/C/D/S/sum）\n"
              "- 比較演算子: `H>=100` `A>150` `S<=80` `D=90`\n"
              "- 等値演算子: `A==C` `A+100==C` `H==B==D`\n"
              "- 算術演算子: `A+C>=200` `((H+75)*(B+20)*(D+20))/((B+D+40))>10044`\n"
              "**論理演算子**: 条件の組み合わせ\n"
              "- OR演算子: `いわ|はがね`（いわタイプまたははがねタイプ）\n"
              "- AND演算子: `みず&S>100`（みずタイプかつすばやさ>100）\n"
              "- 複合条件: `でんき&S>=120|ひこう&S>=100`\n"
              "**例**: ```/search query: かくとう テクニシャン 3 A>=130 S>=70 最終進化```",
        inline=False
    )
    search_view = discord.ui.View(timeout=None)
    
    components = SearchResultFormatter.build_search_ui_components(searcher.database)
    for component in components.values():
        search_view.add_item(component)
    
    await interaction.response.send_message(
        embed=search_embed,
        view=search_view,
        ephemeral=True
    )

async def perform_search(interaction: discord.Interaction, filter_words: List[str]) -> None:
    """ポケモン検索を実行し結果を表示する
    
    Parameters:
    ----------
    interaction : discord.Interaction
        Discordのインタラクションオブジェクト
    filter_words : List[str]
        検索条件のリスト
    """
    # モーダルからの送信の場合はdeferを呼び出さない
    if not interaction.response.is_done():
        await interaction.response.defer()

    searcher = PokemonSearcher()
    
    filter_dict = searcher.make_filter_dict(filter_words)
    searched_df, _ = searcher.search(filter_dict)
    
    if len(searcher.current_results) > 0:
        search_embed = SearchResultFormatter.build_search_embed(searcher, 0, filter_words)
        
        if len(searcher.current_results) > 10:
            nav_view = SearchResultFormatter.build_pagination_view(0, len(searcher.current_results))
            await interaction.followup.send(embed=search_embed, view=nav_view)
        else:
            await interaction.followup.send(embed=search_embed)
    else:
        no_result_embed = discord.Embed(
            title="検索結果なし",
            description=f"条件「{' '.join(filter_words)}」に一致するポケモンは見つかりませんでした。",
            color=0xFF0000
        )
        await interaction.followup.send(embed=no_result_embed)

async def handle_search_button(interaction: discord.Interaction, button_id: str) -> None:
    """検索関連ボタンの処理を行う
    
    Parameters:
    ----------
    interaction : discord.Interaction
        Discordのインタラクションオブジェクト
    button_id : str
        ボタンのID
    """
    if button_id == "search_execute_button":
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
        embed = interaction.message.embeds[0]
        embed.set_field_at(
            0,
            name="現在の検索条件",
            value="```\n(なし)\n```",
            inline=False
        )
        await interaction.response.edit_message(embed=embed)
        
    elif button_id == "search_modal_button":
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
        await show_search_ui(interaction)

async def handle_search_select_menu(interaction: discord.Interaction, custom_id: str, 
                                  values: List[str]) -> None:
    """検索選択メニューの処理を行う
    
    Parameters:
    ----------
    interaction : discord.Interaction
        Discordのインタラクションオブジェクト
    custom_id : str
        メニューのID
    values : List[str]
        選択された値のリスト
    """
    output_log(f"[DEBUG] セレクトメニュー処理開始: custom_id={custom_id}, values={values}")
    
    embed = interaction.message.embeds[0]
    current_query_field = embed.fields[0]
    
    current_query = current_query_field.value.strip("```\n")
    if current_query == "(なし)":
        current_query = ""
    
    output_log(f"[DEBUG] 現在のクエリ: {current_query}")
    new_query = current_query
    
    # セレクトメニューの取得
    select_menu = None
    output_log(f"[DEBUG] コンポーネント数: {len(interaction.message.components)}")
    
    for component in interaction.message.components:
        output_log(f"[DEBUG] コンポーネントタイプ: {type(component)}")
        if hasattr(component, 'children'):
            output_log(f"[DEBUG] 子要素数: {len(component.children)}")
            for child in component.children:
                output_log(f"[DEBUG] 子要素タイプ: {type(child)}, custom_id: {getattr(child, 'custom_id', None)}")
                if isinstance(child, (discord.ui.Select, discord.components.SelectMenu)) and child.custom_id == custom_id:
                    select_menu = child
                    break
            if select_menu:
                break
    
    output_log(f"[DEBUG] セレクトメニュー取得: {select_menu is not None}")
    
    if select_menu:
        if custom_id == "search_type_select":
            # タイプの条件をすべて削除
            words = new_query.split()
            # &を含む条件を探して削除
            filtered_words = []
            for word in words:
                if not any(type_name in word for type_name in [option.value for option in select_menu.options]):
                    filtered_words.append(word)
            new_query = " ".join(filtered_words)
            
            # 新しいタイプをAND条件で追加
            if values:
                type_condition = "&".join(values)
                new_query += f" {type_condition}"
            output_log(f"[DEBUG] タイプ条件更新: {new_query}")
        
        elif custom_id == "search_gen_select":
            # 世代の条件をすべて削除
            words = new_query.split()
            gen_options = [option.value for option in select_menu.options]
            filtered_words = [word for word in words if word not in gen_options]
            new_query = " ".join(filtered_words)
            
            # 新しい世代を追加
            for gen in values:
                if gen not in new_query.split():
                    new_query += f" {gen}"
            output_log(f"[DEBUG] 世代条件更新: {new_query}")
        
        elif custom_id == "search_evo_select":
            # 進化段階の条件をすべて削除
            words = new_query.split()
            evo_options = [option.value for option in select_menu.options]
            filtered_words = [word for word in words if word not in evo_options]
            new_query = " ".join(filtered_words)
            
            # 新しい進化段階を追加
            for evo in values:
                if evo not in new_query.split():
                    new_query += f" {evo}"
            output_log(f"[DEBUG] 進化段階条件更新: {new_query}")
    
    new_query = new_query.strip()
    if not new_query:
        new_query = "(なし)"
    
    output_log(f"[DEBUG] 最終的なクエリ: {new_query}")
    
    embed.set_field_at(
        0,
        name="現在の検索条件",
        value=f"```\n{new_query}\n```",
        inline=False
    )
    
    try:
        await interaction.response.edit_message(embed=embed)
        output_log(f"[DEBUG] メッセージ更新成功")
    except Exception as e:
        output_log(f"[ERROR] メッセージ更新失敗: {str(e)}")

async def handle_pagination(interaction: discord.Interaction, current_page: int, 
                          direction: str, total_results: int, filter_words: List[str]) -> None:
    """ページネーションを処理する関数
    
    Parameters:
    ----------
    interaction : discord.Interaction
        Discordのインタラクションオブジェクト
    current_page : int
        現在のページ番号
    direction : str
        ページ移動方向（"prev" or "next"）
    total_results : int
        検索結果の総数
    filter_words : List[str]
        検索条件のリスト
    """
    searcher = PokemonSearcher()
    
    next_page = max(0, current_page - 1) if direction == "prev" else current_page + 1
    
    await interaction.response.defer()
    
    filter_dict = searcher.make_filter_dict(filter_words)
    searcher.search(filter_dict)
    
    search_embed = SearchResultFormatter.build_search_embed(searcher, next_page, filter_words)
    nav_view = SearchResultFormatter.build_pagination_view(next_page, total_results)
    
    await interaction.followup.edit_message(
        message_id=interaction.message.id,
        embed=search_embed,
        view=nav_view
    )


