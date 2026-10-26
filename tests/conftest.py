import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.pop("ANTHROPIC_API_KEY", None)
