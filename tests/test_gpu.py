"""测试 CnOCR GPU 配置"""
import sys
sys.path.insert(0, "./")

print("=" * 60)
print("GPU 环境检测")
print("=" * 60)

# 1. 检查 PyTorch
print("\n[1] PyTorch 检测:")
try:
    import torch
    print(f"  PyTorch 版本: {torch.__version__}")
    print(f"  CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA 版本: {torch.version.cuda}")
        print(f"  GPU 设备: {torch.cuda.get_device_name(0)}")
except ImportError as e:
    print(f"  PyTorch 未安装: {e}")

# 2. 检查 CnOCR 后端
print("\n[2] CnOCR 后端检测:")
try:
    from cnocr import CnOcr

    # 检查默认后端
    ocr_default = CnOcr(rec_model_name='densenet_lite_136-fc')
    print(f"  默认 rec_model_backend: {getattr(ocr_default, 'rec_model_backend', 'unknown')}")

    # 查看 rec_model 类型
    if hasattr(ocr_default, 'rec_model'):
        print(f"  rec_model 类型: {type(ocr_default.rec_model)}")
        if hasattr(ocr_default.rec_model, 'model'):
            print(f"  内部 model 类型: {type(ocr_default.rec_model.model)}")

except Exception as e:
    print(f"  错误: {e}")

# 3. 性能对比测试
print("\n[3] 性能对比测试:")
try:
    import numpy as np
    import time
    from cnocr import CnOcr

    test_img = np.random.randint(0, 255, (32, 100, 3), dtype=np.uint8)

    # 测试不同配置
    configs = [
        {"name": "默认 (ONNX CPU)", "params": {"rec_model_name": "densenet_lite_136-fc"}},
        {"name": "ONNX + context=gpu", "params": {"rec_model_name": "densenet_lite_136-fc", "context": "gpu"}},
        {"name": "PyTorch CPU", "params": {"rec_model_name": "densenet_lite_136-fc", "rec_model_backend": "pytorch", "context": "cpu"}},
        {"name": "PyTorch GPU", "params": {"rec_model_name": "densenet_lite_136-fc", "rec_model_backend": "pytorch", "context": "gpu"}},
    ]

    for cfg in configs:
        print(f"\n  {cfg['name']}:")
        try:
            # 重置 GPU 内存统计
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.empty_cache()
                mem_before = torch.cuda.memory_allocated()

            ocr = CnOcr(**cfg['params'])

            # 预热
            for _ in range(3):
                ocr.ocr(test_img)

            # 计时
            times = []
            for _ in range(20):
                t0 = time.time()
                ocr.ocr(test_img)
                times.append(time.time() - t0)

            avg_time = sum(times) / len(times) * 1000
            print(f"    平均耗时: {avg_time:.1f}ms")

            if torch.cuda.is_available():
                mem_after = torch.cuda.memory_allocated()
                mem_used = (mem_after - mem_before) / 1024 / 1024
                print(f"    GPU 内存增量: {mem_used:.1f}MB")

        except Exception as e:
            print(f"    失败: {e}")

except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
