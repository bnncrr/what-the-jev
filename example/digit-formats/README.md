# Digit Recognition from a base64-Encoded Image

This experiment tests whether the Jev model can recognize a digit from a base64-encoded image.

It contains 1 sample: the first entry of the MNIST test split, a 28×28 grayscale handwritten digit given as a PNG data URI (base64-encoded, 362 characters).

One question is asked:

1. "Judge which digit is written in the image." Choose one of `0` to `9`. (`choice`)

   - `0`: "The digit 0."
   - `1`: "The digit 1."
   - `2`: "The digit 2."
   - `3`: "The digit 3."
   - `4`: "The digit 4."
   - `5`: "The digit 5."
   - `6`: "The digit 6."
   - `7`: "The digit 7."
   - `8`: "The digit 8."
   - `9`: "The digit 9."

## Results

The sample's true label is 7. `digit` was judged `1`, which is wrong.

Per-option probabilities: `1` 0.35, `0` 0.25, the other eight options between 0.02 and 0.08, and the correct option `7` at 0.08, below the uniform level of 0.10 across ten options. `confidence` 0.28.

The distribution is not uniform, but it concentrates on a wrong option: the model failed to read the digit from the base64 encoding.

Cost: 707 input tokens, 87 output tokens, `0.000029694` USD. Output tokens are not billed.

## Reproduce

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY='<key>'
python run.py example/digit-formats/config.yaml
```

The run processes the English dataset `data/dataset.json` and the Chinese dataset `data/dataset_zh.json`, appending results to `result/responses.jsonl` and `result/responses_zh.jsonl` respectively. Each sample is requested only once per run; records that already succeeded are skipped on reruns, and records that failed in the previous run are cleared and requested again.
