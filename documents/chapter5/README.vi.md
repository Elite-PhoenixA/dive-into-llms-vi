# Thực hành mô hình lớn: Thủy vân mô hình

Dẫn đọc: Phần này giới thiệu thủy vân của mô hình ngôn ngữ

> Nhúng vào nội dung do mô hình ngôn ngữ sinh ra một "thủy vân" mà con người không thể nhận biết, nhưng thuật toán có thể phát hiện được.

## Mục tiêu của giáo trình

1. Nhúng thủy vân: nhúng thủy vân khi mô hình ngôn ngữ sinh nội dung
2. Phát hiện thủy vân: phát hiện cường độ thủy vân của một văn bản cho trước
3. Đánh giá thủy vân: đánh giá hiệu năng phát hiện của phương pháp thủy vân
4. Đánh giá tính bền vững (robustness) của thủy vân (tùy chọn)



## Chuẩn bị công việc

### 2.1 Tìm hiểu kho mã X-SIR

https://github.com/zwhe99/X-SIR

Kho X-SIR bao gồm phần hiện thực của những nội dung sau

- Ba thuật toán thủy vân văn bản: X-SIR, SIR và KGW
- Hai phương pháp tấn công loại bỏ thủy vân: paraphrase và translation

![img](./assets/x-sir.png)

### 2.2 Chuẩn bị môi trường

```Shell
git clone https://github.com/zwhe99/X-SIR && cd X-SIR
conda create -n xsir python==3.10.10
conda activate xsir
pip3 install -r requirements.txt
# [optional] pip3 install flash-attn==2.3.3
```

> Các phiên bản trong requirements.txt đều là phiên bản đề xuất, không phải yêu cầu bắt buộc.



## Ví dụ thực hành

> Dùng thuật toán KGW để nhúng thủy vân vào nội dung do mô hình ngôn ngữ sinh ra

### 3.1 Chuẩn bị dữ liệu

Tổ chức các gợi ý (prompt) cần đưa vào mô hình ngôn ngữ thành tệp jsonl:

```JSON
{"prompt": "Ghost of Emmett Till: Based on Real Life Events "}
{"prompt": "Antique Cambridge Glass Pink Decagon Console Bowl Engraved Gold Highlights\n"}
{"prompt": "2009 > Information And Communication Technology Index statistics - Countries "}
......
```

- Mỗi dòng là một json object, và phải chứa ít nhất khóa tên là "prompt"
- Nội dung tiếp theo lấy tệp `data/dataset/mc4/mc4.en.jsonl` làm ví dụ. Tệp này gồm tổng cộng 500 mục dữ liệu, nếu thấy mô hình xử lý quá lâu, có thể tự rút gọn dữ liệu.

### 3.2 Nhúng thủy vân

- Chọn mô hình và thuật toán thủy vân. Ở đây chúng ta chọn mô hình `baichuan-inc/Baichuan-7B` và thuật toán thủy vân `KGW`

  - ```Shell
    MODEL_NAME=baichuan-inc/Baichuan-7B
    MODEL_ABBR=baichuan-7b
    WATERMARK_METHOD_FLAG="--watermark_method kgw"
    ```

- Sinh nội dung và nhúng thủy vân

  - ```Shell
    python3 gen.py \
        --base_model $MODEL_NAME \
        --fp16 \
        --batch_size 32 \
        --input_file data/dataset/mc4/mc4.en.jsonl \
        --output_file gen/$MODEL_ABBR/kgw/mc4.en.mod.jsonl \
        $WATERMARK_METHOD_FLAG
    ```

  - Lệnh này lưu nội dung do mô hình sinh ra vào tệp đầu ra: `gen/$MODEL_ABBR/kgw/mc4.en.mod.jsonl`

  - Định dạng tệp đầu ra như sau, trong đó response là nội dung đầu ra của mô hình:

    - ```JSON
      {"prompt": "Ghost of Emmett Till: Based on Real Life Events ", "response": ".In August if 1955 African American Emmett Louis Till (21)\nThe second part of The Man From Waco, about Dan Millers trial for murdering his friend Michael Capps in a Texas wiener wrastle as I believe the statute says called it then; back at that time that would have surely occurred since Dan kept his pistol in one of those watery doggy bags he keeps around to clean himself with after emptying can into a nearby lake just minutes before committing his crime. If what we read is true thats exactly where Dan left his stolen gun and later used it in the robbery gone wrong which killed two innocent boys when his own accomplice got into an argument over not being paid enough therefore wanting out. This angered Miller whos history of mental instability could be taken one way or another but this criminal act was unavoidable once they entered FBIs hands and some other very powerful law officers who were involved either directly"}
      {"prompt": "Antique Cambridge Glass Pink Decagon Console Bowl Engraved Gold Highlights\n", "response": "An exceptionally fine decorative antique pink decagonal glass side bowl is the perfect example of early art and innovation . Fully engraved, this beautiful English vintage tableware piece exhibits a great degree on craftsmanship! Made in England during the mid 1800's it features three sets of concentric ribbons on the exterior to elegantly highlight an intricate, deep reddish color which evokes warmth and comfort for years to come! This historically significant vase has been featured within numerous museum exhibitions including \"Glass at The Corning Museum\" ; \"The First Half Century\" & a special travelling exhibit called:\" Sight Of Glass: British Cut Glass\" by ibex limited (retailer) as well as \"SIGNALS - Celebrating History In American Silver Through The Articulated Bottle Vessel\" presented at the Corning Museum of Glass 2012 ASA national symposium! We provide our customers with quality phot"}
      {"prompt": "2009 > Information And Communication Technology Index statistics - Countries ", "response": "5/22/2016\nAnnual change of mobile telephone subscriptions in Armenia (per 1 population). 2.2% increase is equivalent to 38 subscriptions per 100 people. Density rank: 121 out of 222.\nCyclist(s)/month(S). Likes bike riding? Take advantage of discount and cheap rental bikes at Rimon Bike Rentals in Yerevan! No advance payments or additional deposits are required. They have a good range of bicycles, including mountainbikes. More on their Facebook page \nYou must know about electric cars. The Renault Fluence KZERO gets it right in the city but I'm not sure what mileage you can expect from it. Still its fun project http://www.renault-kzen.com\nFor more on this and related issues : Armenian Institute for Electronic Governance reports |"}
      ......
      ```



### 3.3 Phát hiện thủy vân

> Phát hiện thủy vân tức là cho trước một đoạn văn bản, tính cường độ thủy vân (z-score) của đoạn văn bản đó.

- Tính cường độ thủy vân của văn bản **có thủy vân**

  - ```python
    python3 detect.py \
        --base_model $MODEL_NAME \
        --detect_file gen/$MODEL_ABBR/kgw/mc4.en.mod.jsonl \
        --output_file gen/$MODEL_ABBR/kgw/mc4.en.mod.z_score.jsonl \
        $WATERMARK_METHOD_FLAG
    ```

- Tính cường độ thủy vân của văn bản **không có thủy vân**

  - ```python
    python3 detect.py \
        --base_model $MODEL_NAME \
        --detect_file data/dataset/mc4/mc4.en.jsonl \
        --output_file gen/$MODEL_ABBR/kgw/mc4.en.hum.z_score.jsonl \
        $WATERMARK_METHOD_FLAG
    ```

- Định dạng tệp đầu ra là:

  - ```JSON
    {"z_score": 12.105422509165574, "prompt": "Ghost of Emmett Till: Based on Real Life Events ", "response": ".In August if 1955 African American Emmett Louis Till (21)\nThe second part of The Man From Waco, about Dan Millers trial for murdering his friend Michael Capps in a Texas wiener wrastle as I believe the statute says called it then; back at that time that would have surely occurred since Dan kept his pistol in one of those watery doggy bags he keeps around to clean himself with after emptying can into a nearby lake just minutes before committing his crime. If what we read is true thats exactly where Dan left his stolen gun and later used it in the robbery gone wrong which killed two innocent boys when his own accomplice got into an argument over not being paid enough therefore wanting out. This angered Miller whos history of mental instability could be taken one way or another but this criminal act was unavoidable once they entered FBIs hands and some other very powerful law officers who were involved either directly", "biases": null}
    {"z_score": 12.990684249887122, "prompt": "Antique Cambridge Glass Pink Decagon Console Bowl Engraved Gold Highlights\n", "response": "An exceptionally fine decorative antique pink decagonal glass side bowl is the perfect example of early art and innovation . Fully engraved, this beautiful English vintage tableware piece exhibits a great degree on craftsmanship! Made in England during the mid 1800's it features three sets of concentric ribbons on the exterior to elegantly highlight an intricate, deep reddish color which evokes warmth and comfort for years to come! This historically significant vase has been featured within numerous museum exhibitions including \"Glass at The Corning Museum\" ; \"The First Half Century\" & a special travelling exhibit called:\" Sight Of Glass: British Cut Glass\" by ibex limited (retailer) as well as \"SIGNALS - Celebrating History In American Silver Through The Articulated Bottle Vessel\" presented at the Corning Museum of Glass 2012 ASA national symposium! We provide our customers with quality phot", "biases": null}
    {"z_score": 11.455466938203664, "prompt": "2009 > Information And Communication Technology Index statistics - Countries ", "response": "5/22/2016\nAnnual change of mobile telephone subscriptions in Armenia (per 1 population). 2.2% increase is equivalent to 38 subscriptions per 100 people. Density rank: 121 out of 222.\nCyclist(s)/month(S). Likes bike riding? Take advantage of discount and cheap rental bikes at Rimon Bike Rentals in Yerevan! No advance payments or additional deposits are required. They have a good range of bicycles, including mountainbikes. More on their Facebook page \nYou must know about electric cars. The Renault Fluence KZERO gets it right in the city but I'm not sure what mileage you can expect from it. Still its fun project http://www.renault-kzen.com\nFor more on this and related issues : Armenian Institute for Electronic Governance reports |", "biases": null}
    ......
    ```

- Quan sát bằng mắt thường sự khác biệt về cường độ thủy vân giữa hai tệp

### 3.4 Đánh giá thủy vân
<a name="eval"></a>

- Đưa vào tệp z-score của phát hiện thủy vân, tính độ chính xác phát hiện, vẽ đường cong ROC

  - ```Shell
    python3 eval_detection.py \
            --hm_zscore gen/$MODEL_ABBR/kgw/mc4.en.hum.z_score.jsonl \
            --wm_zscore gen/$MODEL_ABBR/kgw/mc4.en.mod.z_score.jsonl \
            --roc_curve roc
    
    AUC: 1.000
    
    TPR@FPR=0.1: 0.998
    TPR@FPR=0.01: 0.998
    
    F1@FPR=0.1: 0.999
    F1@FPR=0.01: 0.999
    ```

![img](./assets/curve.png)

## Đánh giá tính bền vững của thủy vân (tùy chọn)

> Sau khi tấn công paraphrase và translation lên văn bản có thủy vân, đánh giá lại hiệu quả phát hiện của nó

### 4.1 Chuẩn bị công việc

Chúng ta dùng mô hình gpt-3.5-turbo-1106 để thực hiện paraphrase và translation trên văn bản có thủy vân. Cũng có thể tự chọn công cụ khác.

- Thiết lập apikey của openai

  - ```Shell
    export OPENAI_API_KEY=xxxx
    ```

- Sửa RPM (requests per min) và TPM (tokens per min) trong `attack/const.py`

### 4.2 Thực hiện tấn công (lấy dịch làm ví dụ)

- Dịch văn bản có thủy vân sang tiếng Trung

  - ```Shell
    python3 attack/translate.py \
        --input_file gen/$MODEL_ABBR/kgw/mc4.en.mod.jsonl \
        --output_file gen/$MODEL_ABBR/kgw/mc4.en-zh.mod.jsonl \
        --model gpt-3.5-turbo-1106 \
        --src_lang en \
        --tgt_lang zh
    ```

- Đánh giá lại

  -  Xem [3.4](#eval)

- So sánh sự thay đổi hiệu năng thủy vân trước và sau khi tấn công



## Bài tập nâng cao

- Xem tài liệu [X-SIR](https://github.com/zwhe99/X-SIR), học cách sử dụng hai thuật toán còn lại (X-SIR, SIR), và đánh giá hiệu năng của chúng dưới các phương pháp tấn công khác nhau
