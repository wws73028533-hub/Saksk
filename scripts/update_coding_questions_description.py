# -*- coding: utf-8 -*-
"""
更新编程题的description字段脚本
用于为已存在的题目添加description（存储到explanation字段）
"""
import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app
from app.core.utils.database import get_db

# 题目数据（与add_test_coding_questions.py中的相同）
QUESTIONS_DATA = {
    '反转字符串': '''编写一个函数，其作用是将输入的字符串反转过来。输入字符串以字符数组 s 的形式给出。

不要给另外的数组分配额外的空间，你必须原地修改输入数组、使用 O(1) 的额外空间解决这一问题。''',
    '最大子数组和': '''给你一个整数数组 nums ，请你找出一个具有最大和的连续子数组（子数组最少包含一个元素），返回其最大和。

子数组 是数组中的一个连续部分。''',
    '合并两个有序数组': '''给你两个按 非递减顺序 排列的整数数组 nums1 和 nums2，另有两个整数 m 和 n ，分别表示 nums1 和 nums2 中元素的数目。

请你 合并 nums2 到 nums1 中，使合并后的数组同样按 非递减顺序 排列。

注意：最终，合并后数组不应由函数返回，而是存储在数组 nums1 中。为了应对这种情况，nums1 的初始长度为 m + n，其中前 m 个元素表示应合并的元素，后 n 个元素为 0 ，应忽略。nums2 的长度为 n 。''',
    '有效的括号': '''给定一个只包括 '('，')'，'{'，'}'，'['，']' 的字符串 s ，判断字符串是否有效。

有效字符串需满足：

1. 左括号必须用相同类型的右括号闭合。
2. 左括号必须以正确的顺序闭合。
3. 每个右括号都有一个对应的相同类型的左括号。''',
    '爬楼梯': '''假设你正在爬楼梯。需要 n 阶你才能到达楼顶。

每次你可以爬 1 或 2 个台阶。你有多少种不同的方法可以爬到楼顶呢？''',
    '两数之和': '''给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出 和为目标值 target  的那 两个 整数，并返回它们的数组下标。

你可以假设每种输入只会对应一个答案。但是，数组中同一个元素在答案里不能重复出现。

你可以按任意顺序返回答案。'''
}


def update_questions():
    """更新题目的description字段"""
    app = create_app()
    
    with app.app_context():
        db = get_db()
        updated_count = 0
        
        for title, description in QUESTIONS_DATA.items():
            try:
                # 查找题目
                question = db.execute(
                    "SELECT id FROM questions WHERE content = ? AND q_type = '编程题'",
                    (title,)
                ).fetchone()
                
                if question:
                    question_id = question['id']
                    # 更新explanation字段（存储description）
                    db.execute(
                        "UPDATE questions SET explanation = ? WHERE id = ? AND q_type = '编程题'",
                        (description, question_id)
                    )
                    db.commit()
                    print(f"[OK] 更新题目: {title} (ID: {question_id})")
                    updated_count += 1
                else:
                    print(f"[SKIP] 题目 '{title}' 不存在，跳过")
                    
            except Exception as e:
                print(f"[ERROR] 更新题目 '{title}' 失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n完成！共更新 {updated_count} 道题目")


if __name__ == '__main__':
    update_questions()






























