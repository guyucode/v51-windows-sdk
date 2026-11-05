# V51 GPU Solver SDK — Binary Preview

GPU MILP 与 GPU LP 两个链接库入口，可由 Python 调用。仅发布二进制、客户端示例和用法，不发布求解器实现源码、原理文档或私有模型。

## 下载

- **[Windows ARM64 / x64 v0.2.0 测试预览](https://github.com/guyucode/v51-windows-sdk/releases/tag/v0.2.0-windows-preview)**：[Windows用法](windows-v0.2/README.txt)。针对v0.1验算缺陷、通用GPU入口及证书输出升级；**Windows GPU实机验证尚未完成**，并非Mac版功能等价移植。

- **[v0.2.0 Preview：macOS Apple Silicon / CPython 3.9](https://github.com/guyucode/v51-windows-sdk/releases/tag/v0.2.0-preview)**：GPU MILP + GPU LP。
- [旧 Windows ARM64 / x64 DLL v0.1.0 Preview](https://github.com/guyucode/v51-windows-sdk/releases/tag/v0.1.0-preview)：**存在已复现的验算缺陷，不建议继续使用**；不包含Mac新 GPU LP 接口。[旧版用法](WINDOWS_v0.1_README.md)。

当前仓库沿用历史名称 `v51-windows-sdk`，Mac v0.2包适用于 macOS 15及以上、Apple Silicon、原生 ARM64 CPython 3.9；Windows v0.2是另一个测试预览包，接口和证明能力范围见其独立说明。

## Mac版两个功能

Windows版使用单独的`v51_solver.dll`和`Solver`客户端，当前不包含Mac批量GPU内点法LP后端。小模型可由自研CPU精确证明模块求解，不能把CPU证明标为GPU完成。

| 入口 | 当前能力与边界 |
|---|---|
| `libv51_milp.dylib` | GPU MILP 搜索；连续补全仍依赖 **CPU HiGHS IPX**，不是全 GPU MILP。不保证短预算内找到可行解或证明最优。 |
| `libv51_lp.dylib` | 独立 GPU LP，支持单个及同结构批量。当前约化自由变量≤192、屏障约束≤4096，已验证批量1/8/16。尚未替换MILP默认连续后端。 |

这是带明确支持范围的预览版，**不宣称全面超过 HiGHS，也不是成熟通用求解器的替代品**。未找到解不代表不可行。

## Mac版运行

下载并解压 v0.2 ZIP，保留整个目录，包含 `runtime` 二进制模块。需要指定 Python ABI 和运行依赖；不能只复制两个 dylib。

在 **CPython 3.9** 虚拟环境中：

```bash
python -m pip install numpy==2.0.2 scipy==1.13.1 torch==2.8.0 highspy==1.15.1
python test_example.py
```

```python
from v51 import MILPSolver, LPSolver

result = MILPSolver(seconds=5, seed=11).solve(milp_model)
if result.get("validated"):
    print(result["objective"], result["solution"])

with LPSolver(lp_model, capacity=16) as solver:
    batch = solver.solve([{}, {"rhs": updated_rhs}], seconds=2)
    for point in batch.get("results", []):
        if point["qualified"]:
            print(point["metrics"], point["continuous"])
```

模型采用线性最小化、`A x >= rhs`，稀疏索引从0开始；`null` 表示该侧无界。字段和状态见 [完整Mac用法](macos/README.txt)。ZIP内的 `test_example.py` 可直接运行。

`v51.py` 只是客户端绑定，使用 `ctypes.PyDLL` 保持GIL。MILP须由主线程调用；同一LP句柄串行使用。

## 验证与耗时

- 二进制在项目目录外运行，未回退到实现源码。
- GPU LP：六个既有结构、批量1/8/16、300个结果独立核验通过；测试期间禁止调用CPU LP。原始/对偶标准 `1e-7`，相对间隙 `1e-6`；完整Python调用最长约116ms。
- GPU MILP：装配模型、一般整数混合模型及示例通过原约束/整数性检查；另验证空域、无界边界模型和非法输入状态。
- 这些是有限的预览版验证，不代表所有模型的成功率或性能。LP并非全程纯FP32。

`seconds` 是协作式后端预算，首次初始化、提交、回读及JSON转换可能使完整调用稍晚。查看 `python_full_call_seconds`；LP模型创建成本单列。仅使用通过相应核验标记的点。

发布包内 `validation.json`、`SHA256SUMS.txt` 和Release的 `.sha256` 文件提供验证摘要与校验。第三方依赖遵循各自许可，包内保留必要声明。
