"""Debug test to find the issue."""

import os
import sys

os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

sys.path.insert(0, "src")

from src.graph.workflow import PaperCoderWorkflow

# Create workflow
workflow = PaperCoderWorkflow({
    "output_dir": "./test_output",
    "skip_validation": True,
})

# Create initial state
state = workflow._create_initial_state("paper_examples/1607.01759v3.pdf")

print("Initial state:")
print("  current_step:", state.get("current_step"))
print("  pdf_path:", state.get("pdf_path"))

# Check next step
next_step = workflow._determine_next_step(state)
print("\nFirst next_step:", next_step)

# Execute first step
print("\nExecuting", next_step, "...")
state = workflow.pdf_reader(state)

print("\nAfter PDF Reader:")
print("  current_step:", state.get("current_step"))
print("  paper_content exists:", state.get("paper_content") is not None)

# Check next step again
next_step2 = workflow._determine_next_step(state)
print("\nSecond next_step:", next_step2)
