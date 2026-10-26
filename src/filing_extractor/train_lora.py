"""LoRA fine-tune of a small open model (Hugging Face Transformers + PEFT).

Runs on a GPU (Colab or Kaggle, see notebooks/) or, with --smoke, a few steps on CPU.
Metrics and parameters go to MLflow. The adapter is saved to --out.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from filing_extractor.config import OUTPUT_DIR
from filing_extractor.data import Passage, load_passages
from filing_extractor.lora_format import (
    EncodedExample,
    build_completion,
    build_prompt,
    encode_example,
    pad_batch,
)

DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
MLFLOW_DB = OUTPUT_DIR / "mlflow.db"
EXPERIMENT = "filing-extractor"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=DEFAULT_MODEL, help="Qwen2.5-0.5B/1.5B or Llama-3.2-1B")
    p.add_argument("--out", type=Path, default=OUTPUT_DIR / "lora-qwen2.5-0.5b")
    p.add_argument("--epochs", type=float, default=3.0)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--max-length", type=int, default=768)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps")
    p.add_argument("--max-train-examples", type=int, default=0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--smoke", action="store_true", help="tiny CPU run: 12 examples, 6 steps")
    p.add_argument("--no-mlflow", action="store_true")
    return p.parse_args(argv)


def encode_passages(tokenizer, passages: list[Passage], max_length: int) -> list[EncodedExample]:
    out = []
    eos = tokenizer.eos_token or ""
    for p in passages:
        prompt_ids = tokenizer(build_prompt(p.text), add_special_tokens=False)["input_ids"]
        completion_ids = tokenizer(build_completion(p.gold, eos), add_special_tokens=False)[
            "input_ids"
        ]
        out.append(encode_example(prompt_ids, completion_ids, max_length))
    return out


def pick_device_and_dtype():
    import torch

    if torch.cuda.is_available():
        bf16 = torch.cuda.is_bf16_supported()
        return "cuda", torch.bfloat16 if bf16 else torch.float16
    return "cpu", torch.float32


def train(args: argparse.Namespace) -> dict[str, float | int | str]:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device, dtype = pick_device_and_dtype()

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype)
    model = get_peft_model(
        model,
        LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            target_modules=TARGET_MODULES,
            task_type="CAUSAL_LM",
        ),
    )
    model.to(device)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())

    train_passages = load_passages(split="train")
    if args.max_train_examples:
        train_passages = train_passages[: args.max_train_examples]
    examples = encode_passages(tokenizer, train_passages, args.max_length)

    steps_per_epoch = max(1, len(examples) // (args.batch_size * args.grad_accum))
    total_steps = args.max_steps or max(1, int(steps_per_epoch * args.epochs))
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0
    )
    scheduler = get_linear_schedule_with_warmup(optimizer, max(1, total_steps // 10), total_steps)

    run = _start_mlflow(args, trainable, total, len(examples), device)
    model.train()
    step, micro, losses = 0, 0, []
    started = time.time()
    while step < total_steps:
        order = list(range(len(examples)))
        random.shuffle(order)
        for start in range(0, len(order), args.batch_size):
            batch = [examples[i] for i in order[start : start + args.batch_size]]
            ids, mask, labels = pad_batch(batch, tokenizer.pad_token_id)
            out = model(
                input_ids=torch.tensor(ids, device=device),
                attention_mask=torch.tensor(mask, device=device),
                labels=torch.tensor(labels, device=device),
            )
            (out.loss / args.grad_accum).backward()
            losses.append(out.loss.item())
            micro += 1
            if micro % args.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                step += 1
                recent = sum(losses[-args.grad_accum :]) / args.grad_accum
                print(f"step {step}/{total_steps} loss {recent:.4f}", flush=True)
                _log_metric(run, "train_loss", recent, step)
                if step >= total_steps:
                    break

    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    summary = {
        "base_model": args.model,
        "device": device,
        "train_examples": len(examples),
        "optimizer_steps": step,
        "first_loss": round(losses[0], 4),
        "last_loss": round(sum(losses[-args.grad_accum :]) / args.grad_accum, 4),
        "trainable_params": trainable,
        "total_params": total,
        "seconds": round(time.time() - started, 1),
        "smoke": bool(args.smoke),
    }
    (args.out / "train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _end_mlflow(run, summary, args.out)
    return summary


def _start_mlflow(args, trainable: int, total: int, n_examples: int, device: str):
    if args.no_mlflow:
        return None
    import mlflow

    MLFLOW_DB.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB}")
    mlflow.set_experiment(EXPERIMENT)
    run = mlflow.start_run(run_name=f"lora-{'smoke' if args.smoke else 'train'}")
    mlflow.log_params(
        {
            "model": args.model,
            "kind": "lora-train",
            "lora_r": args.lora_r,
            "lora_alpha": args.lora_alpha,
            "lr": args.lr,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "grad_accum": args.grad_accum,
            "max_length": args.max_length,
            "device": device,
            "train_examples": n_examples,
            "trainable_params": trainable,
            "total_params": total,
            "smoke": args.smoke,
        }
    )
    return run


def _log_metric(run, name: str, value: float, step: int) -> None:
    if run is not None:
        import mlflow

        mlflow.log_metric(name, value, step=step)


def _end_mlflow(run, summary: dict, out: Path) -> None:
    if run is None:
        return
    import mlflow

    mlflow.log_metrics({"first_loss": summary["first_loss"], "last_loss": summary["last_loss"]})
    mlflow.log_artifact(str(out / "train_summary.json"))
    mlflow.end_run()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.smoke:
        args.max_steps = args.max_steps or 6
        args.max_train_examples = args.max_train_examples or 12
        args.batch_size, args.grad_accum, args.max_length = 2, 1, 512
        args.out = args.out if "--out" in (argv or []) else OUTPUT_DIR / "lora-smoke"
    print(json.dumps(train(args), indent=2))


if __name__ == "__main__":
    main()
