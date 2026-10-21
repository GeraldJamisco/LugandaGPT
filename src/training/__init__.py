"""Local preparation and guarded execution for LugandaGPT training.

Importing this package does not import PyTorch, Transformers, TRL, Datasets,
or any other optional training dependency. Those imports happen only inside
the functions that need them, after authorization and data checks pass.
"""

__all__ = []
