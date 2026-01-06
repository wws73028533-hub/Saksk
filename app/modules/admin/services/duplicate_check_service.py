# -*- coding: utf-8 -*-
"""
题目查重服务
负责计算题目相似度、查找重复题目
"""
from typing import Dict, List, Tuple, Any, Optional
import difflib
import re
import json
from app.core.utils.database import get_db


class DuplicateCheckService:
    """题目查重服务"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        标准化文本，用于相似度比较
        
        Args:
            text: 原始文本
            
        Returns:
            标准化后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除标点符号（可选，根据需求决定是否保留）
        # text = re.sub(r'[^\w\s]', '', text)
        # 转换为小写（对于中文可能不需要，但可以保留）
        return text.strip()
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（0-1之间）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度（0-1之间）
        """
        if not text1 or not text2:
            return 0.0
        
        # 标准化文本
        norm1 = DuplicateCheckService.normalize_text(text1)
        norm2 = DuplicateCheckService.normalize_text(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # 如果完全相同
        if norm1 == norm2:
            return 1.0
        
        # 使用SequenceMatcher计算相似度
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        
        return round(similarity, 4)
    
    @staticmethod
    def check_duplicates(subject_id: int, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        检查指定科目中的重复题目
        
        Args:
            subject_id: 科目ID
            similarity_threshold: 相似度阈值（默认0.8，即80%相似）
            
        Returns:
            重复题目对列表，每个元素包含：
            {
                'question1': {...},  # 题目1的完整信息
                'question2': {...},  # 题目2的完整信息
                'similarity': 0.95,  # 相似度
                'similarity_percent': 95  # 相似度百分比
            }
        """
        db = get_db()
        
        # 获取该科目下的所有题目
        questions = db.execute(
            '''
            SELECT id, subject_id, content, q_type, options, answer, explanation, 
                   difficulty, created_at, updated_at
            FROM questions
            WHERE subject_id = ?
            ORDER BY id
            ''',
            (subject_id,)
        ).fetchall()
        
        if len(questions) < 2:
            return []
        
        # 转换为字典列表
        question_list = [dict(q) for q in questions]
        
        # 计算所有题目对的相似度
        duplicates = []
        checked_pairs = set()  # 用于避免重复比较
        
        for i in range(len(question_list)):
            for j in range(i + 1, len(question_list)):
                q1 = question_list[i]
                q2 = question_list[j]
                
                # 跳过同一道题目
                if q1['id'] == q2['id']:
                    continue
                
                # 创建唯一标识符（避免重复比较）
                pair_key = tuple(sorted([q1['id'], q2['id']]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                # 计算题目内容的相似度
                similarity = DuplicateCheckService.calculate_similarity(
                    q1.get('content', '') or '',
                    q2.get('content', '') or ''
                )
                
                # 如果相似度超过阈值，添加到结果中
                if similarity >= similarity_threshold:
                    duplicates.append({
                        'question1': q1,
                        'question2': q2,
                        'similarity': similarity,
                        'similarity_percent': int(similarity * 100)
                    })
        
        # 按相似度降序排序
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        
        return duplicates
    
    @staticmethod
    def get_duplicate_check_results(
        subject_id: int,
        min_similarity: Optional[float] = None,
        max_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        获取查重结果（支持相似度筛选）
        
        Args:
            subject_id: 科目ID
            min_similarity: 最小相似度（0-1之间，可选）
            max_similarity: 最大相似度（0-1之间，可选）
            
        Returns:
            {
                'total_pairs': int,  # 总重复对数
                'duplicates': List[Dict],  # 重复题目对列表
                'subject_id': int,
                'subject_name': str
            }
        """
        db = get_db()
        
        # 获取科目信息
        subject = db.execute(
            'SELECT id, name FROM subjects WHERE id = ?',
            (subject_id,)
        ).fetchone()
        
        if not subject:
            return {
                'total_pairs': 0,
                'duplicates': [],
                'subject_id': subject_id,
                'subject_name': None
            }
        
        subject_name = dict(subject).get('name', '')
        
        # 执行查重
        duplicates = DuplicateCheckService.check_duplicates(subject_id)
        
        # 应用相似度筛选
        if min_similarity is not None or max_similarity is not None:
            filtered_duplicates = []
            for dup in duplicates:
                sim = dup['similarity']
                if min_similarity is not None and sim < min_similarity:
                    continue
                if max_similarity is not None and sim > max_similarity:
                    continue
                filtered_duplicates.append(dup)
            duplicates = filtered_duplicates
        
        return {
            'total_pairs': len(duplicates),
            'duplicates': duplicates,
            'subject_id': subject_id,
            'subject_name': subject_name
        }
    
    @staticmethod
    def save_duplicate_check_record(
        subject_id: int,
        duplicates: List[Dict[str, Any]],
        similarity_threshold: float = 0.8,
        created_by: Optional[int] = None
    ) -> int:
        """
        保存查重记录到数据库
        
        Args:
            subject_id: 科目ID
            duplicates: 重复题目对列表
            similarity_threshold: 相似度阈值
            created_by: 创建者用户ID（可选）
            
        Returns:
            保存的记录ID
        """
        db = get_db()
        
        # 将重复对列表转换为JSON字符串
        duplicates_json = json.dumps(duplicates, ensure_ascii=False, default=str)
        
        cursor = db.execute(
            '''
            INSERT INTO duplicate_check_records 
            (subject_id, total_pairs, duplicates_json, similarity_threshold, created_by)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (subject_id, len(duplicates), duplicates_json, similarity_threshold, created_by)
        )
        db.commit()
        
        return cursor.lastrowid
    
    @staticmethod
    def get_latest_duplicate_check_record(subject_id: int) -> Optional[Dict[str, Any]]:
        """
        获取指定科目的最新查重记录
        
        Args:
            subject_id: 科目ID
            
        Returns:
            查重记录字典，如果不存在则返回None
        """
        db = get_db()
        
        record = db.execute(
            '''
            SELECT id, subject_id, total_pairs, duplicates_json, similarity_threshold,
                   created_by, created_at
            FROM duplicate_check_records
            WHERE subject_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            ''',
            (subject_id,)
        ).fetchone()
        
        if not record:
            return None
        
        record_dict = dict(record)
        
        # 解析JSON数据
        try:
            record_dict['duplicates'] = json.loads(record_dict.get('duplicates_json', '[]'))
        except (json.JSONDecodeError, TypeError):
            record_dict['duplicates'] = []
        
        # 移除JSON字符串字段（已解析）
        record_dict.pop('duplicates_json', None)
        
        return record_dict
    
    @staticmethod
    def perform_and_save_duplicate_check(
        subject_id: int,
        similarity_threshold: float = 0.8,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行查重并保存记录
        
        Args:
            subject_id: 科目ID
            similarity_threshold: 相似度阈值
            created_by: 创建者用户ID（可选）
            
        Returns:
            包含查重结果和记录ID的字典
        """
        # 执行查重
        duplicates = DuplicateCheckService.check_duplicates(subject_id, similarity_threshold)
        
        # 获取科目信息
        db = get_db()
        subject = db.execute(
            'SELECT id, name FROM subjects WHERE id = ?',
            (subject_id,)
        ).fetchone()
        
        subject_name = dict(subject).get('name', '') if subject else ''
        
        # 保存查重记录
        record_id = DuplicateCheckService.save_duplicate_check_record(
            subject_id=subject_id,
            duplicates=duplicates,
            similarity_threshold=similarity_threshold,
            created_by=created_by
        )
        
        return {
            'record_id': record_id,
            'total_pairs': len(duplicates),
            'duplicates': duplicates,
            'subject_id': subject_id,
            'subject_name': subject_name,
            'similarity_threshold': similarity_threshold
        }

