V51 Windows v0.2.0 Test Preview — ARM64 / x64
===========================================

这是针对Windows v0.1问题的独立测试预览，并不表示三个问题在所有模型上
都已解决，也不是Mac v0.2功能完全等价移植。

已改动
------
1. 修复原始行验算中的大数相消漏洞。v0.1可能把违反约束的点误报可行；
   新版使用保守验算，无法可靠确认时不接纳为解。
2. 严格GPU模式增加通用稀疏矩阵路径，不再仅因模型不是匹配/差分结构
   就直接返回unsupported_gpu_structure。实际GPU支持仍取决于驱动和资源。
3. 增加best_bound、absolute_gap、relative_gap、optimality_proven、
   proof_complete、termination_reason及证书核验接口。
4. 支持标准max/maximize目标规范化、一般整数及无显式上界的小模型证明。

证明范围和CPU工作必须区分
------------------------
小规模模型可由自研CPU精确证明模块直接解决并给出可核验证书。当前上限：
原变量16、原约束64、最多256证明节点，另有时间和精确算术范围限制。
这会进行CPU精确分支工作，不是GPU计算，也没有隐藏调用HiGHS MIP。
若证明已解决模型，metadata.gpu_used=false，GPU搜索可能完全跳过。
可设置proof_seconds=0禁用此模块，测试实际GPU搜索路径。

其他模型可能只有可行解和较弱的全局界，也可能返回unknown/超时。
best_bound为null表示没有可用界；gap为null表示无法计算。gap=0本身不
等同于最优性证明。只有proof_complete=true、证书核验通过时才使用数学
终止结论；最优性还需optimality_proven=true。最小化界为下界，最大化界
为上界。validated表示原模型在1e-7数值标准下的可行点；证书针对原始
二进制浮点输入的精确模型。不要把数值可行标记当作精确最优证明。

当前不包含Mac版GPU批量内点法LP后端。连续LP可提交同一模型接口，但
不能沿用Mac批量LP的速度、精度覆盖或功能等价结论。

平台及验证状态
--------------
Windows 11、64位Python，客户端只需Python标准库，无需PyTorch或HiGHS。
原生ARM64 Python选arm64/v51_solver.dll；x64 Python（包括ARM机器上
模拟运行的x64 Python）选x64/v51_solver.dll，绑定会自动识别。

发布者在Mac完成了数学/接口验证、与HiGHS测试预言机的180个随机小模型
对照、负面/边界回归和证书篡改检查，两架构DLL交叉编译及导出检查，
另做HLSL静态语法验证。没有Windows Direct3D GPU实机执行环境：
Windows_runtime_tested=false。不要把交叉编译成功当作实机验证通过。

运行
----
  python test_windows.py

该命令先检查小模型证书，再实际测试通用GPU和原结构GPU路径。若GPU
不可用会失败，不会用CPU测试结果伪装GPU成功。只检查数学/接口可用：
  python test_windows.py --cpu-only

请回传windows_check_result.json；如果测试中途失败，附控制台报错。

调用示例
--------
  from v51 import Solver
  with Solver(seconds=5, backend="gpu", proof_seconds=0.05) as s:
      result = s.solve(model)
      print(result["status"], result["best_bound"], result["relative_gap"])
      if result.get("validated"):
          print(result["solution"], result["objective"])
      if result.get("certificate"):
          print(s.verify_certificate(model, result["certificate"]))

输入c、lower、upper、rhs、row、col、value；binary/integer标记变量类型，
binary可省略。约束Ax>=rhs，COO索引从0开始，null为无界，offset默认0。
只支持线性目标。objective_sense可min或max。每句柄串行调用，使用后
close；返回字符串由DLL管理。v51.py只是客户端绑定，不含求解器实现。
backend=gpu不允许CPU替代GPU候选搜索，但CPU证明/预处理仍可运行；
backend=auto显式允许CPU候选回退，请查看实际backend和gpu_used。

预算为协作式，初始化和回传可能超出预算。没有找到点不代表不可行。
复杂无界问题尚无完整证明能力，精确算术或工作预算耗尽时不宣称最优。
包内只有DLL、调用/回归脚本、验证摘要和许可；无EXE、实现源码、原理
文档或私有模型。旧v0.1存在验算缺陷，建议停止使用其可行性结论。
