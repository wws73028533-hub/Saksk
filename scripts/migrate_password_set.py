# -*- coding: utf-8 -*-
"""
迁移脚本：为所有有密码的老用户设置 has_password_set=1
"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.core.utils.database import get_db

def migrate_password_set():
    """迁移所有老用户的has_password_set字段"""
    app = create_app()
    
    with app.app_context():
        conn = get_db()
        
        try:
            # 检查has_password_set字段是否存在
            cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if 'has_password_set' not in cols:
                print('[迁移] 添加has_password_set字段...')
                conn.execute('ALTER TABLE users ADD COLUMN has_password_set INTEGER DEFAULT 0')
                conn.commit()
                print('[迁移] 字段添加成功')
            
            # 先查看所有用户的情况
            print('\n[迁移] 检查所有用户情况...')
            all_users = conn.execute('''
                SELECT id, username, email, 
                       CASE WHEN password_hash IS NOT NULL AND password_hash != '' THEN 1 ELSE 0 END as has_password,
                       has_password_set
                FROM users
            ''').fetchall()
            
            print(f'[迁移] 总用户数: {len(all_users)}')
            for user in all_users:
                print(f'  - 用户ID {user["id"]}: username={user["username"]}, email={user["email"]}, has_password={user["has_password"]}, has_password_set={user["has_password_set"]}')
            
            # 策略1：更新没有邮箱的老用户（通过用户名注册）
            count_no_email = conn.execute('''
                SELECT COUNT(*) as count
                FROM users 
                WHERE password_hash IS NOT NULL 
                AND password_hash != '' 
                AND (email IS NULL OR email = '')
                AND (has_password_set != 1 OR has_password_set IS NULL)
            ''').fetchone()
            
            need_update_no_email = count_no_email['count'] if count_no_email else 0
            
            if need_update_no_email > 0:
                print(f'\n[迁移] 发现 {need_update_no_email} 个无邮箱的老用户需要更新')
                result1 = conn.execute('''
                    UPDATE users 
                    SET has_password_set = 1 
                    WHERE password_hash IS NOT NULL 
                    AND password_hash != '' 
                    AND (email IS NULL OR email = '')
                    AND (has_password_set != 1 OR has_password_set IS NULL)
                ''')
                print(f'[迁移] ✓ 已更新 {result1.rowcount} 个无邮箱的老用户')
            
            # 策略2：更新有邮箱但可能是老用户的用户
            # 判断标准：有邮箱 + has_password_set=0 + 有password_hash
            # 这些用户可能是老用户后来绑定了邮箱，也可能是新用户
            # 为了安全，我们假设：如果用户可以通过密码登录（有password_hash），且has_password_set=0
            # 那么很可能是老用户后来绑定了邮箱，应该设置为1
            # 但新用户（邮箱验证码注册）的has_password_set应该保持为0
            # 
            # 更安全的做法：只更新那些创建时间较早的用户（在邮箱验证码注册功能之前）
            # 或者：检查用户是否曾经通过密码登录过（但这需要额外的日志表）
            #
            # 简化方案：如果用户有邮箱且has_password_set=0，检查created_at
            # 如果created_at在某个日期之前（比如2024年之前），认为是老用户
            # 或者：检查是否有其他特征表明是老用户
            
            # 先查看有邮箱但has_password_set=0的用户
            users_with_email = conn.execute('''
                SELECT id, username, email, created_at, has_password_set
                FROM users 
                WHERE password_hash IS NOT NULL 
                AND password_hash != '' 
                AND email IS NOT NULL 
                AND email != ''
                AND (has_password_set = 0 OR has_password_set IS NULL)
            ''').fetchall()
            
            if users_with_email:
                print(f'\n[迁移] 发现 {len(users_with_email)} 个有邮箱但has_password_set=0的用户:')
                for user in users_with_email:
                    print(f'  - ID {user["id"]}: {user["username"]}, email={user["email"]}, created_at={user["created_at"]}')
                
                # 检查这些用户是否可能是老用户
                # 策略1：如果username不是邮箱格式，且不是纯数字，可能是老用户
                # 策略2：如果created_at在2025-12-25之前（邮箱验证码注册功能上线之前），可能是老用户
                old_users_with_email = []
                for user in users_with_email:
                    username = user['username']
                    created_at = user['created_at']
                    
                    # 策略1：username不是邮箱格式
                    if '@' not in username and not username.isdigit():
                        old_users_with_email.append(user['id'])
                    # 策略2：created_at在2025-12-25之前
                    elif created_at and created_at < '2025-12-25':
                        old_users_with_email.append(user['id'])
                        print(f'  [迁移] 用户ID {user["id"]} ({username}) 创建于 {created_at}，判定为老用户')
                
                if old_users_with_email:
                    print(f'\n[迁移] 发现 {len(old_users_with_email)} 个可能是老用户的账户（有邮箱但username不是邮箱格式）')
                    placeholders = ','.join(['?'] * len(old_users_with_email))
                    result2 = conn.execute(f'''
                        UPDATE users 
                        SET has_password_set = 1 
                        WHERE id IN ({placeholders})
                    ''', old_users_with_email)
                    print(f'[迁移] 已更新 {result2.rowcount} 个有邮箱的老用户')
                else:
                    result2 = type('obj', (object,), {'rowcount': 0})()
            else:
                result2 = type('obj', (object,), {'rowcount': 0})()
            
            if need_update_no_email == 0 and (not 'result2' in locals() or result2.rowcount == 0):
                print('\n[迁移] 没有需要更新的用户')
                return
            
            total_updated = (result1.rowcount if need_update_no_email > 0 else 0) + (result2.rowcount if 'result2' in locals() else 0)
            conn.commit()
            
            if total_updated > 0:
                print(f'\n[迁移] 成功为 {total_updated} 个老用户设置 has_password_set=1')
            else:
                print('\n[迁移] 没有需要更新的用户')
            
            # 验证结果
            verify_result = conn.execute('''
                SELECT COUNT(*) as count
                FROM users 
                WHERE password_hash IS NOT NULL 
                AND password_hash != '' 
                AND (email IS NULL OR email = '')
                AND has_password_set = 1
            ''').fetchone()
            
            verified_count = verify_result['count'] if verify_result else 0
            print(f'[迁移] 验证：当前有 {verified_count} 个无邮箱的老用户 has_password_set=1')
            
            # 验证有邮箱的老用户
            verify_result2 = conn.execute('''
                SELECT COUNT(*) as count
                FROM users 
                WHERE password_hash IS NOT NULL 
                AND password_hash != '' 
                AND email IS NOT NULL 
                AND email != ''
                AND has_password_set = 1
            ''').fetchone()
            
            verified_count2 = verify_result2['count'] if verify_result2 else 0
            print(f'[迁移] 验证：当前有 {verified_count2} 个有邮箱的老用户 has_password_set=1')
            
        except Exception as e:
            print(f'[迁移] 迁移失败: {str(e)}')
            import traceback
            traceback.print_exc()
            conn.rollback()

if __name__ == '__main__':
    print('=' * 60)
    print('开始迁移老用户的 has_password_set 字段')
    print('=' * 60)
    migrate_password_set()
    print('=' * 60)
    print('迁移完成')
    print('=' * 60)

