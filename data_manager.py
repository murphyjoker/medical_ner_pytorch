import copy
import pickle as cPickle
import torch

class DataManager():
    def __init__(self, max_length=100, batch_size=20, data_type='train', tags=[]):
        self.index = 0
        self.input_size = 0
        self.batch_size = batch_size
        self.max_length = max_length
        self.data_type = data_type
        self.data = []
        self.batch_data = []
        self.vocab = {"unk": 0}
        self.tag_map = {"O":0, "START":1, "STOP":2}

        if data_type == "train":
            assert tags, Exception("请指定需要训练的tag类型，如[\"TREATMENT\", \"BODY\",\"SIGNS\",\"CHECK\",\"DISEASE\"]")
            self.generate_tags(tags)
            self.data_path = "data/train"
        elif data_type == "dev":
            self.data_path = "data/dev"
            self.load_data_map()
        elif data_type == "test":
            self.data_path = "data/test"
            self.load_data_map()

        self.load_data()
        self.prepare_batch()

    # 给要命名的实体加上B-,I-,E-,前缀标签
    def generate_tags(self, tags):
        self.tags = []
        for tag in tags:
            for prefix in ["B-", "I-", "E-", "S-"]:
                self.tags.append(prefix + tag)
        self.tags.append("O")

    def load_data_map(self):
        with open("models/data_6all.pkl", "rb") as f:
            self.data_map = cPickle.load(f)
            self.vocab = self.data_map.get("vocab", {})
            self.tag_map = self.data_map.get("tag_map", {})
            self.tags = self.data_map.keys()

    # 读取文件，将每个end前面的数据当成一个句子，并写入[sentence,target]中，target是对应标签的索引，
    # 将[sentence,target]这个当前self.data列表的一个元素
    def load_data(self):
        # load data
        # add vocab
        # covert to one-hot
        sentence = []
        target = []
        with open(self.data_path,encoding='gbk') as f:
            for line in f:
                line = line[:-1]
                if line == "end":
                    self.data.append([sentence, target]) # 构造data列表
                    sentence = []
                    target = []
                    continue
                try:
                    word, tag = line.split("\t") # 分割每一行数据，获取汉字和标签
                except Exception:
                    continue
                if word not in self.vocab and self.data_type == "train":
                    self.vocab[word] = max(self.vocab.values()) + 1 
                if tag not in self.tag_map and self.data_type == "train" and tag in self.tags:
                    self.tag_map[tag] = len(self.tag_map.keys())
                sentence.append(self.vocab.get(word, 0))  # 找到vocab字典中对应汉字的值，添加到sentence中
                target.append(self.tag_map.get(tag, 0))
        self.input_size = len(self.vocab.values())
        print("{} data: {}".format(self.data_type ,len(self.data)))
        print("vocab size: {}".format(self.input_size))
        print("unique tag: {}".format(len(self.tag_map.values())))
        print("-"*50)
    
    def convert_tag(self, data):
        # add E-XXX for tags
        # add O-XXX for tags
        _, tags = data
        converted_tags = []
        for _, tag in enumerate(tags[:-1]):
            if tag not in self.tag_map and self.data_type == "train":
                self.tag_map[tag] = len(self.tag_map.keys())
            converted_tags.append(self.tag_map.get(tag, 0))
        converted_tags.append(0)
        data[1] = converted_tags
        assert len(converted_tags) == len(tags), "convert error, the list dosen't match!"
        return data

    def prepare_batch(self):
        '''
            prepare data for batch
        '''
        index = 0
        while True:
            # 超过self.data中所有句子的数目时，循环终止
            if index+self.batch_size >= len(self.data):
                pad_data = self.pad_data(self.data[-self.batch_size:])
                self.batch_data.append(pad_data)
                break
            else:
                pad_data = self.pad_data(self.data[index:index+self.batch_size])
                index += self.batch_size
                self.batch_data.append(pad_data)
    # 将self.data数据分割成多份，每份batch_size个-默认20个 (list:20)
    def pad_data(self, data):
        # 拷贝这30份句子
        c_data = copy.deepcopy(data)
        # 找到这30个句子中最长的句子，并把他的长度赋值给max_length
        max_length = max([len(i[0]) for i in c_data])
        # 根据max_length长度补零
        for i in c_data:
            i.append(len(i[0])) # 将c_data第三个元素设置为句子的长度
            i[0] = i[0] + (max_length-len(i[0])) * [0]
            i[1] = i[1] + (max_length-len(i[1])) * [0]
            # i[0] = torch.tensor(i[0])
            # i[1] = torch.tensor(i[1])
        return c_data

    def iteration(self):
        idx = 0
        while True:
            yield self.batch_data[idx]
            idx += 1
            if idx > len(self.batch_data)-1:
                idx = 0

    def get_batch(self):
        for data in self.batch_data:
            yield data
