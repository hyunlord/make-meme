# Public data attribution and scope

This experiment uses the DAVIS 2017 semi-supervised TrainVal 480p images and instance annotations, obtained from the [official DAVIS download page](https://davischallenge.org/davis2017/code.html). The downloaded archive URL, SHA256 and byte count are recorded in DOWNLOAD.json; exact sequences/tracks/frames are in selection.json and CASES.md.

Attribution: Jordi Pont-Tuset, Federico Perazzi, Sergi Caelles, Pablo Arbeláez, Alexander Sorkine-Hornung and Luc Van Gool, *The 2017 DAVIS Challenge on Video Object Segmentation*, arXiv:1704.00675; Federico Perazzi, Jordi Pont-Tuset, Brian McWilliams, Luc Van Gool, Markus Gross and Alexander Sorkine-Hornung, *A Benchmark Dataset and Evaluation Methodology for Video Object Segmentation*, CVPR 2016.

The official dataset site's [pinned metadata](https://github.com/davisvideochallenge/davisvideochallenge.github.io/blob/30be16ff9d289f6711328c950a19c6288306ade3/index.html#L33-L42) identifies [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). This is a noncommercial research evaluation. Commercial use, unrelated redistribution rights, personality/publicity rights and final system deployment are not established by this experiment. A model/code license is not substituted for the data license.

Changes: selected consecutive frames and target-track references; aspect-fit resize/letterbox; selected GT track mapped to RED with semantic WHITE/BLACK background; reference non-object RGB set to128; model-generated edited videos; preview videos/contact sheets. Ground-truth instance masks are supplied inputs, not predictions. Native FPS was not confirmed, so previews use24fps without a native-time preservation claim.

Public GitHub contains specifications, hashes and code only. The private review archive contains the selected media and derived results for review, with this attribution and change notice. It excludes the full dataset archive. No personal pet media from earlier experiments is included in B-027.
