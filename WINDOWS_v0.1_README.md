> 已知问题：v0.1存在已复现的浮点验算缺陷，可能误接纳违反原约束的点，不建议继续用于可行性结论。请查看Windows v0.2测试预览及其验证范围。

# V51 Windows DLL

Windows ARM64 / x64 链接库的二进制发布与 Python 调用说明。

从 [Releases](https://github.com/guyucode/v51-windows-sdk/releases) 下载运行包，解压后使用。包内不含 EXE、求解器实现源码、研究记录或原理文档。

## 环境

- Windows 11，64 位 Python。
- 原生 ARM64 Python 使用 `arm64/v51_solver.dll`。
- x64 Python（包括 Windows ARM 上模拟运行的 x64 Python）使用 `x64/v51_solver.dll`。
- Python 调用只依赖标准库，无需安装 PyTorch、NumPy 或 SciPy。
- GPU 功能取决于设备及驱动，自检通过后再用于实际任务。

当前为移植试用版，尚未完成 Windows ARM 实机验证。不能直接沿用其他平台的功能、质量或性能结论。

## Python 调用

在解压目录运行以下代码。将 `model.json` 替换为自己的输入文件：

```python
import ctypes
import json
import struct
import sysconfig
from pathlib import Path

if struct.calcsize("P") != 8:
    raise RuntimeError("需要64位Python")
target = sysconfig.get_platform().lower()
if "arm64" in target:
    arch = "arm64"
elif "amd64" in target or "x86_64" in target:
    arch = "x64"
else:
    raise RuntimeError("不支持的Python平台: " + target)
lib = ctypes.CDLL(str(Path(arch, "v51_solver.dll").resolve()))

lib.v51_create.argtypes = [ctypes.c_char_p]
lib.v51_create.restype = ctypes.c_void_p
lib.v51_solve_json.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.v51_solve_json.restype = ctypes.c_char_p
lib.v51_self_test.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.v51_self_test.restype = ctypes.c_char_p
lib.v51_last_error.argtypes = []
lib.v51_last_error.restype = ctypes.c_char_p
lib.v51_destroy.argtypes = [ctypes.c_void_p]
lib.v51_destroy.restype = None

options = {"seconds": 5, "seed": 11, "backend": "gpu"}
handle = lib.v51_create(json.dumps(options).encode("utf-8"))
if not handle:
    raise RuntimeError(lib.v51_last_error().decode("utf-8"))
try:
    # 先自检；0为CPU自检，1为严格GPU自检。
    check = json.loads(lib.v51_self_test(handle, 1).decode("utf-8"))
    print("GPU self-test:", check.get("passed"))
    if not check.get("passed"):
        raise RuntimeError(json.dumps(check, ensure_ascii=False))

    model = json.loads(Path("model.json").read_text(encoding="utf-8"))
    payload = json.dumps(model, ensure_ascii=False, allow_nan=False).encode("utf-8")
    result = json.loads(lib.v51_solve_json(handle, payload).decode("utf-8"))
    Path("result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(result["status"], result.get("objective"))
finally:
    lib.v51_destroy(handle)
```

## 参数和结果

`backend` 可选：

- `gpu`：严格GPU模式，不能初始化或模型不兼容时返回相应状态，不自动回退。
- `cpu`：CPU功能验证。
- `auto`：允许CPU回退，须查看返回的 `backend` 和 `metadata.gpu_used`。

输入字段：`c`、`lower`、`upper`、`binary`、`rhs`、`row`、`col`、`value`；可选 `offset` 和 `integer`。稀疏索引从0开始，每行约束采用“大于等于右端”，边界中的 `null` 表示该侧无界。目前仅接受线性最小化目标。

检查 `status` 和 `validated`。仅当 `validated=true` 时使用 `solution`；它按原变量顺序返回，`objective` 为原始目标值。未找到解不代表问题不可行，不承诺最优解。

`seconds` 是原生处理预算，返回可能稍晚于截止；截止后的候选不接纳。完整调用耗时应在 Python 侧计量，包含输入转换、DLL调用和结果解码。

每个句柄串行调用；不同句柄独立。返回字符串由库管理，下一次同句柄调用或销毁前应复制。不要自行释放返回字符串。可从其他线程调用 `v51_cancel(handle)` 请求停止；销毁前须等待调用结束。

## 校验与许可

解压包中的 `SHA256SUMS.txt` 提供文件校验值，`licenses` 保留必要的第三方声明。
