"""
调试 MuMu12 nemu IPC 连接问题
"""
import ctypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def debug_nemu_connect():
    """调试 nemu_connect 函数"""

    nemu_folder = r"C:\Program Files\Netease\MuMu Player 12"

    # 查找 DLL
    dll_paths = [
        os.path.join(nemu_folder, 'shell', 'sdk', 'external_renderer_ipc.dll'),
        os.path.join(nemu_folder, 'nx_main', 'sdk', 'external_renderer_ipc.dll'),
    ]

    dll_path = None
    for p in dll_paths:
        if os.path.exists(p):
            dll_path = p
            print(f"找到 DLL: {p}")
            break

    if not dll_path:
        print("未找到 DLL!")
        return

    # 加载 DLL
    print(f"\n加载 DLL: {dll_path}")
    lib = ctypes.CDLL(dll_path)

    # 查看导出函数
    print("\n尝试不同的参数格式...")

    instance_id = 0

    # 方式 1: 直接字符串
    print(f"\n方式 1: lib.nemu_connect('{nemu_folder}', {instance_id})")
    try:
        result = lib.nemu_connect(nemu_folder, instance_id)
        print(f"  结果: {result}")
        if result > 0:
            print("  成功!")
            lib.nemu_disconnect(result)
            return
    except Exception as e:
        print(f"  错误: {e}")

    # 方式 2: bytes
    print(f"\n方式 2: lib.nemu_connect(b'{nemu_folder}', {instance_id})")
    try:
        result = lib.nemu_connect(nemu_folder.encode('utf-8'), instance_id)
        print(f"  结果: {result}")
        if result > 0:
            print("  成功!")
            lib.nemu_disconnect(result)
            return
    except Exception as e:
        print(f"  错误: {e}")

    # 方式 3: c_char_p
    print(f"\n方式 3: lib.nemu_connect(c_char_p(b'{nemu_folder}'), {instance_id})")
    try:
        result = lib.nemu_connect(ctypes.c_char_p(nemu_folder.encode('utf-8')), instance_id)
        print(f"  结果: {result}")
        if result > 0:
            print("  成功!")
            lib.nemu_disconnect(result)
            return
    except Exception as e:
        print(f"  错误: {e}")

    # 方式 4: c_wchar_p (Unicode)
    print(f"\n方式 4: lib.nemu_connect(c_wchar_p('{nemu_folder}'), {instance_id})")
    try:
        result = lib.nemu_connect(ctypes.c_wchar_p(nemu_folder), instance_id)
        print(f"  结果: {result}")
        if result > 0:
            print("  成功!")
            lib.nemu_disconnect(result)
            return
    except Exception as e:
        print(f"  错误: {e}")

    # 方式 5: 尝试不同的路径格式
    alt_paths = [
        nemu_folder,
        nemu_folder + "\\",
        nemu_folder.replace("\\", "/"),
        os.path.join(nemu_folder, "nx_main"),
    ]

    print("\n尝试不同的路径...")
    for path in alt_paths:
        print(f"\n  路径: {path}")
        try:
            result = lib.nemu_connect(path, instance_id)
            print(f"  结果: {result}")
            if result > 0:
                print("  成功!")
                lib.nemu_disconnect(result)
                return
        except Exception as e:
            print(f"  错误: {e}")

    print("\n所有尝试都失败了")
    print("\n可能的原因:")
    print("  1. 模拟器未运行")
    print("  2. 模拟器版本不支持此 API")
    print("  3. 需要管理员权限")
    print("  4. 路径格式不正确")


if __name__ == "__main__":
    debug_nemu_connect()
