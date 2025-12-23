import subprocess
import sys

def run_code(user_code, input_data=""):
    """
    接收用户代码和输入数据，返回运行结果。
    """
    try:
        # 使用当前 Python 解释器运行代码
        result = subprocess.run(
            [sys.executable, "-c", user_code],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=2  # 超时时间 2 秒
        )
        
        if result.returncode == 0:
            return {"status": "Success", "output": result.stdout.strip()}
        else:
            return {"status": "Error", "output": result.stderr}

    except subprocess.TimeoutExpired:
        return {"status": "Timeout", "output": "运行超时！请检查死循环。"}
    except Exception as e:
        return {"status": "SystemError", "output": str(e)}