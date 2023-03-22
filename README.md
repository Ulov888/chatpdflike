# chatpdflike

虽然chatpdf.com的实现代码并不开源，但是基于作者的twitter回复还是大致理顺了功能原理，主要流程原理如下：

> 1 、文本切割

将文本切割成一小部分，调用 openai 的 embedding 接口，返回这段文本的 embedding 的向量数据。存储这些数据，并且保存好对应关系。

> 2 、用户提问

将用户提的问题，调用 openai 的 embedding 接口，返回问题的向量数据。

> 3 、搜索向量

计算相似度,用问题的向量，在之前切割的所有向量数据里，计算和问题向量相似度最高的几个文本(余弦定理)。

> 4 、调用 chatgpt

准备合适的 prompt ，里面带上切割的文本内容，加上问题的 prompt 。


基于以上的流程，只需要开发少量的适配代码，主要功能都是由openai的接口完成，

## 使用指南
1 .配置系统环境变量OPENAI_API_KEY

2. 运行
```
python run.py 
```
### Prerequisites 项目环境依赖


```
six~=1.16.0
rasa~=3.1.0
zlib~=1.2.12
tqdm~=4.64.0
```

### 安装
```
pip install -r requirements.txt
```
