# -*- coding: utf-8 -*-
"""
科目权限管理服务
"""
from typing import List, Dict, Any, Optional
from app.core.utils.database import get_db
from app.core.utils.subject_permissions import is_admin


class SubjectPermissionService:
    """科目权限管理服务类"""
    
    @staticmethod
    def get_user_subjects(user_id: int) -> Dict[str, Any]:
        """
        获取用户的科目权限信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含用户信息和科目列表的字典
        """
        conn = get_db()
        
        # 获取用户信息
        user = conn.execute(
            'SELECT id, username FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        
        # 获取所有科目及其题目数量
        all_subjects = conn.execute('''
            SELECT s.id, s.name, COUNT(q.id) as question_count
            FROM subjects s
            LEFT JOIN questions q ON s.id = q.subject_id
            GROUP BY s.id, s.name
            ORDER BY s.id
        ''').fetchall()
        
        # 获取用户被限制的科目
        restricted_subjects = conn.execute(
            'SELECT subject_id, restricted_at FROM user_subjects WHERE user_id = ?',
            (user_id,)
        ).fetchall()
        
        restricted_dict = {
            row['subject_id']: row['restricted_at'] 
            for row in restricted_subjects
        }
        
        # 构建科目列表
        subjects_list = []
        restricted_count = 0
        
        for subject in all_subjects:
            subject_id = subject['id']
            is_restricted = subject_id in restricted_dict
            
            subjects_list.append({
                'id': subject_id,
                'name': subject['name'],
                'question_count': subject['question_count'],
                'is_restricted': is_restricted,
                'restricted_at': restricted_dict.get(subject_id)
            })
            
            if is_restricted:
                restricted_count += 1
        
        return {
            'user': {
                'id': user['id'],
                'username': user['username']
            },
            'all_subjects': subjects_list,
            'restricted_count': restricted_count,
            'total_count': len(subjects_list)
        }
    
    @staticmethod
    def restrict_subjects(user_id: int, subject_ids: List[int], admin_id: int) -> Dict[str, Any]:
        """
        限制用户访问指定科目（添加到黑名单）
        
        Args:
            user_id: 用户ID
            subject_ids: 科目ID列表
            admin_id: 操作的管理员ID
            
        Returns:
            操作结果字典
        """
        if not subject_ids:
            raise ValueError("科目ID列表不能为空")
        
        conn = get_db()
        success_count = 0
        
        try:
            for subject_id in subject_ids:
                # 检查科目是否存在
                subject = conn.execute(
                    'SELECT id FROM subjects WHERE id = ?',
                    (subject_id,)
                ).fetchone()
                
                if not subject:
                    continue
                
                # 检查是否已存在限制
                existing = conn.execute(
                    'SELECT id FROM user_subjects WHERE user_id = ? AND subject_id = ?',
                    (user_id, subject_id)
                ).fetchone()
                
                if not existing:
                    conn.execute(
                        '''INSERT INTO user_subjects 
                           (user_id, subject_id, restricted_by)
                           VALUES (?, ?, ?)''',
                        (user_id, subject_id, admin_id)
                    )
                    success_count += 1
            
            conn.commit()
            
            return {
                'restricted_count': success_count,
                'message': f'成功限制 {success_count} 个科目'
            }
        except Exception as e:
            conn.rollback()
            raise Exception(f"限制科目失败: {str(e)}")
    
    @staticmethod
    def unrestrict_subject(user_id: int, subject_id: int) -> None:
        """
        取消用户对指定科目的限制（从黑名单移除）
        
        Args:
            user_id: 用户ID
            subject_id: 科目ID
        """
        conn = get_db()
        
        conn.execute(
            'DELETE FROM user_subjects WHERE user_id = ? AND subject_id = ?',
            (user_id, subject_id)
        )
        conn.commit()
    
    @staticmethod
    def batch_restrict_subjects(
        user_id: int, 
        subject_ids: List[int], 
        action: str,
        admin_id: int
    ) -> Dict[str, Any]:
        """
        批量限制/取消限制科目
        
        Args:
            user_id: 用户ID
            subject_ids: 科目ID列表
            action: 操作类型（'restrict' 或 'unrestrict'）
            admin_id: 操作的管理员ID
            
        Returns:
            操作结果字典
        """
        if action == 'restrict':
            return SubjectPermissionService.restrict_subjects(user_id, subject_ids, admin_id)
        elif action == 'unrestrict':
            conn = get_db()
            success_count = 0
            
            try:
                for subject_id in subject_ids:
                    deleted = conn.execute(
                        'DELETE FROM user_subjects WHERE user_id = ? AND subject_id = ?',
                        (user_id, subject_id)
                    ).rowcount
                    if deleted > 0:
                        success_count += 1
                
                conn.commit()
                
                return {
                    'unrestricted_count': success_count,
                    'message': f'成功取消限制 {success_count} 个科目'
                }
            except Exception as e:
                conn.rollback()
                raise Exception(f"取消限制失败: {str(e)}")
        else:
            raise ValueError(f"不支持的操作类型: {action}")
    
    @staticmethod
    def batch_restrict_users_subjects(
        user_ids: List[int],
        subject_ids: List[int],
        action: str,
        admin_id: int
    ) -> Dict[str, Any]:
        """
        批量为多个用户限制/取消限制多个科目
        
        Args:
            user_ids: 用户ID列表
            subject_ids: 科目ID列表
            action: 操作类型（'restrict' 或 'unrestrict'）
            admin_id: 操作的管理员ID
            
        Returns:
            操作结果字典
        """
        if not user_ids or not subject_ids:
            raise ValueError("用户ID列表和科目ID列表不能为空")
        
        conn = get_db()
        affected_users = 0
        affected_subjects = len(subject_ids)
        
        try:
            for user_id in user_ids:
                # 跳过管理员（管理员不受限制）
                if is_admin(user_id):
                    continue
                
                if action == 'restrict':
                    for subject_id in subject_ids:
                        existing = conn.execute(
                            'SELECT id FROM user_subjects WHERE user_id = ? AND subject_id = ?',
                            (user_id, subject_id)
                        ).fetchone()
                        
                        if not existing:
                            conn.execute(
                                '''INSERT INTO user_subjects 
                                   (user_id, subject_id, restricted_by)
                                   VALUES (?, ?, ?)''',
                                (user_id, subject_id, admin_id)
                            )
                elif action == 'unrestrict':
                    for subject_id in subject_ids:
                        conn.execute(
                            'DELETE FROM user_subjects WHERE user_id = ? AND subject_id = ?',
                            (user_id, subject_id)
                        )
                
                affected_users += 1
            
            conn.commit()
            
            return {
                'affected_users': affected_users,
                'affected_subjects': affected_subjects,
                'message': f'成功为 {affected_users} 个用户{action} {affected_subjects} 个科目'
            }
        except Exception as e:
            conn.rollback()
            raise Exception(f"批量操作失败: {str(e)}")
    
    @staticmethod
    def get_overview_data(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取批量管理页面所需的数据
        
        Args:
            page: 页码
            per_page: 每页数量
            search: 搜索关键词
            
        Returns:
            包含用户列表、科目列表和统计信息的字典
        """
        conn = get_db()
        offset = (page - 1) * per_page
        
        # 构建用户查询
        user_where = 'WHERE 1=1'
        user_params = []
        
        if search:
            user_where += ' AND username LIKE ?'
            user_params.append(f'%{search}%')
        
        # 获取用户总数
        total_users = conn.execute(
            f'SELECT COUNT(1) FROM users {user_where}',
            user_params
        ).fetchone()[0]
        
        # 获取用户列表（带限制科目统计）
        users_sql = f'''
            SELECT u.id, u.username,
                   COUNT(DISTINCT us.subject_id) as restricted_subjects_count
            FROM users u
            LEFT JOIN user_subjects us ON u.id = us.user_id
            {user_where}
            GROUP BY u.id, u.username
            ORDER BY u.id
            LIMIT ? OFFSET ?
        '''
        users = conn.execute(users_sql, user_params + [per_page, offset]).fetchall()
        
        # 获取科目总数
        total_subjects = conn.execute('SELECT COUNT(1) FROM subjects').fetchone()[0]
        
        # 获取科目列表（带限制用户统计）
        subjects = conn.execute('''
            SELECT s.id, s.name, COUNT(q.id) as question_count,
                   COUNT(DISTINCT us.user_id) as restricted_users_count
            FROM subjects s
            LEFT JOIN questions q ON s.id = q.subject_id
            LEFT JOIN user_subjects us ON s.id = us.subject_id
            GROUP BY s.id, s.name
            ORDER BY s.id
        ''').fetchall()
        
        # 获取总限制数
        total_restrictions = conn.execute(
            'SELECT COUNT(1) FROM user_subjects'
        ).fetchone()[0]
        
        return {
            'users': [
                {
                    'id': u['id'],
                    'username': u['username'],
                    'restricted_subjects_count': u['restricted_subjects_count'] or 0,
                    'total_subjects_count': total_subjects
                }
                for u in users
            ],
            'subjects': [
                {
                    'id': s['id'],
                    'name': s['name'],
                    'question_count': s['question_count'],
                    'restricted_users_count': s['restricted_users_count'] or 0
                }
                for s in subjects
            ],
            'stats': {
                'total_users': total_users,
                'total_subjects': total_subjects,
                'total_restrictions': total_restrictions
            },
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_users,
                'pages': (total_users + per_page - 1) // per_page
            }
        }
    
    @staticmethod
    def get_subject_restricted_users(subject_id: int) -> List[int]:
        """
        获取某个科目被限制的用户ID列表
        
        Args:
            subject_id: 科目ID
            
        Returns:
            被限制的用户ID列表
        """
        conn = get_db()
        
        # 检查科目是否存在
        subject = conn.execute(
            'SELECT id FROM subjects WHERE id = ?',
            (subject_id,)
        ).fetchone()
        
        if not subject:
            raise ValueError(f"科目 {subject_id} 不存在")
        
        # 获取被限制的用户ID列表
        rows = conn.execute(
            'SELECT DISTINCT user_id FROM user_subjects WHERE subject_id = ?',
            (subject_id,)
        ).fetchall()
        
        return [row['user_id'] for row in rows]




