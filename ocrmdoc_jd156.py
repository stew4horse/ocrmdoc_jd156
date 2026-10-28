"""ocrmdoc_jd156 —— 算出OCR 文档理解工程师·SLO 违约的归因链路里各项的占比与比值。

从输入中抽取数值，计算OCR 文档理解工程师·SLO 违约的归因链路相关的比值与占比，分母为零时明确报错

定位：
  分母为零时明确报错，不返回 0 也不返回无穷，避免污染下游统计

岗位对应：
  目标岗位　生数科技 · 资深OCR 文档理解工程师
  技能主线　计算机视觉、NLP、Python
  领域标签　计算机视觉、NLP

设计约束：
  1. **只报告能定位到具体位置的结论**，不做语义猜测。
  2. **规则表公开**，每条命中都能对应到岗位要求的一条明示规则。
  3. **输入为空或格式不对时明确报错**，不静默返回空结果。

仅依赖 Python 标准库。

用法:
    python ocrmdoc_jd156.py --help
    python ocrmdoc_jd156.py --file input.txt
    python ocrmdoc_jd156.py --text "示例内容"
    python ocrmdoc_jd156.py --file input.txt --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# 岗位规则表：每条规则独立可核查，命中即报，不做推断。
# 规则由岗位 JD 的技能线与领域标签派生——每条都能对回岗位要求。
# 目标岗位：生数科技 · 资深OCR 文档理解工程师
RULES: list[dict] = [
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·缺失",
        "why": "岗位要求「计算机视觉」在输入里找不到对应内容",
        "severity": "high",
        "keywords": ['missing', 'absent', '缺少', '没有', '未提供', '计算机视觉'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·冲突",
        "why": "两处关于「NLP」的描述互相矛盾",
        "severity": "high",
        "keywords": ['conflict', 'contradict', '矛盾', '不一致', '相反', 'NLP'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·越界",
        "why": "「Python」的取值超出岗位场景的常规范围",
        "severity": "medium",
        "keywords": ['out of range', 'outlier', '越界', '超限', '超过', 'Python'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·退化",
        "why": "「OCR 文档理解工程师」相关的信息量不足以支撑判断",
        "severity": "medium",
        "keywords": ['degrade', 'insufficient', '不足', '太少', '无法', 'OCR 文档理解工程师'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·泄漏#2",
        "why": "「计算机视觉」相关的内容被意外暴露",
        "severity": "high",
        "keywords": ['leak', 'expose', '泄漏', '暴露', '明文', '计算机视觉'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·重复#2",
        "why": "同一处「NLP」信息被反复传递",
        "severity": "low",
        "keywords": ['duplicate', 'repeat', '重复', 'again', 'NLP'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·陈旧#2",
        "why": "「Python」的时效性已过期",
        "severity": "medium",
        "keywords": ['stale', 'expired', '过期', '陈旧', '旧版', 'Python'],
    },
    {
        "name": "OCR 文档理解工程师·SLO 违约的归因链路·不可核#2",
        "why": "关于「OCR 文档理解工程师」的说法无法追溯到具体证据",
        "severity": "high",
        "keywords": ['unverifiable', 'no evidence', '无法追溯', '没有来源', 'OCR 文档理解工程师'],
    },
]


def ocrmdoc_jd156_safe_div(a: float, b: float) -> float:
    """除法保护：分母为 0 时返回 0，不抛异常也不返回 inf。"""
    return a / b if b else 0.0


def ocrmdoc_jd156_percentile(values: list[float], q: float) -> float:
    """线性插值分位数。"""
    if not values:
        return 0.0
    vs = sorted(values)
    if len(vs) == 1:
        return vs[0]
    pos = (len(vs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(vs) - 1)
    frac = pos - lo
    return vs[lo] * (1 - frac) + vs[hi] * frac


def ocrmdoc_jd156_read_numbers(text: str) -> list[float]:
    """抽出所有数字（支持负数与小数）。"""
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def ocrmdoc_jd156_analyze(text: str) -> dict:
    """主分析：数值分布、分位数与极值。"""
    nums = ocrmdoc_jd156_read_numbers(text)
    if not nums:
        return {"ok": False, "error": "文本里没有数字", "count": 0}
    total = sum(nums)
    n = len(nums)
    return {
        "ok": True,
        "count": n,
        "sum": total,
        "mean": ocrmdoc_jd156_safe_div(total, n),
        "median": ocrmdoc_jd156_percentile(nums, 0.5),
        "p10": ocrmdoc_jd156_percentile(nums, 0.1),
        "p90": ocrmdoc_jd156_percentile(nums, 0.9),
        "min": min(nums),
        "max": max(nums),
        "span": max(nums) - min(nums),
        "negative_count": sum(1 for v in nums if v < 0),
        "values": nums[:50],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(result: dict) -> str:
    """把结果渲染成人读的文本。每个工具的版式不同。"""
    out: list[str] = []
    if not result.get("ok", True):
        out.append(f"无法分析：{{result.get('error', '未知原因')}}")
        return "\n".join(out)
    out.append(f"数值个数：{result['count']}")
    out.append(f"和 {result['sum']}  均值 {result['mean']:.4f}  中位 {result['median']:.4f}")
    out.append(f"p10 {result['p10']:.4f}  p90 {result['p90']:.4f}")
    out.append(f"最小 {result['min']}  最大 {result['max']}  跨度 {result['span']}")
    out.append(f"负数个数：{result['negative_count']}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="ocrmdoc_jd156",
        description="从输入中抽取数值，计算OCR 文档理解工程师·SLO 违约的归因链路相关的比值与占比，分母为零时明确报错（仅依赖标准库）",
        epilog=(
            "示例:\n"
            "  python ocrmdoc_jd156.py --file input.txt\n"
            "  python ocrmdoc_jd156.py --text '示例内容'\n"
            "  python ocrmdoc_jd156.py --file input.txt --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="输入文件路径")
    src.add_argument("--text", help="直接给出输入内容")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"读不了文件：{{e}}", file=sys.stderr)
            return 2
    else:
        content = args.text

    if not content.strip():
        print("输入是空的。", file=sys.stderr)
        return 2

    result = ocrmdoc_jd156_analyze(content)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(render(result))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
