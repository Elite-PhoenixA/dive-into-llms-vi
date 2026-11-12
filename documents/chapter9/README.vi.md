# Thực hành mô hình lớn: Xây dựng tác tử GUI
## Mục tiêu của giáo trình
1. Hiểu các hướng kỹ thuật và hiện trạng nghiên cứu trong lĩnh vực tác tử GUI

2. Thử phương pháp xây dựng tác tử GUI tương tác người - máy thích ứng dựa trên mô hình mã nguồn mở Qwen2-VL-7B và bộ dữ liệu OS-Kairos

3. Thử suy luận dựa trên tác tử GUI đã xây dựng
## 1. Chuẩn bị công việc
### 1.1 Tìm hiểu hướng kỹ thuật và hiện trạng nghiên cứu trong lĩnh vực tác tử GUI
Đọc giáo trình: [[Slides](https://github.com/Lordog/dive-into-llms/blob/main/documents/chapter8/GUIagent.pdf)]

### 1.2 Tìm hiểu tác tử GUI tương tác người - máy thích ứng là gì
Bài báo tham khảo: [[Paper](https://arxiv.org/abs/2503.16465)]

### 1.3 Chuẩn bị bộ dữ liệu
Giáo trình lấy OS-Kairos làm ví dụ, dựa trên bộ dữ liệu mã nguồn mở của công trình này để xây dựng và suy luận một tác tử GUI đơn giản.

Tải bộ dữ liệu từ liên kết tải trong tệp README.md của [[Data](https://github.com/Wuzheng02/OS-Kairos)], và giải nén vào môi trường.

Ví dụ định dạng dữ liệu như sau:
```json
    {
        "task": "打开网易云音乐，搜索《Shape of You》，并播放这首歌。",
        "image_path": "/data1/wuzh/cloud_music/images/1736614680.6518524_1.png",
        "list": [
            " 打开网易云音乐  ",
            " 点击首页顶部的搜索框  ",
            " 输入：Shape of You  ",
            " 选择正确的搜索结果  ",
            " 点击歌名以播放  "
        ],
        "now_step": 1,
        "previous_actions": [
            "CLICK <point>[[381,367]]</point>"
        ],
        "score": 5,
        "osatlas_action": "CLICK <point>[[454,87]]</point>",
        "teacher_action": "CLICK <point>[[500,100]]</point>",
        "success": false
    },
```
### 1.4 Chuẩn bị mô hình
Tải trọng số mô hình Qwen2-VL-7B từ [[Model](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct)].

## 1.5 Chuẩn bị mã nguồn tinh chỉnh có giám sát
Giáo trình dùng LLaMa-Factory để tinh chỉnh có giám sát Qwen2-VL-7B, vì vậy trước tiên tải mã nguồn từ [[Code](https://github.com/hiyouga/LLaMA-Factory/)].

## 2. Xây dựng tác tử GUI
### 2.1 Tiền xử lý dữ liệu
Lưu đoạn mã sau thành get_sharpgpt.py, điền vào đó đường dẫn của Kairos_train.json và đường dẫn dự kiến lưu tệp json của tập huấn luyện sau xử lý, rồi chạy tệp này.
```python
import json


with open('', 'r', encoding='utf-8') as f:
    data = json.load(f)


preprocessed_data = []
for item in data:
    task = item.get("task", "")
    previous_actions = item.get("previous_actions", "") 
    image_path = item.get("image_path","")
    prompt_text = f"""
    You are now operating in Executable Language Grounding mode. Your goal is to help users accomplish tasks by suggesting executable actions that best fit their needs and give a score. Your skill set includes both basic and custom actions:

    1. Basic Actions
    Basic actions are standardized and available across all platforms. They provide essential functionality and are defined with a specific format, ensuring consistency and reliability. 
    Basic Action 1: CLICK 
        - purpose: Click at the specified position.
        - format: CLICK <point>[[x-axis, y-axis]]</point>
        - example usage: CLICK <point>[[101, 872]]</point>

    Basic Action 2: TYPE
        - purpose: Enter specified text at the designated location.
        - format: TYPE [input text]
        - example usage: TYPE [Shanghai shopping mall]

    Basic Action 3: SCROLL
        - Purpose: SCROLL in the specified direction.
        - Format: SCROLL [direction (UP/DOWN/LEFT/RIGHT)]
        - Example Usage: SCROLL [UP]

    2. Custom Actions
    Custom actions are unique to each user's platform and environment. They allow for flexibility and adaptability, enabling the model to support new and unseen actions defined by users. These actions extend the functionality of the basic set, making the model more versatile and capable of handling specific tasks.

    Custom Action 1: PRESS_BACK
        - purpose: Press a back button to navigate to the previous screen.
        - format: PRESS_BACK
        - example usage: PRESS_BACK

    Custom Action 2: PRESS_HOME
        - purpose: Press a home button to navigate to the home page.
        - format: PRESS_HOME
        - example usage: PRESS_HOME

    Custom Action 3: ENTER
        - purpose: Press the enter button.
        - format: ENTER
        - example usage: ENTER

    Custom Action 4: IMPOSSIBLE
        - purpose: Indicate the task is impossible.
        - format: IMPOSSIBLE
        - example usage: IMPOSSIBLE

    In most cases, task instructions are high-level and abstract. Carefully read the instruction and action history, then perform reasoning to determine the most appropriate next action.

    And I hope you evaluate your action to be scored, giving it a score from 1 to 5. 
    A higher score indicates that you believe this action is more likely to accomplish the current goal for the given screenshot.
    1 means you believe this action definitely cannot achieve the goal.
    2 means you believe this action is very unlikely to achieve the goal.
    3 means you believe this action has a certain chance of achieving the goal.
    4 means you believe this action is very likely to achieve the goal.
    5 means you believe this action will definitely achieve the goal.

    And your final goal, previous actions, and associated screenshot are as follows:
    Final goal: {task}
    previous actions: {previous_actions}
    screenshot:<image>
    Your output must strictly follow the format below, and especially avoid using unnecessary quotation marks or other punctuation marks.(where osatlas action must be one of the action formats I provided and score must be 1 to 5):
    action:
    score:
    """

    action = item.get("osatlas_action", "")
    score = item.get("score", "")
    preprocessed_item = {
        "messages": [
            {
                "role": "user",
                "content": prompt_text,
            },
            {
                "role": "assistant",
                "content": f"action: {action}\nscore:{score}",
            }
        ],
        "images":[image_path]
    }
    preprocessed_data.append(preprocessed_item)


with open('', 'w', encoding='utf-8') as f:
    json.dump(preprocessed_data, f, ensure_ascii=False, indent=4)
```
Sau bước này, chúng ta đã chuyển thành công tập huấn luyện của OS-Kairos thành dữ liệu đúng định dạng sharpgpt, thuận tiện cho bước huấn luyện tiếp theo, hoàn tất tiền xử lý dữ liệu.
## 2.2 Tinh chỉnh có giám sát
Ở bước trên, chúng ta đã thu được bộ dữ liệu Kairos có định dạng phù hợp để huấn luyện bằng LLaMa-Factory. Tiếp theo chúng ta cần sửa LLaMa-Factory để đăng ký bộ dữ liệu và cấu hình thông tin huấn luyện.
Trước tiên sửa data/dataset_info.json, thêm nội dung sau để đăng ký bộ dữ liệu:
```json
"Karios" :{
  "file_name": "Karios_qwenscore.json",
  "formatting": "sharegpt",
  "columns": {
    "messages": "messages",
    "images": "images"
  },
  "tags": {
    "role_tag": "role",
    "content_tag": "content",
    "user_tag": "user",
    "assistant_tag": "assistant"
  }
},   
```
Tiếp tục sửa /examples/train_full/qwen2vl_full_sft.yaml để cấu hình thông tin huấn luyện:
```yaml
### model
model_name_or_path: 
stage: sft
do_train: true
finetuning_type: full
deepspeed: examples/deepspeed/ds_z3_config.json

### dataset
dataset: Karios
template: qwen2_vl
cutoff_len: 4096
max_samples: 9999999
#max_samples: 999
overwrite_cache: true
preprocessing_num_workers: 4

### output
output_dir: 
logging_steps: 10
save_steps: 60000
plot_loss: true
overwrite_output_dir: true

### train
per_device_train_batch_size: 2
gradient_accumulation_steps: 2
learning_rate: 1.0e-5
num_train_epochs: 5.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: true
ddp_timeout: 180000000

### eval
val_size: 0.1
per_device_eval_batch_size: 1
eval_strategy: steps
eval_steps: 20000
```
Trên đây là một cấu hình ví dụ, model_name_or_path là đường dẫn tới Qwen2-VL-7B, output_dir là đường dẫn lưu checkpoint (điểm dừng) và log.
Sau khi cấu hình xong có thể cấu hình suy luận, dòng lệnh ví dụ:
```
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 FORCE_TORCHRUN=1 llamafactory-cli train examples/train_full/qwen2vl_full_sft.yaml
```
Ở đây cần dùng ít nhất 3 card A100 80GB.

## 3. Kiểm chứng suy luận với OS-Kairos
Sau khi huấn luyện xong, chúng ta có thể tiến hành suy luận; suy luận cũng có nhiều cách để lựa chọn, có thể tự xây dựng mã suy luận bằng thư viện transformers và torch, cũng có thể dùng LLaMa-Factory để suy luận một cú nhấp. Dưới đây minh họa cách dùng LLaMa-Factory để suy luận một cú nhấp.
Trước tiên cần sửa /examples/inference/qwen2_vl.yaml, một ví dụ như sau
```yaml
model_name_or_path: 
template: qwen2_vl
```
Trong đó model_name_or_path là đường dẫn checkpoint sau huấn luyện.
Sau đó có thể thông qua
```
CUDA_VISIBLE_DEVICES=0 FORCE_TORCHRUN=1 llamafactory-cli webchat examples/inference/qwen2_vl.yaml
```
để suy luận một cú nhấp, bạn có thể tự lấy ảnh từ tập kiểm thử OS-Kairos, hoặc ảnh chụp màn hình điện thoại cá nhân, kết hợp với prompt văn bản theo định dạng trong get_sharpgpt.py để đưa vào tác tử; sau khi suy luận, OS-Karios sẽ đưa ra action mà nó cho là nên thực hiện hiện tại và điểm tin cậy cho action đó. Điểm tin cậy càng thấp thì chỉ thị hiện tại càng vượt quá biên giới năng lực của OS-Kairos, cần con người can thiệp để thực hiện tương tác người - máy.
