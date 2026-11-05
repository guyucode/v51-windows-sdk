V51 Windows v0.3.0 Test Preview — GPU MILP + batched GPU LP
========================================================

Windows ARM64 / x64 DLL，Python客户端仅需标准库。无EXE、求解器实现源码、
原理文档或私有模型。两个功能共用同一个v51_solver.dll，并非两个独立DLL。
这是有限范围的测试预览，不承诺通用MILP最优性或超过HiGHS。

支持范围
--------
Solver：GPU MILP候选搜索，包括原结构路径和通用稀疏矩阵路径；支持二进制、
一般整数、混合连续、min/max目标。原模型验算独立执行。严格GPU模式不会
把WARP或CPU候选搜索冒充GPU。小模型的CPU精确证明可在GPU搜索前直接解决，
检查metadata.gpu_used、cpu_exact_search_for_proof，不能将其计作GPU收益。

LPBatch：从Mac移植的同结构批量GPU内点法数值后端。每个LP独立维护收敛、
步长和精化状态；CPU按固定GPU阶段顺序提交工作，只在chunk（默认4次Newton
步）之间检查整体预算，Newton内部不逐步回读标量。主要方向计算使用FP32，
状态/残差另有补偿精度和CPU原模型核验，不能称全程纯单精度。

Windows LP前端当前仅消去固定变量；自由变量<=192、屏障行<=4096、批量
容量1..64。Mac完整结构压缩及GPU参数生成/恢复链尚未全部移植。原始r80
固定赋值LP有859个连续列，当前Windows LP直接接口超规模，不标记为通过；
设施及生产四组固定赋值通过移植算子的Mac GPU核对。这些不等同于Windows
GPU实机验证或完整Mac功能等价。MILP一般矩阵入口不采用上述192列LP限制。

每个LP的矩阵系数、类型和有限边界拓扑须与代表模型相同；可更新RHS、目标、
数值上下界、固定值和offset。改变系数或固定/自由拓扑需新建句柄，否则
返回template_miss类错误。参数打包、恢复、原模型核验及界证书仍由CPU执行，
计入在线时间。没有CPU Newton数值回退，也没有外部HiGHS运行时依赖。

正确性及证明
------------
未找到解、内点法停滞、分解/精化失败，均不能作为不可行证明。
LPBatch无证书时返回unknown或feasible，不宣称已证明不可行/无界。

validated：原模型在1e-7数值标准下可行。
qualified：LP原约束及对偶误差<=1e-7、相对gap<=1e-6，且存在可核验保守界。
optimal_within_tolerance：满足上述数值标准，不是精确最优证明。
optimality_proven / proof_complete：只有完整精确证书通过核验才置true。
gap=0、设备收敛状态或qualified不能替代完整证明。

Solver的小模型CPU精确证明上限：原变量16、原约束64、256证明节点，另有
时间和有界精确算术限制。支持精确最优树/不可行树、空域、简单箱域无界证书；
复杂无界问题没有完整证明能力。LPBatch当前只返回保守对偶界证书，完整精确
证明可单独提交Solver。CPU证明成本计入Solver预算，proof_seconds=0禁用。

best_bound为null表示无可用界；gap为null表示无法计算。min界为下界，max界
为上界。verify_certificate会针对提供的原模型重新核验。证书格式可能升级。
本次保留并回归v0.1大数相消错误可行问题，并校验精确证明与返回数值点
的目标一致性；显著负间隙不直接夹成零来判定高质量，不能继续信任旧v0.1的验算结论。

验证状态
--------
具体结果以包内validation.json、Windows CI报告及Release说明为准。
Mac GPU执行移植后的算子、原Mac内核、CPU数值参考和HiGHS的160个批量LP
对照通过；另有混合可行/无解、无界、等式、固定变量、max、弱方向、工作区
污染/重排、下界证书篡改回归。Windows ARM64 / x64分别执行19组回归：9组证书/契约检查（含32个小模型），
5组通用MILP软件执行，5组批量LP软件执行。具体通过状态见随包实际报告。
WARP是Windows Direct3D软件执行，不是GPU硬件性能测试。
尚无发布者在Windows真实GPU上完成的MILP/LP硬件验证，不能标为GPU实测通过。

调用
----
  from v51 import Solver, LPBatch

  with Solver(seconds=2, backend="gpu", proof_seconds=0) as s:
      r = s.solve(milp_model)
      print(r["status"], r.get("objective"), r.get("best_bound"))

  with LPBatch(lp_model, capacity=16, chunk=4) as s:
      r = s.solve([lp_model, updated_full_lp_model], seconds=2)
      for item in r.get("results", []):
          print(item["status"], item.get("objective"), item.get("relative_gap"))

LPBatch.solve当前要求完整模型列表，不沿用Mac版的部分字段更新接口。
输入c/lower/upper/rhs/row/col/value，binary与integer可省略，offset默认0；
约束Ax>=rhs，COO索引从0开始，null为无界。只支持线性目标，不支持MIQP。
同一原生句柄串行使用；C调用者须保证destroy不与solve/cancel并发。

原生C接口（UTF-8 JSON、cdecl，返回字符串由DLL管理）
  void* v51_create(const char* options_json);
  const char* v51_solve_json(void* handle,const char* model_json);
  void v51_cancel(void* handle); void v51_destroy(void* handle);
  void* v51_lp_create_json(const char* representative,const char* options_json);
  const char* v51_lp_solve_batch_json(void* handle,const char* full_models,double seconds);
  void v51_lp_cancel(void* handle); void v51_lp_destroy(void* handle);
  const char* v51_verify_certificate_json(const char* model,const char* certificate);
  const char* v51_last_error(); const char* v51_version();

测试
----
  python test_windows.py             # 实际GPU MILP + LP，以及CPU证书检查
  python test_windows.py --cpu-only  # 只检查DLL和CPU精确证书，不算GPU通过
  python test_windows.py --warp-lp   # CPU证书 + Direct3D WARP MILP/LP软件验证

报告windows_check_result.json记录每项通过/失败，即使测试失败也保存结果。
WARP仅可显式作为验证后端：Solver(backend="warp_validation")或
LPBatch(..., validation_backend="warp")；结果明确标记软件执行，LP返回
GPU_executed=false、CPU_software_shader=true，不是严格GPU模式的隐式回退。
ARM64 Python加载arm64 DLL；x64 Python加载x64 DLL，包括ARM上的x64模拟进程。

seconds为协作式预算；正在执行的chunk、初始化、回读与核验可能造成超时。
在线时间包含参数处理、上传、求解、轮询、恢复、核验与界证书。创建/编译成本
另列offline_full_call_seconds；Python完整调用另列python_full_call_seconds。
当前未提供Windows GPU吞吐或端到端性能胜过HiGHS的实测结论。
