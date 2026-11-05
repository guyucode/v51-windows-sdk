V51 GPU MILP + GPU LP SDK 0.2.0 Preview
=====================================

平台：macOS 15及以上、Apple Silicon、原生 ARM64 CPython 3.9。
这是供 Python 调用的链接库预览版；保留整个 SDK 目录，包括 runtime。
不含求解器实现源码、原理文档、私有模型或 EXE。

两个入口：
- libv51_milp.dylib：GPU MILP 搜索。当前连续补全依赖 CPU HiGHS IPX；
  不是全 GPU MILP，不承诺找到最优解或在短预算内找到可行解。
- libv51_lp.dylib：独立 GPU LP 单个/同结构批量求解，原始与对偶违反
  标准1e-7，相对间隙1e-6。该独立后端尚未替换MILP默认连续后端。

环境
----
本次在 Apple Silicon macOS 实机验证。运行依赖须安装在同一个 CPython
3.9 环境；本次验证版本：
  numpy==2.0.2
  scipy==1.13.1
  torch==2.8.0
  highspy==1.15.1

例如使用 CPython 3.9 创建虚拟环境后安装：
  python3.9 -m venv .venv
  .venv/bin/python -m pip install numpy==2.0.2 scipy==1.13.1 torch==2.8.0 highspy==1.15.1
  .venv/bin/python test_example.py

其他 Python ABI、Windows、Intel Mac 不支持本次新包；旧 Windows DLL
另见仓库 v0.1.0-preview。不能把本次验证结论直接用于旧 Windows 包。

Python 使用
-----------
v51.py 只是公开客户端绑定；实现位于二进制中。

  from v51 import MILPSolver, LPSolver

  result = MILPSolver(seconds=5, seed=11).solve(milp_model)
  if result.get("validated"):
      print(result["solution"], result["objective"])

  with LPSolver(lp_model, capacity=16) as solver:
      print(solver.compilation)  # 创建与离线结构开销单列
      batch = solver.solve([{}, {"rhs": new_rhs}], seconds=2)
      for point in batch.get("results", []):
          if point["qualified"]:
              print(point["continuous"], point["metrics"])

test_example.py 包含可直接运行的两个小模型，不需要私有数据。

输入
----
线性最小化，约束 A x >= rhs，稀疏索引从0开始。
模型字段：c、offset、lower、upper、rhs、row、col、value。
MILP另需binary；可用integer标记一般整数变量。null表示单侧无界。
LP入口只接受连续变量。二次目标不支持。

同一个LP句柄中矩阵系数和变量类型不变，可批量更新rhs、c、lower、
upper、offset。单个求解使用solver.solve()，批量使用字典列表。
底层还接受continuous_scale、continuous_cost_multiplier作为显式输入
变换；默认1，不会自动调参。通常直接提供需要的rhs/c/边界即可。
若返回template_miss_requires_regrouping，应按更新后的模型重新创建句柄。
不把未知或未找到解当作不可行证明。

当前LP约化系统自由变量上限192、屏障约束上限4096，默认批量容量16；
已测批量1/8/16。超出支持范围可能在创建时返回错误。未宣称支持任意
规模的稀疏LP，也未提供完整不可行/无界证书。MILP一般路径也有支持
范围，查看status/backend并只使用validated=true的解。

精度与时间
----------
LP主要计算使用FP32，关键状态和核验采用补偿表示；不是全程纯FP32。
本包二进制在六个既有LP结构的300个结果上独立核验通过；MILP通过
装配模型、一般整数混合模型及示例的原约束/整数性检查。另测空域、
无界边界模型与非法输入状态。这些是预览版验证，不代表广泛基准领先。

seconds是后端协作式在线预算，不是强制终止；初始化、提交、回读、
JSON转换可能使完整调用稍晚。查看python_full_call_seconds，LP另列
compilation/first_online_discovery_seconds。未通过核验的结果不得当作解。
MILP首次编译可能耗尽很短预算；示例采用默认5秒。没有CPU MIP回退。

ABI与线程
---------
使用ctypes.PyDLL，不能用会释放GIL的ctypes.CDLL。需要调用方CPython
运行时；不是脱离Python可独立运行的通用C库。公开JSON ABI：
  v51_milp_solve_json(model_json, options_json) -> UTF-8 JSON
  v51_lp_create_json(model_json, options_json) -> 包含handle的JSON
  v51_lp_solve_json(updates_json, {handle, seconds}) -> JSON
  v51_lp_destroy_json({handle}) -> JSON
  v51_version() -> UTF-8版本字符串
所有参数均为const char* JSON，返回字符串由库管理，下一次调用前复制。
同一LP句柄串行使用。MILP须由Python主线程调用；不要同时调用两个MILP
搜索。v51.py提供串行客户端锁。退出时关闭LP句柄。

校验与依赖声明
--------------
SHA256SUMS.txt提供文件校验。第三方运行依赖由各自项目许可管理，
未打包其实现；licenses保留相关构建工具声明。SDK仅供当前预览验证。
