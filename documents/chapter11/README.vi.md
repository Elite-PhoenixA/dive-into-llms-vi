# Thực hành mô hình lớn: RLHF

> Sổ tay thí nghiệm này được dịch và tổng hợp từ tài liệu trên mạng [blog](https://newfacade.github.io/notes-on-reinforcement-learning/17-ppo-trl.html) & [trl examples](https://github.com/huggingface/trl/blob/main/examples/notebooks/gpt2-sentiment.ipynb)

Cấu hình tái hiện thí nghiệm: một card NVDIA A800-SXM4-80GB, chiếm dụng 10097MiB, thời gian huấn luyện 35min19s.

Đọc giáo trình: [slide](./RLHF.pdf)

notebook: [notebook](./RLHF.ipynb)

## PPO hoạt động như thế nào
1. Rollout: mô hình ngôn ngữ sinh phản hồi dựa trên query.
2. Evaluation: truy vấn và phản hồi được đánh giá bằng hàm, mô hình, phản hồi của con người hoặc một tổ hợp nào đó của chúng. Quá trình này nên sinh ra một **giá trị vô hướng** cho mỗi cặp truy vấn/phản hồi.
3. Optimization: trong bước tối ưu, cặp truy vấn/phản hồi được dùng để tính log xác suất của các token trong chuỗi. Việc này được thực hiện thông qua mô hình đang huấn luyện và mô hình tham chiếu. Phân kỳ KL giữa hai đầu ra được dùng làm tín hiệu phần thưởng bổ sung, nhằm đảm bảo phản hồi sinh ra không lệch quá xa mô hình ngôn ngữ tham chiếu. Sau đó dùng PPO để huấn luyện mô hình ngôn ngữ chủ động.
<div style="text-align: center">
<img src='figs/trl1.png' width='600'>
<p style="text-align: center;"> <b>Hình:</b> lưu đồ PPO </p>
</div>

# Tinh chỉnh GPT-2 để sinh bình luận tích cực  
> Bằng việc dùng bộ phân loại cảm xúc BERT làm hàm phần thưởng, tối ưu GPT-2 để sinh các bình luận phim IMDB tích cực.

<div style="text-align: center">
<img src='figs/gpt2_bert_training.png' width='600'>
<p style="text-align: center;"> <b>Hình:</b> thiết lập thí nghiệm tinh chỉnh GPT-2</p>
</div>

Chúng tôi tinh chỉnh GPT-2 để sinh bình luận phim tích cực dựa trên bộ dữ liệu IMDB. Mô hình sẽ nhận phần mở đầu của bình luận thật, và cần sinh phần tiếp theo tích cực. Để thưởng cho phần tiếp theo tích cực, chúng tôi dùng bộ phân loại BERT để phân tích cảm xúc của câu được sinh ra, và lấy đầu ra của bộ phân loại làm tín hiệu phần thưởng cho huấn luyện PPO.

## Thiết lập thí nghiệm

### Tải mô hình và dữ liệu
Bộ dữ liệu
```bash
export HF_ENDPOINT=https://hf-mirror.com; huggingface-cli download --resume-download stanfordnlp/imdb --local-dir dataset/imdb --repo-type dataset
```
Mô hình tham chiếu
```bash
export HF_ENDPOINT=https://hf-mirror.com; huggingface-cli download --resume-download lvwerra/gpt2-imdb --local-dir model/gpt2-imdb
```
Mô hình phần thưởng
```bash
export HF_ENDPOINT=https://hf-mirror.com; huggingface-cli download --resume-download lvwerra/distilbert-imdb --local-dir model/distilbert-imdb
```

### Import các gói phụ thuộc


```python
# %pip install -r requirements.txt
# import os
# os.environ['CUDA_VISIBLE_DEVICES'] = '7'
```


```python
import torch
from tqdm import tqdm
import pandas as pd

tqdm.pandas()

from transformers import pipeline, AutoTokenizer
from datasets import load_dataset

from trl import PPOTrainer, PPOConfig, AutoModelForCausalLMWithValueHead
from trl.core import LengthSampler
```

### Cấu hình


```python
config = PPOConfig(
    model_name="model/gpt2-imdb",
    learning_rate=1.41e-5,
    log_with="wandb",
)

sent_kwargs = {"top_k": None, "function_to_apply": "none", "batch_size": 16}
```


```python
import wandb

wandb.init()
```

Bạn có thể thấy chúng tôi đã nạp một mô hình GPT-2 tên là `gpt2_imdb`. Mô hình này được tinh chỉnh thêm 1 epoch trên bộ dữ liệu IMDB, sử dụng [script](https://github.com/huggingface/transformers/blob/main/examples/legacy/run_language_modeling.py) của Hugging Face (không có thiết lập đặc biệt). Các tham số còn lại chủ yếu lấy từ bài báo gốc 《[Fine-Tuning Language Models from Human Preferences](https://huggingface.co/papers/1909.08593)》. Mô hình này cùng mô hình BERT đều có thể tìm thấy trong kho mô hình của Hugging Face, liên kết cụ thể tại [đây](https://huggingface.co/models).

## Nạp dữ liệu và mô hình

### Nạp bộ dữ liệu IMDB  
Bộ dữ liệu IMDB gồm 50.000 bình luận phim, được gán nhãn cảm xúc "tích cực"/"tiêu cực". Chúng tôi nạp bộ dữ liệu IMDB vào một DataFrame, và lọc ra các bình luận có ít nhất 200 ký tự. Sau đó, chúng tôi phân tách (tokenize) từng văn bản, và dùng `LengthSampler` để cắt ngẫu nhiên thành độ dài chỉ định.


```python
def build_dataset(
    config,
    dataset_name="dataset/imdb",
    input_min_text_length=2,
    input_max_text_length=8,
):
    """
    Build dataset for training. This builds the dataset from `load_dataset`, one should
    customize this function to train the model on its own dataset.

    Args:
        dataset_name (`str`):
            The name of the dataset to be loaded.

    Returns:
        dataloader (`torch.utils.data.DataLoader`):
            The dataloader for the dataset.
    """
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    # load imdb with datasets
    ds = load_dataset(dataset_name, split="train")
    ds = ds.rename_columns({"text": "review"})
    ds = ds.filter(lambda x: len(x["review"]) > 200, batched=False)

    input_size = LengthSampler(input_min_text_length, input_max_text_length)

    def tokenize(sample):
        sample["input_ids"] = tokenizer.encode(sample["review"])[: input_size()]
        sample["query"] = tokenizer.decode(sample["input_ids"])
        return sample

    ds = ds.map(tokenize, batched=False)
    ds.set_format(type="torch")
    return ds
```


```python
dataset = build_dataset(config)


def collator(data):
    return dict((key, [d[key] for d in data]) for key in data[0])
```

### Nạp mô hình ngôn ngữ GPT2 đã tiền huấn luyện
Chúng tôi nạp mô hình GPT2 có value head (đầu giá trị) và tokenizer. Chúng tôi nạp mô hình hai lần; mô hình thứ nhất dùng để tối ưu, còn mô hình thứ hai làm tham chiếu, dùng để tính phân kỳ KL (KL-divergence) so với điểm ban đầu. Điều này đóng vai trò tín hiệu phần thưởng bổ sung trong huấn luyện PPO, nhằm đảm bảo mô hình sau tối ưu không lệch quá xa mô hình ngôn ngữ gốc.


```python
model = AutoModelForCausalLMWithValueHead.from_pretrained(config.model_name)
ref_model = AutoModelForCausalLMWithValueHead.from_pretrained(config.model_name)
tokenizer = AutoTokenizer.from_pretrained(config.model_name)

tokenizer.pad_token = tokenizer.eos_token
```

### Khởi tạo PPOTrainer  
`PPOTrainer` chịu trách nhiệm phân bổ thiết bị và tối ưu ở các bước sau:


```python
ppo_trainer = PPOTrainer(
    config, model, ref_model, tokenizer, dataset=dataset, data_collator=collator
)
```


### Nạp bộ phân loại BERT  
Chúng tôi nạp một bộ phân loại BERT đã được tinh chỉnh trên bộ dữ liệu IMDB.


```python
device = ppo_trainer.accelerator.device
if ppo_trainer.accelerator.num_processes == 1:
    device = 0 if torch.cuda.is_available() else "cpu"  # to avoid a `pipeline` bug
sentiment_pipe = pipeline(
    "sentiment-analysis", model="model/distilbert-imdb", device=device
)
```

    Device set to use cuda:0


Mô hình xuất ra logits của lớp tiêu cực và lớp tích cực. Chúng tôi sẽ dùng logits của lớp tích cực làm tín hiệu phần thưởng cho mô hình ngôn ngữ.


```python
text = "this movie was really bad!!"
sentiment_pipe(text, **sent_kwargs)
```




    [{'label': 'NEGATIVE', 'score': 2.3350484371185303},
     {'label': 'POSITIVE', 'score': -2.726576089859009}]




```python
text = "this movie was really good!!"
sentiment_pipe(text, **sent_kwargs)
```




    [{'label': 'POSITIVE', 'score': 2.557040214538574},
     {'label': 'NEGATIVE', 'score': -2.294790267944336}]



### Thiết lập sinh  
Đối với việc sinh phản hồi, chúng tôi chỉ dùng phương pháp lấy mẫu, đảm bảo tắt top-k và lấy mẫu hạt nhân (nucleus sampling), đồng thời đặt một độ dài tối thiểu.


```python
gen_kwargs = {
    "min_length": -1,
    "top_k": 0.0,
    "top_p": 1.0,
    "do_sample": True,
    "pad_token_id": tokenizer.eos_token_id,
}
```

## Tối ưu mô hình

### Vòng huấn luyện

Vòng huấn luyện gồm các bước chính sau:
1. Lấy phản hồi cho truy vấn từ mạng chính sách (GPT-2)  
2. Lấy cảm xúc của cặp truy vấn/phản hồi từ BERT  
3. Dùng PPO tối ưu chính sách, sử dụng bộ ba (truy vấn, phản hồi, phần thưởng)  


```python
output_min_length = 4
output_max_length = 16
output_length_sampler = LengthSampler(output_min_length, output_max_length)


generation_kwargs = {
    "min_length": -1,
    "top_k": 0.0,
    "top_p": 1.0,
    "do_sample": True,
    "pad_token_id": tokenizer.eos_token_id,
}


for epoch, batch in enumerate(tqdm(ppo_trainer.dataloader)):
    query_tensors = batch["input_ids"]

    #### Get response from gpt2
    response_tensors = []
    for query in query_tensors:
        gen_len = output_length_sampler()
        generation_kwargs["max_new_tokens"] = gen_len
        query_response = ppo_trainer.generate(query, **generation_kwargs).squeeze()
        response_len = len(query_response) - len(query)
        response_tensors.append(query_response[-response_len:])
    batch["response"] = [tokenizer.decode(r.squeeze()) for r in response_tensors]

    #### Compute sentiment score
    texts = [q + r for q, r in zip(batch["query"], batch["response"])]
    pipe_outputs = sentiment_pipe(texts, **sent_kwargs)
    positive_scores = [
        item["score"]
        for output in pipe_outputs
        for item in output
        if item["label"] == "POSITIVE"
    ]
    rewards = [torch.tensor(score) for score in positive_scores]

    #### Run PPO step
    stats = ppo_trainer.step(query_tensors, response_tensors, rewards)
    ppo_trainer.log_stats(stats, batch, rewards)
```

      0%|          | 0/194 [00:00<?, ?it/s]The attention mask is not set and cannot be inferred from input because pad token is same as eos token. As a consequence, you may observe unexpected behavior. Please pass your input's `attention_mask` to obtain reliable results.
      4%|▍         | 8/194 [01:23<32:18, 10.42s/it]You seem to be using the pipelines sequentially on GPU. In order to maximize efficiency please use a dataset
    100%|██████████| 194/194 [35:19<00:00, 10.92s/it]


### Tiến độ huấn luyện  
Nếu bạn đang dùng Weights & Biases để theo dõi tiến độ huấn luyện, bạn sẽ thấy đường cong tương tự hình dưới đây. Xem báo cáo ví dụ tương tác trên wandb.ai: [liên kết](https://wandb.ai/huggingface/trl/runs/w9l3110g).  
<div style="text-align: center">
<img src='figs/gpt2_tuning_progress.png' width='800'>
<p style="text-align: center;"> <b>Hình:</b> diễn biến giá trị phần thưởng trung bình trong quá trình huấn luyện </p>
</div>  
Có thể quan sát thấy rằng, sau vài bước tối ưu, mô hình bắt đầu sinh ra đầu ra tích cực hơn.  

## Kiểm tra mô hình  
Hãy cùng kiểm tra một số ví dụ từ bộ dữ liệu IMDB. Chúng ta có thể dùng `ref_model` để so sánh mô hình sau tối ưu `model` với mô hình trước tối ưu.


```python
#### get a batch from the dataset
bs = 16
game_data = dict()
dataset.set_format("pandas")
df_batch = dataset[:].sample(bs)
game_data["query"] = df_batch["query"].tolist()
query_tensors = df_batch["input_ids"].tolist()

response_tensors_ref, response_tensors = [], []

#### get response from gpt2 and gpt2_ref
for i in range(bs):
    query = torch.tensor(query_tensors[i]).to(device)

    gen_len = output_length_sampler()
    query_response = ref_model.generate(
        query.unsqueeze(0), max_new_tokens=gen_len, **gen_kwargs
    ).squeeze()
    response_len = len(query_response) - len(query)
    response_tensors_ref.append(query_response[-response_len:])

    query_response = model.generate(
        query.unsqueeze(0), max_new_tokens=gen_len, **gen_kwargs
    ).squeeze()
    response_len = len(query_response) - len(query)
    response_tensors.append(query_response[-response_len:])

#### decode responses
game_data["response (before)"] = [
    tokenizer.decode(response_tensors_ref[i]) for i in range(bs)
]
game_data["response (after)"] = [
    tokenizer.decode(response_tensors[i]) for i in range(bs)
]

#### sentiment analysis of query/response pairs before/after
texts = [q + r for q, r in zip(game_data["query"], game_data["response (before)"])]
pipe_outputs = sentiment_pipe(texts, **sent_kwargs)
positive_scores = [
    item["score"]
    for output in pipe_outputs
    for item in output
    if item["label"] == "POSITIVE"
]
game_data["rewards (before)"] = positive_scores

texts = [q + r for q, r in zip(game_data["query"], game_data["response (after)"])]
pipe_outputs = sentiment_pipe(texts, **sent_kwargs)
positive_scores = [
    item["score"]
    for output in pipe_outputs
    for item in output
    if item["label"] == "POSITIVE"
]
game_data["rewards (after)"] = positive_scores

# store results in a dataframe
df_results = pd.DataFrame(game_data)
df_results
```

<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>query</th>
      <th>response (before)</th>
      <th>response (after)</th>
      <th>rewards (before)</th>
      <th>rewards (after)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Well I guess I know</td>
      <td>that Cantor may be an</td>
      <td>..but I loved it</td>
      <td>0.230196</td>
      <td>2.281557</td>
    </tr>
    <tr>
      <th>1</th>
      <td>This is an excellent,</td>
      <td>direct-to-video film with typical</td>
      <td>enjoyable movie.&lt;|endoftext|&gt;</td>
      <td>2.846593</td>
      <td>2.840860</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Now, I</td>
      <td>'ve never had the chance with James</td>
      <td>loved the growing episode - and the</td>
      <td>0.656194</td>
      <td>2.525894</td>
    </tr>
    <tr>
      <th>3</th>
      <td>We tend</td>
      <td>not to see Arthur</td>
      <td>to like this very</td>
      <td>-0.280880</td>
      <td>2.183822</td>
    </tr>
    <tr>
      <th>4</th>
      <td>The proverb "Never judge a book</td>
      <td>by the cover" has caught on. After glancing t...</td>
      <td>with high compliments, but it is recommended ...</td>
      <td>0.274649</td>
      <td>2.065951</td>
    </tr>
    <tr>
      <th>5</th>
      <td>I've never understood</td>
      <td>why so many artsmen,</td>
      <td>this film but it's delightful</td>
      <td>0.835574</td>
      <td>2.782384</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Hugh (Ed Harris) is</td>
      <td>an acclaimed "hero" and his fian</td>
      <td>a wonderful actor who is a good adaptation</td>
      <td>1.580167</td>
      <td>2.602940</td>
    </tr>
    <tr>
      <th>7</th>
      <td>This particular Joe McDoakes</td>
      <td>' episode brought all the wrong bits and</td>
      <td>movie is really a great movie. It</td>
      <td>0.870956</td>
      <td>2.795245</td>
    </tr>
    <tr>
      <th>8</th>
      <td>Sisters In</td>
      <td>Vrooms 8.23, I signed up for all of the</td>
      <td>The Universe 1: Sunny is cute, and has a cute...</td>
      <td>1.175259</td>
      <td>2.062330</td>
    </tr>
    <tr>
      <th>9</th>
      <td>I was very fond of this</td>
      <td>film, it was obviously a bad idea when first ...</td>
      <td>show, and know that I have seen it several times</td>
      <td>1.058164</td>
      <td>2.511273</td>
    </tr>
    <tr>
      <th>10</th>
      <td>If he wanted to be</td>
      <td>funny, he could</td>
      <td>a genius eventually,</td>
      <td>-0.388943</td>
      <td>0.405888</td>
    </tr>
    <tr>
      <th>11</th>
      <td>Thats My</td>
      <td>Grade...&lt;br /&gt;&lt;br /&gt;Although</td>
      <td>Way was the best movie that I watched.</td>
      <td>-0.151680</td>
      <td>2.473050</td>
    </tr>
    <tr>
      <th>12</th>
      <td>This is possibly the best short</td>
      <td>film I have come across in almost two years.</td>
      <td>film ever written. It has some very memorable...</td>
      <td>2.511835</td>
      <td>2.775994</td>
    </tr>
    <tr>
      <th>13</th>
      <td>Some people say this is</td>
      <td>exactly what happens in Hollywood; where come...</td>
      <td>a powerful film to listen to. It really captures</td>
      <td>0.637631</td>
      <td>2.821085</td>
    </tr>
    <tr>
      <th>14</th>
      <td>A remake of</td>
      <td>"The Wizard of Oz</td>
      <td>the legendary Kingan oil</td>
      <td>0.292409</td>
      <td>0.434021</td>
    </tr>
    <tr>
      <th>15</th>
      <td>What a terrible</td>
      <td>movie!&lt;|endoftext|&gt;</td>
      <td>chopping sounded so good, I love it! We have a</td>
      <td>-2.681461</td>
      <td>2.340650</td>
    </tr>
  </tbody>
</table>


Qua quan sát giá trị trung bình/trung vị phần thưởng của các chuỗi được sinh ra, chúng tôi phát hiện sự khác biệt rõ rệt.


```python
print("mean:")
display(df_results[["rewards (before)", "rewards (after)"]].mean())
print()
print("median:")
display(df_results[["rewards (before)", "rewards (after)"]].median())
```

    mean:

    rewards (before)    0.591666
    rewards (after)     2.243934
    dtype: float64


​    
    median:

    rewards (before)    0.646912
    rewards (after)     2.492161
    dtype: float64


## Lưu mô hình  
Cuối cùng, chúng tôi lưu mô hình để dùng về sau.


```python
model.save_pretrained("model/gpt2-imdb-pos-v2")
tokenizer.save_pretrained("model/gpt2-imdb-pos-v2")
```




    ('model/gpt2-imdb-pos-v2/tokenizer_config.json',
     'model/gpt2-imdb-pos-v2/special_tokens_map.json',
     'model/gpt2-imdb-pos-v2/vocab.json',
     'model/gpt2-imdb-pos-v2/merges.txt',
     'model/gpt2-imdb-pos-v2/added_tokens.json',
     'model/gpt2-imdb-pos-v2/tokenizer.json')
