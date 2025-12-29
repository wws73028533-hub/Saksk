# -*- coding: utf-8 -*-
"""
添加测试编程题脚本
用于向数据库中添加一些经典的编程题用于测试
"""
import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app
from app.modules.coding.services.question_service import QuestionService
from app.modules.coding.schemas.question_schemas import QuestionCreateSchema
from app.core.utils.database import get_db


def get_or_create_subject(name: str) -> int:
    """获取或创建科目"""
    db = get_db()
    row = db.execute('SELECT id FROM subjects WHERE name = ?', (name,)).fetchone()
    if row:
        return row['id']
    
    # 创建新科目
    cursor = db.execute('INSERT INTO subjects (name) VALUES (?)', (name,))
    db.commit()
    return cursor.lastrowid


def add_test_questions():
    """添加测试题目"""
    app = create_app()
    
    with app.app_context():
        # 获取或创建"算法"科目
        subject_id = get_or_create_subject('算法')
        
        # 定义测试题目
        test_questions = [
            {
                'title': '两数之和',
                'difficulty': 'easy',
                'description': '''给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出 和为目标值 target  的那 两个 整数，并返回它们的数组下标。

你可以假设每种输入只会对应一个答案。但是，数组中同一个元素在答案里不能重复出现。

你可以按任意顺序返回答案。''',
                'examples': [
                    {
                        'input': 'nums = [2,7,11,15], target = 9',
                        'output': '[0,1]',
                        'explanation': '因为 nums[0] + nums[1] == 9 ，返回 [0, 1] 。'
                    },
                    {
                        'input': 'nums = [3,2,4], target = 6',
                        'output': '[1,2]',
                        'explanation': ''
                    },
                    {
                        'input': 'nums = [3,3], target = 6',
                        'output': '[0,1]',
                        'explanation': ''
                    }
                ],
                'constraints': [
                    '2 <= nums.length <= 10^4',
                    '-10^9 <= nums[i] <= 10^9',
                    '-10^9 <= target <= 10^9',
                    '只会存在一个有效答案'
                ],
                'code_template': '''def twoSum(nums, target):
    """
    :type nums: List[int]
    :type target: int
    :rtype: List[int]
    """
    pass''',
                'test_cases_json': json.dumps({
                    'test_cases': [
                        {'input': '4\n2\n7\n11\n15\n9', 'output': '[0, 1]', 'description': '示例1'},
                        {'input': '3\n3\n2\n4\n6', 'output': '[1, 2]', 'description': '示例2'},
                        {'input': '2\n3\n3\n6', 'output': '[0, 1]', 'description': '示例3'}
                    ],
                    'hidden_cases': [
                        {'input': '5\n1\n2\n3\n4\n5\n9', 'output': '[3, 4]'},
                        {'input': '5\n-1\n-2\n-3\n-4\n-5\n-8', 'output': '[2, 4]'}
                    ]
                }, ensure_ascii=False),
                'hints': ['可以使用哈希表来存储已遍历的元素和其索引', '遍历数组，对于每个元素，检查 target - nums[i] 是否在哈希表中']
            },
            {
                'title': '反转字符串',
                'difficulty': 'easy',
                'description': '''编写一个函数，其作用是将输入的字符串反转过来。输入字符串以字符数组 s 的形式给出。

不要给另外的数组分配额外的空间，你必须原地修改输入数组、使用 O(1) 的额外空间解决这一问题。''',
                'examples': [
                    {
                        'input': 's = ["h","e","l","l","o"]',
                        'output': '["o","l","l","e","h"]',
                        'explanation': ''
                    },
                    {
                        'input': 's = ["H","a","n","n","a","h"]',
                        'output': '["h","a","n","n","a","H"]',
                        'explanation': ''
                    }
                ],
                'constraints': [
                    '1 <= s.length <= 10^5',
                    's[i] 都是 ASCII 码表中的可打印字符'
                ],
                'code_template': '''def reverseString(s):
    """
    Do not return anything, modify s in-place instead.
    :type s: List[str]
    """
    pass''',
                'test_cases_json': json.dumps({
                    'test_cases': [
                        {'input': '["h","e","l","l","o"]', 'output': '["o","l","l","e","h"]', 'description': '示例1'},
                        {'input': '["H","a","n","n","a","h"]', 'output': '["h","a","n","n","a","H"]', 'description': '示例2'}
                    ],
                    'hidden_cases': [
                        {'input': '["a"]', 'output': '["a"]'},
                        {'input': '["a","b"]', 'output': '["b","a"]'}
                    ]
                }, ensure_ascii=False),
                'hints': ['使用双指针，一个指向开头，一个指向结尾', '交换两个指针指向的元素，然后向中间移动']
            },
            {
                'title': '最大子数组和',
                'difficulty': 'medium',
                'description': '''给你一个整数数组 nums ，请你找出一个具有最大和的连续子数组（子数组最少包含一个元素），返回其最大和。

子数组 是数组中的一个连续部分。''',
                'examples': [
                    {
                        'input': 'nums = [-2,1,-3,4,-1,2,1,-5,4]',
                        'output': '6',
                        'explanation': '连续子数组 [4,-1,2,1] 的和最大，为 6 。'
                    },
                    {
                        'input': 'nums = [1]',
                        'output': '1',
                        'explanation': ''
                    },
                    {
                        'input': 'nums = [5,4,-1,7,8]',
                        'output': '23',
                        'explanation': ''
                    }
                ],
                'constraints': [
                    '1 <= nums.length <= 10^5',
                    '-10^4 <= nums[i] <= 10^4'
                ],
                'code_template': '''def maxSubArray(nums):
    """
    :type nums: List[int]
    :rtype: int
    """
    pass''',
                'test_cases_json': json.dumps({
                    'test_cases': [
                        {'input': '[-2,1,-3,4,-1,2,1,-5,4]', 'output': '6', 'description': '示例1'},
                        {'input': '[1]', 'output': '1', 'description': '示例2'},
                        {'input': '[5,4,-1,7,8]', 'output': '23', 'description': '示例3'}
                    ],
                    'hidden_cases': [
                        {'input': '[-1]', 'output': '-1'},
                        {'input': '[-2,-1]', 'output': '-1'}
                    ]
                }, ensure_ascii=False),
                'hints': ['使用动态规划思想', '如果当前子数组的和为负数，则重新开始计算']
            },
            {
                'title': '合并两个有序数组',
                'difficulty': 'easy',
                'description': '''给你两个按 非递减顺序 排列的整数数组 nums1 和 nums2，另有两个整数 m 和 n ，分别表示 nums1 和 nums2 中元素的数目。

请你 合并 nums2 到 nums1 中，使合并后的数组同样按 非递减顺序 排列。

注意：最终，合并后数组不应由函数返回，而是存储在数组 nums1 中。为了应对这种情况，nums1 的初始长度为 m + n，其中前 m 个元素表示应合并的元素，后 n 个元素为 0 ，应忽略。nums2 的长度为 n 。''',
                'examples': [
                    {
                        'input': 'nums1 = [1,2,3,0,0,0], m = 3, nums2 = [2,5,6], n = 3',
                        'output': '[1,2,2,3,5,6]',
                        'explanation': '需要合并 [1,2,3] 和 [2,5,6] 。合并结果是 [1,2,2,3,5,6] 。'
                    },
                    {
                        'input': 'nums1 = [1], m = 1, nums2 = [], n = 0',
                        'output': '[1]',
                        'explanation': '需要合并 [1] 和 [] 。合并结果是 [1] 。'
                    },
                    {
                        'input': 'nums1 = [0], m = 0, nums2 = [1], n = 1',
                        'output': '[1]',
                        'explanation': '需要合并的数组是 [] 和 [1] 。合并结果是 [1] 。'
                    }
                ],
                'constraints': [
                    'nums1.length == m + n',
                    'nums2.length == n',
                    '0 <= m, n <= 200',
                    '1 <= m + n <= 200',
                    '-10^9 <= nums1[i], nums2[j] <= 10^9'
                ],
                'code_template': '''def merge(nums1, m, nums2, n):
    """
    Do not return anything, modify nums1 in-place instead.
    :type nums1: List[int]
    :type m: int
    :type nums2: List[int]
    :type n: int
    """
    pass''',
                'test_cases_json': json.dumps({
                    'test_cases': [
                        {'input': '[1,2,3,0,0,0]\\n3\\n[2,5,6]\\n3', 'output': '[1,2,2,3,5,6]', 'description': '示例1'},
                        {'input': '[1]\\n1\\n[]\\n0', 'output': '[1]', 'description': '示例2'},
                        {'input': '[0]\\n0\\n[1]\\n1', 'output': '[1]', 'description': '示例3'}
                    ],
                    'hidden_cases': [
                        {'input': '[4,5,6,0,0,0]\\n3\\n[1,2,3]\\n3', 'output': '[1,2,3,4,5,6]'},
                        {'input': '[1,2,3,0,0]\\n3\\n[4,5]\\n2', 'output': '[1,2,3,4,5]'}
                    ]
                }, ensure_ascii=False),
                'hints': ['从后往前合并可以避免覆盖nums1中的元素', '使用三个指针，分别指向nums1有效部分的末尾、nums2的末尾和合并后的末尾']
            },
            {
                'title': '有效的括号',
                'difficulty': 'easy',
                'description': '''给定一个只包括 '('，')'，'{'，'}'，'['，']' 的字符串 s ，判断字符串是否有效。

有效字符串需满足：

1. 左括号必须用相同类型的右括号闭合。
2. 左括号必须以正确的顺序闭合。
3. 每个右括号都有一个对应的相同类型的左括号。''',
                'examples': [
                    {
                        'input': 's = "()"',
                        'output': 'True',
                        'explanation': ''
                    },
                    {
                        'input': 's = "()[]{}"',
                        'output': 'True',
                        'explanation': ''
                    },
                    {
                        'input': 's = "(]"',
                        'output': 'False',
                        'explanation': ''
                    }
                ],
                'constraints': [
                    '1 <= s.length <= 10^4',
                    's 仅由括号 \'()[]{}\' 组成'
                ],
                'code_template': '''def isValid(s):
    """
    :type s: str
    :rtype: bool
    """
    pass''',
                'test_cases_json': json.dumps({
                    'test_cases': [
                        {'input': '"()"', 'output': 'True', 'description': '示例1'},
                        {'input': '"()[]{}"', 'output': 'True', 'description': '示例2'},
                        {'input': '"(]"', 'output': 'False', 'description': '示例3'}
                    ],
                    'hidden_cases': [
                        {'input': '"([)]"', 'output': 'False'},
                        {'input': '"{[]}"', 'output': 'True'}
                    ]
                }, ensure_ascii=False),
                'hints': ['使用栈来处理括号匹配', '遇到左括号入栈，遇到右括号检查栈顶是否匹配']
            },
            {
                'title': '爬楼梯',
                'difficulty': 'easy',
                'description': '''假设你正在爬楼梯。需要 n 阶你才能到达楼顶。

每次你可以爬 1 或 2 个台阶。你有多少种不同的方法可以爬到楼顶呢？''',
                'examples': [
                    {
                        'input': 'n = 2',
                        'output': '2',
                        'explanation': '有两种方法可以爬到楼顶。\\n1. 1 阶 + 1 阶\\n2. 2 阶'
                    },
                    {
                        'input': 'n = 3',
                        'output': '3',
                        'explanation': '有三种方法可以爬到楼顶。\\n1. 1 阶 + 1 阶 + 1 阶\\n2. 1 阶 + 2 阶\\n3. 2 阶 + 1 阶'
                    }
                ],
                'constraints': [
                    '1 <= n <= 45'
                ],
                'code_template': '''def climbStairs(n):
    """
    :type n: int
    :rtype: int
    """
    pass''',
                'test_cases_json': json.dumps({
                    'test_cases': [
                        {'input': '2', 'output': '2', 'description': '示例1'},
                        {'input': '3', 'output': '3', 'description': '示例2'}
                    ],
                    'hidden_cases': [
                        {'input': '1', 'output': '1'},
                        {'input': '4', 'output': '5'},
                        {'input': '5', 'output': '8'}
                    ]
                }, ensure_ascii=False),
                'hints': ['这是一个斐波那契数列问题', '使用动态规划，f(n) = f(n-1) + f(n-2)']
            }
        ]
        
        # 添加题目
        created_count = 0
        for question_data in test_questions:
            try:
                # 检查题目是否已存在
                db = get_db()
                existing = db.execute(
                    "SELECT id FROM questions WHERE content = ? AND q_type = '编程题'",
                    (question_data['title'],)
                ).fetchone()
                
                if existing:
                    print(f"[SKIP] 题目 '{question_data['title']}' 已存在，跳过")
                    continue
                
                # 创建题目Schema
                schema = QuestionCreateSchema(
                    title=question_data['title'],
                    subject_id=subject_id,
                    difficulty=question_data['difficulty'],
                    description=question_data['description'],
                    examples=question_data.get('examples', []),
                    constraints=question_data.get('constraints', []),
                    code_template=question_data.get('code_template', ''),
                    programming_language='python',
                    time_limit=5,
                    memory_limit=128,
                    test_cases_json=question_data['test_cases_json'],
                    hints=question_data.get('hints', []),
                    is_enabled=True
                )
                
                # 创建题目
                question = QuestionService.create_question(schema)
                print(f"[OK] 成功添加题目: {question_data['title']} (ID: {question['id']})")
                created_count += 1
                
            except Exception as e:
                print(f"[ERROR] 添加题目 '{question_data['title']}' 失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n完成！共添加 {created_count} 道题目")


if __name__ == '__main__':
    add_test_questions()

