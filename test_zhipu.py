"""Test script for ZhipuAI integration."""

import os
import sys

# Set environment variables for ZhipuAI
os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

# Set other config
os.environ["LLM_MAX_TOKENS"] = "4096"
os.environ["LLM_TEMPERATURE"] = "0.7"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tools.llm_client import LLMClient


def test_basic_generation():
    """Test basic text generation."""
    print("=" * 60)
    print("Testing ZhipuAI Basic Generation")
    print("=" * 60)

    try:
        client = LLMClient()

        prompt = "你好，请用一句话介绍一下你自己。"

        print(f"\nPrompt: {prompt}")
        print("\nGenerating response...")

        response = client.generate(prompt)

        print(f"\nResponse: {response}")
        print("\n✓ Basic generation test passed!")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_structured_generation():
    """Test structured JSON generation."""
    print("\n" + "=" * 60)
    print("Testing ZhipuAI Structured Generation")
    print("=" * 60)

    try:
        client = LLMClient()

        prompt = """请分析以下算法描述，并以JSON格式返回关键信息：

算法描述：这是一个简单的线性回归算法，使用梯度下降进行优化。
它包含权重参数w和偏置参数b，学习率设置为0.01。

请提取以下信息：
- algorithm_name: 算法名称
- hyperparameters: 超参数字典
- type: 算法类型
"""

        output_format = {
            "algorithm_name": "string",
            "hyperparameters": {},
            "type": "string",
        }

        print(f"\nPrompt: {prompt[:100]}...")
        print("\nGenerating structured response...")

        response = client.generate_structured(prompt, output_format)

        print(f"\nResponse: {response}")
        print("\n✓ Structured generation test passed!")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_algorithm_analysis():
    """Test algorithm analysis with paper content."""
    print("\n" + "=" * 60)
    print("Testing ZhipuAI Algorithm Analysis")
    print("=" * 60)

    try:
        from src.tools.llm_client import LLMClient
        from src.agents.algorithm_analyzer import AlgorithmAnalyzerAgent

        # Create a mock paper content
        paper_content = {
            "title": "A Novel Deep Learning Approach",
            "abstract": "This paper proposes a novel deep learning approach for image classification.",
            "full_text": """
# A Novel Deep Learning Approach

## Abstract
This paper proposes a novel deep learning approach for image classification.

## Introduction
We introduce a new neural network architecture called XYZ-Net.
The architecture uses residual connections and attention mechanisms.

## Method
Our method consists of three main components:
1. Feature extraction backbone
2. Attention module
3. Classification head

The algorithm processes input images through a convolutional backbone,
applies multi-head attention, and performs final classification.

## Experiments
We test on ImageNet and achieve state-of-the-art results.

## Conclusion
Our method achieves 95% accuracy on ImageNet.
""",
        }

        # Create analyzer agent
        agent = AlgorithmAnalyzerAgent()

        # Create state
        state = {"paper_content": paper_content}

        print("\nAnalyzing paper content...")
        print(f"Paper title: {paper_content['title']}")
        print(f"Abstract: {paper_content['abstract'][:80]}...")

        result = agent(state)

        if "errors" in result and result["errors"]:
            print(f"\nErrors: {result['errors']}")
            return False

        if "algorithm_analysis" in result:
            analysis = result["algorithm_analysis"]
            print(f"\n✓ Algorithm analysis completed!")
            print(f"\nAnalysis Result:")
            print(f"  Algorithm Name: {analysis.get('algorithm_name', 'N/A')}")
            print(f"  Algorithm Type: {analysis.get('algorithm_type', 'N/A')}")
            print(f"  Core Logic: {analysis.get('core_logic', 'N/A')[:100]}...")
            return True
        else:
            print("\n✗ Analysis result not found")
            return False

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "ZhipuAI Test Suite" + " " * 29 + "║")
    print("╚" + "═" * 58 + "╝")

    tests = [
        ("Basic Generation", test_basic_generation),
        ("Structured Generation", test_structured_generation),
        ("Algorithm Analysis", test_algorithm_analysis),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return 1
        except Exception as e:
            print(f"\n✗ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 22 + "Test Summary" + " " * 29 + "║")
    print("╠" + "═" * 58 + "╣")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        icon = "✓" if result else "✗"
        status = "PASSED" if result else "FAILED"
        print(f"║ {icon} {test_name:30s} {status:22s} ║")

    print("╠" + "═" * 58 + "╣")
    print(f"║ Total: {passed}/{total} tests passed {' ' * (40 - len(f'Total: {passed}/{total} tests passed'))} ║")
    print("╚" + "═" * 58 + "╝")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
