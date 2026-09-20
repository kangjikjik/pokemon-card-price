"""두 번째 35개 확장팩에 달다구리 한국판 이미지만 안전하게 적용."""
from __future__ import annotations

import fill_batch1_35_daldagury_verified as runner


runner.TARGETS = {
    "S11a": 267, "S11": 266, "S10b": 265, "S10a": 264,
    "S9": 263, "S9a": 354, "S8": 262, "S8a": 261, "S8b": 260,
    "S7F": 350, "S7R": 20, "S7D": 344,
    "S6H": 342, "S6G": 256, "S6L": 340,
    "S5F": 255, "S5S": 338, "S5P": 339,
    "S4SV": 337, "S4B": 21, "S3H": 254,
    "S3Z": 253, "S2R": 252, "S2": 331,
    "S1a": 251, "S1W": 249, "S1H": 250,
    "SM12a": 324, "SM12": 248, "SM11b": 247, "SM11a": 246,
    "SM10": 37, "SM9": 315, "SM8b": 314, "SM9a": 313,
}
runner.REPORT = runner.Path("_audit_out/daldagury_batch2_35_verified_apply.json")


if __name__ == "__main__":
    runner.main()
