import pandas as pd
import os

def create_question_import_template_v2():
    """
    生成题库导入的Excel模板文件（V2），使用分列格式。
    """
    # 1. 创建示例数据
    sample_data = {
        'subject': [
            '计算机网络',
            '计算机网络',
            '操作系统',
            '操作系统',
            '数据结构',
            '数据结构'
        ],
        'q_type': [
            '选择题',
            '多选题',
            '判断题',
            '填空题',
            '填空题',
            '问答题'
        ],
        'content': [
            '下列哪个协议不属于应用层协议？',
            'TCP协议提供的服务包括哪些？',
            '进程是资源分配的基本单位。',
            '操作系统的主要功能包括处理器管理、__管理、设备管理、文件管理和用户接口。',
            '队列是一种__的线性表，栈是一种__的线性表。',
            '简述TCP协议的三次握手过程。'
        ],
        'option_A': ['HTTP', '面向连接', '', '', '', ''],
        'option_B': ['FTP', '流量控制', '', '', '', ''],
        'option_C': ['TCP', '拥塞控制', '', '', '', ''],
        'option_D': ['DNS', '不可靠传输', '', '', '', ''],
        'option_E': ['', '', '', '', '', ''],
        'answer': [
            'C',
            'ABC',
            '正确',
            '', # 填空题的答案移至 blank_n 列
            '', # 填空题的答案移至 blank_n 列
            '第一次握手：客户端发送SYN=1, seq=x到服务器。第二次握手：服务器接收后，回复SYN=1, ACK=1, seq=y, ack=x+1。第三次握手：客户端接收后，发送ACK=1, seq=x+1, ack=y+1。'
        ],
        'blank_1': ['', '', '', '存储;内存', '先进先出;FIFO', ''],
        'blank_2': ['', '', '', '', '后进先出;LIFO', ''],
        'explanation': [
            'TCP是传输层协议，而HTTP, FTP, DNS都是应用层协议。',
            'TCP是面向连接的、可靠的传输协议，提供流量控制和拥塞控制。D是UDP的特点。',
            '在传统的操作系统中，进程是资源分配和调度的基本单位。',
            '操作系统的五大功能之一是存储管理或内存管理。',
            '队列遵循先进先出（FIFO）原则，栈遵循后进先出（LIFO）原则。',
            '这是TCP建立连接的标准过程，确保双方都准备好通信。'
        ]
    }
    sample_df = pd.DataFrame(sample_data)

    # 2. 创建说明数据
    instructions_data = {
        '列名': [
            'subject (科目)',
            'q_type (题型)',
            'content (题干)',
            'option_A, option_B, ...',
            'answer (答案)',
            'blank_1, blank_2, ...',
            'explanation (解析)'
        ],
        '说明': [
            '必填。题目的所属科目，如“计算机网络”。如果科目不存在，系统将自动创建。',
            '必填。题型必须是“选择题”、“多选题”、“判断题”、“填空题”、“问答题”之一。',
            '必填。题目的具体内容。对于填空题，请使用两个下划线 "__" 表示一个填空位。',
            '仅对“选择题”和“多选题”有效。请将每个选项的文本分别填入对应的 option_A, option_B, option_C... 列中。无需填写 "A." 等前缀。',
            '对于“选择题”、“多选题”、“判断题”、“问答题”为必填。\n- 选择题: 对应的正确选项字母，如 "C"。\n- 多选题: 对应的所有正确选项字母，连续书写，如 "ABC"。\n- 判断题: "正确" 或 "错误"。\n- 问答题: 参考答案文本。\n- 填空题: 此列留空。',
            '仅对“填空题”有效。请将每个空的答案分别填入对应的 blank_1, blank_2... 列中。如果一个空有多个可能答案，用一个分号 ";" 隔开。',
            '选填。对题目的详细解释。'
        ]
    }
    instructions_df = pd.DataFrame(instructions_data)

    # 3. 写入Excel文件
    output_path = os.path.join('instance', 'question_import_template.xlsx')
    
    os.makedirs('instance', exist_ok=True)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        sample_df.to_excel(writer, sheet_name='题目示例', index=False)
        instructions_df.to_excel(writer, sheet_name='填写说明', index=False)

        # 调整列宽
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column_letter = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                # 对于说明列，给予更宽的宽度
                if sheet_name == '填写说明' and column_letter == 'B':
                    adjusted_width = 80
                worksheet.column_dimensions[column_letter].width = adjusted_width if adjusted_width < 100 else 100

    print(f"新版模板文件已生成: {output_path}")

if __name__ == '__main__':
    create_question_import_template_v2()
