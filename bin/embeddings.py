"""jina-embeddings-v5-omni-small embedding engine (text-only, MLX).

Self-contained model/encoding logic for the /v1/embeddings service. Loads the
repo's own model.py/utils.py (no transformers dependency) and exposes a small,
stable surface the server wires up: resolve_model_dir, resolve_task,
EmbeddingEngine, load_engine.

Thread-safety: EmbeddingEngine does NOT hold a GPU lock. switch_task() mutates
the in-memory weights in place, so encode() must be called under the server's
single global GPU lock (_gpu_queue()) to avoid concurrent task switches.
"""

import importlib.util
import json
import math
import os
import sys

DEFAULT_EMBED_MODEL_ID = "jinaai/jina-embeddings-v5-omni-small-mlx"
MATRYOSHKA_DIMS = {32, 64, 128, 256, 512, 1024}

# USB model base, mirrors server.py.
_USB_BASE = "/Volumes/vault/ai-models"

# input_type -> (task, task_type). task is the LoRA adapter to switch to;
# task_type is the prefix/pooling mode passed to model.encode.
_INPUT_TYPE_MAP = {
    "retrieval.query": ("retrieval", "retrieval.query"),
    "query": ("retrieval", "retrieval.query"),
    "retrieval.passage": ("retrieval", "retrieval.passage"),
    "retrieval.document": ("retrieval", "retrieval.passage"),
    "passage": ("retrieval", "retrieval.passage"),
    "document": ("retrieval", "retrieval.passage"),
    "text-matching": ("text-matching", "text-matching"),
    "classification": ("classification", "classification"),
    "clustering": ("clustering", "clustering"),
}
_DEFAULT_TASK = ("retrieval", "retrieval.passage")


def resolve_model_dir(model_id: str = DEFAULT_EMBED_MODEL_ID) -> str:
    """Resolve a local dir with model.py/utils.py/model.safetensors, offline-first.

    Order:
      1. env JINA_EMBED_MODEL_DIR if set and exists
      2. USB direct: /Volumes/vault/ai-models/<model_id>
      3. huggingface_hub.snapshot_download(model_id) (local cache; already cached)
    """
    env_dir = os.environ.get("JINA_EMBED_MODEL_DIR")
    if env_dir and os.path.isdir(env_dir):
        return os.path.abspath(env_dir)

    usb_dir = os.path.join(_USB_BASE, *model_id.split("/"))
    if os.path.isdir(usb_dir):
        return os.path.abspath(usb_dir)

    from huggingface_hub import snapshot_download

    return os.path.abspath(snapshot_download(model_id))


def resolve_task(input_type: str | None) -> tuple[str, str]:
    """Map an OpenClaw input_type to (task, task_type). Unknown -> retrieval.passage."""
    if not input_type:
        return _DEFAULT_TASK
    return _INPUT_TYPE_MAP.get(input_type.strip().lower(), _DEFAULT_TASK)


def _l2_normalize(embeddings):
    """L2-normalize each row of an mx.array; return as Python list of float lists."""
    import mlx.core as mx

    norms = mx.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = mx.maximum(norms, 1e-12)
    normalized = embeddings / norms
    mx.eval(normalized)
    return normalized.tolist()


class EmbeddingEngine:
    """Wraps the repo's JinaMultiTaskModel for text embedding."""

    def __init__(self, model_dir: str):
        self._model = None
        self._dim = 1024
        self._current_task = None

        # Read Matryoshka max dim from config when present.
        try:
            with open(os.path.join(model_dir, "config.json")) as f:
                cfg = json.load(f)
            dims = cfg.get("matryoshka_dimensions")
            if dims:
                self._dim = int(max(dims))
        except Exception:
            pass

        # Load the repo's utils.py and build the multi-task model via its own loader.
        if model_dir not in sys.path:
            sys.path.insert(0, model_dir)
        spec = importlib.util.spec_from_file_location(
            "jina_omni_utils", os.path.join(model_dir, "utils.py")
        )
        utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(utils)
        self._model = utils.load_model(model_dir)

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def dim(self) -> int:
        return self._dim

    def encode(
        self,
        texts: list[str],
        input_type: str | None = None,
        truncate_dim: int | None = None,
    ) -> list[list[float]]:
        """Encode texts to L2-normalized float vectors.

        Must be called under the server's GPU lock: switch_task() mutates weights
        in place. Empty input returns []. truncate_dim is honored only for valid
        Matryoshka dims; anything else falls back to full dim.
        """
        if not texts:
            return []
        if self._model is None:
            raise RuntimeError("Embedding model not loaded")

        task, task_type = resolve_task(input_type)
        if task != self._current_task:
            self._model.switch_task(task)
            self._current_task = task

        if truncate_dim not in MATRYOSHKA_DIMS:
            truncate_dim = None

        embeddings = self._model.encode(
            texts, task_type=task_type, truncate_dim=truncate_dim
        )
        # model.encode only normalizes when truncate_dim is set; always normalize here.
        return _l2_normalize(embeddings)


def load_engine(model_id: str = DEFAULT_EMBED_MODEL_ID) -> EmbeddingEngine:
    """Resolve the model dir and return a loaded EmbeddingEngine."""
    return EmbeddingEngine(resolve_model_dir(model_id))


if __name__ == "__main__":
    engine = load_engine()
    print(f"loaded={engine.loaded} dim={engine.dim}")

    query = engine.encode(["What is the capital of France?"], input_type="retrieval.query")
    passage = engine.encode(
        ["Paris is the capital and most populous city of France."],
        input_type="retrieval.passage",
    )
    print(f"query shape: {len(query)}x{len(query[0])}")
    print(f"passage shape: {len(passage)}x{len(passage[0])}")

    cos = sum(a * b for a, b in zip(query[0], passage[0]))
    qn = math.sqrt(sum(a * a for a in query[0]))
    pn = math.sqrt(sum(b * b for b in passage[0]))
    print(f"query norm: {qn:.6f}  passage norm: {pn:.6f}")
    print(f"query-vs-passage cosine: {cos:.6f}")
