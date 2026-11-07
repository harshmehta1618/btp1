"""
dataset.py
-----------
PyTorch Dataset for loading IQ–Phase patch pairs from the extracted patch folders.
Patches are loaded by matching filename across iq/ and phase/ directories.
"""

import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


class EBSDPatchDataset(Dataset):
    """
    Loads 128×128 patch pairs from:
        patches/{split}/iq/     → float32 grayscale [0,1]
        patches/{split}/phase/  → uint8 label mask {0, 1, 255}

    Filenames in iq/ and phase/ are identical → guaranteed pair alignment.
    """

    def __init__(self, patch_dir: str, split: str):
        """
        Args:
            patch_dir: root patches directory
            split: "train", "val", or "test"
        """
        self.iq_dir    = os.path.join(patch_dir, split, "iq")
        self.phase_dir = os.path.join(patch_dir, split, "phase")

        iq_files    = set(os.listdir(self.iq_dir))
        phase_files = set(os.listdir(self.phase_dir))

        # Only keep files present in BOTH folders
        common = sorted(iq_files & phase_files)
        if len(common) == 0:
            raise RuntimeError(
                f"No matching patch files found in {self.iq_dir} and {self.phase_dir}. "
                f"Run 3_patch_extraction.py first."
            )

        self.filenames = common
        print(f"EBSDPatchDataset [{split}]: {len(self.filenames)} patches")

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, idx: int):
        fname = self.filenames[idx]

        iq_path    = os.path.join(self.iq_dir,    fname)
        phase_path = os.path.join(self.phase_dir, fname)

        iq    = np.load(iq_path)    # float32 (128, 128)
        label = np.load(phase_path) # uint8   (128, 128) with values {0, 1, 255}

        # Add channel dim for IQ → (1, 128, 128)
        iq_tensor    = torch.from_numpy(iq).unsqueeze(0).float()
        label_tensor = torch.from_numpy(label.astype(np.int64)).long()

        return iq_tensor, label_tensor


def get_dataloaders(
    patch_dir: str,
    batch_size: int = 16,
    num_workers: int = 0,
):
    """
    Returns train, val, test DataLoaders.

    Args:
        patch_dir:   root patches directory (contains train/, val/, test/)
        batch_size:  mini-batch size
        num_workers: DataLoader worker processes (0 = main thread, safe on Windows)
    """
    train_ds = EBSDPatchDataset(patch_dir, "train")
    val_ds   = EBSDPatchDataset(patch_dir, "val")
    test_ds  = EBSDPatchDataset(patch_dir, "test")

    train_loader = DataLoader(
        train_ds, batch_size=batch_size,
        shuffle=True, num_workers=num_workers, pin_memory=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size,
        shuffle=False, num_workers=num_workers, pin_memory=True
    )
    test_loader = DataLoader(
        test_ds, batch_size=batch_size,
        shuffle=False, num_workers=num_workers, pin_memory=True
    )

    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    # Quick sanity check
    import os
    patch_dir = os.path.join(os.path.dirname(__file__), "patches")
    train_loader, val_loader, test_loader = get_dataloaders(patch_dir, batch_size=4)

    iq_batch, label_batch = next(iter(train_loader))
    print(f"IQ batch shape   : {iq_batch.shape}")     # (4, 1, 128, 128)
    print(f"Label batch shape: {label_batch.shape}")   # (4, 128, 128)
    print(f"IQ   dtype/range : {iq_batch.dtype}  [{iq_batch.min():.2f}, {iq_batch.max():.2f}]")
    print(f"Label unique vals: {label_batch.unique()}")
    print("[OK] DataLoader OK")
