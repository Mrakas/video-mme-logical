# Video-MME-Logical Mini Set

A fixed 375-sample subset (10%) of [Video-MME-Logical](https://huggingface.co/datasets/marcuskwan/video-mme-logical) by Hohin Kwan, Hongyu Li, Ray Zhang, Manyuan Zhang, Xianghao Kong, Anyi Rao, Jiahao Xie, and Si Liu.

- 25 tasks × 3 difficulty levels × 5 samples, sampled without replacement with seed `20261012`.
- 125 easy, 125 medium, and 125 hard samples; 375 videos and 90 reference images.
- Original questions, answers, videos, and reference images are unchanged. Only sample selection differs from the full release.
- `mini_test_375.json` uses the original schema. Resolve `video_path` and `image_paths` relative to the manifest's directory.
- `sampling.json` records the sampling method, sample IDs, and manifest checksums.

GitHub: https://github.com/Mrakas/video-mme-logical
Paper: https://arxiv.org/abs/2606.27828
License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), inherited from the source dataset.
